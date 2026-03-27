"""Tests for src.risk.correlation module."""

import numpy as np
import pandas as pd

from src.risk.correlation import (
    CORR_EMOJI,
    CorrelationResult,
    compute_correlation_matrix,
    format_correlation_heatmap,
)


def test_correlation_matrix_shape(sample_price_data: dict[str, pd.Series]) -> None:
    """Correlation matrix has correct dimensions."""
    result = compute_correlation_matrix(sample_price_data)
    assert len(result.matrix) == len(sample_price_data)
    for sym, row in result.matrix.items():
        assert len(row) == len(sample_price_data)


def test_correlation_matrix_symmetric(sample_price_data: dict[str, pd.Series]) -> None:
    """Correlation matrix is symmetric."""
    result = compute_correlation_matrix(sample_price_data)
    symbols = list(result.matrix.keys())
    for i, s1 in enumerate(symbols):
        for s2 in symbols[i + 1 :]:
            assert abs(result.matrix[s1][s2] - result.matrix[s2][s1]) < 1e-6


def test_correlation_diagonal_is_one(sample_price_data: dict[str, pd.Series]) -> None:
    """Diagonal of correlation matrix is 1.0."""
    result = compute_correlation_matrix(sample_price_data)
    for sym in result.matrix:
        assert abs(result.matrix[sym][sym] - 1.0) < 1e-6


def test_high_pairs_threshold(sample_price_data: dict[str, pd.Series]) -> None:
    """High-correlation pairs detected above 0.8 threshold."""
    result = compute_correlation_matrix(sample_price_data)
    for s1, s2, val in result.high_pairs:
        assert abs(val) > 0.8
        assert s1 != s2


def test_format_heatmap_returns_string(sample_price_data: dict[str, pd.Series]) -> None:
    """format_correlation_heatmap returns an HTML string."""
    result = compute_correlation_matrix(sample_price_data)
    html = format_correlation_heatmap(result)
    assert isinstance(html, str)
    assert "<code>" in html


def test_single_asset_correlation() -> None:
    """Single asset returns trivial 1x1 matrix."""
    rng = np.random.default_rng(1)
    prices = pd.Series(100.0 * np.cumprod(1 + rng.normal(0, 0.01, 30)))
    result = compute_correlation_matrix({"BTC": prices})
    assert result.matrix == {"BTC": {"BTC": 1.0}}
    assert result.high_pairs == []
    assert result.avg_correlation == 1.0


def test_corr_emoji_keys() -> None:
    """CORR_EMOJI has the required keys."""
    expected = {"high_pos", "med_pos", "low", "med_neg", "high_neg"}
    assert set(CORR_EMOJI.keys()) == expected


def test_avg_correlation_in_range(sample_price_data: dict[str, pd.Series]) -> None:
    """Average correlation is between -1 and 1."""
    result = compute_correlation_matrix(sample_price_data)
    assert -1.0 <= result.avg_correlation <= 1.0
