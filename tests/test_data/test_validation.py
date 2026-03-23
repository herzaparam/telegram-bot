"""Tests for OHLCV validation module."""

import math
from datetime import date, datetime, timezone

import structlog

import pytest

from src.data.base import OHLCVRow
from src.data.validation import ValidationResult, validate_date_coverage, validate_rows


class TestValidateRows:
    """Tests for validate_rows function."""

    def test_all_valid_rows_returned(
        self, five_ohlcv_rows: list[OHLCVRow]
    ) -> None:
        result = validate_rows(five_ohlcv_rows)
        assert len(result.valid) == 5
        assert len(result.rejected) == 0

    def test_nan_open_rejected(
        self, five_ohlcv_rows: list[OHLCVRow]
    ) -> None:
        five_ohlcv_rows[2] = OHLCVRow(
            time=five_ohlcv_rows[2].time,
            asset_id=1,
            open=float("nan"),
            high=9800.0,
            low=9600.0,
            close=9750.0,
            volume=1_300_000.0,
            source="yfinance",
        )
        result = validate_rows(five_ohlcv_rows)
        assert len(result.valid) == 4
        assert len(result.rejected) == 1
        assert "nan" in result.rejected[0][1].lower()

    def test_none_volume_rejected(
        self, five_ohlcv_rows: list[OHLCVRow]
    ) -> None:
        # Replace volume with None (type: ignore since dataclass expects float)
        five_ohlcv_rows[0] = OHLCVRow(
            time=five_ohlcv_rows[0].time,
            asset_id=1,
            open=9500.0,
            high=9600.0,
            low=9400.0,
            close=9550.0,
            volume=None,  # type: ignore[arg-type]
            source="yfinance",
        )
        result = validate_rows(five_ohlcv_rows)
        assert len(result.valid) == 4
        assert len(result.rejected) == 1
        assert "none" in result.rejected[0][1].lower()

    def test_high_less_than_low_rejected(
        self, five_ohlcv_rows: list[OHLCVRow]
    ) -> None:
        five_ohlcv_rows[1] = OHLCVRow(
            time=five_ohlcv_rows[1].time,
            asset_id=1,
            open=9550.0,
            high=9400.0,  # high < low
            low=9500.0,
            close=9650.0,
            volume=1_500_000.0,
            source="yfinance",
        )
        result = validate_rows(five_ohlcv_rows)
        assert len(result.valid) == 4
        assert len(result.rejected) == 1
        assert "high < low" in result.rejected[0][1]

    def test_negative_volume_rejected(
        self, five_ohlcv_rows: list[OHLCVRow]
    ) -> None:
        five_ohlcv_rows[3] = OHLCVRow(
            time=five_ohlcv_rows[3].time,
            asset_id=1,
            open=9750.0,
            high=9850.0,
            low=9700.0,
            close=9800.0,
            volume=-100.0,
            source="yfinance",
        )
        result = validate_rows(five_ohlcv_rows)
        assert len(result.valid) == 4
        assert len(result.rejected) == 1

    def test_logs_rejected_rows(
        self, five_ohlcv_rows: list[OHLCVRow]
    ) -> None:
        five_ohlcv_rows[0] = OHLCVRow(
            time=five_ohlcv_rows[0].time,
            asset_id=1,
            open=float("nan"),
            high=9600.0,
            low=9400.0,
            close=9550.0,
            volume=1_200_000.0,
            source="yfinance",
        )
        cap = structlog.testing.CapturingLogger()
        old_factory = structlog.get_config().get("logger_factory")

        structlog.configure(logger_factory=lambda *a, **kw: cap)
        try:
            validate_rows(five_ohlcv_rows, asset_symbol="BBCA.JK")
        finally:
            if old_factory:
                structlog.configure(logger_factory=old_factory)
            else:
                structlog.reset_defaults()

        warning_calls = [c for c in cap.calls if c.method_name == "warning"]
        assert len(warning_calls) >= 1
        # Check the log event has the expected fields
        event_kwargs = warning_calls[0].kwargs
        assert event_kwargs.get("event") == "ohlcv_row_rejected"
        assert event_kwargs.get("asset") == "BBCA.JK"

    def test_empty_input_returns_empty(self) -> None:
        result = validate_rows([])
        assert len(result.valid) == 0
        assert len(result.rejected) == 0

    def test_all_invalid_returns_empty_valid(self) -> None:
        rows = [
            OHLCVRow(
                time=datetime(2026, 3, 20, tzinfo=timezone.utc),
                asset_id=1,
                open=float("nan"),
                high=9600.0,
                low=9400.0,
                close=9550.0,
                volume=1_200_000.0,
                source="yfinance",
            ),
            OHLCVRow(
                time=datetime(2026, 3, 21, tzinfo=timezone.utc),
                asset_id=1,
                open=9500.0,
                high=9600.0,
                low=9400.0,
                close=None,  # type: ignore[arg-type]
                volume=1_200_000.0,
                source="yfinance",
            ),
        ]
        result = validate_rows(rows)
        assert len(result.valid) == 0
        assert len(result.rejected) == 2


