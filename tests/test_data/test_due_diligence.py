"""Tests for sector benchmark, management quality, competitive positioning, DD flags."""

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


def _make_fundamental(
    asset_id: int,
    trailing_pe: float | None = None,
    price_to_book: float | None = None,
    return_on_equity: float | None = None,
    revenue_growth: float | None = None,
    debt_to_equity: float | None = None,
) -> MagicMock:
    """Create a mock StockFundamental."""
    f = MagicMock()
    f.asset_id = asset_id
    f.trailing_pe = trailing_pe
    f.price_to_book = price_to_book
    f.return_on_equity = return_on_equity
    f.revenue_growth = revenue_growth
    f.debt_to_equity = debt_to_equity
    return f


def _make_financial_data(
    asset_id: int,
    metric_name: str,
    metric_value: float,
    period: str,
    period_date: date | None = None,
) -> MagicMock:
    """Create a mock FinancialData record."""
    fd = MagicMock()
    fd.asset_id = asset_id
    fd.metric_name = metric_name
    fd.metric_value = metric_value
    fd.period = period
    fd.period_date = period_date or date(2025, 1, 1)
    return fd


class TestSectorBenchmark:
    """Tests for compute_sector_benchmark."""

    @pytest.mark.asyncio
    async def test_pe_below_sector_median(self) -> None:
        """Company P/E=12 with sector median P/E=15 returns pe_vs_median=-20.0."""
        asset = _make_asset("BBCA", asset_id=1)

        # Company fundamental
        company_fund = _make_fundamental(1, trailing_pe=12.0, return_on_equity=0.18)

        # Sector peers (including company)
        peer_funds = [
            _make_fundamental(1, trailing_pe=12.0, return_on_equity=0.18),
            _make_fundamental(2, trailing_pe=15.0, return_on_equity=0.12),
            _make_fundamental(3, trailing_pe=18.0, return_on_equity=0.10),
        ]

        mock_session = AsyncMock()
        # First query: company fundamental
        result1 = MagicMock()
        result1.scalar_one_or_none.return_value = company_fund
        # Second query: sector peers
        result2 = MagicMock()
        result2.all.return_value = peer_funds

        mock_session.execute.side_effect = [result1, result2]

        from src.data.due_diligence import compute_sector_benchmark

        result = await compute_sector_benchmark(mock_session, asset, "banking")

        assert result is not None
        assert result["pe"]["value"] == 12.0
        assert result["pe"]["median"] == 15.0
        assert result["pe"]["vs_median"] == pytest.approx(-20.0)
        assert result["pe"]["position"] == "below"

    @pytest.mark.asyncio
    async def test_roe_above_sector_median(self) -> None:
        """Company ROE=18% with sector median 12% returns roe_vs_median=+50.0."""
        asset = _make_asset("BBCA", asset_id=1)

        company_fund = _make_fundamental(1, return_on_equity=0.18)

        peer_funds = [
            _make_fundamental(1, return_on_equity=0.18),
            _make_fundamental(2, return_on_equity=0.12),
            _make_fundamental(3, return_on_equity=0.06),
        ]

        mock_session = AsyncMock()
        result1 = MagicMock()
        result1.scalar_one_or_none.return_value = company_fund
        result2 = MagicMock()
        result2.all.return_value = peer_funds

        mock_session.execute.side_effect = [result1, result2]

        from src.data.due_diligence import compute_sector_benchmark

        result = await compute_sector_benchmark(mock_session, asset, "banking")

        assert result is not None
        assert result["roe"]["value"] == pytest.approx(0.18)
        assert result["roe"]["median"] == pytest.approx(0.12)
        assert result["roe"]["vs_median"] == pytest.approx(50.0)
        assert result["roe"]["position"] == "above"

    @pytest.mark.asyncio
    async def test_no_sector_data_returns_none(self) -> None:
        """compute_sector_benchmark with no sector data returns None."""
        asset = _make_asset("BBCA", asset_id=1)

        mock_session = AsyncMock()
        result1 = MagicMock()
        result1.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result1

        from src.data.due_diligence import compute_sector_benchmark

        result = await compute_sector_benchmark(mock_session, asset, "banking")

        assert result is None


