"""Tests for data tier classification and failure handling."""

import pytest
import structlog

from src.pipeline.tiers import (
    DataTier,
    DegradedResult,
    SkippedResult,
    SOURCE_TIERS,
    SourceCriticalError,
    get_tier,
    handle_source_failure,
)


class TestDataTierEnum:
    """DataTier enum value tests."""

    def test_has_critical(self):
        assert DataTier.CRITICAL == "critical"

    def test_has_important(self):
        assert DataTier.IMPORTANT == "important"

    def test_has_supplementary(self):
        assert DataTier.SUPPLEMENTARY == "supplementary"


class TestSourceTiersMapping:
    """SOURCE_TIERS mapping tests."""

    def test_price_ohlcv_is_critical(self):
        assert SOURCE_TIERS["price_ohlcv"] == DataTier.CRITICAL

    def test_orderbook_is_important(self):
        assert SOURCE_TIERS["orderbook"] == DataTier.IMPORTANT

    def test_news_sentiment_is_supplementary(self):
        assert SOURCE_TIERS["news_sentiment"] == DataTier.SUPPLEMENTARY

    def test_social_metrics_is_supplementary(self):
        assert SOURCE_TIERS["social_metrics"] == DataTier.SUPPLEMENTARY

    def test_macro_data_is_important(self):
        assert SOURCE_TIERS["macro_data"] == DataTier.IMPORTANT

    def test_technical_is_critical(self):
        assert SOURCE_TIERS["technical"] == DataTier.CRITICAL


class TestGetTier:
    """get_tier function tests."""

    def test_known_source_returns_mapped_tier(self):
        assert get_tier("price_ohlcv") == DataTier.CRITICAL

    def test_unknown_source_returns_supplementary(self):
        assert get_tier("totally_unknown_source") == DataTier.SUPPLEMENTARY


class TestHandleSourceFailure:
    """handle_source_failure routing tests."""

    def test_critical_raises_source_critical_error(self):
        with pytest.raises(SourceCriticalError, match="Critical source price_ohlcv failed"):
            handle_source_failure("price_ohlcv", RuntimeError("API down"))

    def test_important_returns_degraded_result(self):
        result = handle_source_failure("orderbook", RuntimeError("timeout"))
        assert isinstance(result, DegradedResult)
        assert result.source == "orderbook"
        assert result.tier == DataTier.IMPORTANT
        assert "timeout" in result.error

    def test_supplementary_returns_skipped_result(self):
        result = handle_source_failure("news_sentiment", RuntimeError("rate limited"))
        assert isinstance(result, SkippedResult)
        assert result.source == "news_sentiment"
        assert result.tier == DataTier.SUPPLEMENTARY
        assert "rate limited" in result.error

    def test_supplementary_logs_warning(self, caplog):
        """Supplementary failures are logged."""
        result = handle_source_failure("social_metrics", RuntimeError("unavailable"))
        assert isinstance(result, SkippedResult)

    def test_unknown_source_treated_as_supplementary(self):
        result = handle_source_failure("mystery_source", RuntimeError("error"))
        assert isinstance(result, SkippedResult)
        assert result.tier == DataTier.SUPPLEMENTARY