class TestValidateDateCoverage:
    """Tests for validate_date_coverage function."""

    def test_no_gaps_returns_empty(self) -> None:
        # Mon-Fri of a single week
        rows = [
            OHLCVRow(
                time=datetime(2026, 3, 16, tzinfo=timezone.utc),  # Monday
                asset_id=1,
                open=100.0,
                high=110.0,
                low=90.0,
                close=105.0,
                volume=1000.0,
                source="yfinance",
            ),
            OHLCVRow(
                time=datetime(2026, 3, 17, tzinfo=timezone.utc),
                asset_id=1,
                open=105.0,
                high=115.0,
                low=95.0,
                close=110.0,
                volume=1000.0,
                source="yfinance",
            ),
            OHLCVRow(
                time=datetime(2026, 3, 18, tzinfo=timezone.utc),
                asset_id=1,
                open=110.0,
                high=120.0,
                low=100.0,
                close=115.0,
                volume=1000.0,
                source="yfinance",
            ),
            OHLCVRow(
                time=datetime(2026, 3, 19, tzinfo=timezone.utc),
                asset_id=1,
                open=115.0,
                high=125.0,
                low=105.0,
                close=120.0,
                volume=1000.0,
                source="yfinance",
            ),
            OHLCVRow(
                time=datetime(2026, 3, 20, tzinfo=timezone.utc),  # Friday
                asset_id=1,
                open=120.0,
                high=130.0,
                low=110.0,
                close=125.0,
                volume=1000.0,
                source="yfinance",
            ),
        ]
        missing = validate_date_coverage(
            rows, start=date(2026, 3, 16), end=date(2026, 3, 20)
        )
        assert missing == []

    def test_gap_detected_and_logged(self) -> None:
        # Only Mon and Fri -- Tue-Thu missing
        rows = [
            OHLCVRow(
                time=datetime(2026, 3, 16, tzinfo=timezone.utc),
                asset_id=1,
                open=100.0,
                high=110.0,
                low=90.0,
                close=105.0,
                volume=1000.0,
                source="yfinance",
            ),
            OHLCVRow(
                time=datetime(2026, 3, 20, tzinfo=timezone.utc),
                asset_id=1,
                open=120.0,
                high=130.0,
                low=110.0,
                close=125.0,
                volume=1000.0,
                source="yfinance",
            ),
        ]
        cap = structlog.testing.CapturingLogger()
        old_factory = structlog.get_config().get("logger_factory")

        structlog.configure(logger_factory=lambda *a, **kw: cap)
        try:
            missing = validate_date_coverage(
                rows,
                start=date(2026, 3, 16),
                end=date(2026, 3, 20),
                asset_symbol="BBCA.JK",
            )
        finally:
            if old_factory:
                structlog.configure(logger_factory=old_factory)
            else:
                structlog.reset_defaults()

        assert len(missing) == 3  # Tue, Wed, Thu
        warning_calls = [c for c in cap.calls if c.method_name == "warning"]
        assert len(warning_calls) >= 1
        assert warning_calls[0].kwargs.get("event") == "ohlcv_date_gaps"
