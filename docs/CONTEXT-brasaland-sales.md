# 📊 Contexto de Datos: Brasaland Sales Forecast

## Información de la Empresa

**Nombre**: Brasaland  
**Industria**: Restaurantes (Cocina a la Brasa)  
**Fundación**: 2008  
**Ubicaciones**: 14 restaurantes (10 en Colombia, 4 en Estados Unidos - Florida)  
**Empleados**: 115 personas  
**Facturación Anual**: ~$6M USD  
**CEO**: Mariana Restrepo  

---

## Dataset: `brasaland_sales.csv`

### Ubicación
```
data/raw/brasaland_sales.csv
```

### Descripción
Datos históricos de ventas mensuales consolidados de Brasaland desde 2014 hasta 2024 (10 años). Los datos incluyen ingresos en COP y USD, número de órdenes y desagregación por local.

### Schema de Columnas

| Columna | Tipo | Descripción | Ejemplo | Unidad |
|---------|------|-------------|---------|--------|
| `date` | DATE | Fecha del mes (primer día) | `2014-01-01` | YYYY-MM-DD |
| `revenue_cop` | NUMERIC | Ingresos en pesos colombianos | `12500000` | COP |
| `revenue_usd` | NUMERIC | Ingresos en dólares estadounidenses | `6250` | USD |
| `orders` | INTEGER | Número de órdenes completadas | `145` | count |
| `location_id` | INTEGER | ID del restaurante | `1` | id |
| `location_name` | VARCHAR | Nombre del local | `Medellín Centro` | text |
| `country` | VARCHAR | País del local | `Colombia` | text |

### Magnitudes Típicas

- **Revenue COP**: 8M - 47M COP/mes
- **Revenue USD**: 4K - 23K USD/mes
- **Orders**: 97 - 539 órdenes/mes
- **Tasa de Cambio**: ~2,000 COP/USD (promedio histórico)

### Período Temporal

- **Inicio**: Enero 2014
- **Fin**: Octubre 2024
- **Total**: 130 meses (10 años + 10 meses)

**Partición Temporal para Modelado**:
- **Training Set**: Enero 2014 - Diciembre 2021 (8 años = 96 meses)
- **Test Set**: Enero 2022 - Octubre 2024 (2 años + 10 meses = 34 meses)

---

## Características del Negocio

### Estacionalidad

**Picos de Demanda**:
- Diciembre: +20-30% (fiestas navideñas)
- Julio: +15% (vacaciones escolares Colombia)
- Enero: -15% (post-navidad, dieta)

### Tendencia

- Crecimiento anual promedio: +10-15%
- Apertura de nuevos locales (2014-2019)
- Impacto COVID-19: Marzo-Mayo 2020 (-50% caída)
- Recuperación post-COVID: Junio 2020 - Diciembre 2021

### Eventos Externos

- **2020 Q1-Q2**: Pandemia COVID-19 (lockdowns)
- **2019**: Expansión a Estados Unidos (Miami)
- **2017**: Apertura de 3 locales nuevos en Colombia

---

## Variables Objetivo para Predicción

### Variable Target Principal
**`revenue_cop`**: Ingresos totales mensuales en pesos colombianos.

**Razón de Elección**:
- Moneda local de operación principal (10 de 14 locales)
- Mayor estabilidad que USD (menor volatilidad cambiaria)
- Métricas financieras internas reportadas en COP

### Variables Alternativas
- `revenue_usd`: Para análisis de mercado estadounidense
- `orders`: Para optimización operativa (staffing, inventario)

---

## Feature Engineering Propuesto

### Features Temporales
```python
# Extraer componentes de fecha
df['year'] = df['date'].dt.year
df['month'] = df['date'].dt.month
df['quarter'] = df['date'].dt.quarter

# Encoding cíclico para estacionalidad
df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
```

### Features de Lag (Valores Pasados)
```python
# Ventas del mes anterior
df['revenue_lag1'] = df['revenue_cop'].shift(1)

# Ventas de hace 12 meses (mismo mes año anterior)
df['revenue_lag12'] = df['revenue_cop'].shift(12)

# Media móvil 3 meses
df['revenue_ma3'] = df['revenue_cop'].rolling(window=3).mean()
```

