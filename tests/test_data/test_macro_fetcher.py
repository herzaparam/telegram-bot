"""Tests for macro data fetcher (FRED API wrapper)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestFetchMacroData:
    """Tests for fetch_macro_data() function."""

    @pytest.mark.asyncio
    async def test_fetch_macro_data_upserts_all_series(self) -> None:
        """fetch_macro_data() fetches 4 FRED series and upserts MacroData rows."""
        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock()

        from datetime import date

        series_results = {
            "DFF": (date(2026, 3, 1), 5.33),
            "CPIAUCSL": (date(2026, 2, 1), 314.5),
            "DTWEXBGS": (date(2026, 3, 15), 122.4),
            "CCUSMA02IDM618N": (date(2026, 2, 1), 16200.0),
        }

        with (
            patch("src.data.macro_fetcher.settings") as mock_settings,
            patch(
                "src.data.macro_fetcher._fetch_fred_series",
                side_effect=lambda fred, series_id: series_results.get(series_id),
            ),
        ):
            mock_settings.fred_api_key = "test-key-123"

            from src.data.macro_fetcher import fetch_macro_data

            await fetch_macro_data(mock_session)

        # execute should have been called 4 times (one per series upsert)
        assert mock_session.execute.call_count >= 4

    @pytest.mark.asyncio
    async def test_fetch_macro_data_skips_when_no_api_key(self) -> None:
        """fetch_macro_data() returns empty when FRED_API_KEY is empty string."""
        mock_session = AsyncMock()

        with patch("src.data.macro_fetcher.settings") as mock_settings:
            mock_settings.fred_api_key = ""

            from src.data.macro_fetcher import fetch_macro_data

            await fetch_macro_data(mock_session)

        # No DB operations should have happened
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_macro_data_partial_success_on_series_error(self) -> None:
        """fetch_macro_data() catches FRED API errors per-series (partial success)."""
        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock()

        from datetime import date

        call_count = 0

        def flaky_fetch(fred: object, series_id: str) -> tuple | None:
            nonlocal call_count
            call_count += 1
            if series_id == "DFF":
                raise RuntimeError("FRED API error")
            return (date(2026, 3, 1), 100.0)

        with (
            patch("src.data.macro_fetcher.settings") as mock_settings,
            patch(
                "src.data.macro_fetcher._fetch_fred_series",
                side_effect=flaky_fetch,
            ),
        ):
            mock_settings.fred_api_key = "test-key-123"

            from src.data.macro_fetcher import fetch_macro_data

            # Should not raise even though one series fails
            await fetch_macro_data(mock_session)

        # 4 series attempted, 1 failed, 3 upserted
        assert call_count == 4
        assert mock_session.execute.call_count >= 3
