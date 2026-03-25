---
phase: 10-remaining-specialized-engines
plan: 04
subsystem: ml
tags: [xgboost, lstm, onnx, onnxruntime, feature-engineering, machine-learning]

requires:
  - phase: 10-remaining-specialized-engines/01
    provides: "BaseEngine contract, Signal dataclass, MLPrediction model"
provides:
  - "MLAIEngine with ONNX inference and 60/40 ensemble"
  - "Feature engineering module (20 OHLCV-derived features)"
  - "XGBoost training CLI with ONNX export"
  - "LSTM training CLI with ONNX export"
affects: [analyze-stage, pipeline-integration, model-training]

tech-stack:
  added: [onnxruntime, xgboost, onnxmltools, torch, sklearn]
  patterns: [lazy-onnx-loading, session-release-after-inference, testable-session-factory]

key-files:
  created:
    - src/ml/__init__.py
    - src/ml/features.py
    - src/ml/models/.gitkeep
    - src/ml/train_xgboost.py
    - src/ml/train_lstm.py
    - src/engines/ml_ai.py
    - tests/test_ml/__init__.py
    - tests/test_ml/test_features.py
    - tests/test_engines/test_ml_ai.py
  modified: []

key-decisions:
  - "Separated _create_session factory for testability instead of patching onnxruntime directly"
  - "MACD/ATR/OBV features normalized by close price for scale-invariance across assets"
  - "LSTM training uses shuffle=False for temporal data to avoid look-ahead bias"

patterns-established:
  - "Lazy ONNX import: import onnxruntime only inside _create_session, not at module level"
  - "Session lifecycle: create, use in try/finally, del session for explicit memory release"
  - "Testable inference: _create_session as module-level function enables clean mocking"

requirements-completed: [ENGN-04]

duration: 5min
completed: 2026-03-25
---

# Phase 10 Plan 04: ML/AI Engine Summary

**ONNX-based ML/AI engine with 20 OHLCV features, XGBoost/LSTM 60-40 ensemble, and training CLI scripts**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-25T17:36:58Z
- **Completed:** 2026-03-25T17:41:45Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Feature engineering module producing 20 OHLCV-derived features (returns, volatility, RSI, MACD, Bollinger %B, ATR, OBV slope)
- MLAIEngine with lazy ONNX loading, 60/40 XGBoost/LSTM ensemble, explicit session release per D-22
- Graceful degradation returning score=0/confidence=0 when model files are missing
- XGBoost training script with onnxmltools conversion and round-trip verification
- LSTM training script with PyTorch nn.LSTM and torch.onnx.export

## Task Commits

Each task was committed atomically:

1. **Task 1: Feature engineering module and ML/AI inference engine** - `617e8b3` (feat) -- TDD: RED/GREEN
2. **Task 2: XGBoost and LSTM training scripts** - `ebfcb0d` (feat)

## Files Created/Modified
- `src/ml/__init__.py` - ML package init
- `src/ml/features.py` - 20-feature extraction from OHLCV (returns, volatility, RSI, MACD, BB%B, lags, ATR, OBV)
- `src/ml/models/.gitkeep` - Directory for ONNX model files
- `src/ml/train_xgboost.py` - CLI tool: XGBClassifier training with onnxmltools ONNX export (opset 18)
- `src/ml/train_lstm.py` - CLI tool: PyTorch LSTM training with torch.onnx.export (opset 18)
- `src/engines/ml_ai.py` - MLAIEngine with lazy ONNX inference, 60/40 ensemble, session release
- `tests/test_ml/__init__.py` - Test package init
- `tests/test_ml/test_features.py` - 6 tests for feature extraction (shape, dtype, edge cases)
- `tests/test_engines/test_ml_ai.py` - 9 tests for ML/AI engine (metadata, no-model fallback, mock inference, ensemble)

## Decisions Made
- Separated `_create_session` as module-level factory function for clean mock injection in tests (avoids patching onnxruntime internals)
- Features normalized by close price (MACD, ATR) for scale-invariance across different asset price ranges
- LSTM training uses shuffle=False in DataLoader to preserve temporal ordering and prevent look-ahead bias

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. Training scripts require xgboost, torch, onnxmltools as dev dependencies (not needed for production inference).

## Known Stubs

None - the engine is fully wired. When model files are absent, it gracefully returns score=0/confidence=0 with clear instructions to run training scripts.

## Next Phase Readiness
- ML/AI engine ready for integration into analyze_stage
- Model training requires populated price data in database (run training scripts after data ingestion)
- ONNX model files will be generated in src/ml/models/ by training scripts

## Self-Check: PASSED

- All 9 created files verified present on disk
- Commit 617e8b3 (Task 1) verified in git log
- Commit ebfcb0d (Task 2) verified in git log
- All 15 tests pass

---
*Phase: 10-remaining-specialized-engines*
*Completed: 2026-03-25*
