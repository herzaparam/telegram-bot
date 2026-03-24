"""Tests for the pipeline report stage (Telegram delivery via httpx)."""

from __future__ import annotations

import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.data.report import (
    send_daily_report,
    send_pipeline_failure_alert,
    send_telegram_message,
)


@pytest.fixture()
def mock_settings():
    """Provide mock settings with bot token and chat ID."""
    with patch("src.data.report.settings") as s:
        s.telegram_bot_token = MagicMock()
        s.telegram_bot_token.get_secret_value.return_value = "test-token-123"
        s.telegram_chat_id = "111,222"
        yield s


@pytest.fixture()
def sample_decisions():
    """Create sample decision + asset pairs for testing."""
    decisions = []
    for i, (sym, name, verdict, score) in enumerate(
        [
            ("BBCA", "Bank Central Asia", "BUY", 0.42),
            ("BTC", "Bitcoin", "STRONG BUY", 0.85),
            ("ETH", "Ethereum", "HOLD", 0.05),
        ],
        start=1,
    ):
        dec = MagicMock()
        dec.verdict = verdict
        dec.score = score
        dec.confidence = 0.75
        dec.reasoning = "Test reasoning for " + sym
        dec.risk_warning = None

        asset = MagicMock()
        asset.symbol = sym
        asset.name = name

        decisions.append((dec, asset))
    return decisions


@pytest.fixture()
def mock_session(sample_decisions):
    """Create a mock async session that returns watchlist and decisions."""
    session = AsyncMock()

    # Watchlist query returns 3 asset IDs
    watchlist_result = MagicMock()
    watchlist_scalars = MagicMock()
    watchlist_scalars.all.return_value = [MagicMock(asset_id=1), MagicMock(asset_id=2), MagicMock(asset_id=3)]
    watchlist_result.scalars.return_value = watchlist_scalars

    # Decisions query returns sample_decisions
    decisions_result = MagicMock()
    decisions_result.all.return_value = sample_decisions

    # Track which query is being made
    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return watchlist_result
        return decisions_result

    session.execute = mock_execute
    return session


# --- send_telegram_message tests ---


