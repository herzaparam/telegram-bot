"""Tests for IDX ownership data fetching with mocked HTTP."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_asset(symbol: str = "BBCA", asset_id: int = 1) -> MagicMock:
    """Create a mock Asset object for testing."""
    asset = MagicMock()
    asset.id = asset_id
    asset.symbol = symbol
    asset.asset_type = "stock"
    asset.yfinance_symbol = f"{symbol}.JK"
    return asset


class TestFetchOwnership:
    """Tests for fetch_ownership_data."""

    @pytest.mark.asyncio
    async def test_fetch_ownership_parses_shareholder_list(self) -> None:
        """fetch_ownership_data with mocked httpx returns parsed shareholder list."""
        asset = _make_asset("BBCA")
        mock_session = AsyncMock()

        # No existing snapshot (cache miss)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        idx_response = {
            "draw": 1,
            "recordsTotal": 2,
            "recordsFiltered": 2,
            "data": [
                {"ShareHolderName": "PT Dwimuria Investama Andalan", "Percentage": "54.94"},
                {"ShareHolderName": "Public", "Percentage": "45.06"},
            ],
        }

        mock_http_response = MagicMock()
        mock_http_response.status_code = 200
        mock_http_response.json.return_value = idx_response
        mock_http_response.raise_for_status = MagicMock()

        with patch("src.data.ownership_fetcher.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.get.return_value = mock_http_response
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.data.ownership_fetcher import fetch_ownership_data

            result = await fetch_ownership_data(mock_session, asset)

        assert result is not None
        assert "shareholders" in result
        assert len(result["shareholders"]) == 2
        assert result["shareholders"][0]["name"] == "PT Dwimuria Investama Andalan"
        assert result["shareholders"][0]["pct"] == pytest.approx(54.94)

    @pytest.mark.asyncio
    async def test_fetch_ownership_http_error_returns_none(self) -> None:
        """fetch_ownership_data with HTTP error returns None (graceful degradation)."""
        asset = _make_asset("BBCA")
        mock_session = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        with patch("src.data.ownership_fetcher.httpx.AsyncClient") as MockClient:
            client_instance = AsyncMock()
            client_instance.get.side_effect = Exception("Connection timeout")
            MockClient.return_value.__aenter__ = AsyncMock(return_value=client_instance)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)

            from src.data.ownership_fetcher import fetch_ownership_data

            result = await fetch_ownership_data(mock_session, asset)

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_ownership_returns_cached(self) -> None:
        """fetch_ownership_data returns cached snapshot when fresh."""
        asset = _make_asset("BBCA")
        mock_session = AsyncMock()

        cached = MagicMock()
        cached.snapshot_date = date.today()
        cached.shareholders = [{"name": "Cached", "pct": 50.0}]
        cached.public_float_pct = 50.0
        cached.total_shares = 1000000.0

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = cached
        mock_session.execute.return_value = mock_result

        from src.data.ownership_fetcher import fetch_ownership_data

        result = await fetch_ownership_data(mock_session, asset)

        assert result is not None
        assert result["shareholders"] == [{"name": "Cached", "pct": 50.0}]


class TestParseShareholderResponse:
    """Tests for _parse_shareholder_response."""

    def test_parse_valid_response(self) -> None:
        """Parses IDX API response into shareholder list."""
        from src.data.ownership_fetcher import _parse_shareholder_response

        data = {
            "data": [
                {"ShareHolderName": "PT ABC", "Percentage": "54.94"},
                {"ShareHolderName": "Public", "Percentage": "45.06"},
            ],
        }

        result = _parse_shareholder_response(data)
        assert len(result["shareholders"]) == 2
        assert result["shareholders"][0]["pct"] == pytest.approx(54.94)
        assert result["public_float_pct"] is not None

    def test_parse_empty_response(self) -> None:
        """Returns empty shareholders for empty data."""
        from src.data.ownership_fetcher import _parse_shareholder_response

        result = _parse_shareholder_response({"data": []})
        assert result["shareholders"] == []


class TestComputeOwnershipChanges:
    """Tests for _compute_ownership_changes."""

    def test_ownership_change_detected(self) -> None:
        """Detects major ownership changes above 2pp threshold."""
        from src.data.ownership_fetcher import _compute_ownership_changes

        current = {
            "shareholders": [
                {"name": "PT ABC", "pct": 50.0},
                {"name": "Public", "pct": 50.0},
            ]
        }
        previous = {
            "shareholders": [
                {"name": "PT ABC", "pct": 55.0},
                {"name": "Public", "pct": 45.0},
            ]
        }

        result = _compute_ownership_changes(current, previous)
        assert result is not None
        assert len(result["major_changes"]) > 0
        # PT ABC went from 55% -> 50% (decrease)
        abc_changes = [c for c in result["major_changes"] if c["name"] == "PT ABC"]
        assert len(abc_changes) == 1
        assert abc_changes[0]["direction"] == "decrease"

    def test_no_previous_returns_none(self) -> None:
        """Returns None when no previous snapshot."""
        from src.data.ownership_fetcher import _compute_ownership_changes

        result = _compute_ownership_changes({"shareholders": []}, None)
        assert result is None
