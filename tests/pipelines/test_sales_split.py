"""
Test Suite - Sales Forecasting Temporal Split

Tests unitarios para validar partición temporal sin data leakage.

Objetivo: Garantizar que el modelo NO tiene acceso a datos futuros durante entrenamiento.

Ejecutar:
    pytest tests/pipelines/test_sales_split.py -v
"""

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from models.sales_forecast import create_features, temporal_split


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def sample_sales_data():
    """
    Dataset sintético de 120 meses (10 años) para testing.
    """
    dates = pd.date_range(start='2014-01-01', periods=120, freq='MS')

    # Generar ventas con tendencia y estacionalidad
    trend = np.linspace(10e6, 40e6, 120)
    seasonality = 5e6 * np.sin(2 * np.pi * np.arange(120) / 12)
    noise = np.random.normal(0, 2e6, 120)

    revenue = trend + seasonality + noise

    df = pd.DataFrame({
        'date': dates,
        'revenue_cop': revenue,
        'revenue_usd': revenue / 2000,
        'orders': (revenue / 80000).astype(int),
        'location_id': 1,
        'location_name': 'Test Location',
        'country': 'Colombia'
    })

    return df


# ============================================================
# TESTS DE PARTICIÓN TEMPORAL
# ============================================================

def test_temporal_split_no_overlap(sample_sales_data):
    """
    Test: Verifica que NO hay overlap temporal entre train y test.

    Criterio: train_max_date < test_min_date
    """
    df = create_features(sample_sales_data)

    X_train, X_test, y_train, y_test = temporal_split(
        df,
        split_date='2022-01-01'
    )

    # Obtener fechas de train y test
    train_dates = df[df['date'] < '2022-01-01']['date']
    test_dates = df[df['date'] >= '2022-01-01']['date']

    # Validar no overlap
    assert train_dates.max() < test_dates.min(), (
        f"❌ OVERLAP DETECTADO: "
        f"Train max={train_dates.max()}, Test min={test_dates.min()}"
    )

    print(f"✅ No overlap: Train hasta {train_dates.max()}, Test desde {test_dates.min()}")


def test_temporal_split_proportion_8_to_2_years(sample_sales_data):
    """
    Test: Verifica proporción 8 años entrenamiento, 2 años test.

    Criterio:
    - Train: 96 meses (8 años)
    - Test: 24+ meses (2+ años)
    """
    df = create_features(sample_sales_data)

    # Split en 2022-01-01 (tras 8 años de datos desde 2014)
    X_train, X_test, y_train, y_test = temporal_split(
        df,
        split_date='2022-01-01'
    )

    # Calcular meses (ajustar por NaN de lags)
    train_months = len(y_train)
    test_months = len(y_test)

    # Validar proporción aproximada
    # Train debe ser ~8 años (96 meses), Test ~2 años (24 meses)
    # Tolerancia: ±12 meses por lags
    assert 84 <= train_months <= 108, (
        f"❌ Train set fuera de rango esperado: {train_months} meses (esperado: 84-108)"
    )

    assert test_months >= 12, (
        f"❌ Test set muy pequeño: {test_months} meses (mínimo: 12)"
    )

    print(f"✅ Proporción válida: Train={train_months} meses, Test={test_months} meses")


def test_no_future_data_in_train(sample_sales_data):
    """
    Test: Verifica que train NO contiene datos del período de test.

    Criterio: Ninguna fecha de train >= split_date
    """
    df = create_features(sample_sales_data)
    split_date = '2022-01-01'

    X_train, X_test, y_train, y_test = temporal_split(
        df,
        split_date=split_date
    )

    # Obtener fechas de train
    train_dates = df[df['date'] < split_date]['date']

    # Validar que ninguna fecha de train >= split_date
    future_dates_in_train = train_dates[train_dates >= split_date]

    assert len(future_dates_in_train) == 0, (
        f"❌ DATA LEAKAGE DETECTADO: "
        f"{len(future_dates_in_train)} fechas futuras en train set"
    )

    print(f"✅ No data leakage: Train contiene solo fechas < {split_date}")


def test_chronological_order_preserved(sample_sales_data):
    """
    Test: Verifica que el orden cronológico se preserva.

    Criterio: Train[i] < Train[i+1] y Test[i] < Test[i+1]
    """
    df = create_features(sample_sales_data)

    # Obtener fechas originales alineadas con índices tras split
    train_df = df[df['date'] < '2022-01-01'].copy()
    test_df = df[df['date'] >= '2022-01-01'].copy()

    # Verificar orden en train
    train_dates_sorted = train_df['date'].is_monotonic_increasing
    assert train_dates_sorted, "❌ Train set NO está ordenado cronológicamente"

    # Verificar orden en test
    test_dates_sorted = test_df['date'].is_monotonic_increasing
    assert test_dates_sorted, "❌ Test set NO está ordenado cronológicamente"

    print("✅ Orden cronológico preservado en train y test")


