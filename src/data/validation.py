"""OHLCV row validation and date coverage checking.

Rejects rows with null/NaN fields, invalid high/low relationships,
and negative volume. Logs all rejections via structlog.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta

import structlog

from src.data.base import OHLCVRow

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of validating a batch of OHLCV rows."""

    valid: list[OHLCVRow] = field(default_factory=list)
    rejected: list[tuple[OHLCVRow, str]] = field(default_factory=list)


def validate_rows(
    rows: list[OHLCVRow], asset_symbol: str = ""
) -> ValidationResult:
    """Validate a list of OHLCV rows, rejecting any with invalid fields.

    Checks performed per row:
    - open, high, low, close, volume are not None
    - None of those fields are NaN
    - high >= low
    - volume >= 0

    Args:
        rows: Raw OHLCVRow instances to validate.
        asset_symbol: Human-readable symbol for logging (e.g. 'BBCA.JK').

    Returns:
        ValidationResult with valid and rejected (row, reason) lists.
    """
    result = ValidationResult()

    for row in rows:
        reason = _check_row(row)
        if reason is not None:
            result.rejected.append((row, reason))
            logger.warning(
                "ohlcv_row_rejected",
                asset=asset_symbol,
                time=str(row.time),
                reason=reason,
            )
        else:
            result.valid.append(row)

    return result


def _check_row(row: OHLCVRow) -> str | None:
    """Return a rejection reason string, or None if the row is valid."""
    fields = {
        "open": row.open,
        "high": row.high,
        "low": row.low,
        "close": row.close,
        "volume": row.volume,
    }

    for name, value in fields.items():
        if value is None:
            return f"{name} is None"
        if isinstance(value, float) and math.isnan(value):
            return f"{name} is NaN"

    # Sanity checks (only reached if no None/NaN)
    if row.high < row.low:
        return "high < low"
    if row.volume < 0:
        return "volume < 0"

    return None


def validate_date_coverage(
    rows: list[OHLCVRow],
    start: date,
    end: date,
    asset_symbol: str = "",
) -> list[date]:
    """Check for missing business days in the returned data.

    Uses a simple heuristic: weekdays (Mon-Fri) are expected trading days.
    Exchange-specific holidays are not accounted for here.

    Args:
        rows: OHLCV rows to check coverage for.
        start: Expected start date (inclusive).
        end: Expected end date (inclusive).
        asset_symbol: Human-readable symbol for logging.

    Returns:
        List of missing business dates (may be empty).
    """
    actual_dates: set[date] = set()
    for row in rows:
        actual_dates.add(row.time.date() if hasattr(row.time, "date") else row.time)

    # Generate expected weekdays between start and end (inclusive)
    expected: set[date] = set()
    current = start
    while current <= end:
        if current.weekday() < 5:  # Mon=0 .. Fri=4
            expected.add(current)
        current += timedelta(days=1)

    missing = sorted(expected - actual_dates)

    if missing:
        logger.warning(
            "ohlcv_date_gaps",
            asset=asset_symbol,
            missing_count=len(missing),
            missing_dates=[str(d) for d in missing[:5]],
        )

    return missing
