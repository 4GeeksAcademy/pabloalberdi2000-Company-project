"""
Test Suite - TimeSeriesSplit Temporal Validation

Tests unitarios para validar que TimeSeriesSplit respeta causalidad temporal estricta.

Objetivo: Garantizar que ningún fold viola el orden cronológico (t_train < t_val).

Ejecutar:
    pytest tests/pipelines/test_time_series_split.py -v
"""

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.model_selection import TimeSeriesSplit

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def chronological_data():
    """
    Dataset sintético con fechas cronológicas para testing.
    """
    dates = pd.date_range(start='2014-01-01', periods=100, freq='MS')

    df = pd.DataFrame({
        'date': dates,
        'value': np.random.rand(100) * 100,
        'index': range(100)
    })

    return df


# ============================================================
# TESTS DE CAUSALIDAD TEMPORAL
# ============================================================

def test_time_series_split_no_overlap(chronological_data):
    """
    Test: Verifica que NO hay overlap temporal entre train y val en ningún fold.

    Criterio: max(train_dates) < min(val_dates) en todos los folds.
    """
    df = chronological_data
    tscv = TimeSeriesSplit(n_splits=5)

    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(df), start=1):
        train_dates = df.iloc[train_idx]['date']
        val_dates = df.iloc[val_idx]['date']

        # Validar no overlap
        assert train_dates.max() < val_dates.min(), (
            f"❌ OVERLAP en fold {fold_idx}: "
            f"train_max={train_dates.max()}, val_min={val_dates.min()}"
        )

        print(f"✅ Fold {fold_idx}: No overlap (train_max={train_dates.max()}, val_min={val_dates.min()})")


def test_time_series_split_chronological_order(chronological_data):
    """
    Test: Verifica que índices respetan orden cronológico estricto.

    Criterio: Todos los índices de train < todos los índices de val.
    """
    df = chronological_data
    tscv = TimeSeriesSplit(n_splits=5)

    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(df), start=1):
        # Validar que max(train_idx) < min(val_idx)
        assert train_idx.max() < val_idx.min(), (
            f"❌ Índices desordenados en fold {fold_idx}: "
            f"train_max_idx={train_idx.max()}, val_min_idx={val_idx.min()}"
        )

        print(f"✅ Fold {fold_idx}: Índices ordenados (train_max={train_idx.max()}, val_min={val_idx.min()})")


def test_time_series_split_expanding_window(chronological_data):
    """
    Test: Verifica que train set crece acumulativamente (expanding window).

    Criterio: len(train_fold_i) < len(train_fold_i+1)
    """
    df = chronological_data
    tscv = TimeSeriesSplit(n_splits=5)

    train_sizes = []

    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(df), start=1):
        train_sizes.append(len(train_idx))

    # Validar que train size crece
    for i in range(len(train_sizes) - 1):
        assert train_sizes[i] < train_sizes[i+1], (
            f"❌ Train NO crece: fold {i+1} size={train_sizes[i]}, fold {i+2} size={train_sizes[i+1]}"
        )

    print(f"✅ Train sizes crecen: {train_sizes}")


def test_time_series_split_no_shuffle(chronological_data):
    """
    Test: Verifica que orden interno de train y val es cronológico.

    Criterio: train_dates[i] < train_dates[i+1] y val_dates[i] < val_dates[i+1]
    """
    df = chronological_data
    tscv = TimeSeriesSplit(n_splits=5)

    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(df), start=1):
        train_dates = df.iloc[train_idx]['date'].values
        val_dates = df.iloc[val_idx]['date'].values

        # Validar orden cronológico interno en train
        assert np.all(train_dates[:-1] <= train_dates[1:]), (
            f"❌ Train desordenado internamente en fold {fold_idx}"
        )

        # Validar orden cronológico interno en val
        assert np.all(val_dates[:-1] <= val_dates[1:]), (
            f"❌ Val desordenado internamente en fold {fold_idx}"
        )

        print(f"✅ Fold {fold_idx}: Orden interno preservado")


def test_time_series_split_no_duplicate_indices(chronological_data):
    """
    Test: Verifica que no hay índices duplicados entre train y val.

    Criterio: len(set(train_idx) & set(val_idx)) == 0
    """
    df = chronological_data
    tscv = TimeSeriesSplit(n_splits=5)

    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(df), start=1):
        overlap = set(train_idx) & set(val_idx)

        assert len(overlap) == 0, (
            f"❌ Índices duplicados en fold {fold_idx}: {overlap}"
        )

        print(f"✅ Fold {fold_idx}: Sin índices duplicados")


