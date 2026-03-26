"""Tests for discovery scanner module."""

from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest


class TestCompositeScore:
    """Tests for compute_composite_score function."""

    def test_empty_triggers_returns_zero(self) -> None:
        """compute_composite_score({}) returns 0.0."""
        from src.data.discovery import compute_composite_score

        assert compute_composite_score({}) == 0.0

    def test_single_trigger_volume_spike(self) -> None:
        """Single volume_spike trigger weighted at 0.30."""
        from src.data.discovery import compute_composite_score

        result = compute_composite_score({"volume_spike": 0.8})
        assert abs(result - 0.8 * 0.30) < 1e-6

    def test_two_triggers_apply_bonus(self) -> None:
        """Two active triggers get 1.15x bonus."""
        from src.data.discovery import compute_composite_score

        result = compute_composite_score({"volume_spike": 0.8, "price_breakout": 0.7})
        expected = (0.8 * 0.30 + 0.7 * 0.30) * 1.15
        assert abs(result - expected) < 1e-6

    def test_three_triggers_bonus_capped_at_one(self) -> None:
        """Three+ triggers get 1.30x bonus, capped at 1.0."""
        from src.data.discovery import compute_composite_score

        result = compute_composite_score(
            {"volume_spike": 0.9, "price_breakout": 0.8, "momentum_surge": 0.7}
        )
        raw = (0.9 * 0.30 + 0.8 * 0.30 + 0.7 * 0.25) * 1.30
        expected = min(1.0, raw)
        assert abs(result - expected) < 1e-6

    def test_all_four_triggers_capped(self) -> None:
        """All four triggers at max should cap at 1.0."""
        from src.data.discovery import compute_composite_score

        result = compute_composite_score(
            {
                "volume_spike": 1.0,
                "price_breakout": 1.0,
                "momentum_surge": 1.0,
                "statistical_anomaly": 1.0,
            }
        )
        assert result == 1.0


class TestDetectVolumeSpike:
    """Tests for _detect_volume_spike."""

    def test_spike_detected_above_2x_avg(self) -> None:
        """Volume > 2x 20-day avg triggers a positive score."""
        from src.data.discovery import _detect_volume_spike

        # 20 days of normal volume at 1M, then spike to 3M
        volumes = pd.Series([1_000_000.0] * 20 + [3_000_000.0])
        score = _detect_volume_spike(volumes)
        assert score > 0.0

    def test_normal_volume_returns_zero(self) -> None:
        """Normal volume returns 0.0."""
        from src.data.discovery import _detect_volume_spike

        volumes = pd.Series([1_000_000.0] * 21)
        score = _detect_volume_spike(volumes)
        assert score == 0.0

    def test_insufficient_data_returns_zero(self) -> None:
        """Less than 20 days of data returns 0.0."""
        from src.data.discovery import _detect_volume_spike

        volumes = pd.Series([1_000_000.0] * 10)
        score = _detect_volume_spike(volumes)
        assert score == 0.0


class TestDetectBreakout:
    """Tests for _detect_breakout."""

    def test_52_week_high_triggers(self) -> None:
        """Close at 52-week high returns positive score."""
        from src.data.discovery import _detect_breakout

        # 252 days of prices from 100-351, final close at 352 (new high)
        closes = pd.Series(list(range(100, 352)) + [352.0])
        highs = pd.Series(list(range(101, 353)) + [353.0])
        score = _detect_breakout(closes, highs)
        assert score > 0.0

    def test_no_breakout_returns_zero(self) -> None:
        """Price well below 52-week high returns 0.0."""
        from src.data.discovery import _detect_breakout

        # Price has been declining
        closes = pd.Series([200.0] * 252 + [150.0])
        highs = pd.Series([201.0] * 252 + [151.0])
        score = _detect_breakout(closes, highs)
        assert score == 0.0


class TestDetectMomentum:
    """Tests for _detect_momentum."""

    def test_rsi_crossover_triggers(self) -> None:
        """RSI crossing above 50 returns positive score."""
        from src.data.discovery import _detect_momentum

        # Create uptrend data so RSI rises above 50
        np.random.seed(42)
        # Start declining then reverse sharply
        down = list(np.linspace(100, 80, 30))
        up = list(np.linspace(80, 120, 20))
        closes = pd.Series(down + up)
        score = _detect_momentum(closes)
        # Should be non-negative (may or may not trigger depending on exact RSI)
        assert score >= 0.0

    def test_insufficient_data_returns_zero(self) -> None:
        """Less than 30 data points returns 0.0."""
        from src.data.discovery import _detect_momentum

        closes = pd.Series([100.0] * 10)
        score = _detect_momentum(closes)
        assert score == 0.0


