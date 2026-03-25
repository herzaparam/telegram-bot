"""Tests for ML feature engineering module."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture()
def sample_df_200() -> pd.DataFrame:
    """200-row synthetic OHLCV DataFrame for feature extraction."""
    rng = np.random.default_rng(42)
    n = 200
    dates = pd.bdate_range("2025-06-01", periods=n, freq="B")

    returns = rng.normal(0.0005, 0.015, size=n)
    close = 10000.0 * np.cumprod(1 + returns)

    high = close * (1 + rng.uniform(0.001, 0.02, size=n))
    low = close * (1 - rng.uniform(0.001, 0.02, size=n))
    open_ = low + rng.uniform(0.3, 0.7, size=n) * (high - low)
    volume = rng.uniform(500_000, 5_000_000, size=n)

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


@pytest.fixture()
def sample_df_10() -> pd.DataFrame:
    """10-row DataFrame -- insufficient for feature extraction."""
    rng = np.random.default_rng(999)
    n = 10
    dates = pd.bdate_range("2026-03-01", periods=n, freq="B")

    returns = rng.normal(0.0, 0.01, size=n)
    close = 10000.0 * np.cumprod(1 + returns)

    high = close * (1 + rng.uniform(0.002, 0.01, size=n))
    low = close * (1 - rng.uniform(0.002, 0.01, size=n))
    open_ = low + rng.uniform(0.4, 0.6, size=n) * (high - low)
    volume = rng.uniform(1_000_000, 2_000_000, size=n)

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


class TestExtractFeatures:
    """Tests for extract_features function."""

    def test_returns_ndarray_with_correct_shape(self, sample_df_200: pd.DataFrame) -> None:
        from src.ml.features import extract_features

        result = extract_features(sample_df_200)
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.shape == (1, 20)

    def test_returns_float32_dtype(self, sample_df_200: pd.DataFrame) -> None:
        from src.ml.features import extract_features

        result = extract_features(sample_df_200)
        assert result is not None
        assert result.dtype == np.float32

    def test_returns_none_for_insufficient_data(self, sample_df_10: pd.DataFrame) -> None:
        from src.ml.features import extract_features

        result = extract_features(sample_df_10)
        assert result is None

    def test_no_nan_in_output(self, sample_df_200: pd.DataFrame) -> None:
        from src.ml.features import extract_features

        result = extract_features(sample_df_200)
        assert result is not None
        assert not np.any(np.isnan(result))

    def test_consistent_feature_count(self, sample_df_200: pd.DataFrame) -> None:
        from src.ml.features import FEATURE_NAMES, extract_features

        result = extract_features(sample_df_200)
        assert result is not None
        assert len(FEATURE_NAMES) == 20
        assert result.shape[1] == len(FEATURE_NAMES)

    def test_feature_names_list(self) -> None:
        from src.ml.features import FEATURE_NAMES

        assert isinstance(FEATURE_NAMES, list)
        assert len(FEATURE_NAMES) == 20
        assert all(isinstance(name, str) for name in FEATURE_NAMES)