class TestManagementQuality:
    """Tests for compute_management_quality."""

    def test_sufficient_data_returns_positive_score(self) -> None:
        """compute_management_quality with 4+ quarters revenue growth returns score >0."""
        records = [
            _make_financial_data(1, "revenue", 100.0, "Q1-2024", date(2024, 3, 31)),
            _make_financial_data(1, "revenue", 110.0, "Q2-2024", date(2024, 6, 30)),
            _make_financial_data(1, "revenue", 120.0, "Q3-2024", date(2024, 9, 30)),
            _make_financial_data(1, "revenue", 130.0, "Q4-2024", date(2024, 12, 31)),
            _make_financial_data(1, "total_equity", 500.0, "Q1-2024", date(2024, 3, 31)),
            _make_financial_data(1, "total_equity", 510.0, "Q2-2024", date(2024, 6, 30)),
            _make_financial_data(1, "total_equity", 520.0, "Q3-2024", date(2024, 9, 30)),
            _make_financial_data(1, "total_equity", 530.0, "Q4-2024", date(2024, 12, 31)),
            _make_financial_data(1, "net_profit", 50.0, "Q1-2024", date(2024, 3, 31)),
            _make_financial_data(1, "net_profit", 55.0, "Q2-2024", date(2024, 6, 30)),
            _make_financial_data(1, "net_profit", 60.0, "Q3-2024", date(2024, 9, 30)),
            _make_financial_data(1, "net_profit", 65.0, "Q4-2024", date(2024, 12, 31)),
        ]

        from src.data.due_diligence import compute_management_quality

        result = compute_management_quality(records)

        assert result["score"] > 0
        assert "revenue_cagr" in result["detail"]

    def test_insufficient_data_returns_zero(self) -> None:
        """compute_management_quality with <4 records returns score=0."""
        records = [
            _make_financial_data(1, "revenue", 100.0, "Q1-2024"),
            _make_financial_data(1, "revenue", 110.0, "Q2-2024"),
        ]

        from src.data.due_diligence import compute_management_quality

        result = compute_management_quality(records)

        assert result["score"] == 0.0
        assert result["label"] == "Insufficient data"
        assert result["detail"] == {}

    def test_excellent_management_score(self) -> None:
        """15% CAGR and 20% ROE returns score >0.7 label='Excellent'."""
        # Create records that produce ~15% CAGR and ~20% ROE
        records = [
            _make_financial_data(1, "revenue", 100.0, "Q1-2024", date(2024, 3, 31)),
            _make_financial_data(1, "revenue", 103.5, "Q2-2024", date(2024, 6, 30)),
            _make_financial_data(1, "revenue", 107.1, "Q3-2024", date(2024, 9, 30)),
            _make_financial_data(1, "revenue", 115.0, "Q4-2024", date(2024, 12, 31)),
            # ROE = net_profit / total_equity ~ 20%
            _make_financial_data(1, "net_profit", 100.0, "Q1-2024", date(2024, 3, 31)),
            _make_financial_data(1, "net_profit", 100.0, "Q2-2024", date(2024, 6, 30)),
            _make_financial_data(1, "net_profit", 100.0, "Q3-2024", date(2024, 9, 30)),
            _make_financial_data(1, "net_profit", 100.0, "Q4-2024", date(2024, 12, 31)),
            _make_financial_data(1, "total_equity", 500.0, "Q1-2024", date(2024, 3, 31)),
            _make_financial_data(1, "total_equity", 500.0, "Q2-2024", date(2024, 6, 30)),
            _make_financial_data(1, "total_equity", 500.0, "Q3-2024", date(2024, 9, 30)),
            _make_financial_data(1, "total_equity", 500.0, "Q4-2024", date(2024, 12, 31)),
        ]

        from src.data.due_diligence import compute_management_quality

        result = compute_management_quality(records)

        assert result["score"] > 0.7
        assert result["label"] == "Excellent"


class TestCompetitivePosition:
    """Tests for compute_competitive_position."""

    @pytest.mark.asyncio
    async def test_returns_rank_and_total(self) -> None:
        """compute_competitive_position returns rank and total count within sector."""
        asset = _make_asset("BBCA", asset_id=1)

        peer_funds = [
            _make_fundamental(1, return_on_equity=0.20, revenue_growth=0.15, debt_to_equity=0.5),
            _make_fundamental(2, return_on_equity=0.12, revenue_growth=0.10, debt_to_equity=1.0),
            _make_fundamental(3, return_on_equity=0.08, revenue_growth=0.05, debt_to_equity=1.5),
        ]

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.all.return_value = peer_funds
        mock_session.execute.return_value = mock_result

        from src.data.due_diligence import compute_competitive_position

        result = await compute_competitive_position(mock_session, asset, "banking")

        assert "rank" in result
        assert "of" in result
        assert result["of"] == 3
        assert result["rank"] >= 1
        assert "moat_indicators" in result