### Features de Tendencia
```python
# Tendencia lineal (contador de meses desde inicio)
df['trend'] = range(len(df))

# Crecimiento interanual
df['yoy_growth'] = (df['revenue_cop'] - df['revenue_lag12']) / df['revenue_lag12']
```

### Features Binarias de Eventos
```python
# Indicador de mes de diciembre (pico estacional)
df['is_december'] = (df['month'] == 12).astype(int)

# Indicador de período COVID (marzo-mayo 2020)
df['is_covid'] = ((df['date'] >= '2020-03-01') & (df['date'] <= '2020-05-31')).astype(int)
```

---

## Métricas de Evaluación

### 1. MSE (Mean Squared Error)
**Definición**: Promedio de errores al cuadrado.

$$MSE = \frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y}_i)^2$$

**Interpretación**:
- Unidad: COP² (penaliza errores grandes)
- Menor es mejor
- Sensible a outliers

**Umbral Aceptable**: MSE < 50,000,000,000 COP² (~error de ±7M COP)

---

### 2. RMSE (Root Mean Squared Error)
**Definición**: Raíz cuadrada del MSE.

$$RMSE = \sqrt{MSE}$$

**Interpretación**:
- Unidad: COP (misma que target)
- Error promedio en términos de ingresos
- Más interpretable que MSE

**Umbral Aceptable**: RMSE < 7,000,000 COP (~20% de ingreso promedio)

---

### 3. MAPE (Mean Absolute Percentage Error)
**Definición**: Error porcentual absoluto promedio.

$$MAPE = \frac{100\%}{n}\sum_{i=1}^{n}\left|\frac{y_i - \hat{y}_i}{y_i}\right|$$

**Interpretación**:
- Unidad: Porcentaje
- Escala independiente
- Fácil comunicación a stakeholders

**Umbral Aceptable**: MAPE < 15%

---

### 4. R² (Coefficient of Determination)
**Definición**: Proporción de varianza explicada.

$$R^2 = 1 - \frac{\sum(y_i - \hat{y}_i)^2}{\sum(y_i - \bar{y})^2}$$

**Interpretación**:
- Rango: 0 a 1 (mayor es mejor)
- R² = 0.8 significa "explica 80% de varianza"

**Umbral Aceptable**: R² > 0.75

---

### 5. PSI (Population Stability Index)
**Definición**: Medida de estabilidad distribucional.

$$PSI = \sum_{i=1}^{n}(A_i - E_i) \cdot \ln\left(\frac{A_i}{E_i}\right)$$

Donde:
- $A_i$: Proporción actual (test set)
- $E_i$: Proporción esperada (train set)

**Interpretación**:
- PSI < 0.1: Sin cambio significativo
- 0.1 < PSI < 0.25: Cambio moderado
- PSI > 0.25: Cambio significativo (drift)

**Uso**: Detectar data drift entre periodos de entrenamiento y test.

---

### 6. Gini Coefficient (Normalizado)
**Definición**: Medida de capacidad discriminativa.

$$Gini = 2 \cdot AUC - 1$$

**Interpretación**:
- Rango: -1 a 1
- Gini > 0.4: Buen poder predictivo

**Uso**: Evaluar si el modelo puede discriminar entre meses de alta y baja venta.

---

### 7. K2 Score (AIC/BIC adaptado)
**Definición**: Penalización por complejidad del modelo.

$$K2 = \text{LogLikelihood} - k \cdot \log(n)$$

Donde:
- $k$: Número de features
- $n$: Número de observaciones

**Interpretación**:
- Mayor es mejor
- Penaliza modelos sobre-complejos

**Uso**: Selección de modelo (trade-off explicabilidad vs precisión).

---

## Consideraciones Financieras

### Por Qué MSE Bajo NO Es Suficiente

