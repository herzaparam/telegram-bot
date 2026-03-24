"""Tests for /lessons bot command handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def _mock_auth():
    """Patch is_authorized to return True."""
    with patch("src.bot.handlers.lessons.is_authorized", return_value=True) as m:
        yield m


@pytest.fixture
def _mock_auth_deny():
    """Patch is_authorized to return False."""
    with patch("src.bot.handlers.lessons.is_authorized", return_value=False) as m:
        yield m


@pytest.fixture
def sample_display_data():
    """Sample data returned by lesson_repo.get_lessons_for_display."""
    return {
        "recently_learned": [
            {
                "id": 1,
                "lesson": "RSI reversals precede bounces",
                "tier": "pattern",
                "times_observed": 12,
                "times_applied": 8,
                "accuracy": 0.75,
                "asset_type": "stock",
                "engine_tags": ["technical"],
                "topic": "momentum",
                "date": "2026-03-20",
            },
        ],
        "top_lessons": [
            {
                "id": 2,
                "lesson": "Sentiment overreaction fades within 3 days",
                "tier": "rule",
                "times_observed": 35,
                "times_applied": 20,
                "accuracy": 0.80,
                "asset_type": "all",
                "engine_tags": ["sentiment"],
                "topic": "sentiment",
                "date": "2026-03-15",
            },
        ],
    }


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_auth")
@patch("src.bot.handlers.lessons.async_session_factory")
@patch("src.bot.handlers.lessons.lesson_repo")
async def test_lessons_handler_no_filters(
    mock_lesson_repo: MagicMock,
    mock_session_factory: MagicMock,
    mock_update,
    mock_context,
    sample_display_data,
) -> None:
    """No filters: returns both recently_learned and top_lessons sections."""
    from src.bot.handlers.lessons import lessons_handler

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_lesson_repo.get_lessons_for_display = AsyncMock(return_value=sample_display_data)

    await lessons_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited()
    sent_text = mock_update.message.reply_text.call_args[0][0]
    assert "Lessons" in sent_text
    assert "Recently Learned (7d)" in sent_text


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_auth")
@patch("src.bot.handlers.lessons.async_session_factory")
@patch("src.bot.handlers.lessons.lesson_repo")
async def test_lessons_handler_with_asset_filter(
    mock_lesson_repo: MagicMock,
    mock_session_factory: MagicMock,
    mock_update,
    mock_context,
    sample_display_data,
) -> None:
    """Asset filter passed through to get_lessons_for_display."""
    from src.bot.handlers.lessons import lessons_handler

    mock_context.args = ["crypto"]
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_lesson_repo.get_lessons_for_display = AsyncMock(return_value=sample_display_data)

    await lessons_handler(mock_update, mock_context)

    call_kwargs = mock_lesson_repo.get_lessons_for_display.call_args[1]
    assert call_kwargs.get("asset_type") == "crypto"


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_auth")
@patch("src.bot.handlers.lessons.async_session_factory")
@patch("src.bot.handlers.lessons.lesson_repo")
async def test_lessons_handler_with_engine_filter(
    mock_lesson_repo: MagicMock,
    mock_session_factory: MagicMock,
    mock_update,
    mock_context,
    sample_display_data,
) -> None:
    """Engine filter passed through to get_lessons_for_display."""
    from src.bot.handlers.lessons import lessons_handler

    mock_context.args = ["technical"]
    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_lesson_repo.get_lessons_for_display = AsyncMock(return_value=sample_display_data)

    await lessons_handler(mock_update, mock_context)

    call_kwargs = mock_lesson_repo.get_lessons_for_display.call_args[1]
    assert call_kwargs.get("engine_filter") == "technical"


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_auth")
async def test_lessons_handler_invalid_filter(
    mock_update,
    mock_context,
) -> None:
    """Invalid filter returns error message."""
    from src.bot.handlers.lessons import lessons_handler

    mock_context.args = ["invalid_thing"]

    await lessons_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_awaited_once()
    sent_text = mock_update.message.reply_text.call_args[0][0]
    assert "Unknown filter" in sent_text


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_auth")
@patch("src.bot.handlers.lessons.async_session_factory")
@patch("src.bot.handlers.lessons.lesson_repo")
async def test_lessons_handler_empty_state(
    mock_lesson_repo: MagicMock,
    mock_session_factory: MagicMock,
    mock_update,
    mock_context,
) -> None:
    """Empty data returns 'No lessons learned yet' message."""
    from src.bot.handlers.lessons import lessons_handler

    mock_session = AsyncMock()
    mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_lesson_repo.get_lessons_for_display = AsyncMock(
        return_value={"recently_learned": [], "top_lessons": []}
    )

    await lessons_handler(mock_update, mock_context)

    sent_text = mock_update.message.reply_text.call_args[0][0]
    assert "No lessons learned yet" in sent_text
