"""Tests for src.risk.concentration module."""

from src.risk.concentration import ConcentrationResult, compute_concentration

SECTOR_MAP = {
    "BBCA": "banking",
    "BBRI": "banking",
    "TLKM": "telco",
}


def test_sector_pct_sums_to_100(sample_assets: list[dict]) -> None:
    """Sector percentages sum to approximately 100."""
    result = compute_concentration(sample_assets, SECTOR_MAP)
    total = sum(result.sector_pct.values())
    assert abs(total - 100.0) < 0.01


def test_idr_usd_sums_to_100(sample_assets: list[dict]) -> None:
    """IDR + USD percentages equal 100."""
    result = compute_concentration(sample_assets, SECTOR_MAP)
    assert abs(result.idr_pct + result.usd_pct - 100.0) < 0.01


def test_max_single_pct_equal_weight(sample_assets: list[dict]) -> None:
    """Max single asset pct = 100/N for equal-weight."""
    result = compute_concentration(sample_assets, SECTOR_MAP)
    expected = 100.0 / len(sample_assets)
    assert abs(result.max_single_pct - expected) < 0.01


def test_single_asset_concentration() -> None:
    """Single asset is 100% concentration."""
    assets = [{"symbol": "BBCA", "asset_type": "stock"}]
    result = compute_concentration(assets, SECTOR_MAP)
    assert result.max_single_pct == 100.0
    assert result.idr_pct == 100.0
    assert result.usd_pct == 0.0
    assert result.asset_count == 1


def test_unknown_sector_fallback() -> None:
    """Unknown ticker maps to 'unknown' sector."""
    assets = [{"symbol": "XXXX", "asset_type": "stock"}]
    result = compute_concentration(assets, SECTOR_MAP)
    assert "unknown" in result.sector_pct


def test_empty_portfolio() -> None:
    """Empty portfolio returns zeroes."""
    result = compute_concentration([], SECTOR_MAP)
    assert result.asset_count == 0
    assert result.max_single_pct == 0.0


def test_crypto_gets_crypto_sector(sample_assets: list[dict]) -> None:
    """Crypto assets are grouped under 'crypto' sector."""
    result = compute_concentration(sample_assets, SECTOR_MAP)
    assert "crypto" in result.sector_pct
