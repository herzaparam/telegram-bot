"""Feature engineering from OHLCV data for ML models.

All features are derived from price and volume only (per D-01).
No external data sources.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_NAMES: list[str] = [
    # Returns at different horizons (5)
    "return_1d",
    "return_3d",
    "return_5d",
    "return_10d",
    "return_20d",
    # Volatility at different windows (3)
    "volatility_5d",
    "volatility_10d",
    "volatility_20d",
    # Momentum indicators (1)
    "rsi_14",
    # Volume (1)
    "volume_ratio_20d",
    # MACD family (3)
    "macd",
    "macd_signal",
    "macd_histogram",
    # Bollinger (1)
    "bollinger_pct_b",
    # Lagged close ratios (4)
    "lag_ratio_1d",
    "lag_ratio_2d",
    "lag_ratio_3d",
    "lag_ratio_5d",
    # ATR (1)
    "atr_14_norm",
    # OBV slope (1)
    "obv_slope_20d",
]


def extract_features(
    df: pd.DataFrame, min_rows: int = 60
) -> np.ndarray | None:
    """Extract ML features from OHLCV DataFrame.

    Args:
        df: DataFrame with columns open, high, low, close, volume.
        min_rows: Minimum number of rows required.

    Returns:
        Feature array of shape (1, 20) with dtype float32, or None if
        insufficient data.
    """
    if len(df) < min_rows:
        return None

    close = df["close"].values.astype(float)
    high = df["high"].values.astype(float)
    low = df["low"].values.astype(float)
    volume = df["volume"].values.astype(float)

    features: list[float] = []

    # --- Returns at horizons [1, 3, 5, 10, 20] days ---
    for d in [1, 3, 5, 10, 20]:
        if len(close) > d:
            features.append(close[-1] / close[-1 - d] - 1.0)
        else:
            features.append(0.0)

    # --- Volatility at windows [5, 10, 20] ---
    log_returns = np.diff(np.log(close))
    for w in [5, 10, 20]:
        if len(log_returns) >= w:
            features.append(float(np.std(log_returns[-w:])))
        else:
            features.append(0.0)

    # --- RSI-14 ---
    if len(close) >= 15:
        deltas = np.diff(close)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)

        avg_gain = float(np.mean(gains[-14:]))
        avg_loss = float(np.mean(losses[-14:]))

        if avg_loss > 0:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
        else:
            rsi = 100.0
        features.append(rsi / 100.0)  # Normalize to [0, 1]
    else:
        features.append(0.5)

    # --- Volume ratio: vol[-1] / mean(vol[-20:]) ---
    if len(volume) >= 20:
        vol_mean = float(np.mean(volume[-20:]))
        features.append(float(volume[-1] / vol_mean) if vol_mean > 0 else 1.0)
    else:
        features.append(1.0)

    # --- MACD: ema12 - ema26 ---
    close_series = pd.Series(close)
    ema12 = close_series.ewm(span=12, adjust=False).mean()
    ema26 = close_series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    macd_signal = macd_line.ewm(span=9, adjust=False).mean()
    macd_histogram = macd_line - macd_signal

    # Normalize MACD by close price for scale-invariance
    last_close = close[-1] if close[-1] != 0 else 1.0
    features.append(float(macd_line.iloc[-1]) / last_close)
    features.append(float(macd_signal.iloc[-1]) / last_close)
    features.append(float(macd_histogram.iloc[-1]) / last_close)

    # --- Bollinger %B: (close - lower) / (upper - lower) with 20-period, 2-std ---
    if len(close) >= 20:
        rolling_mean = close_series.rolling(20).mean()
        rolling_std = close_series.rolling(20).std()
        upper = rolling_mean + 2 * rolling_std
        lower = rolling_mean - 2 * rolling_std

        band_width = float(upper.iloc[-1] - lower.iloc[-1])
        if band_width > 0:
            pct_b = (close[-1] - float(lower.iloc[-1])) / band_width
        else:
            pct_b = 0.5
        features.append(float(pct_b))
    else:
        features.append(0.5)

    # --- Lagged close ratios at [1, 2, 3, 5] days ---
    for d in [1, 2, 3, 5]:
        if len(close) > d:
            features.append(close[-1] / close[-1 - d])
        else:
            features.append(1.0)

    # --- ATR 14-period normalized by close ---
    if len(high) >= 15:
        tr = np.maximum(
            high[1:] - low[1:],
            np.maximum(
                np.abs(high[1:] - close[:-1]),
                np.abs(low[1:] - close[:-1]),
            ),
        )
        atr = float(np.mean(tr[-14:]))
        features.append(atr / last_close if last_close > 0 else 0.0)
    else:
        features.append(0.0)

    # --- OBV 20-day slope ---
    if len(close) >= 21 and len(volume) >= 21:
        price_direction = np.sign(np.diff(close))
        obv = np.cumsum(price_direction * volume[1:])

        if len(obv) >= 20:
            obv_recent = obv[-20:]
            x = np.arange(20, dtype=float)
            slope, _ = np.polyfit(x, obv_recent, 1)
            # Normalize by mean volume
            mean_vol = float(np.mean(volume[-20:]))
            features.append(slope / mean_vol if mean_vol > 0 else 0.0)
        else:
            features.append(0.0)
    else:
        features.append(0.0)

    # Replace NaN with 0.0
    result = np.array(features, dtype=np.float32).reshape(1, -1)
    result = np.nan_to_num(result, nan=0.0, posinf=0.0, neginf=0.0)

    return result
