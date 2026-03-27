"""Tests for portfolio risk snapshot formatting (REPT-06)."""

from __future__ import annotations

from src.report.formatter import format_portfolio_risk_snapshot


class TestFormatPortfolioRiskSnapshot:
    """Tests for format_portfolio_risk_snapshot."""

    def test_full_snapshot(self) -> None:
        """Full snapshot with all fields renders correctly."""
        snapshot = {
            "concentration": {
                "sector_pct": {"banking": 40.0, "crypto": 30.0, "telecom": 20.0, "mining": 10.0},
                "max_single_pct": 10.0,
                "idr_pct": 70.0,
                "usd_pct": 30.0,
            },
            "correlation_alerts": [("BBCA", "BBRI", 0.92), ("BBCA", "BMRI", 0.85)],
            "var_summary": {
                "daily_var_95": -0.023,
                "daily_var_99": -0.035,
                "weekly_var_95": -0.051,
                "weekly_var_99": -0.078,
                "max_drawdown": -0.12,
            },
            "sharpe_ratio": 1.2,
            "sortino_ratio": 1.8,
        }

        result = format_portfolio_risk_snapshot(snapshot)

        assert "Portfolio Risk" in result
        assert "banking 40%" in result
        assert "Corr alerts" in result
        assert "BBCA/BBRI 0.92" in result
        assert "VaR (95%)" in result
        assert "Sharpe: 1.20" in result
        assert "Sortino: 1.80" in result

    def test_no_correlation_alerts(self) -> None:
        """Snapshot with no correlation alerts shows 'No high-correlation alerts'."""
        snapshot = {
            "concentration": {"sector_pct": {"banking": 100.0}},
            "correlation_alerts": [],
            "var_summary": {},
            "sharpe_ratio": None,
            "sortino_ratio": None,
        }

        result = format_portfolio_risk_snapshot(snapshot)

        assert "No high-correlation alerts" in result
        assert "Concentration" in result

    def test_empty_snapshot(self) -> None:
        """Empty snapshot still renders header."""
        snapshot: dict = {
            "concentration": {},
            "correlation_alerts": [],
            "var_summary": {},
            "sharpe_ratio": None,
            "sortino_ratio": None,
        }

        result = format_portfolio_risk_snapshot(snapshot)

        assert "Portfolio Risk" in result

    def test_var_formatting(self) -> None:
        """VaR percentages formatted correctly."""
        snapshot = {
            "concentration": {},
            "correlation_alerts": [],
            "var_summary": {
                "daily_var_95": -0.023,
                "weekly_var_95": -0.051,
                "max_drawdown": -0.12,
            },
            "sharpe_ratio": None,
            "sortino_ratio": None,
        }

        result = format_portfolio_risk_snapshot(snapshot)

        assert "-2.3% daily" in result
        assert "-5.1% weekly" in result
        assert "Max DD: -12.0%" in result
