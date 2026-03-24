"""Tests for src/engines/base.py — BaseEngine ABC and Signal dataclass."""

import dataclasses

import pandas as pd
import pytest

from src.engines.base import BaseEngine, Signal


class _DummyEngine(BaseEngine):
    """Concrete engine subclass for testing BaseEngine defaults."""

    def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
        return Signal(
            category="test",
            score=0.5,
            confidence=0.8,
            reasoning="Test signal",
            indicators={"rsi_14": 50},
            data_quality={"sources_available": ["test"], "indicators_skipped": [], "trading_days": 200},
        )

    @property
    def category(self) -> str:
        return "test"


class TestSignalDataclass:
    """Test Signal frozen dataclass properties."""

    def test_signal_is_frozen(self) -> None:
        """Signal is immutable — attribute assignment raises FrozenInstanceError."""
        sig = Signal(
            category="technical",
            score=0.5,
            confidence=0.8,
            reasoning="Test",
            indicators={},
            data_quality={},
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            sig.score = 0.9  # type: ignore[misc]

    def test_signal_fields(self) -> None:
        """Signal has all 6 required fields."""
        fields = {f.name for f in dataclasses.fields(Signal)}
        expected = {"category", "score", "confidence", "reasoning", "indicators", "data_quality"}
        assert expected == fields

    def test_signal_values(self) -> None:
        """Signal stores values correctly."""
        sig = Signal(
            category="technical",
            score=-0.5,
            confidence=0.3,
            reasoning="Bearish divergence",
            indicators={"rsi_14": 28, "macd_hist": -0.5},
            data_quality={"sources_available": ["yfinance"], "indicators_skipped": [], "trading_days": 100},
        )
        assert sig.category == "technical"
        assert sig.score == -0.5
        assert sig.confidence == 0.3
        assert sig.reasoning == "Bearish divergence"
        assert sig.indicators["rsi_14"] == 28
        assert sig.data_quality["trading_days"] == 100


class TestBaseEngine:
    """Test BaseEngine ABC contract."""

    def test_base_engine_is_abstract(self) -> None:
        """BaseEngine cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseEngine()  # type: ignore[abstract]

    def test_concrete_engine_must_implement_analyze_and_category(self) -> None:
        """A subclass missing analyze() or category raises TypeError."""

        class _PartialEngine(BaseEngine):
            @property
            def category(self) -> str:
                return "partial"
            # Missing analyze()

        with pytest.raises(TypeError):
            _PartialEngine()  # type: ignore[abstract]

    def test_concrete_engine_missing_category(self) -> None:
        """A subclass missing category raises TypeError."""

        class _NoCategoryEngine(BaseEngine):
            def analyze(self, asset_id: int, asset_symbol: str, df: pd.DataFrame) -> Signal:
                return Signal("x", 0, 0, "", {}, {})
            # Missing category

        with pytest.raises(TypeError):
            _NoCategoryEngine()  # type: ignore[abstract]

    def test_supports_stocks_default_true(self) -> None:
        """Concrete engine .supports_stocks defaults to True."""
        engine = _DummyEngine()
        assert engine.supports_stocks is True

    def test_supports_crypto_default_true(self) -> None:
        """Concrete engine .supports_crypto defaults to True."""
        engine = _DummyEngine()
        assert engine.supports_crypto is True

    def test_dummy_engine_analyze_returns_signal(self) -> None:
        """Concrete engine analyze() returns a Signal."""
        engine = _DummyEngine()
        df = pd.DataFrame({"open": [1], "high": [2], "low": [0.5], "close": [1.5], "volume": [1000]})
        result = engine.analyze(1, "TEST", df)
        assert isinstance(result, Signal)
        assert result.category == "test"
        assert result.score == 0.5

    def test_engine_category_property(self) -> None:
        """Concrete engine category property works."""
        engine = _DummyEngine()
        assert engine.category == "test"


class TestSignalRecordModel:
    """Test SignalRecord ORM model columns and constraints."""

    def test_signal_record_columns(self) -> None:
        """SignalRecord model has all required columns."""
        from sqlalchemy import inspect as sa_inspect

        from src.db.models import SignalRecord

        mapper = sa_inspect(SignalRecord)
        col_names = {c.key for c in mapper.column_attrs}
        expected = {
            "id",
            "asset_id",
            "date",
            "category",
            "score",
            "confidence",
            "reasoning",
            "indicators",
            "data_quality",
            "price_at_signal",
            "created_at",
        }
        assert expected.issubset(col_names), f"Missing columns: {expected - col_names}"

    def test_signal_record_tablename(self) -> None:
        """SignalRecord table name is 'signals'."""
        from src.db.models import SignalRecord

        assert SignalRecord.__tablename__ == "signals"

    def test_signal_record_unique_constraint(self) -> None:
        """SignalRecord has unique constraint on (asset_id, date, category)."""
        from src.db.models import SignalRecord

        table = SignalRecord.__table__
        unique_constraints = [c for c in table.constraints if hasattr(c, "columns") and len(c.columns) > 1]
        found = False
        for uc in unique_constraints:
            col_names = {col.name for col in uc.columns}
            if col_names == {"asset_id", "date", "category"}:
                found = True
                break
        assert found, "UniqueConstraint on (asset_id, date, category) not found"

    def test_signal_record_asset_fk(self) -> None:
        """SignalRecord has FK to assets."""
        from src.db.models import SignalRecord

        table = SignalRecord.__table__
        fk_targets = {fk.target_fullname for fk in table.foreign_keys}
        assert "assets.id" in fk_targets
