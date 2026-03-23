"""Tests for src/db/models.py ORM models."""


from sqlalchemy import inspect


class TestNamingConvention:
    """Test Base metadata has naming conventions."""

    def test_naming_convention_keys(self):
        """Base.metadata has naming_convention with keys ix, uq, ck, fk, pk."""
        from src.db.models import Base

        nc = Base.metadata.naming_convention
        assert "ix" in nc
        assert "uq" in nc
        assert "ck" in nc
        assert "fk" in nc
        assert "pk" in nc


class TestAssetModel:
    """Test Asset model columns and constraints."""

    def test_asset_columns(self):
        """Asset model has all required columns."""
        from src.db.models import Asset

        mapper = inspect(Asset)
        col_names = {c.key for c in mapper.column_attrs}
        expected = {
            "id",
            "symbol",
            "name",
            "asset_type",
            "exchange",
            "yfinance_symbol",
            "ccxt_symbol",
            "is_active",
            "created_at",
        }
        assert expected.issubset(col_names), f"Missing columns: {expected - col_names}"

    def test_asset_unique_constraint(self):
        """Asset model has unique constraint on (symbol, asset_type)."""
        from src.db.models import Asset

        table = Asset.__table__
        unique_constraints = [c for c in table.constraints if hasattr(c, "columns") and len(c.columns) > 1]
        found = False
        for uc in unique_constraints:
            col_names = {col.name for col in uc.columns}
            if col_names == {"symbol", "asset_type"}:
                found = True
                break
        assert found, "UniqueConstraint on (symbol, asset_type) not found"

    def test_asset_tablename(self):
        """Asset table name is 'assets'."""
        from src.db.models import Asset

        assert Asset.__tablename__ == "assets"


class TestPipelineRunModel:
    """Test PipelineRun model columns and constraints."""

    def test_pipeline_run_columns(self):
        """PipelineRun model has all required columns."""
        from src.db.models import PipelineRun

        mapper = inspect(PipelineRun)
        col_names = {c.key for c in mapper.column_attrs}
        expected = {"id", "run_date", "stage", "status", "started_at", "completed_at", "metadata_"}
        assert expected.issubset(col_names), f"Missing columns: {expected - col_names}"

    def test_pipeline_run_unique_constraint(self):
        """PipelineRun has unique constraint on (run_date, stage)."""
        from src.db.models import PipelineRun

        table = PipelineRun.__table__
        unique_constraints = [c for c in table.constraints if hasattr(c, "columns") and len(c.columns) > 1]
        found = False
        for uc in unique_constraints:
            col_names = {col.name for col in uc.columns}
            if col_names == {"run_date", "stage"}:
                found = True
                break
        assert found, "UniqueConstraint on (run_date, stage) not found"

    def test_pipeline_run_id_is_uuid(self):
        """PipelineRun id column is UUID type."""
        from src.db.models import PipelineRun

        table = PipelineRun.__table__
        col = table.c.id
        assert "UUID" in str(col.type).upper() or "Uuid" in str(type(col.type))


class TestPipelineAssetRunModel:
    """Test PipelineAssetRun model columns and constraints."""

    def test_pipeline_asset_run_columns(self):
        """PipelineAssetRun model has all required columns."""
        from src.db.models import PipelineAssetRun

        mapper = inspect(PipelineAssetRun)
        col_names = {c.key for c in mapper.column_attrs}
        expected = {
            "id",
            "run_id",
            "asset_id",
            "status",
            "started_at",
            "completed_at",
            "error_message",
            "retry_count",
        }
        assert expected.issubset(col_names), f"Missing columns: {expected - col_names}"

    def test_pipeline_asset_run_unique_constraint(self):
        """PipelineAssetRun has unique constraint on (run_id, asset_id)."""
        from src.db.models import PipelineAssetRun

        table = PipelineAssetRun.__table__
        unique_constraints = [c for c in table.constraints if hasattr(c, "columns") and len(c.columns) > 1]
        found = False
        for uc in unique_constraints:
            col_names = {col.name for col in uc.columns}
            if col_names == {"run_id", "asset_id"}:
                found = True
                break
        assert found, "UniqueConstraint on (run_id, asset_id) not found"

    def test_pipeline_asset_run_foreign_keys(self):
        """PipelineAssetRun has FKs to pipeline_runs and assets."""
        from src.db.models import PipelineAssetRun

        table = PipelineAssetRun.__table__
        fk_targets = {fk.target_fullname for fk in table.foreign_keys}
        assert "pipeline_runs.id" in fk_targets
        assert "assets.id" in fk_targets


