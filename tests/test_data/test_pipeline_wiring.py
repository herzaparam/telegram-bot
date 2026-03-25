"""Tests for pipeline wiring: IDX doc fetch+parse, financial data loading, ValuationEngine wiring, Telegram alerts."""

from __future__ import annotations

from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.db.models import Asset, FinancialData, FinancialDoc


def _make_stock_asset(asset_id: int = 1, symbol: str = "BBCA") -> Asset:
    """Create a mock stock Asset instance."""
    asset = MagicMock(spec=Asset)
    asset.id = asset_id
    asset.symbol = symbol
    asset.asset_type = "stock"
    asset.yfinance_symbol = f"{symbol}.JK"
    asset.name = f"Test {symbol}"
    return asset


def _make_crypto_asset(asset_id: int = 100, symbol: str = "ETH") -> Asset:
    """Create a mock crypto Asset instance."""
    asset = MagicMock(spec=Asset)
    asset.id = asset_id
    asset.symbol = symbol
    asset.asset_type = "crypto"
    asset.ccxt_symbol = f"{symbol}/USDT"
    asset.name = f"Test {symbol}"
    return asset


# ---------------------------------------------------------------------------
# Test 1: _fetch_and_parse_docs calls fetch_idx_docs for stock assets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_fetch_and_parse_docs_calls_fetch_idx_docs() -> None:
    """_fetch_and_parse_docs calls fetch_idx_docs for stock assets."""
    from src.data.ingest import _fetch_and_parse_docs

    session = AsyncMock()
    asset = _make_stock_asset()

    # No pending docs after fetch
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    with patch("src.data.ingest.fetch_idx_docs", new_callable=AsyncMock) as mock_fetch:
        await _fetch_and_parse_docs(session, asset)
        mock_fetch.assert_called_once_with(session, asset)


# ---------------------------------------------------------------------------
# Test 2: _fetch_and_parse_docs calls parse_financial_doc for pending docs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_fetch_and_parse_docs_calls_parse_for_pending() -> None:
    """_fetch_and_parse_docs calls parse_financial_doc for pending docs."""
    from src.data.ingest import _fetch_and_parse_docs

    session = AsyncMock()
    asset = _make_stock_asset()

    pending_doc = MagicMock(spec=FinancialDoc)
    pending_doc.file_path = "/tmp/test.pdf"
    pending_doc.parse_status = "pending"
    pending_doc.id = 1
    pending_doc.asset_id = 1

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [pending_doc]
    session.execute.return_value = mock_result

    parse_result = {
        "revenue": 1e12,
        "net_profit": 2e11,
        "period": "Q3 2025",
        "management_outlook": "Positive growth expected",
    }

    with (
        patch("src.data.ingest.fetch_idx_docs", new_callable=AsyncMock),
        patch(
            "src.data.ingest.parse_financial_doc",
            new_callable=AsyncMock,
            return_value=parse_result,
        ) as mock_parse,
    ):
        await _fetch_and_parse_docs(session, asset)
        mock_parse.assert_called_once_with("/tmp/test.pdf", asset.symbol)


# ---------------------------------------------------------------------------
# Test 3: _fetch_and_parse_docs sets parse_status="parsed" on success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_fetch_and_parse_docs_sets_parsed_on_success() -> None:
    """_fetch_and_parse_docs sets parse_status='parsed' and parsed_at on success."""
    from src.data.ingest import _fetch_and_parse_docs

    session = AsyncMock()
    asset = _make_stock_asset()

    pending_doc = MagicMock(spec=FinancialDoc)
    pending_doc.file_path = "/tmp/test.pdf"
    pending_doc.parse_status = "pending"
    pending_doc.id = 1
    pending_doc.asset_id = 1

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [pending_doc]
    session.execute.return_value = mock_result

    parse_result = {
        "revenue": 1e12,
        "net_profit": 2e11,
        "period": "Q3 2025",
    }

    with (
        patch("src.data.ingest.fetch_idx_docs", new_callable=AsyncMock),
        patch(
            "src.data.ingest.parse_financial_doc",
            new_callable=AsyncMock,
            return_value=parse_result,
        ),
    ):
        await _fetch_and_parse_docs(session, asset)

    assert pending_doc.parse_status == "parsed"
    assert pending_doc.parsed_at is not None


