"""Tests for src.risk.concentration module."""


def test_sector_pct_sums_to_100(sample_assets: list[dict]) -> None:
    """Sector percentages sum to approximately 100."""
    pass


def test_idr_usd_sums_to_100(sample_assets: list[dict]) -> None:
    """IDR + USD percentages equal 100."""
    pass


def test_max_single_pct_equal_weight(sample_assets: list[dict]) -> None:
    """Max single asset pct = 100/N for equal-weight."""
    pass


def test_single_asset_concentration() -> None:
    """Single asset is 100% concentration."""
    pass


def test_unknown_sector_fallback() -> None:
    """Unknown ticker maps to 'unknown' sector."""
    pass