@pytest.mark.asyncio()
async def test_send_telegram_message_success():
    """Test successful message send returns True."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("src.data.report.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await send_telegram_message("123", "Hello", "tok")
        assert result is True
        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert "sendMessage" in str(call_kwargs)


@pytest.mark.asyncio()
async def test_send_telegram_message_rate_limit():
    """Test 429 rate limit triggers retry and succeeds on second attempt."""
    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 429
    rate_limit_response.json.return_value = {"parameters": {"retry_after": 0.01}}

    success_response = MagicMock()
    success_response.status_code = 200

    with patch("src.data.report.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = [rate_limit_response, success_response]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        with patch("src.data.report.asyncio.sleep", new_callable=AsyncMock):
            result = await send_telegram_message("123", "Hello", "tok")
            assert result is True
            assert mock_client.post.call_count == 2


@pytest.mark.asyncio()
async def test_send_telegram_message_error_returns_false():
    """Test non-200/429 status code returns False."""
    error_response = MagicMock()
    error_response.status_code = 400
    error_response.text = "Bad Request"

    with patch("src.data.report.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = error_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await send_telegram_message("123", "Hello", "tok")
        assert result is False


# --- send_daily_report tests ---


@pytest.mark.asyncio()
async def test_send_daily_report_with_decisions(mock_settings, mock_session):
    """Test report with 3 watchlist assets and 3 decisions sends messages."""
    with patch("src.data.report.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        await send_daily_report(mock_session, date(2026, 3, 24))

        # Should send to both chat IDs
        assert mock_send.call_count >= 2
        # Verify message contains asset symbols
        all_texts = [call.args[1] for call in mock_send.call_args_list]
        combined = " ".join(all_texts)
        assert "BBCA" in combined
        assert "BTC" in combined
        assert "ETH" in combined


@pytest.mark.asyncio()
async def test_send_daily_report_empty_watchlist(mock_settings):
    """Test empty watchlist does not send any messages."""
    session = AsyncMock()
    watchlist_result = MagicMock()
    watchlist_scalars = MagicMock()
    watchlist_scalars.all.return_value = []
    watchlist_result.scalars.return_value = watchlist_scalars
    session.execute = AsyncMock(return_value=watchlist_result)

    with patch("src.data.report.send_telegram_message", new_callable=AsyncMock) as mock_send:
        await send_daily_report(session, date(2026, 3, 24))
        mock_send.assert_not_called()


@pytest.mark.asyncio()
async def test_send_daily_report_no_decisions(mock_settings):
    """Test no decisions sends 'no signals' message."""
    session = AsyncMock()

    # Watchlist returns items
    watchlist_result = MagicMock()
    watchlist_scalars = MagicMock()
    watchlist_scalars.all.return_value = [MagicMock(asset_id=1)]
    watchlist_result.scalars.return_value = watchlist_scalars

    # Decisions returns empty
    decisions_result = MagicMock()
    decisions_result.all.return_value = []

    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return watchlist_result
        return decisions_result

    session.execute = mock_execute

    with patch("src.data.report.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        await send_daily_report(session, date(2026, 3, 24))
        assert mock_send.call_count >= 1
        sent_text = mock_send.call_args_list[0].args[1]
        assert "No signals" in sent_text or "no signals" in sent_text.lower()


@pytest.mark.asyncio()
async def test_send_daily_report_empty_bot_token():
    """Test empty bot token does not send any messages."""
    with patch("src.data.report.settings") as s:
        s.telegram_bot_token = MagicMock()
        s.telegram_bot_token.get_secret_value.return_value = ""
        s.telegram_chat_id = "111"

        session = AsyncMock()
        with patch("src.data.report.send_telegram_message", new_callable=AsyncMock) as mock_send:
            await send_daily_report(session, date(2026, 3, 24))
            mock_send.assert_not_called()


@pytest.mark.asyncio()
async def test_send_daily_report_contains_all_symbols(mock_settings, mock_session):
    """Test that report includes all 3 asset symbols in the message body."""
    with patch("src.data.report.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        await send_daily_report(mock_session, date(2026, 3, 24))

        all_texts = [call.args[1] for call in mock_send.call_args_list]
        combined = " ".join(all_texts)
        for sym in ("BBCA", "BTC", "ETH"):
            assert sym in combined, f"Symbol {sym} not found in report"


@pytest.mark.asyncio()
async def test_send_pipeline_failure_alert(mock_settings):
    """Test pipeline failure alert contains 'Pipeline Failed'."""
    with patch("src.data.report.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        await send_pipeline_failure_alert(date(2026, 3, 24))
        assert mock_send.call_count >= 1
        sent_text = mock_send.call_args_list[0].args[1]
        assert "Pipeline Failed" in sent_text


@pytest.mark.asyncio()
async def test_message_splitting_many_decisions(mock_settings):
    """Test message splitting with 20 mock decisions triggers multiple messages per chat."""
    session = AsyncMock()

    # Watchlist returns 20 items
    watchlist_result = MagicMock()
    watchlist_scalars = MagicMock()
    watchlist_scalars.all.return_value = [MagicMock(asset_id=i) for i in range(1, 21)]
    watchlist_result.scalars.return_value = watchlist_scalars

    # 20 decisions with long reasoning to force splitting
    decisions = []
    for i in range(20):
        dec = MagicMock()
        dec.verdict = "BUY"
        dec.score = 0.5
        dec.confidence = 0.8
        dec.reasoning = "A" * 200  # Long reasoning to push size
        dec.risk_warning = None

        asset = MagicMock()
        asset.symbol = f"ASSET{i:02d}"
        asset.name = f"Asset Number {i}"

        decisions.append((dec, asset))

    decisions_result = MagicMock()
    decisions_result.all.return_value = decisions

    call_count = 0

    async def mock_execute(stmt):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return watchlist_result
        return decisions_result

    session.execute = mock_execute

    with patch("src.data.report.send_telegram_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = True
        await send_daily_report(session, date(2026, 3, 24))
        # With 2 chat IDs and 20 long cards, expect multiple messages per chat
        # At minimum more than 2 sends (more than 1 per chat)
        assert mock_send.call_count > 2, f"Expected multiple message sends, got {mock_send.call_count}"