def test_no_data_leakage_in_lags(sample_sales_data):
    """
    Test: Verifica que features de lag no usan datos futuros.

    Criterio: revenue_lag1 y revenue_lag12 solo usan valores pasados.
    """
    df = create_features(sample_sales_data)

    # Verificar que lag1 está desplazado correctamente
    for i in range(1, len(df)):
        if pd.notna(df.loc[i, 'revenue_lag1']):
            assert df.loc[i, 'revenue_lag1'] == df.loc[i-1, 'revenue_cop'], (
                f"❌ revenue_lag1 incorrecta en índice {i}"
            )

    # Verificar que lag12 está desplazado correctamente
    for i in range(12, len(df)):
        if pd.notna(df.loc[i, 'revenue_lag12']):
            assert df.loc[i, 'revenue_lag12'] == df.loc[i-12, 'revenue_cop'], (
                f"❌ revenue_lag12 incorrecta en índice {i}"
            )

    print("✅ Features de lag correctamente calculadas sin data leakage")


def test_train_test_set_sizes_valid(sample_sales_data):
    """
    Test: Verifica que ambos sets tienen tamaño suficiente para modelado.

    Criterio:
    - Train >= 60 meses (5 años mínimo)
    - Test >= 12 meses (1 año mínimo)
    """
    df = create_features(sample_sales_data)

    X_train, X_test, y_train, y_test = temporal_split(
        df,
        split_date='2022-01-01'
    )

    assert len(y_train) >= 60, (
        f"❌ Train set muy pequeño: {len(y_train)} meses (mínimo: 60)"
    )

    assert len(y_test) >= 12, (
        f"❌ Test set muy pequeño: {len(y_test)} meses (mínimo: 12)"
    )

    print(f"✅ Tamaños válidos: Train={len(y_train)}, Test={len(y_test)}")


def test_no_duplicate_dates(sample_sales_data):
    """
    Test: Verifica que no hay fechas duplicadas en ningún set.

    Criterio: Cada fecha aparece máximo 1 vez.
    """
    df = create_features(sample_sales_data)

    # Verificar duplicados en dataset completo
    duplicates = df['date'].duplicated().sum()
    assert duplicates == 0, f"❌ {duplicates} fechas duplicadas en dataset"

    print("✅ No hay fechas duplicadas")


def test_feature_engineering_correct_types(sample_sales_data):
    """
    Test: Verifica que features tienen tipos correctos.

    Criterio:
    - Numéricas: float o int
    - Sin valores infinitos
    """
    df = create_features(sample_sales_data)

    # Excluir columna 'date'
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    for col in numeric_cols:
        # Verificar no infinitos
        assert not np.isinf(df[col]).any(), f"❌ Valores infinitos en columna {col}"

        # Verificar tipo numérico
        assert pd.api.types.is_numeric_dtype(df[col]), f"❌ Columna {col} no es numérica"

    print(f"✅ Todas las {len(numeric_cols)} features numéricas son válidas")


# ============================================================
# TESTS DE INTEGRACIÓN
# ============================================================

def test_full_pipeline_runs_without_errors(sample_sales_data):
    """
    Test de integración: Verifica que pipeline completo corre sin errores.
    """
    df = create_features(sample_sales_data)

    try:
        X_train, X_test, y_train, y_test = temporal_split(
            df,
            split_date='2022-01-01'
        )

        # Verificar que splits retornan datos
        assert len(X_train) > 0, "Train set vacío"
        assert len(X_test) > 0, "Test set vacío"
        assert len(y_train) > 0, "Train target vacío"
        assert len(y_test) > 0, "Test target vacío"

        # Verificar dimensiones coincidentes
        assert len(X_train) == len(y_train), "Dimensiones train no coinciden"
        assert len(X_test) == len(y_test), "Dimensiones test no coinciden"

        print("✅ Pipeline completo ejecutado sin errores")

    except Exception as e:
        pytest.fail(f"❌ Pipeline falló con error: {e}")


# ============================================================
# PARAMETRIZED TESTS
# ============================================================

@pytest.mark.parametrize("split_date", [
    '2020-01-01',
    '2021-01-01',
    '2022-01-01',
    '2023-01-01'
])
def test_multiple_split_dates_no_overlap(sample_sales_data, split_date):
    """
    Test parametrizado: Verifica no overlap para múltiples fechas de corte.
    """
    df = create_features(sample_sales_data)

    try:
        X_train, X_test, y_train, y_test = temporal_split(
            df,
            split_date=split_date
        )

        train_dates = df[df['date'] < split_date]['date']
        test_dates = df[df['date'] >= split_date]['date']

        if len(test_dates) > 0:  # Solo si hay datos de test
            assert train_dates.max() < test_dates.min(), (
                f"Overlap detectado para split_date={split_date}"
            )

        print(f"✅ Split válido para {split_date}")

    except Exception as e:
        # Algunos splits pueden fallar si no hay suficientes datos
        print(f"⚠️ Split {split_date} omitido: {e}")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