1. **Magnitud del Error**:
   - MSE = 10,000,000,000 COP²
   - RMSE = 100,000 COP (~0.3% del ingreso promedio)
   - **Aparentemente bueno**, pero...

2. **Sesgo Sistemático**:
   - Modelo puede subestimar consistentemente picos de diciembre
   - MSE bajo promedio, pero falla en momentos críticos

3. **Estabilidad Temporal (PSI)**:
   - Si PSI > 0.25, modelo entrenado en 2014-2021 no aplica a 2022-2024
   - Drift de población (nuevos locales, pandemia, cambios de mercado)

4. **Capacidad Discriminativa (Gini)**:
   - Predecir "siempre 35M COP" da MSE bajo
   - Pero Gini = 0 (no discrimina entre meses buenos y malos)
   - Inútil para planificación financiera

5. **Incertidumbre (Intervalos de Confianza)**:
   - Predicción puntual: 35M COP
   - Intervalo 95%: [28M, 42M COP]
   - **Rango de ±7M es demasiado amplio para presupuesto**

### Mensaje a Finanzas

> **"Un modelo con MSE bajo puede ser técnicamente preciso en promedio, pero si no captura picos estacionales, subestima incertidumbre, o sufre drift temporal, es inútil para planificación financiera real. Necesitamos evaluar MSE + PSI + Gini + intervalos de confianza para determinar viabilidad."**

---

## Recomendaciones Técnicas

### Algoritmos Candidatos

#### 1. Random Forest Regressor
**Pros**:
- Interpretable (feature importance)
- Robusto a outliers
- No requiere escalado de features

**Contras**:
- Entrenamiento lento (>100 árboles)
- Mayor uso de memoria

**Cuándo Usar**: Dataset pequeño (<10K filas), necesidad de explicabilidad.

---

#### 2. XGBoost Regressor
**Pros**:
- Mayor precisión (boosting)
- Entrenamiento rápido (paralelización)
- Manejo nativo de missing values

**Contras**:
- Menos interpretable
- Hiperparámetros sensibles

**Cuándo Usar**: Dataset grande (>10K filas), máxima precisión.

---

### Decisión para Brasaland

**Dataset Actual**:
- 130 observaciones (10 años mensuales)
- Features: ~15 (temporales + lags + binarias)

**Recomendación**: **Random Forest**

**Razones**:
1. Dataset pequeño (130 filas) → RF suficiente
2. Stakeholder financiero → necesita feature importance
3. Tiempo de entrenamiento <1 min → no crítico
4. Robustez a outliers (COVID-19)

**Configuración Sugerida**:
```python
RandomForestRegressor(
    n_estimators=100,
    max_depth=10,
    min_samples_split=5,
    random_state=42,
    n_jobs=-1
)
```

---

## Validación de No Data Leakage

### Checklist de Validación

- [ ] Train set: Enero 2014 - Diciembre 2021 (96 meses)
- [ ] Test set: Enero 2022 - Octubre 2024 (34 meses)
- [ ] Train set NO contiene fechas ≥ 2022-01-01
- [ ] Test set NO contiene fechas < 2022-01-01
- [ ] Scaler fit SOLO en train set
- [ ] Features de lag calculadas sin usar future data
- [ ] NO se usa `df.sort_values()` con shuffle

### Test Unitario
```python
def test_no_temporal_overlap():
    assert train_df['date'].max() < test_df['date'].min()
    assert len(set(train_df['date']) & set(test_df['date'])) == 0
```

---

## Entregables Esperados

1. ✅ `brasaland_sales.csv` - Dataset
2. ✅ `CONTEXT-brasaland-sales.md` - Documentación
3. 📝 `models/sales_forecast.py` - Script de entrenamiento
4. 📝 `tests/pipelines/test_sales_split.py` - Validación de split
5. 📝 `docs/SALES_FORECAST_REPORT.md` - Reporte ejecutivo
6. 📊 `results/sales_forecast_plot.png` - Visualización con intervalos

---

**Preparado por**: Brasaland Digital - Data Science Team  
**Fecha**: 30 de Octubre, 2026  
**Versión**: 1.0
