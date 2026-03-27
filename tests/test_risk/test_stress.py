"""Tests for src.risk.stress module."""

from src.risk.stress import STRESS_SCENARIOS, StressResult, run_stress_test


def test_four_scenarios_returned(sample_assets: list[dict]) -> None:
    """run_stress_test returns exactly 4 scenarios."""
    results = run_stress_test(sample_assets)
    assert len(results) == 4


def test_portfolio_impact_range(sample_assets: list[dict]) -> None:
    """Portfolio impact is between -1 and 0 for all scenarios."""
    results = run_stress_test(sample_assets)
    for r in results:
        assert -1.0 <= r.portfolio_impact <= 0.0


def test_scenario_ids_match(sample_assets: list[dict]) -> None:
    """Scenario IDs match expected set."""
    results = run_stress_test(sample_assets)
    ids = {r.scenario_id for r in results}
    assert ids == {"covid_2020", "crypto_winter_2022", "taper_tantrum_2013", "gfc_2008"}


def test_single_stock_portfolio() -> None:
    """Stress test with only stock assets."""
    assets = [{"symbol": "BBCA", "asset_type": "stock"}]
    results = run_stress_test(assets)
    for r in results:
        # Impact should equal the stock drawdown when portfolio is all stocks
        assert abs(r.portfolio_impact - r.stock_drawdown) < 1e-6


def test_single_crypto_portfolio() -> None:
    """Stress test with only crypto assets."""
    assets = [{"symbol": "BTC", "asset_type": "crypto"}]
    results = run_stress_test(assets)
    for r in results:
        assert abs(r.portfolio_impact - r.crypto_drawdown) < 1e-6


def test_stress_result_type(sample_assets: list[dict]) -> None:
    """Results are StressResult instances."""
    results = run_stress_test(sample_assets)
    for r in results:
        assert isinstance(r, StressResult)


def test_empty_portfolio() -> None:
    """Empty portfolio returns empty list."""
    assert run_stress_test([]) == []


def test_stress_scenarios_keys() -> None:
    """STRESS_SCENARIOS dict has required keys."""
    assert set(STRESS_SCENARIOS.keys()) == {
        "covid_2020",
        "crypto_winter_2022",
        "taper_tantrum_2013",
        "gfc_2008",
    }