class TestDailyDecisionModel:
    """Test DailyDecision model columns and constraints."""

    def test_daily_decision_columns(self):
        """DailyDecision model has all required columns."""
        from src.db.models import DailyDecision

        mapper = inspect(DailyDecision)
        col_names = {c.key for c in mapper.column_attrs}
        expected = {
            "id",
            "asset_id",
            "date",
            "verdict",
            "score",
            "confidence",
            "decision_price",
            "decision_price_at",
            "evaluation_price",
            "evaluation_price_at",
            "all_signals",
            "reasoning",
            "key_factors",
            "risk_warning",
            "wait_for",
            "lessons_applied",
            "model_used",
            "created_at",
        }
        assert expected.issubset(col_names), f"Missing columns: {expected - col_names}"

    def test_daily_decision_unique_constraint(self):
        """DailyDecision has unique constraint on (asset_id, date)."""
        from src.db.models import DailyDecision

        table = DailyDecision.__table__
        unique_constraints = [c for c in table.constraints if hasattr(c, "columns") and len(c.columns) > 1]
        found = False
        for uc in unique_constraints:
            col_names = {col.name for col in uc.columns}
            if col_names == {"asset_id", "date"}:
                found = True
                break
        assert found, "UniqueConstraint on (asset_id, date) not found"

    def test_daily_decision_look_ahead_bias_columns(self):
        """DailyDecision has look-ahead bias prevention columns with correct types."""
        from src.db.models import DailyDecision

        table = DailyDecision.__table__

        # decision_price exists
        assert "decision_price" in table.c

        # decision_price_at is timezone-aware datetime
        col = table.c.decision_price_at
        assert col is not None
        assert col.type.timezone is True, "decision_price_at must be timezone-aware"

        # evaluation_price is nullable
        col = table.c.evaluation_price
        assert col.nullable is True, "evaluation_price must be nullable"

        # evaluation_price_at is nullable and timezone-aware
        col = table.c.evaluation_price_at
        assert col.nullable is True, "evaluation_price_at must be nullable"
        assert col.type.timezone is True, "evaluation_price_at must be timezone-aware"

    def test_daily_decision_asset_fk(self):
        """DailyDecision has FK to assets."""
        from src.db.models import DailyDecision

        table = DailyDecision.__table__
        fk_targets = {fk.target_fullname for fk in table.foreign_keys}
        assert "assets.id" in fk_targets


class TestSeedAssets:
    """Test seed data availability."""

    def test_seed_assets_exists(self):
        """SEED_ASSETS list exists and has expected entries."""
        from src.db.models import SEED_ASSETS

        assert len(SEED_ASSETS) >= 6
        symbols = {a["symbol"] for a in SEED_ASSETS}
        assert "BBCA" in symbols
        assert "BTC" in symbols
        assert "ETH" in symbols
        assert "SOL" in symbols

    def test_seed_assets_have_required_fields(self):
        """Each seed asset has symbol, name, asset_type, exchange."""
        from src.db.models import SEED_ASSETS

        for asset in SEED_ASSETS:
            assert "symbol" in asset
            assert "name" in asset
            assert "asset_type" in asset
            assert "exchange" in asset
