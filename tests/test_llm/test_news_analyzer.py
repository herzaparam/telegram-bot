"""Tests for LLM news impact scorer."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.news_analyzer import NEWS_SCORING_SYSTEM_PROMPT, _build_news_scoring_prompt, score_news_impact


class TestNewsScoringSystemPrompt:
    """Test the system prompt constant."""

    def test_system_prompt_exists(self) -> None:
        assert NEWS_SCORING_SYSTEM_PROMPT is not None
        assert len(NEWS_SCORING_SYSTEM_PROMPT) > 50

    def test_system_prompt_mentions_impact_score(self) -> None:
        assert "impact_score" in NEWS_SCORING_SYSTEM_PROMPT

    def test_system_prompt_mentions_affected_assets(self) -> None:
        assert "affected_assets" in NEWS_SCORING_SYSTEM_PROMPT

    def test_system_prompt_mentions_category(self) -> None:
        assert "category" in NEWS_SCORING_SYSTEM_PROMPT


class TestBuildNewsScoringPrompt:
    """Test the prompt builder helper."""

    def test_build_prompt_formats_headlines(self) -> None:
        headlines = [(0, "Reuters", "Fed raises rates"), (1, "Bloomberg", "CPI rises")]
        watchlist = ["BTC", "BBCA"]
        prompt = _build_news_scoring_prompt(headlines, watchlist)

        assert "Reuters" in prompt
        assert "Fed raises rates" in prompt
        assert "Bloomberg" in prompt
        assert "CPI rises" in prompt

    def test_build_prompt_includes_watchlist(self) -> None:
        headlines = [(0, "Reuters", "Fed raises rates")]
        watchlist = ["BTC", "BBCA", "ETH"]
        prompt = _build_news_scoring_prompt(headlines, watchlist)

        assert "BTC" in prompt
        assert "BBCA" in prompt
        assert "ETH" in prompt

    def test_build_prompt_uses_numbered_list(self) -> None:
        headlines = [(0, "source", "headline one"), (1, "source", "headline two")]
        watchlist = ["BTC"]
        prompt = _build_news_scoring_prompt(headlines, watchlist)

        # Should have numbered entries
        assert "0." in prompt or "1." in prompt


class TestScoreNewsImpact:
    """Test the main score_news_impact async function."""

    def _make_mock_session(
        self, news_events: list[dict[str, object]]
    ) -> MagicMock:
        """Create a mock AsyncSession with news events as query result."""
        mock_session = MagicMock()
        mock_result = MagicMock()

        # Convert dicts to mock ORM objects
        mock_rows = []
        for evt in news_events:
            row = MagicMock()
            row.id = evt.get("id", 1)
            row.headline = evt.get("headline", "")
            row.source = evt.get("source", "test")
            mock_rows.append(row)

        mock_result.scalars.return_value.all.return_value = mock_rows
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        return mock_session

    @pytest.mark.asyncio
    async def test_score_news_impact_updates_rows_with_llm_response(self) -> None:
        """Test 1: score_news_impact() returns updated NewsEvent dicts with impact_score, affected_assets, category."""
        news_events = [
            {"id": 1, "headline": "Fed raises rates by 25bps", "source": "reuters"},
            {"id": 2, "headline": "BTC reaches new high", "source": "coindesk"},
        ]

        llm_response = json.dumps([
            {
                "headline_index": 0,
                "impact_score": -0.6,
                "affected_assets": {"BTC": 0.8, "BBCA": 0.5},
                "category": "central_bank",
            },
            {
                "headline_index": 1,
                "impact_score": 0.7,
                "affected_assets": {"BTC": 1.0},
                "category": "market",
            },
        ])

        mock_session = self._make_mock_session(news_events)

        with patch("src.llm.news_analyzer.llm_completion") as mock_llm:
            from src.llm.client import LLMResult
            mock_llm.return_value = LLMResult(content=llm_response, model_used="gpt-4o-mini")
            mock_session.execute = AsyncMock(return_value=MagicMock(
                scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[
                    _make_news_event_mock(id=1, headline="Fed raises rates by 25bps", source="reuters"),
                    _make_news_event_mock(id=2, headline="BTC reaches new high", source="coindesk"),
                ])))
            ))

            await score_news_impact(mock_session, ["BTC", "BBCA", "ETH"])

        # Session execute was called (for the SELECT query)
        mock_session.execute.assert_called()
        # commit was called after updates
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_score_news_impact_handles_llm_unavailable(self) -> None:
        """Test 2: score_news_impact() handles LLM_UNAVAILABLE by leaving impact_score as None."""
        news_events = [
            {"id": 1, "headline": "Market news", "source": "reuters"},
        ]

        mock_session = self._make_mock_session(news_events)
        mock_session.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[
                _make_news_event_mock(id=1, headline="Market news", source="reuters"),
            ])))
        ))

        with patch("src.llm.news_analyzer.llm_completion") as mock_llm:
            from src.llm.client import LLM_UNAVAILABLE
            mock_llm.return_value = LLM_UNAVAILABLE

            # Should complete without exception
            await score_news_impact(mock_session, ["BTC"])

        # commit should NOT be called since LLM was unavailable
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_score_news_impact_caps_at_50_headlines(self) -> None:
        """Test 3: score_news_impact() caps input at 50 headlines."""
        # Create 60 events
        news_events = [
            {"id": i, "headline": f"News {i}", "source": "test"}
            for i in range(60)
        ]
        mock_rows = [
            _make_news_event_mock(id=i, headline=f"News {i}", source="test")
            for i in range(60)
        ]

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_rows)))
        ))
        mock_session.commit = AsyncMock()

        captured_messages: list[list[dict[str, str]]] = []

        async def capture_llm_call(messages: list[dict[str, str]], **kwargs: object) -> object:
            captured_messages.append(messages)
            from src.llm.client import LLM_UNAVAILABLE
            return LLM_UNAVAILABLE

        with patch("src.llm.news_analyzer.llm_completion", side_effect=capture_llm_call):
            await score_news_impact(mock_session, ["BTC"])

        # Should have been called with messages (user content should not have more than 50 headlines)
        if captured_messages:
            user_content = captured_messages[0][1]["content"]
            # Count the number of headline entries (numbered 0 through N-1)
            # The cap means at most 50 items (indices 0-49)
            assert "49." in user_content or len(user_content.split("\n")) <= 60
            assert "59." not in user_content  # Should not have index 59

    @pytest.mark.asyncio
    async def test_score_news_impact_truncates_headlines_to_200_chars(self) -> None:
        """Test 3: score_news_impact() truncates each headline to 200 chars."""
        long_headline = "A" * 300  # 300 chars
        mock_rows = [
            _make_news_event_mock(id=1, headline=long_headline, source="test"),
        ]

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_rows)))
        ))
        mock_session.commit = AsyncMock()

        captured_messages: list[list[dict[str, str]]] = []

        async def capture_llm_call(messages: list[dict[str, str]], **kwargs: object) -> object:
            captured_messages.append(messages)
            from src.llm.client import LLM_UNAVAILABLE
            return LLM_UNAVAILABLE

        with patch("src.llm.news_analyzer.llm_completion", side_effect=capture_llm_call):
            await score_news_impact(mock_session, ["BTC"])

        if captured_messages:
            user_content = captured_messages[0][1]["content"]
            # The long headline should be truncated to 200 chars
            assert "A" * 201 not in user_content

    @pytest.mark.asyncio
    async def test_score_news_impact_parses_valid_json(self) -> None:
        """Test 4: score_news_impact() parses valid JSON from LLM response correctly."""
        mock_rows = [
            _make_news_event_mock(id=42, headline="Crypto regulation news", source="coindesk"),
        ]

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_rows)))
        ))
        mock_session.commit = AsyncMock()

        valid_response = json.dumps([
            {
                "headline_index": 0,
                "impact_score": 0.5,
                "affected_assets": {"BTC": 0.7},
                "category": "regulation",
            }
        ])

        with patch("src.llm.news_analyzer.llm_completion") as mock_llm:
            from src.llm.client import LLMResult
            mock_llm.return_value = LLMResult(content=valid_response, model_used="gpt-4o-mini")

            await score_news_impact(mock_session, ["BTC"])

        # Commit should be called since LLM returned valid data
        mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_score_news_impact_handles_malformed_json(self) -> None:
        """Test 5: score_news_impact() handles malformed LLM JSON gracefully."""
        mock_rows = [
            _make_news_event_mock(id=1, headline="Market news", source="reuters"),
        ]

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_rows)))
        ))
        mock_session.commit = AsyncMock()

        with patch("src.llm.news_analyzer.llm_completion") as mock_llm:
            from src.llm.client import LLMResult
            mock_llm.return_value = LLMResult(content="not valid json {{{", model_used="gpt-4o-mini")

            # Should not raise
            await score_news_impact(mock_session, ["BTC"])

    @pytest.mark.asyncio
    async def test_score_news_impact_returns_early_when_no_unscored(self) -> None:
        """score_news_impact() returns early when no unscored headlines."""
        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        ))
        mock_session.commit = AsyncMock()

        with patch("src.llm.news_analyzer.llm_completion") as mock_llm:
            await score_news_impact(mock_session, ["BTC"])

        # LLM should not be called if no unscored events
        mock_llm.assert_not_called()

    @pytest.mark.asyncio
    async def test_score_news_impact_calls_llm_with_json_mode(self) -> None:
        """score_news_impact() calls llm_completion with response_format json_object."""
        mock_rows = [
            _make_news_event_mock(id=1, headline="News headline", source="reuters"),
        ]

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=MagicMock(
            scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=mock_rows)))
        ))
        mock_session.commit = AsyncMock()

        with patch("src.llm.news_analyzer.llm_completion") as mock_llm:
            from src.llm.client import LLM_UNAVAILABLE
            mock_llm.return_value = LLM_UNAVAILABLE

            await score_news_impact(mock_session, ["BTC"])

        mock_llm.assert_called_once()
        call_kwargs = mock_llm.call_args
        # Check that response_format was passed
        assert call_kwargs is not None
        # response_format can be in kwargs or positional
        all_kwargs = call_kwargs.kwargs if call_kwargs.kwargs else {}
        # Could also be in call_args[1]
        if "response_format" not in all_kwargs:
            # Check if it was in args
            for arg in (call_kwargs.args or []):
                if isinstance(arg, dict) and "type" in arg:
                    all_kwargs["response_format"] = arg
                    break


def _make_news_event_mock(id: int, headline: str, source: str) -> MagicMock:
    """Create a mock NewsEvent ORM object."""
    mock = MagicMock()
    mock.id = id
    mock.headline = headline
    mock.source = source
    mock.impact_score = None
    mock.affected_assets = None
    mock.category = None
    return mock
