"""ML/AI inference engine using ONNX models for prediction.

Performs lazy ONNX model loading and release per D-22.
Ensemble: 60% XGBoost + 40% LSTM per D-06.
Predicts next-day return direction and magnitude per D-05.
"""

from __future__ import annotations

import math
import os

import numpy as np
import pandas as pd
import structlog

from src.engines.base import BaseEngine, Signal

logger = structlog.get_logger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "ml", "models")


def _create_session(model_path: str) -> object:
    """Create an ONNX InferenceSession. Separated for testability.

    Args:
        model_path: Path to the .onnx model file.

    Returns:
        An onnxruntime.InferenceSession.
    """
    import onnxruntime as ort  # Lazy import -- only needed at inference time

    return ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])


class MLAIEngine(BaseEngine):
    """ML/AI engine using ONNX inference with XGBoost/LSTM ensemble.

    Constructor:
        asset_type: "stock" or "crypto" -- determines which model files to load.
    """

    def __init__(self, asset_type: str = "stock") -> None:
        self._asset_type = asset_type

    @property
    def category(self) -> str:
        """Return the engine category."""
        return "ml_ai"

    @property
    def supports_stocks(self) -> bool:
        """Whether this engine supports stock assets."""
        return True

    @property
    def supports_crypto(self) -> bool:
        """Whether this engine supports crypto assets."""
        return True

    def analyze(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Run ML/AI analysis on price data.

        Never raises -- returns score=0/confidence=0 on any failure.
        """
        try:
            return self._analyze_impl(asset_id, asset_symbol, df)
        except Exception as exc:
            logger.warning(
                "ml_ai_engine_error",
                asset_id=asset_id,
                asset_symbol=asset_symbol,
                error=str(exc),
            )
            return Signal(
                category="ml_ai",
                score=0.0,
                confidence=0.0,
                reasoning=f"ML/AI analysis failed: {exc}",
                indicators={},
                data_quality={"error": str(exc)},
            )

    def _analyze_impl(
        self, asset_id: int, asset_symbol: str, df: pd.DataFrame
    ) -> Signal:
        """Internal analysis implementation."""
        from src.ml.features import extract_features

        # 1. Extract features
        features = extract_features(df)
        if features is None:
            return Signal(
                category="ml_ai",
                score=0.0,
                confidence=0.0,
                reasoning="Insufficient data for ML feature extraction",
                indicators={},
                data_quality={"insufficient_data": True, "rows": len(df)},
            )

        # 2. XGBoost inference (lazy load per D-22)
        xgb_model_path = os.path.join(MODEL_DIR, f"xgboost_{self._asset_type}.onnx")
        if not os.path.exists(xgb_model_path):
            return Signal(
                category="ml_ai",
                score=0.0,
                confidence=0.0,
                reasoning="Model not trained yet. Run: python -m src.ml.train_xgboost",
                indicators={},
                data_quality={"model_missing": True},
            )

        session = _create_session(xgb_model_path)
        try:
            input_name = session.get_inputs()[0].name  # type: ignore[union-attr]
            outputs = session.run(None, {input_name: features})  # type: ignore[union-attr]
            xgb_pred = float(outputs[0][0])
            xgb_prob = float(outputs[1][0][1]) if len(outputs) > 1 else 0.5
        finally:
            del session  # Explicit release per D-22

        # 3. LSTM inference (same lazy pattern)
        lstm_model_path = os.path.join(MODEL_DIR, f"lstm_{self._asset_type}.onnx")
        lstm_pred = None
        lstm_prob = None
        models_loaded = ["xgboost"]

        if os.path.exists(lstm_model_path):
            session = _create_session(lstm_model_path)
            try:
                input_name = session.get_inputs()[0].name  # type: ignore[union-attr]
                outputs = session.run(None, {input_name: features})  # type: ignore[union-attr]
                # LSTM output: [[prediction, probability]]
                lstm_pred = float(outputs[0][0][0])
                lstm_prob = float(outputs[0][0][1]) if outputs[0].shape[-1] > 1 else 0.5
                models_loaded.append("lstm")
            finally:
                del session  # Explicit release per D-22

        # 4. Ensemble per D-06
        if lstm_pred is not None and lstm_prob is not None:
            # Both models: 60% XGBoost + 40% LSTM
            ensemble_score = 0.6 * xgb_pred + 0.4 * lstm_pred
            confidence = min(xgb_prob, lstm_prob)
        else:
            # XGBoost only
            ensemble_score = xgb_pred
            confidence = xgb_prob * 0.8

        # 5. Map to [-1, 1] range using tanh
        score = float(math.tanh(ensemble_score))

        # 6. Build indicators
        indicators: dict[str, object] = {
            "xgboost_pred": round(xgb_pred, 6),
            "xgboost_prob": round(xgb_prob, 4),
            "lstm_pred": round(lstm_pred, 6) if lstm_pred is not None else None,
            "lstm_prob": round(lstm_prob, 4) if lstm_prob is not None else None,
            "ensemble_score": round(ensemble_score, 6),
            "asset_type": self._asset_type,
        }

        data_quality: dict[str, object] = {
            "models_loaded": models_loaded,
            "feature_count": 20,
        }

        # Reasoning
        direction = "bullish" if score > 0 else "bearish" if score < 0 else "neutral"
        reasoning = (
            f"ML ensemble ({'+'.join(models_loaded)}): {direction} "
            f"score={score:.4f}, confidence={confidence:.4f}. "
            f"XGB pred={xgb_pred:.4f} prob={xgb_prob:.2f}"
        )
        if lstm_pred is not None:
            reasoning += f", LSTM pred={lstm_pred:.4f} prob={lstm_prob:.2f}"

        return Signal(
            category="ml_ai",
            score=round(score, 6),
            confidence=round(confidence, 4),
            reasoning=reasoning,
            indicators=indicators,
            data_quality=data_quality,
        )
