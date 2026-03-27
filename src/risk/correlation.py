"""Correlation matrix computation and emoji heatmap formatting.

Pure computation module -- no DB or pipeline imports.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CorrelationResult:
    """Result of correlation matrix computation."""

    matrix: dict[str, dict[str, float]]
    high_pairs: list[tuple[str, str, float]]
    avg_correlation: float


# Emoji legend for heatmap cells
CORR_EMOJI: dict[str, str] = {
    "high_pos": "\U0001f534",   # red circle
    "med_pos": "\U0001f7e0",    # orange circle
    "low": "\U0001f7e2",        # green circle
    "med_neg": "\U0001f535",    # blue circle
    "high_neg": "\U0001f7e3",   # purple circle
}


def compute_correlation_matrix(
    price_data: dict[str, pd.Series],
    window: int = 30,
) -> CorrelationResult:
    """Compute NxN correlation matrix from close price series.

    Args:
        price_data: Mapping of symbol -> pd.Series of close prices.
        window: Number of trailing return periods to use.

    Returns:
        CorrelationResult with matrix dict, high-correlation pairs, and average.
    """
    if len(price_data) < 2:
        symbols = list(price_data.keys())
        matrix = {s: {s: 1.0} for s in symbols}
        return CorrelationResult(matrix=matrix, high_pairs=[], avg_correlation=1.0)

    # Build returns DataFrame
    returns_dict = {sym: series.pct_change().dropna() for sym, series in price_data.items()}
    df = pd.DataFrame(returns_dict).tail(window).dropna()

    corr = df.corr()
    symbols = list(corr.columns)
    n = len(symbols)

    # Convert to nested dict
    matrix: dict[str, dict[str, float]] = {}
    for sym in symbols:
        matrix[sym] = {s2: round(float(corr.loc[sym, s2]), 6) for s2 in symbols}

    # Extract high-correlation pairs (|r| > 0.8, upper triangle only)
    high_pairs: list[tuple[str, str, float]] = []
    for i in range(n):
        for j in range(i + 1, n):
            val = float(corr.iloc[i, j])
            if abs(val) > 0.8:
                high_pairs.append((symbols[i], symbols[j], round(val, 6)))

    # Average correlation from upper triangle
    indices = np.triu_indices(n, k=1)
    vals = corr.values[indices]
    avg = float(np.mean(vals)) if len(vals) > 0 else 0.0

    return CorrelationResult(
        matrix=matrix,
        high_pairs=high_pairs,
        avg_correlation=round(avg, 6),
    )


def _emoji_for_corr(value: float) -> str:
    """Select emoji for a correlation value."""
    if value > 0.7:
        return CORR_EMOJI["high_pos"]
    if value > 0.4:
        return CORR_EMOJI["med_pos"]
    if value > -0.3:
        return CORR_EMOJI["low"]
    if value > -0.7:
        return CORR_EMOJI["med_neg"]
    return CORR_EMOJI["high_neg"]


def format_correlation_heatmap(result: CorrelationResult) -> str:
    """Format a CorrelationResult as an HTML emoji heatmap.

    Returns:
        HTML string with ``<code>`` header row and emoji grid.
    """
    symbols = list(result.matrix.keys())
    if not symbols:
        return "<i>No correlation data</i>"

    # Header row: 4-char abbreviated symbols
    short = [s[:4] for s in symbols]
    header = "<code>    " + " ".join(f"{s:>4}" for s in short) + "</code>"

    rows = [header]
    white_square = "\u2b1c"
    for sym in symbols:
        cells: list[str] = []
        for sym2 in symbols:
            if sym == sym2:
                cells.append(white_square)
            else:
                val = result.matrix[sym][sym2]
                cells.append(_emoji_for_corr(val))
        label = sym[:4]
        rows.append(f"<code>{label:>4}</code> {''.join(cells)}")

    return "\n".join(rows)