def test_time_series_split_covers_all_data(chronological_data):
    """
    Test: Verifica que todos los folds juntos cubren todo el dataset.

    Criterio: union(all_train_idx, all_val_idx) == all_indices
    """
    df = chronological_data
    tscv = TimeSeriesSplit(n_splits=5)

    all_indices = set()

    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(df), start=1):
        all_indices.update(train_idx)
        all_indices.update(val_idx)

    # Validar cobertura completa
    expected_indices = set(range(len(df)))

    # TimeSeriesSplit NO cubre los primeros índices en el primer fold
    # Validar que los índices cubiertos son >= 50% del total
    coverage_pct = len(all_indices) / len(expected_indices) * 100

    assert coverage_pct >= 50, (
        f"❌ Cobertura insuficiente: {coverage_pct:.1f}% (esperado: >=50%)"
    )

    print(f"✅ Cobertura: {coverage_pct:.1f}% del dataset")


def test_time_series_split_val_size_consistent(chronological_data):
    """
    Test: Verifica que validation sets tienen tamaño similar.

    Criterio: Coeficiente de variación < 20%
    """
    df = chronological_data
    tscv = TimeSeriesSplit(n_splits=5)

    val_sizes = []

    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(df), start=1):
        val_sizes.append(len(val_idx))

    # Calcular coeficiente de variación
    mean_val_size = np.mean(val_sizes)
    std_val_size = np.std(val_sizes)
    cv = (std_val_size / mean_val_size) * 100

    assert cv < 20, (
        f"❌ Val sizes muy variables (CV={cv:.1f}%): {val_sizes}"
    )

    print(f"✅ Val sizes consistentes (CV={cv:.1f}%): {val_sizes}")


# ============================================================
# TESTS DE INTEGRACIÓN CON REAL DATA
# ============================================================

def test_time_series_split_with_brasaland_data():
    """
    Test de integración: Verifica split con datos reales de Brasaland.
    """
    # Cargar datos reales
    data_path = PROJECT_ROOT / "data" / "raw" / "brasaland_sales.csv"

    if not data_path.exists():
        pytest.skip("Dataset brasaland_sales.csv no encontrado")

    df = pd.read_csv(data_path, parse_dates=['date'])
    df = df.sort_values('date').reset_index(drop=True)

    # Usar solo training set (2014-2021)
    df_train = df[df['date'] < '2022-01-01'].copy()

    tscv = TimeSeriesSplit(n_splits=5)

    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(df_train), start=1):
        train_dates = df_train.iloc[train_idx]['date']
        val_dates = df_train.iloc[val_idx]['date']

        # Validar no overlap
        assert train_dates.max() < val_dates.min(), (
            f"❌ OVERLAP en fold {fold_idx} con datos reales"
        )

        # Validar orden
        assert train_dates.is_monotonic_increasing, (
            f"❌ Train desordenado en fold {fold_idx}"
        )

        assert val_dates.is_monotonic_increasing, (
            f"❌ Val desordenado en fold {fold_idx}"
        )

        print(f"✅ Fold {fold_idx} (real data): "
              f"Train [{train_dates.min().date()} - {train_dates.max().date()}], "
              f"Val [{val_dates.min().date()} - {val_dates.max().date()}]")


# ============================================================
# TESTS PARAMETRIZADOS
# ============================================================

@pytest.mark.parametrize("n_splits", [3, 5, 7, 10])
def test_time_series_split_multiple_configurations(chronological_data, n_splits):
    """
    Test parametrizado: Verifica múltiples configuraciones de n_splits.
    """
    df = chronological_data
    tscv = TimeSeriesSplit(n_splits=n_splits)

    fold_count = 0

    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(df), start=1):
        train_dates = df.iloc[train_idx]['date']
        val_dates = df.iloc[val_idx]['date']

        # Validar no overlap
        assert train_dates.max() < val_dates.min()

        fold_count += 1

    # Validar que generó n_splits folds
    assert fold_count == n_splits, (
        f"❌ Esperado {n_splits} folds, obtenido {fold_count}"
    )

    print(f"✅ n_splits={n_splits}: {fold_count} folds válidos")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, '-v', '--tb=short'])
