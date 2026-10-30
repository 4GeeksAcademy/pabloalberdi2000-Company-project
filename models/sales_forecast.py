"""
Sales Forecasting Model - Brasaland Digital

Modelo de regresión temporal para predecir ventas mensuales con evaluación rigurosa
y explicabilidad financiera.

Arquitectura:
- Partición temporal: 8 años entrenamiento, 2 años test (sin data leakage)
- Algoritmo: Random Forest Regressor (explicable, robusto)
- Métricas: MSE, RMSE, MAPE, R², PSI, Gini, K2
- Visualización: Predicción con intervalos de confianza

Uso:
    python models/sales_forecast.py

    # O con fecha de corte personalizada
    python models/sales_forecast.py --split-date 2022-01-01
"""

import argparse
import logging
import warnings
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

# Configuración
warnings.filterwarnings('ignore')
sns.set_style('whitegrid')
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "brasaland_sales.csv"
RESULTS_DIR = PROJECT_ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ============================================================
# UTILIDADES DE EVALUACIÓN
# ============================================================

def calculate_psi(expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
    """
    Calcula Population Stability Index (PSI) entre dos distribuciones.

    PSI mide el cambio distributivo entre train y test set.

    Args:
        expected: Distribución esperada (train set)
        actual: Distribución actual (test set)
        buckets: Número de bins para discretización

    Returns:
        PSI score:
            < 0.1: Sin cambio significativo
            0.1-0.25: Cambio moderado (monitorear)
            > 0.25: Cambio significativo (drift)

    Formula:
        PSI = Σ (actual_% - expected_%) * ln(actual_% / expected_%)
    """
    # Crear bins basados en expected
    breakpoints = np.percentile(expected, np.linspace(0, 100, buckets + 1))
    breakpoints = np.unique(breakpoints)  # Eliminar duplicados

    if len(breakpoints) < 2:
        logger.warning("Insuficientes breakpoints únicos para PSI, retornando 0")
        return 0.0

    # Discretizar ambas distribuciones
    expected_percents = np.histogram(expected, bins=breakpoints)[0] / len(expected)
    actual_percents = np.histogram(actual, bins=breakpoints)[0] / len(actual)

    # Agregar epsilon para evitar log(0)
    epsilon = 1e-10
    expected_percents = np.where(expected_percents == 0, epsilon, expected_percents)
    actual_percents = np.where(actual_percents == 0, epsilon, actual_percents)

    # Calcular PSI
    psi_values = (actual_percents - expected_percents) * np.log(actual_percents / expected_percents)
    psi = np.sum(psi_values)

    return psi


def calculate_gini(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calcula coeficiente de Gini normalizado.

    Gini mide la capacidad del modelo para discriminar entre valores altos y bajos.

    Args:
        y_true: Valores reales
        y_pred: Valores predichos

    Returns:
        Gini coefficient:
            0: Sin poder discriminativo
            0.4-0.6: Buen poder discriminativo
            > 0.6: Excelente poder discriminativo

    Formula:
        Gini = 2 * AUC - 1

    Interpretación financiera:
        Un Gini alto significa que el modelo puede distinguir bien entre
        meses de alta y baja venta, útil para planificación de recursos.
    """
    # Ordenar por predicción
    sorted_indices = np.argsort(y_pred)
    y_true_sorted = y_true[sorted_indices]

    # Calcular curva de Lorenz
    cumsum_true = np.cumsum(y_true_sorted)
    cumsum_true_normalized = cumsum_true / cumsum_true[-1]

    # Área bajo la curva (trapezoid rule)
    auc = np.trapz(cumsum_true_normalized, dx=1/len(y_true))

    # Gini = 2 * AUC - 1
    gini = 2 * auc - 1

    return gini


def calculate_k2_score(y_true: np.ndarray, y_pred: np.ndarray, n_features: int) -> float:
    """
    Calcula K2 score (similar a BIC).

    K2 penaliza la complejidad del modelo para evitar sobreajuste.

    Args:
        y_true: Valores reales
        y_pred: Valores predichos
        n_features: Número de features usadas

    Returns:
        K2 score (mayor es mejor)

    Formula:
        K2 = -n * ln(MSE) - k * ln(n)

    Interpretación:
        - Penaliza modelos con muchas features
        - Trade-off entre precisión y simplicidad
        - Útil para selección de modelo
    """
    n = len(y_true)
    mse = mean_squared_error(y_true, y_pred)

    # Evitar log(0)
    mse = max(mse, 1e-10)

    # K2 = log-likelihood - penalty
    k2 = -n * np.log(mse) - n_features * np.log(n)

    return k2


# ============================================================
# FEATURE ENGINEERING
# ============================================================

def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea features temporales y de lag para el modelo.

    Features creadas:
    - Temporales: year, month, quarter
    - Cíclicas: month_sin, month_cos (captura estacionalidad)
    - Lag: revenue_lag1, revenue_lag12 (valores pasados)
    - Rolling: revenue_ma3 (media móvil 3 meses)
    - Tendencia: trend (contador de meses)
    - Binarias: is_december, is_covid

    Args:
        df: DataFrame con columna 'date' y 'revenue_cop'

    Returns:
        DataFrame con features adicionales
    """
    df = df.copy()

    # Asegurar datetime
    df['date'] = pd.to_datetime(df['date'])

    # Features temporales básicas
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['quarter'] = df['date'].dt.quarter

    # Encoding cíclico para estacionalidad (captura patrón circular)
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)

    # Features de lag (valores pasados)
    df['revenue_lag1'] = df['revenue_cop'].shift(1)  # Mes anterior
    df['revenue_lag12'] = df['revenue_cop'].shift(12)  # Mismo mes año anterior

    # Media móvil (suaviza ruido)
    df['revenue_ma3'] = df['revenue_cop'].rolling(window=3).mean()

    # Tendencia lineal
    df['trend'] = range(len(df))

    # Features binarias de eventos
    df['is_december'] = (df['month'] == 12).astype(int)  # Pico navideño
    df['is_covid'] = ((df['date'] >= '2020-03-01') & (df['date'] <= '2020-05-31')).astype(int)

    # Crecimiento interanual (%)
    df['yoy_growth'] = ((df['revenue_cop'] - df['revenue_lag12']) / df['revenue_lag12']).fillna(0)

    return df


# ============================================================
# PARTICIÓN TEMPORAL
# ============================================================

def temporal_split(
    df: pd.DataFrame,
    split_date: str = '2022-01-01',
    target_col: str = 'revenue_cop'
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Divide dataset temporalmente SIN data leakage.

    CRÍTICO: Partición cronológica estricta. Train NO puede contener fechas futuras.

    Args:
        df: DataFrame con features y target
        split_date: Fecha de corte (YYYY-MM-DD)
        target_col: Nombre de columna objetivo

    Returns:
        X_train, X_test, y_train, y_test
    """
    # Ordenar por fecha (garantía de orden cronológico)
    df = df.sort_values('date').reset_index(drop=True)

    # Dividir por fecha
    train_mask = df['date'] < split_date
    test_mask = df['date'] >= split_date

    train_df = df[train_mask].copy()
    test_df = df[test_mask].copy()

    logger.info(f"📊 Train set: {train_df['date'].min()} a {train_df['date'].max()} ({len(train_df)} meses)")
    logger.info(f"📊 Test set:  {test_df['date'].min()} a {test_df['date'].max()} ({len(test_df)} meses)")

    # Validar no overlap
    assert train_df['date'].max() < test_df['date'].min(), "❌ ERROR: Overlap temporal detectado!"

    # Features (excluir date y target)
    feature_cols = [col for col in df.columns if col not in ['date', target_col]]

    X_train = train_df[feature_cols]
    X_test = test_df[feature_cols]
    y_train = train_df[target_col]
    y_test = test_df[target_col]

    # Eliminar filas con NaN (de lags)
    train_valid = ~X_train.isnull().any(axis=1)
    test_valid = ~X_test.isnull().any(axis=1)

    X_train = X_train[train_valid]
    y_train = y_train[train_valid]
    X_test = X_test[test_valid]
    y_test = y_test[test_valid]

    logger.info(f"✅ Tras limpieza NaN: Train={len(X_train)}, Test={len(X_test)}")

    return X_train, X_test, y_train, y_test


# ============================================================
# ENTRENAMIENTO Y EVALUACIÓN
# ============================================================

def train_model(X_train: pd.DataFrame, y_train: pd.Series) -> RandomForestRegressor:
    """
    Entrena modelo Random Forest Regressor.

    Razón de elección: Random Forest vs XGBoost

    Random Forest elegido porque:
    1. Dataset pequeño (130 meses) → RF suficiente
    2. Interpretabilidad (feature importance) → stakeholder financiero
    3. Robusto a outliers (COVID-19)
    4. Tiempo de entrenamiento <1 min → no crítico

    XGBoost sería mejor si:
    - Dataset > 10K filas
    - Necesidad de máxima precisión (competencia Kaggle)
    - Menos preocupación por interpretabilidad

    Args:
        X_train: Features de entrenamiento
        y_train: Target de entrenamiento

    Returns:
        Modelo entrenado
    """
    logger.info("🌳 Entrenando Random Forest Regressor...")

    model = RandomForestRegressor(
        n_estimators=100,        # 100 árboles (balance speed/accuracy)
        max_depth=10,            # Profundidad máxima (evitar overfit)
        min_samples_split=5,     # Mínimo 5 muestras para split
        min_samples_leaf=2,      # Mínimo 2 muestras en hoja
        random_state=42,         # Reproducibilidad
        n_jobs=-1,               # Usar todos los CPUs
        verbose=0
    )

    model.fit(X_train, y_train)

    logger.info(f"✅ Modelo entrenado con {len(X_train.columns)} features")

    return model


def evaluate_model(
    model: RandomForestRegressor,
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    y_train: pd.Series,
    y_test: pd.Series
) -> Dict[str, float]:
    """
    Evalúa modelo con múltiples métricas financieras.

    Métricas calculadas:
    - MSE: Error cuadrático medio
    - RMSE: Raíz del MSE (misma unidad que target)
    - MAPE: Error porcentual absoluto (%)
    - R²: Varianza explicada (0-1)
    - PSI: Estabilidad distribucional (drift)
    - Gini: Poder discriminativo
    - K2: Penalización por complejidad

    Args:
        model: Modelo entrenado
        X_train, X_test: Features
        y_train, y_test: Targets

    Returns:
        Diccionario con todas las métricas
    """
    logger.info("📈 Evaluando modelo...")

    # Predicciones
    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    # Métricas básicas
    mse = mean_squared_error(y_test, y_test_pred)
    rmse = np.sqrt(mse)
    mape = mean_absolute_percentage_error(y_test, y_test_pred) * 100  # En %
    r2 = r2_score(y_test, y_test_pred)

    # Métricas avanzadas
    psi = calculate_psi(y_train.values, y_test.values, buckets=10)
    gini = calculate_gini(y_test.values, y_test_pred)
    k2 = calculate_k2_score(y_test.values, y_test_pred, n_features=X_train.shape[1])

    metrics = {
        'MSE': mse,
        'RMSE': rmse,
        'MAPE': mape,
        'R2': r2,
        'PSI': psi,
        'Gini': gini,
        'K2': k2
    }

    # Log resultados
    logger.info("\n" + "="*60)
    logger.info("📊 RESULTADOS DE EVALUACIÓN")
    logger.info("="*60)
    logger.info(f"MSE (Mean Squared Error):        {mse:,.0f} COP²")
    logger.info(f"RMSE (Root MSE):                 {rmse:,.0f} COP")
    logger.info(f"MAPE (Mean Absolute % Error):    {mape:.2f}%")
    logger.info(f"R² (Variance Explained):         {r2:.4f}")
    logger.info(f"PSI (Population Stability):      {psi:.4f}")
    logger.info(f"Gini (Discriminative Power):     {gini:.4f}")
    logger.info(f"K2 (Model Quality Score):        {k2:.2f}")
    logger.info("="*60 + "\n")

    # Interpretación para Finanzas
    logger.info("💼 INTERPRETACIÓN FINANCIERA:")
    logger.info(f"- Error promedio: ±{rmse/1e6:.1f}M COP (~{mape:.1f}% del valor real)")

    if psi < 0.1:
        logger.info(f"- Distribución estable (PSI={psi:.3f} < 0.1): ✅ Modelo aplicable a futuro")
    elif psi < 0.25:
        logger.info(f"- Cambio moderado (PSI={psi:.3f}): ⚠️ Monitorear drift")
    else:
        logger.info(f"- Cambio significativo (PSI={psi:.3f} > 0.25): ❌ Posible drift, reentrenar")

    if gini > 0.4:
        logger.info(f"- Buen poder discriminativo (Gini={gini:.3f}): ✅ Distingue meses altos/bajos")
    else:
        logger.info(f"- Poder discriminativo bajo (Gini={gini:.3f}): ⚠️ Predicciones poco diferenciadas")

    if r2 > 0.75:
        logger.info(f"- Alta varianza explicada (R²={r2:.3f}): ✅ Modelo captura tendencia")
    else:
        logger.info(f"- Baja varianza explicada (R²={r2:.3f}): ⚠️ Factores externos importantes")

    return metrics


def get_prediction_intervals(
    model: RandomForestRegressor,
    X: pd.DataFrame,
    percentile: float = 95
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Calcula intervalos de confianza usando árboles del Random Forest.

    Random Forest permite calcular intervalos aprovechando la variabilidad
    entre árboles individuales.

    Args:
        model: Random Forest entrenado
        X: Features para predicción
        percentile: Percentil para intervalo (95 = intervalo 95%)

    Returns:
        (predicciones, límite_inferior, límite_superior)
    """
    # Predicción de cada árbol individual
    all_predictions = np.array([tree.predict(X) for tree in model.estimators_])

    # Predicción promedio
    y_pred = all_predictions.mean(axis=0)

    # Percentiles para intervalo
    lower_percentile = (100 - percentile) / 2
    upper_percentile = 100 - lower_percentile

    y_lower = np.percentile(all_predictions, lower_percentile, axis=0)
    y_upper = np.percentile(all_predictions, upper_percentile, axis=0)

    return y_pred, y_lower, y_upper


# ============================================================
# VISUALIZACIÓN
# ============================================================

def plot_forecast(
    dates_test: pd.Series,
    y_test: np.ndarray,
    y_pred: np.ndarray,
    y_lower: np.ndarray,
    y_upper: np.ndarray,
    save_path: Path
) -> None:
    """
    Genera gráfico de predicción con intervalos de confianza.

    Visualización requerida:
    1. Línea de valores reales (azul)
    2. Línea de predicción (rojo)
    3. Banda de variabilidad (gris sombreado)

    Args:
        dates_test: Fechas del test set
        y_test: Valores reales
        y_pred: Predicciones
        y_lower: Límite inferior intervalo 95%
        y_upper: Límite superior intervalo 95%
        save_path: Ruta para guardar gráfico
    """
    fig, ax = plt.subplots(figsize=(14, 7))

    # Valores reales
    ax.plot(dates_test, y_test, 'o-', color='#2E86AB', linewidth=2,
            label='Ventas Reales', markersize=6)

    # Predicciones
    ax.plot(dates_test, y_pred, 's-', color='#A23B72', linewidth=2,
            label='Predicción Modelo', markersize=6)

    # Banda de variabilidad (intervalo 95%)
    ax.fill_between(dates_test, y_lower, y_upper,
                     alpha=0.3, color='#F18F01',
                     label='Intervalo Confianza 95%')

    # Formateo
    ax.set_xlabel('Fecha', fontsize=12, fontweight='bold')
    ax.set_ylabel('Ingresos (COP)', fontsize=12, fontweight='bold')
    ax.set_title('Predicción de Ventas Mensuales - Brasaland\n(Test Set: 2022-2024)',
                 fontsize=14, fontweight='bold', pad=20)

    # Formato de eje Y (millones)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x/1e6:.0f}M'))

    # Grid
    ax.grid(True, alpha=0.3, linestyle='--')

    # Leyenda
    ax.legend(loc='upper left', fontsize=11, framealpha=0.95)

    # Rotar fechas
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    logger.info(f"📊 Gráfico guardado en: {save_path}")
    plt.close()


def plot_feature_importance(
    model: RandomForestRegressor,
    feature_names: list,
    save_path: Path,
    top_n: int = 10
) -> None:
    """
    Visualiza importancia de features (explicabilidad).

    Feature importance ayuda a stakeholders financieros a entender
    qué factores impulsan las predicciones.

    Args:
        model: Modelo entrenado
        feature_names: Nombres de features
        save_path: Ruta para guardar gráfico
        top_n: Número de features a mostrar
    """
    importances = model.feature_importances_
    indices = np.argsort(importances)[::-1][:top_n]

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.barh(range(top_n), importances[indices], color='#2E86AB')
    ax.set_yticks(range(top_n))
    ax.set_yticklabels([feature_names[i] for i in indices])
    ax.set_xlabel('Importancia', fontsize=12, fontweight='bold')
    ax.set_title(f'Top {top_n} Features Más Importantes', fontsize=14, fontweight='bold', pad=20)
    ax.invert_yaxis()

    plt.tight_layout()
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    logger.info(f"📊 Feature importance guardado en: {save_path}")
    plt.close()


# ============================================================
# MAIN
# ============================================================

def main(split_date: str = '2022-01-01'):
    """
    Pipeline completo de entrenamiento y evaluación.

    Args:
        split_date: Fecha de corte para train/test split
    """
    logger.info("🚀 Iniciando pipeline de forecasting...")

    # 1. Cargar datos
    logger.info(f"📂 Cargando datos desde: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH, parse_dates=['date'])
    logger.info(f"✅ Cargados {len(df)} registros ({df['date'].min()} a {df['date'].max()})")

    # 2. Feature engineering
    logger.info("🔧 Creando features...")
    df = create_features(df)

    # 3. Partición temporal
    X_train, X_test, y_train, y_test = temporal_split(df, split_date=split_date)

    # Guardar fechas de test para gráfico
    dates_test = df[df['date'] >= split_date]['date'].iloc[-len(y_test):]

    # 4. Entrenar modelo
    model = train_model(X_train, y_train)

    # 5. Evaluar
    metrics = evaluate_model(model, X_train, X_test, y_train, y_test)

    # 6. Intervalos de confianza
    logger.info("📊 Calculando intervalos de confianza...")
    y_pred, y_lower, y_upper = get_prediction_intervals(model, X_test, percentile=95)

    # 7. Visualizaciones
    logger.info("📈 Generando visualizaciones...")

    plot_forecast(
        dates_test=dates_test,
        y_test=y_test.values,
        y_pred=y_pred,
        y_lower=y_lower,
        y_upper=y_upper,
        save_path=RESULTS_DIR / 'sales_forecast_plot.png'
    )

    plot_feature_importance(
        model=model,
        feature_names=X_train.columns.tolist(),
        save_path=RESULTS_DIR / 'feature_importance.png',
        top_n=10
    )

    # 8. Guardar métricas
    metrics_df = pd.DataFrame([metrics])
    metrics_df.to_csv(RESULTS_DIR / 'forecast_metrics.csv', index=False)
    logger.info(f"💾 Métricas guardadas en: {RESULTS_DIR / 'forecast_metrics.csv'}")

    logger.info("\n✅ Pipeline completado exitosamente!")

    return model, metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Brasaland Sales Forecasting')
    parser.add_argument('--split-date', type=str, default='2022-01-01',
                        help='Fecha de corte para train/test (YYYY-MM-DD)')
    args = parser.parse_args()

    main(split_date=args.split_date)
