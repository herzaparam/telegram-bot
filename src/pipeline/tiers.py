"""Data source tier classification and failure handling.

Sources are classified into tiers that determine how failures are handled:
- CRITICAL: Failure skips the asset entirely (e.g., price data)
- IMPORTANT: Failure degrades quality but processing continues
- SUPPLEMENTARY: Failure is logged and ignored
"""

from dataclasses import dataclass
from enum import StrEnum

import structlog

logger = structlog.get_logger(__name__)


class DataTier(StrEnum):
    """Classification tier for data sources."""

    CRITICAL = "critical"
    IMPORTANT = "important"
    SUPPLEMENTARY = "supplementary"


# Mapping of data source names to their tier classification.
SOURCE_TIERS: dict[str, DataTier] = {
    "price_ohlcv": DataTier.CRITICAL,
    "technical": DataTier.CRITICAL,
    "orderbook": DataTier.IMPORTANT,
    "fundamental": DataTier.IMPORTANT,
    "macro_data": DataTier.IMPORTANT,
    "news_sentiment": DataTier.SUPPLEMENTARY,
    "social_metrics": DataTier.SUPPLEMENTARY,
    "onchain_data": DataTier.SUPPLEMENTARY,
    "alt_data": DataTier.SUPPLEMENTARY,
}


class SourceCriticalError(Exception):
    """Raised when a critical data source fails.

    The pipeline should skip this asset for the current stage.
    """


@dataclass(frozen=True)
class DegradedResult:
    """Returned when an important data source fails.

    The pipeline continues with degraded data quality.
    """

    source: str
    tier: DataTier
    error: str


@dataclass(frozen=True)
class SkippedResult:
    """Returned when a supplementary data source fails.

    The pipeline continues normally; the missing data is non-essential.
    """

    source: str
    tier: DataTier
    error: str


def get_tier(source_name: str) -> DataTier:
    """Return the tier for a data source, defaulting to SUPPLEMENTARY for unknown sources."""
    return SOURCE_TIERS.get(source_name, DataTier.SUPPLEMENTARY)


def handle_source_failure(
    source_name: str, error: Exception
) -> DegradedResult | SkippedResult:
    """Handle a data source failure according to its tier.

    Args:
        source_name: The name of the data source that failed.
        error: The exception that occurred.

    Returns:
        DegradedResult for IMPORTANT sources, SkippedResult for SUPPLEMENTARY.

    Raises:
        SourceCriticalError: If the source is CRITICAL tier.
    """
    tier = get_tier(source_name)

    if tier == DataTier.CRITICAL:
        raise SourceCriticalError(
            f"Critical source {source_name} failed: {error}"
        )

    if tier == DataTier.IMPORTANT:
        logger.warning(
            "important_source_failed",
            source=source_name,
            error=str(error),
        )
        return DegradedResult(source=source_name, tier=tier, error=str(error))

    # SUPPLEMENTARY
    logger.warning(
        "supplementary_source_skipped",
        source=source_name,
        error=str(error),
    )
    return SkippedResult(source=source_name, tier=tier, error=str(error))
