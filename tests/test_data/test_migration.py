"""Smoke tests for migration 002 - verify DDL patterns without a real database."""

import inspect


def _get_upgrade_source() -> str:
    from src.db.migrations.versions.002_price_history_hypertables import upgrade

    return inspect.getsource(upgrade)


def _get_downgrade_source() -> str:
    from src.db.migrations.versions.002_price_history_hypertables import downgrade

    return inspect.getsource(downgrade)


class TestMigration002Upgrade:
    """Verify upgrade() contains expected DDL patterns."""

    def test_creates_price_history_hypertable(self) -> None:
        src = _get_upgrade_source()
        assert "create_hypertable" in src
        assert "price_history" in src

    def test_creates_price_history_hourly_hypertable(self) -> None:
        src = _get_upgrade_source()
        assert "price_history_hourly" in src
        assert "create_hypertable" in src

    def test_adds_compression_policy(self) -> None:
        src = _get_upgrade_source()
        assert "add_compression_policy" in src

    def test_adds_retention_policy(self) -> None:
        src = _get_upgrade_source()
        assert "add_retention_policy" in src

    def test_creates_backoff_state_table(self) -> None:
        src = _get_upgrade_source()
        assert "backoff_state" in src


class TestMigration002Downgrade:
    """Verify downgrade() drops all three tables."""

    def test_drops_all_three_tables(self) -> None:
        src = _get_downgrade_source()
        assert "backoff_state" in src
        assert "price_history_hourly" in src
        assert "price_history" in src