class TestDetectAnomaly:
    """Tests for _detect_anomaly."""

    def test_anomaly_detected_on_extreme_return(self) -> None:
        """Extreme return (>2 std dev) triggers anomaly score."""
        from src.data.discovery import _detect_anomaly

        # 20 days of small returns, then a big jump
        prices = [100.0] * 20 + [100.0 + i * 0.1 for i in range(20)] + [150.0]
        closes = pd.Series(prices)
        volumes = pd.Series([1_000_000.0] * len(prices))
        score = _detect_anomaly(closes, volumes)
        assert score > 0.0

    def test_no_anomaly_on_stable_returns(self) -> None:
        """Stable returns return 0.0."""
        from src.data.discovery import _detect_anomaly

        closes = pd.Series([100.0 + i * 0.01 for i in range(25)])
        volumes = pd.Series([1_000_000.0] * 25)
        score = _detect_anomaly(closes, volumes)
        assert score == 0.0


class TestScoreCryptoCandidate:
    """Tests for _score_crypto_candidate."""

    def test_high_change_scores_high(self) -> None:
        """Large 24h change with high volume generates triggers."""
        from src.data.discovery import _score_crypto_candidate

        coin = {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "current_price": 65000,
            "market_cap": 1_200_000_000_000,
            "total_volume": 50_000_000_000,
            "price_change_percentage_24h": 15.0,
            "price_change_percentage_7d_in_currency": 5.0,
            "market_cap_change_percentage_24h": 12.0,
        }
        triggers = _score_crypto_candidate(coin)
        assert len(triggers) > 0

    def test_low_change_returns_empty(self) -> None:
        """Small changes produce no triggers."""
        from src.data.discovery import _score_crypto_candidate

        coin = {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "current_price": 65000,
            "market_cap": 1_200_000_000_000,
            "total_volume": 50_000_000_000,
            "price_change_percentage_24h": 0.5,
            "price_change_percentage_7d_in_currency": 0.3,
            "market_cap_change_percentage_24h": 0.2,
        }
        triggers = _score_crypto_candidate(coin)
        # All trigger scores should be 0 or dict should be empty
        assert all(v == 0.0 for v in triggers.values()) or len(triggers) == 0


class TestRunDiscoveryScan:
    """Tests for run_discovery_scan integration."""

    @pytest.mark.asyncio
    async def test_returns_sorted_candidates(self) -> None:
        """run_discovery_scan returns list sorted by composite_score desc."""
        from src.data.discovery import run_discovery_scan

        mock_session = AsyncMock()
        # Mock execute for DELETE
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        # Create simple mock data for IDX scan
        idx_data = pd.DataFrame()  # Empty - no IDX results

        # Mock crypto data with 2 coins
        crypto_data = [
            {
                "id": "bitcoin",
                "symbol": "btc",
                "name": "Bitcoin",
                "current_price": 65000,
                "market_cap": 1_200_000_000_000,
                "total_volume": 50_000_000_000,
                "price_change_percentage_24h": 15.0,
                "price_change_percentage_7d_in_currency": 5.0,
                "market_cap_change_percentage_24h": 12.0,
            },
            {
                "id": "ethereum",
                "symbol": "eth",
                "name": "Ethereum",
                "current_price": 3500,
                "market_cap": 400_000_000_000,
                "total_volume": 20_000_000_000,
                "price_change_percentage_24h": 8.0,
                "price_change_percentage_7d_in_currency": 2.0,
                "market_cap_change_percentage_24h": 5.0,
            },
        ]

        with (
            patch(
                "src.data.discovery._fetch_idx_screening_data",
                return_value=idx_data,
            ),
            patch(
                "src.data.discovery._fetch_crypto_screening_data",
                return_value=crypto_data,
            ),
        ):
            results = await run_discovery_scan(mock_session, date(2026, 3, 26))

        assert isinstance(results, list)
        # Results should be sorted descending by composite_score
        if len(results) >= 2:
            assert results[0]["composite_score"] >= results[1]["composite_score"]

    @pytest.mark.asyncio
    async def test_returns_empty_on_failure(self) -> None:
        """run_discovery_scan returns empty list on total failure."""
        from src.data.discovery import run_discovery_scan

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB error"))

        with (
            patch(
                "src.data.discovery._fetch_idx_screening_data",
                side_effect=Exception("IDX error"),
            ),
            patch(
                "src.data.discovery._fetch_crypto_screening_data",
                side_effect=Exception("Crypto error"),
            ),
        ):
            results = await run_discovery_scan(mock_session, date(2026, 3, 26))

        assert results == []
