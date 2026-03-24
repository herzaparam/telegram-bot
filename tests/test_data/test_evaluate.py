"""Tests for src/data/evaluate.py -- evaluate_stage with classification and multi-window logic."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _make_asset(asset_type: str = "stock", asset_id: int = 1) -> MagicMock:
    """Create a mock Asset object."""
    asset = MagicMock()
    asset.id = asset_id
    asset.asset_type = asset_type
    asset.symbol = "BBCA" if asset_type == "stock" else "BTC"
    return asset


def _make_decision(
    decision_id: int = 1,
    asset_id: int = 1,
    decision_date: date = date(2026, 3, 23),
    verdict: str = "BUY",
    decision_price: float | None = 10000.0,
    decision_price_at: datetime | None = None,
) -> MagicMock:
    """Create a mock DailyDecision object."""
    d = MagicMock()
    d.id = decision_id
    d.asset_id = asset_id
    d.date = decision_date
    d.verdict = verdict
    d.decision_price = decision_price
    d.decision_price_at = decision_price_at or datetime(
        2026, 3, 23, 7, 0, 0, tzinfo=timezone.utc
    )
    d.evaluation_price = None
    d.evaluation_price_at = None
    return d


def _make_signal(category: str, score: float, confidence: float = 0.8) -> MagicMock:
    """Create a mock SignalRecord object."""
    s = MagicMock()
    s.category = category
    s.score = score
    s.confidence = confidence
    return s


# ---------------------------------------------------------------------------
# TestClassifyResult
# ---------------------------------------------------------------------------
class TestClassifyResult:
    """Test _classify_result direction-based classification."""

    def test_buy_price_up_is_correct(self) -> None:
        from src.data.evaluate import _classify_result

        change_pct, was_correct = _classify_result("BUY", 10000.0, 10500.0, "stock", "24h")
        assert change_pct > 0
        assert was_correct is True

    def test_buy_price_down_is_wrong(self) -> None:
        from src.data.evaluate import _classify_result

        change_pct, was_correct = _classify_result("BUY", 10000.0, 9500.0, "stock", "24h")
        assert change_pct < 0
        assert was_correct is False

    def test_sell_price_down_is_correct(self) -> None:
        from src.data.evaluate import _classify_result

        change_pct, was_correct = _classify_result("SELL", 10000.0, 9500.0, "stock", "24h")
        assert change_pct < 0
        assert was_correct is True

    def test_sell_price_up_is_wrong(self) -> None:
        from src.data.evaluate import _classify_result

        change_pct, was_correct = _classify_result("SELL", 10000.0, 10500.0, "stock", "24h")
        assert change_pct > 0
        assert was_correct is False

    def test_strong_buy_price_up_is_correct(self) -> None:
        from src.data.evaluate import _classify_result

        _, was_correct = _classify_result("STRONG BUY", 10000.0, 10100.0, "stock", "24h")
        assert was_correct is True

    def test_strong_sell_price_down_is_correct(self) -> None:
        from src.data.evaluate import _classify_result

        _, was_correct = _classify_result("STRONG SELL", 10000.0, 9900.0, "stock", "24h")
        assert was_correct is True

    def test_hold_within_stock_24h_band_correct(self) -> None:
        """HOLD + price within +-2% band (stock, 24h) = correct."""
        from src.data.evaluate import _classify_result

        # 1% change, within 2% band
        change_pct, was_correct = _classify_result("HOLD", 10000.0, 10100.0, "stock", "24h")
        assert abs(change_pct) <= 2.0
        assert was_correct is True

    def test_hold_outside_stock_24h_band_wrong(self) -> None:
        """HOLD + price outside +-2% band (stock, 24h) = wrong."""
        from src.data.evaluate import _classify_result

        # 3% change, outside 2% band
        change_pct, was_correct = _classify_result("HOLD", 10000.0, 10300.0, "stock", "24h")
        assert abs(change_pct) > 2.0
        assert was_correct is False

    def test_hold_crypto_24h_5pct_band(self) -> None:
        """HOLD + crypto 24h +-5% band."""
        from src.data.evaluate import _classify_result

        # 3% change, within 5% crypto band
        _, was_correct = _classify_result("HOLD", 10000.0, 10300.0, "crypto", "24h")
        assert was_correct is True

        # 6% change, outside 5% crypto band
        _, was_correct = _classify_result("HOLD", 10000.0, 10600.0, "crypto", "24h")
        assert was_correct is False

    def test_hold_stock_7d_5pct_band(self) -> None:
        """HOLD + stock 7d +-5% band (D-04 scaled)."""
        from src.data.evaluate import _classify_result

        # 4% change, within 5% band
        _, was_correct = _classify_result("HOLD", 10000.0, 10400.0, "stock", "7d")
        assert was_correct is True

        # 6% change, outside 5% band
        _, was_correct = _classify_result("HOLD", 10000.0, 10600.0, "stock", "7d")
        assert was_correct is False

    def test_hold_crypto_30d_20pct_band(self) -> None:
        """HOLD + crypto 30d +-20% band (D-04 scaled)."""
        from src.data.evaluate import _classify_result

        # 15% change, within 20% band
        _, was_correct = _classify_result("HOLD", 10000.0, 11500.0, "crypto", "30d")
        assert was_correct is True

        # 25% change, outside 20% band
        _, was_correct = _classify_result("HOLD", 10000.0, 12500.0, "crypto", "30d")
        assert was_correct is False


# ---------------------------------------------------------------------------
# TestGetNextTradingDay
# ---------------------------------------------------------------------------
class TestGetNextTradingDay:
    """Test _get_next_trading_day for IDX calendar."""

    @pytest.mark.asyncio
    async def test_skips_saturday_sunday(self) -> None:
        """Friday -> Monday when no holiday."""
        from src.data.evaluate import _get_next_trading_day

        session = AsyncMock()

        with patch("src.data.evaluate.evaluation_repo") as mock_repo:
            mock_repo.is_idx_holiday = AsyncMock(return_value=False)
            # 2026-03-20 is Friday
            result = await _get_next_trading_day(session, date(2026, 3, 20))
            assert result == date(2026, 3, 23)  # Monday

    @pytest.mark.asyncio
    async def test_skips_idx_holiday_on_weekday(self) -> None:
        """Skips IDX holiday on a weekday."""
        from src.data.evaluate import _get_next_trading_day

        session = AsyncMock()

        with patch("src.data.evaluate.evaluation_repo") as mock_repo:
            # Monday is a holiday, Tuesday is not
            async def mock_is_holiday(s, d):
                return d == date(2026, 3, 23)

            mock_repo.is_idx_holiday = AsyncMock(side_effect=mock_is_holiday)
            # Friday 2026-03-20 -> skip Sat/Sun -> Mon is holiday -> Tuesday 2026-03-24
            result = await _get_next_trading_day(session, date(2026, 3, 20))
            assert result == date(2026, 3, 24)

    @pytest.mark.asyncio
    async def test_normal_weekday(self) -> None:
        """Monday -> Tuesday when no holiday."""
        from src.data.evaluate import _get_next_trading_day

        session = AsyncMock()

        with patch("src.data.evaluate.evaluation_repo") as mock_repo:
            mock_repo.is_idx_holiday = AsyncMock(return_value=False)
            # 2026-03-23 is Monday
            result = await _get_next_trading_day(session, date(2026, 3, 23))
            assert result == date(2026, 3, 24)  # Tuesday


# ---------------------------------------------------------------------------
# TestEvaluateStage
# ---------------------------------------------------------------------------
class TestEvaluateStage:
    """Test evaluate_stage pipeline function."""

    @pytest.mark.asyncio
    async def test_skips_null_decision_price(self) -> None:
        """evaluate_stage skips decision with null decision_price."""
        from src.data.evaluate import evaluate_stage

        asset = _make_asset("stock")
        session = AsyncMock()
        decision = _make_decision(decision_price=None)

        with (
            patch("src.data.evaluate.decision_repo") as mock_drepo,
            patch("src.data.evaluate.evaluation_repo") as mock_erepo,
            patch("src.data.evaluate.signal_repo"),
        ):
            mock_drepo.get_decision = AsyncMock(return_value=decision)
            mock_erepo.get_evaluation = AsyncMock(return_value=None)
            mock_erepo.upsert_evaluation = AsyncMock()
            mock_erepo.recompute_accuracy_stats = AsyncMock()

            await evaluate_stage(session, asset)

            # Should NOT have called upsert_evaluation
            mock_erepo.upsert_evaluation.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_skips_already_evaluated_window(self) -> None:
        """evaluate_stage skips already-evaluated window (idempotent)."""
        from src.data.evaluate import evaluate_stage

        asset = _make_asset("stock")
        session = AsyncMock()
        decision = _make_decision()

        with (
            patch("src.data.evaluate.decision_repo") as mock_drepo,
            patch("src.data.evaluate.evaluation_repo") as mock_erepo,
            patch("src.data.evaluate.signal_repo"),
        ):
            mock_drepo.get_decision = AsyncMock(return_value=decision)
            # Already evaluated for all windows
            mock_erepo.get_evaluation = AsyncMock(return_value=MagicMock())
            mock_erepo.upsert_evaluation = AsyncMock()
            mock_erepo.recompute_accuracy_stats = AsyncMock()

            await evaluate_stage(session, asset)

            mock_erepo.upsert_evaluation.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_evaluates_24h_window(self) -> None:
        """evaluate_stage evaluates 24h window when 1 day has passed."""
        from src.data.evaluate import evaluate_stage

        asset = _make_asset("stock")
        session = AsyncMock()
        decision = _make_decision()

        eval_time = datetime(2026, 3, 24, 15, 0, 0, tzinfo=timezone.utc)

        with (
            patch("src.data.evaluate.decision_repo") as mock_drepo,
            patch("src.data.evaluate.evaluation_repo") as mock_erepo,
            patch("src.data.evaluate.signal_repo") as mock_srepo,
            patch("src.data.evaluate._get_evaluation_price") as mock_price,
            patch("src.data.evaluate.date") as mock_date,
        ):
            mock_date.today.return_value = date(2026, 3, 24)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            mock_drepo.get_decision = AsyncMock(side_effect=lambda s, a, d: decision if d == date(2026, 3, 23) else None)
            mock_erepo.get_evaluation = AsyncMock(return_value=None)
            mock_erepo.upsert_evaluation = AsyncMock()
            mock_erepo.recompute_accuracy_stats = AsyncMock()
            mock_price.return_value = (10500.0, eval_time)
            mock_srepo.get_signals_for_asset = AsyncMock(return_value=[])

            await evaluate_stage(session, asset)

            # Should have called upsert_evaluation at least once (for 24h window)
            assert mock_erepo.upsert_evaluation.await_count >= 1

    @pytest.mark.asyncio
    async def test_does_not_evaluate_immature_window(self) -> None:
        """evaluate_stage does NOT evaluate 7d window when only 3 days have passed."""
        from src.data.evaluate import evaluate_stage

        asset = _make_asset("stock")
        session = AsyncMock()

        with (
            patch("src.data.evaluate.decision_repo") as mock_drepo,
            patch("src.data.evaluate.evaluation_repo") as mock_erepo,
            patch("src.data.evaluate.signal_repo") as mock_srepo,
            patch("src.data.evaluate._get_evaluation_price") as mock_price,
            patch("src.data.evaluate.date") as mock_date,
        ):
            mock_date.today.return_value = date(2026, 3, 24)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)

            # Only return a decision for 24h window (1 day back), None for others
            decision_24h = _make_decision(decision_date=date(2026, 3, 23))

            async def get_dec(s, a, d):
                if d == date(2026, 3, 23):
                    return decision_24h
                return None

            mock_drepo.get_decision = AsyncMock(side_effect=get_dec)
            mock_erepo.get_evaluation = AsyncMock(return_value=None)
            mock_erepo.upsert_evaluation = AsyncMock()
            mock_erepo.recompute_accuracy_stats = AsyncMock()
            mock_price.return_value = (10500.0, datetime(2026, 3, 24, 15, 0, 0, tzinfo=timezone.utc))
            mock_srepo.get_signals_for_asset = AsyncMock(return_value=[])

            await evaluate_stage(session, asset)

            # Only 24h window should have been evaluated (decision exists only for 1 day back)
            # 3d, 7d, 30d should NOT have decisions
            upsert_calls = mock_erepo.upsert_evaluation.await_count
            assert upsert_calls == 1  # Only the 24h window

    @pytest.mark.asyncio
    async def test_populates_engine_results(self) -> None:
        """evaluate_stage populates engine_results JSONB from signals."""
        from src.data.evaluate import evaluate_stage

        asset = _make_asset("stock")
        session = AsyncMock()
        decision = _make_decision(verdict="BUY")

        signals = [
            _make_signal("technical", 0.5),
            _make_signal("quantitative", -0.3),
        ]

        with (
            patch("src.data.evaluate.decision_repo") as mock_drepo,
            patch("src.data.evaluate.evaluation_repo") as mock_erepo,
            patch("src.data.evaluate.signal_repo") as mock_srepo,
            patch("src.data.evaluate._get_evaluation_price") as mock_price,
            patch("src.data.evaluate.date") as mock_date,
        ):
            mock_date.today.return_value = date(2026, 3, 24)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            mock_drepo.get_decision = AsyncMock(side_effect=lambda s, a, d: decision if d == date(2026, 3, 23) else None)
            mock_erepo.get_evaluation = AsyncMock(return_value=None)
            mock_erepo.upsert_evaluation = AsyncMock()
            mock_erepo.recompute_accuracy_stats = AsyncMock()
            mock_price.return_value = (10500.0, datetime(2026, 3, 24, 15, 0, 0, tzinfo=timezone.utc))
            mock_srepo.get_signals_for_asset = AsyncMock(return_value=signals)

            await evaluate_stage(session, asset)

            # Check engine_results was passed to upsert
            call_kwargs = mock_erepo.upsert_evaluation.call_args_list[0]
            engine_results = call_kwargs.kwargs.get("engine_results") or call_kwargs[1].get("engine_results")
            assert engine_results is not None
            assert "technical" in engine_results
            assert "quantitative" in engine_results

    @pytest.mark.asyncio
    async def test_updates_decision_evaluation_price_for_24h(self) -> None:
        """evaluate_stage updates DailyDecision.evaluation_price for 24h window."""
        from src.data.evaluate import evaluate_stage

        asset = _make_asset("stock")
        session = AsyncMock()
        decision = _make_decision()

        eval_time = datetime(2026, 3, 24, 15, 0, 0, tzinfo=timezone.utc)

        with (
            patch("src.data.evaluate.decision_repo") as mock_drepo,
            patch("src.data.evaluate.evaluation_repo") as mock_erepo,
            patch("src.data.evaluate.signal_repo") as mock_srepo,
            patch("src.data.evaluate._get_evaluation_price") as mock_price,
            patch("src.data.evaluate.date") as mock_date,
        ):
            mock_date.today.return_value = date(2026, 3, 24)
            mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
            mock_drepo.get_decision = AsyncMock(side_effect=lambda s, a, d: decision if d == date(2026, 3, 23) else None)
            mock_erepo.get_evaluation = AsyncMock(return_value=None)
            mock_erepo.upsert_evaluation = AsyncMock()
            mock_erepo.recompute_accuracy_stats = AsyncMock()
            mock_price.return_value = (10500.0, eval_time)
            mock_srepo.get_signals_for_asset = AsyncMock(return_value=[])

            await evaluate_stage(session, asset)

            # Decision should have evaluation_price set
            assert decision.evaluation_price == 10500.0
            assert decision.evaluation_price_at == eval_time

    @pytest.mark.asyncio
    async def test_crypto_daily_fallback_for_long_windows(self) -> None:
        """evaluate_stage: crypto uses daily close fallback for 7d/30d windows."""
        from src.data.evaluate import _get_evaluation_price

        asset = _make_asset("crypto", asset_id=10)
        decision = _make_decision(
            asset_id=10,
            decision_date=date(2026, 3, 17),
            decision_price_at=datetime(2026, 3, 17, 7, 0, 0, tzinfo=timezone.utc),
        )
        session = AsyncMock()

        # For 7d window on crypto, should use daily close (not hourly)
        mock_row = MagicMock()
        mock_row.close = 68000.0
        mock_row.time = datetime(2026, 3, 24, 0, 0, 0, tzinfo=timezone.utc)

        mock_result = MagicMock()
        mock_result.one_or_none.return_value = mock_row

        session.scalars.return_value = mock_result

        with patch("src.data.evaluate._get_next_trading_day") as mock_td:
            mock_td.return_value = date(2026, 3, 24)
            result = await _get_evaluation_price(
                session, asset, decision, "7d", timedelta(days=7)
            )

        assert result is not None
        assert result[0] == 68000.0


# ---------------------------------------------------------------------------
# TestComputeEngineResults
# ---------------------------------------------------------------------------
class TestComputeEngineResults:
    """Test _compute_engine_results signal processing."""

    @pytest.mark.asyncio
    async def test_engine_results_correct_signals(self) -> None:
        """Positive score + positive change = correct for each engine."""
        from src.data.evaluate import _compute_engine_results

        session = AsyncMock()
        signals = [
            _make_signal("technical", 0.5),
            _make_signal("quantitative", -0.3),
        ]

        with patch("src.data.evaluate.signal_repo") as mock_srepo:
            mock_srepo.get_signals_for_asset = AsyncMock(return_value=signals)
            result = await _compute_engine_results(session, 1, date(2026, 3, 23), 5.0)

        assert result["technical"]["correct"] is True  # positive score, positive change
        assert result["quantitative"]["correct"] is False  # negative score, positive change


# ---------------------------------------------------------------------------
# TestHoldBands
# ---------------------------------------------------------------------------
class TestHoldBands:
    """Verify HOLD_BANDS constant values match plan specs."""

    def test_hold_bands_values(self) -> None:
        from src.data.evaluate import HOLD_BANDS

        assert HOLD_BANDS["24h"]["stock"] == 0.02
        assert HOLD_BANDS["24h"]["crypto"] == 0.05
        assert HOLD_BANDS["3d"]["stock"] == 0.03
        assert HOLD_BANDS["3d"]["crypto"] == 0.08
        assert HOLD_BANDS["7d"]["stock"] == 0.05
        assert HOLD_BANDS["7d"]["crypto"] == 0.12
        assert HOLD_BANDS["30d"]["stock"] == 0.08
        assert HOLD_BANDS["30d"]["crypto"] == 0.20