class TestDDFlags:
    """Tests for generate_dd_flags."""

    def test_insider_decrease_flag(self) -> None:
        """Insider decrease >5pp returns flag with severity='warning'."""
        from src.data.due_diligence import generate_dd_flags

        ownership_changes = {
            "major_changes": [
                {"name": "PT ABC", "old_pct": 55.0, "new_pct": 49.0, "direction": "decrease"},
            ],
        }

        flags = generate_dd_flags(
            sector_bench=None,
            mgmt_quality=None,
            ownership_changes=ownership_changes,
        )

        assert len(flags) > 0
        insider_flags = [f for f in flags if f["type"] == "insider_selling"]
        assert len(insider_flags) == 1
        assert insider_flags[0]["severity"] == "warning"

    def test_weak_management_flag(self) -> None:
        """Management score <0.3 returns flag with severity='warning'."""
        from src.data.due_diligence import generate_dd_flags

        flags = generate_dd_flags(
            sector_bench=None,
            mgmt_quality={"score": 0.2, "label": "Weak", "detail": {}},
            ownership_changes=None,
        )

        mgmt_flags = [f for f in flags if f["type"] == "weak_management"]
        assert len(mgmt_flags) == 1
        assert mgmt_flags[0]["severity"] == "warning"

    def test_overvaluation_flag(self) -> None:
        """P/E >50% above sector median returns overvaluation_risk flag."""
        from src.data.due_diligence import generate_dd_flags

        sector_bench = {
            "pe": {"value": 30.0, "median": 15.0, "vs_median": 100.0, "position": "above"},
            "debt_to_equity": {"value": 0.5, "median": 1.0, "vs_median": -50.0, "position": "below"},
        }

        flags = generate_dd_flags(
            sector_bench=sector_bench,
            mgmt_quality=None,
            ownership_changes=None,
        )

        overval_flags = [f for f in flags if f["type"] == "overvaluation_risk"]
        assert len(overval_flags) == 1
        assert overval_flags[0]["severity"] == "info"

    def test_high_leverage_flag(self) -> None:
        """D/E >2x sector median returns high_leverage flag."""
        from src.data.due_diligence import generate_dd_flags

        sector_bench = {
            "pe": {"value": 15.0, "median": 15.0, "vs_median": 0.0, "position": "at_median"},
            "debt_to_equity": {"value": 3.0, "median": 1.0, "vs_median": 200.0, "position": "above"},
        }

        flags = generate_dd_flags(
            sector_bench=sector_bench,
            mgmt_quality=None,
            ownership_changes=None,
        )

        leverage_flags = [f for f in flags if f["type"] == "high_leverage"]
        assert len(leverage_flags) == 1
        assert leverage_flags[0]["severity"] == "warning"

    def test_no_flags_returns_empty(self) -> None:
        """No triggered conditions returns empty list."""
        from src.data.due_diligence import generate_dd_flags

        flags = generate_dd_flags(
            sector_bench=None,
            mgmt_quality={"score": 0.8, "label": "Excellent", "detail": {}},
            ownership_changes=None,
        )

        assert flags == []


class TestComputeDDReport:
    """Tests for compute_dd_report orchestrator."""

    @pytest.mark.asyncio
    async def test_returns_complete_dict(self) -> None:
        """compute_dd_report returns complete dict with all sections."""
        asset = _make_asset("BBCA", asset_id=1)
        mock_session = AsyncMock()

        # Mock cached report check (no cache)
        cache_result = MagicMock()
        cache_result.scalar_one_or_none.return_value = None

        # Mock sector benchmark query (company fundamental)
        company_fund = _make_fundamental(1, trailing_pe=12.0, return_on_equity=0.18,
                                         price_to_book=2.0, revenue_growth=0.1,
                                         debt_to_equity=0.5)
        fund_result = MagicMock()
        fund_result.scalar_one_or_none.return_value = company_fund

        # Mock sector peers
        peer_funds = [
            _make_fundamental(1, trailing_pe=12.0, return_on_equity=0.18,
                              revenue_growth=0.1, debt_to_equity=0.5),
            _make_fundamental(2, trailing_pe=15.0, return_on_equity=0.12,
                              revenue_growth=0.08, debt_to_equity=1.0),
        ]
        peers_result = MagicMock()
        peers_result.all.return_value = peer_funds

        # Mock financial data query
        fin_records = [
            _make_financial_data(1, "revenue", 100.0, "Q1-2024", date(2024, 3, 31)),
            _make_financial_data(1, "revenue", 110.0, "Q2-2024", date(2024, 6, 30)),
            _make_financial_data(1, "revenue", 120.0, "Q3-2024", date(2024, 9, 30)),
            _make_financial_data(1, "revenue", 130.0, "Q4-2024", date(2024, 12, 31)),
        ]
        fin_result = MagicMock()
        fin_result.all.return_value = fin_records

        # Mock competitive position peers
        comp_result = MagicMock()
        comp_result.all.return_value = peer_funds

        mock_session.execute.side_effect = [
            cache_result,      # cache check
            fund_result,       # company fundamental
            peers_result,      # sector peers
            fin_result,        # financial data
            comp_result,       # competitive position peers
        ]

        with (
            patch("src.data.due_diligence.fetch_ownership_data", return_value=None),
            patch("src.data.due_diligence.IDX_SECTOR_MAP", {"BBCA": "banking"}),
        ):
            from src.data.due_diligence import compute_dd_report

            report = await compute_dd_report(mock_session, asset, date(2025, 1, 15))

        assert report is not None
        # The function should call session.add and return a report
        mock_session.add.assert_called_once()
