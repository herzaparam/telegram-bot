"""Tests for ML/AI inference engine."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


@pytest.fixture()
def sample_df_200() -> pd.DataFrame:
    """200-row synthetic OHLCV DataFrame."""
    rng = np.random.default_rng(42)
    n = 200
    dates = pd.bdate_range("2025-06-01", periods=n, freq="B")

    returns = rng.normal(0.0005, 0.015, size=n)
    close = 10000.0 * np.cumprod(1 + returns)

    high = close * (1 + rng.uniform(0.001, 0.02, size=n))
    low = close * (1 - rng.uniform(0.001, 0.02, size=n))
    open_ = low + rng.uniform(0.3, 0.7, size=n) * (high - low)
    volume = rng.uniform(500_000, 5_000_000, size=n)

    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
        index=dates,
    )


class TestMLAIEngineCategory:
    """Test engine metadata."""

    def test_category_is_ml_ai(self) -> None:
        from src.engines.ml_ai import MLAIEngine

        engine = MLAIEngine()
        assert engine.category == "ml_ai"

    def test_supports_stocks(self) -> None:
        from src.engines.ml_ai import MLAIEngine

        engine = MLAIEngine()
        assert engine.supports_stocks is True

    def test_supports_crypto(self) -> None:
        from src.engines.ml_ai import MLAIEngine

        engine = MLAIEngine()
        assert engine.supports_crypto is True


class TestMLAIEngineNoModels:
    """Test engine behavior when model files are missing."""

    def test_returns_zero_score_when_no_models(self, sample_df_200: pd.DataFrame) -> None:
        from src.engines.ml_ai import MLAIEngine

        engine = MLAIEngine(asset_type="stock")
        signal = engine.analyze(1, "BBCA", sample_df_200)
        assert signal.score == 0.0
        assert signal.confidence == 0.0

    def test_reasoning_mentions_not_trained(self, sample_df_200: pd.DataFrame) -> None:
        from src.engines.ml_ai import MLAIEngine

        engine = MLAIEngine(asset_type="stock")
        signal = engine.analyze(1, "BBCA", sample_df_200)
        assert "not trained" in signal.reasoning.lower() or "Model not trained" in signal.reasoning

    def test_data_quality_shows_model_missing(self, sample_df_200: pd.DataFrame) -> None:
        from src.engines.ml_ai import MLAIEngine

        engine = MLAIEngine(asset_type="stock")
        signal = engine.analyze(1, "BBCA", sample_df_200)
        assert signal.data_quality.get("model_missing") is True


class TestMLAIEngineWithMockONNX:
    """Test engine with mocked ONNX inference sessions."""

    def test_xgboost_only_inference(self, sample_df_200: pd.DataFrame) -> None:
        """Mock XGBoost ONNX session, LSTM model missing."""
        from src.engines.ml_ai import MLAIEngine

        mock_session = MagicMock()
        mock_input = MagicMock()
        mock_input.name = "input"
        mock_session.get_inputs.return_value = [mock_input]
        # XGBoost returns: [prediction, probabilities]
        mock_session.run.return_value = [
            np.array([1]),  # predicted class
            np.array([[0.4, 0.6]]),  # class probabilities
        ]

        with (
            patch("os.path.exists") as mock_exists,
            patch("src.engines.ml_ai._create_session", return_value=mock_session),
        ):
            # XGBoost model exists, LSTM does not
            def path_exists(path: str) -> bool:
                return "xgboost" in path

            mock_exists.side_effect = path_exists

            engine = MLAIEngine(asset_type="stock")
            signal = engine.analyze(1, "BBCA", sample_df_200)

        assert signal.score != 0.0
        assert -1.0 <= signal.score <= 1.0
        # XGBoost only: confidence = xgb_prob * 0.8
        assert signal.confidence == pytest.approx(0.6 * 0.8, abs=0.01)

    def test_ensemble_inference(self, sample_df_200: pd.DataFrame) -> None:
        """Mock both XGBoost and LSTM ONNX sessions."""
        from src.engines.ml_ai import MLAIEngine

        mock_xgb_session = MagicMock()
        mock_xgb_input = MagicMock()
        mock_xgb_input.name = "input"
        mock_xgb_session.get_inputs.return_value = [mock_xgb_input]
        mock_xgb_session.run.return_value = [
            np.array([1]),
            np.array([[0.4, 0.6]]),
        ]

        mock_lstm_session = MagicMock()
        mock_lstm_input = MagicMock()
        mock_lstm_input.name = "input"
        mock_lstm_session.get_inputs.return_value = [mock_lstm_input]
        mock_lstm_session.run.return_value = [
            np.array([[0.02, 0.7]]),  # [prediction, probability]
        ]

        call_count = 0

        def mock_create_session(path: str, **kwargs: object) -> MagicMock:
            nonlocal call_count
            call_count += 1
            if "xgboost" in path:
                return mock_xgb_session
            return mock_lstm_session

        with (
            patch("os.path.exists", return_value=True),
            patch("src.engines.ml_ai._create_session", side_effect=mock_create_session),
        ):
            engine = MLAIEngine(asset_type="stock")
            signal = engine.analyze(1, "BBCA", sample_df_200)

        assert signal.score != 0.0
        assert -1.0 <= signal.score <= 1.0
        # Ensemble uses 60/40 weights
        assert signal.indicators.get("ensemble_score") is not None

    def test_ensemble_weights_60_40(self, sample_df_200: pd.DataFrame) -> None:
        """Verify 60% XGBoost + 40% LSTM weighting."""
        from src.engines.ml_ai import MLAIEngine

        # XGBoost predicts class 1 (bullish)
        mock_xgb = MagicMock()
        mock_xgb_input = MagicMock()
        mock_xgb_input.name = "input"
        mock_xgb.get_inputs.return_value = [mock_xgb_input]
        mock_xgb.run.return_value = [np.array([1]), np.array([[0.3, 0.7]])]

        # LSTM predicts a score
        mock_lstm = MagicMock()
        mock_lstm_input = MagicMock()
        mock_lstm_input.name = "input"
        mock_lstm.get_inputs.return_value = [mock_lstm_input]
        mock_lstm.run.return_value = [np.array([[0.05, 0.8]])]

        def mock_create_session(path: str, **kwargs: object) -> MagicMock:
            if "xgboost" in path:
                return mock_xgb
            return mock_lstm

        with (
            patch("os.path.exists", return_value=True),
            patch("src.engines.ml_ai._create_session", side_effect=mock_create_session),
        ):
            engine = MLAIEngine(asset_type="stock")
            signal = engine.analyze(1, "BBCA", sample_df_200)

        # Confidence = min(xgb_prob, lstm_prob) per D-06
        assert signal.confidence == pytest.approx(min(0.7, 0.8), abs=0.01)