# ---------------------------------------------------------------------------
# Test 4: _fetch_and_parse_docs sets parse_status="failed" on parse failure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_fetch_and_parse_docs_sets_failed_on_parse_failure() -> None:
    """_fetch_and_parse_docs sets parse_status='failed' when parse returns None."""
    from src.data.ingest import _fetch_and_parse_docs

    session = AsyncMock()
    asset = _make_stock_asset()

    pending_doc = MagicMock(spec=FinancialDoc)
    pending_doc.file_path = "/tmp/test.pdf"
    pending_doc.parse_status = "pending"
    pending_doc.id = 1
    pending_doc.asset_id = 1

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [pending_doc]
    session.execute.return_value = mock_result

    with (
        patch("src.data.ingest.fetch_idx_docs", new_callable=AsyncMock),
        patch(
            "src.data.ingest.parse_financial_doc",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        await _fetch_and_parse_docs(session, asset)

    assert pending_doc.parse_status == "failed"


# ---------------------------------------------------------------------------
# Test 5: _fetch_and_parse_docs sends Telegram alert on fetch exception (D-05)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_fetch_and_parse_docs_telegram_alert_on_failure() -> None:
    """_fetch_and_parse_docs sends Telegram alert when fetch_idx_docs raises."""
    from src.data.ingest import _fetch_and_parse_docs

    session = AsyncMock()
    asset = _make_stock_asset()

    # No pending docs query needed since fetch fails
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    mock_token = MagicMock()
    mock_token.get_secret_value.return_value = "test-bot-token"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with (
        patch(
            "src.data.ingest.fetch_idx_docs",
            new_callable=AsyncMock,
            side_effect=RuntimeError("IDX API down"),
        ),
        patch("src.data.ingest.settings") as mock_settings,
        patch("src.data.ingest.httpx.AsyncClient", return_value=mock_client),
    ):
        mock_settings.telegram_bot_token = mock_token
        mock_settings.telegram_chat_id = "12345"

        await _fetch_and_parse_docs(session, asset)

        # Verify Telegram message was sent
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "sendMessage" in call_args[0][0]
        assert "IDX doc fetch failed" in call_args[1]["json"]["text"]


# ---------------------------------------------------------------------------
# Test 6: _load_financial_data returns grouped period dicts from DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_load_financial_data_returns_grouped_dicts() -> None:
    """_load_financial_data returns list of dicts grouped by period."""
    from src.data.analyze import _load_financial_data

    session = AsyncMock()
    asset = _make_stock_asset()

    row1 = MagicMock(spec=FinancialData)
    row1.period = "Q3-2025"
    row1.metric_name = "revenue"
    row1.metric_value = 1e12
    row1.metric_text = None

    row2 = MagicMock(spec=FinancialData)
    row2.period = "Q3-2025"
    row2.metric_name = "net_profit"
    row2.metric_value = 2e11
    row2.metric_text = None

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [row1, row2]
    session.execute.return_value = mock_result

    result = await _load_financial_data(session, asset)
    assert result is not None
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["period"] == "Q3-2025"
    assert result[0]["revenue"] == 1e12
    assert result[0]["net_profit"] == 2e11


# ---------------------------------------------------------------------------
# Test 7: _load_financial_data returns None when no data exists
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_load_financial_data_returns_none_when_empty() -> None:
    """_load_financial_data returns None when no data."""
    from src.data.analyze import _load_financial_data

    session = AsyncMock()
    asset = _make_stock_asset()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    result = await _load_financial_data(session, asset)
    assert result is None


# ---------------------------------------------------------------------------
# Test 8: _load_peer_data returns peer metrics for same-sector stocks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio()
async def test_load_peer_data_returns_peer_metrics() -> None:
    """_load_peer_data returns peer metrics for same-sector stocks."""
    from src.data.analyze import _load_peer_data

    session = AsyncMock()
    asset = _make_stock_asset(symbol="BBCA")

    # Mock: find peer assets in banking sector
    peer_asset = MagicMock(spec=Asset)
    peer_asset.id = 2
    peer_asset.symbol = "BBRI"

    # First execute: find peer assets
    mock_result1 = MagicMock()
    mock_result1.scalars.return_value.all.return_value = [asset, peer_asset]

    # Second execute: get fundamentals for peers
    peer_fund = MagicMock()
    peer_fund.trailing_pe = 12.0
    peer_fund.price_to_book = 2.5
    mock_result2 = MagicMock()
    mock_result2.scalars.return_value.all.return_value = [peer_fund]

    session.execute.side_effect = [mock_result1, mock_result2]

    result = await _load_peer_data(session, asset)
    # Should return peer data (at minimum sector averages dict)
    assert result is not None
    assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Test 9: _cross_validate returns warning when revenue differs >10%
# ---------------------------------------------------------------------------


def test_cross_validate_flags_discrepancy() -> None:
    """_cross_validate returns warnings when values differ >10%."""
    from src.data.analyze import _cross_validate

    financial_data = [
        {"period": "Q3-2025", "revenue": 1_000_000_000, "net_profit": 200_000_000},
    ]
    yf_fundamentals = {
        "totalRevenue": 1_200_000_000,  # 20% higher -> should flag
        "netIncome": 210_000_000,  # 5% higher -> within threshold
    }

    warnings = _cross_validate(financial_data, yf_fundamentals)
    assert len(warnings) >= 1
    assert any("revenue" in w.lower() or "Revenue" in w for w in warnings)


# ---------------------------------------------------------------------------
# Test 10: _cross_validate returns empty list when values match
# ---------------------------------------------------------------------------


def test_cross_validate_no_warning_when_matching() -> None:
    """_cross_validate returns empty list when values are within 10%."""
    from src.data.analyze import _cross_validate

    financial_data = [
        {"period": "Q3-2025", "revenue": 1_000_000_000, "net_profit": 200_000_000},
    ]
    yf_fundamentals = {
        "totalRevenue": 1_050_000_000,  # 5% higher -> within threshold
        "netIncome": 195_000_000,  # 2.5% lower -> within threshold
    }

    warnings = _cross_validate(financial_data, yf_fundamentals)
    assert len(warnings) == 0


# ---------------------------------------------------------------------------
# Test 11: _get_engines_for_asset includes ValuationEngine
# ---------------------------------------------------------------------------


def test_get_engines_includes_valuation() -> None:
    """_get_engines_for_asset includes ValuationEngine in returned list."""
    from src.data.analyze import _get_engines_for_asset
    from src.engines.valuation import ValuationEngine

    asset = _make_stock_asset()

    engines = _get_engines_for_asset(asset)
    engine_types = [type(e) for e in engines]
    assert ValuationEngine in engine_types


# ---------------------------------------------------------------------------
# Test 12: _get_engines_for_asset passes tvl_data to ValuationEngine (D-13)
# ---------------------------------------------------------------------------


def test_get_engines_passes_tvl_data() -> None:
    """_get_engines_for_asset passes tvl_data to ValuationEngine constructor."""
    from src.data.analyze import _get_engines_for_asset
    from src.engines.valuation import ValuationEngine

    asset = _make_crypto_asset()
    tvl = {"market_cap": 1e9, "tvl": 5e8}

    engines = _get_engines_for_asset(asset, tvl_data=tvl)
    val_engines = [e for e in engines if isinstance(e, ValuationEngine)]
    assert len(val_engines) == 1
    assert val_engines[0]._tvl_data == tvl
