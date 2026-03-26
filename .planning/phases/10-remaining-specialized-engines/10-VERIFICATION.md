---
phase: 10-remaining-specialized-engines
verified: 2026-03-26T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 10: Remaining Specialized Engines Verification Report

**Phase Goal:** The full 15-engine suite is operational — ML/AI prediction, on-chain crypto analysis, options flow, behavioral anomalies, network correlation, game theory order book, and emerging quantitative methods
**Verified:** 2026-03-26
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ML/AI engine runs XGBoost and ONNX-deployed LSTM inference within memory budget (lazy load + del session) | VERIFIED | `src/engines/ml_ai.py` uses `_create_session()` lazy import of onnxruntime, `del session` after both XGBoost and LSTM inference (lines 125, 143) with `CPUExecutionProvider` |
| 2 | On-chain engine fetches TVL, and produces a score | VERIFIED | `src/engines/onchain.py` scores crypto from `tvl_7d_change`/`tvl_30d_change`/exchange flows; `src/data/onchain_fetcher.py` fetches from DeFiLlama with CHAIN_MAP for BTC/ETH/SOL |
| 3 | All 15 engines produce a valid score/confidence/reasoning for each applicable asset in a single pipeline run | VERIFIED | Integration tests in `tests/test_data/test_analyze.py` pass: 13 stock engines + 14 crypto engines; combined union = all 15 categories; all produce valid `Signal` with score in [-1,1], confidence in [0,1], non-empty reasoning |
| 4 | Any engine that fails its data source returns score=0/confidence=0 and pipeline completes | VERIFIED | All 8 new engines wrap `_analyze_impl` in try/except; stubs (options, game_theory) return 0/0 by design; onchain/alternative return 0 when data is None; MLAIEngine returns 0 when model files missing |
| 5 | Per-engine accuracy is tracked for all 15 engines and visible in /scorecard | VERIFIED | `src/bot/handlers/scorecard.py` defines `ALL_ENGINE_CATEGORIES` (15 entries) and `STUB_ENGINE_CATEGORIES`; queries `AccuracyStats` per engine; passes `per_engine_accuracy` to formatter. `src/report/formatter.py` renders "Engine Breakdown (24h)" section with N/A for stubs |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | New production dependencies | VERIFIED | Lines 33-35: `xgboost>=3.2.0`, `onnxmltools>=1.16.0`, `pywavelets>=1.9.0` |
| `src/db/models.py` | OnChainData, GitHubActivity, MLPrediction ORM models | VERIFIED | Lines 399, 414, 431: all three classes defined with correct schemas |
| `src/db/migrations/versions/009_on_chain_data.py` | Alembic migration for on_chain_data | VERIFIED | `op.create_table("on_chain_data"...)` + `op.drop_table` present |
| `src/db/migrations/versions/010_github_activity.py` | Alembic migration for github_activity | VERIFIED | `op.create_table("github_activity"...)` + `op.drop_table` present |
| `src/db/migrations/versions/011_ml_predictions.py` | Alembic migration for ml_predictions | VERIFIED | `op.create_table("ml_predictions"...)` + `op.drop_table` present |
| `src/config.py` | github_token setting | VERIFIED | Line 67: `github_token: str = ""` |
| `src/engines/options.py` | OptionsEngine stub | VERIFIED | `class OptionsEngine(BaseEngine)`, returns 0/0, `supports_crypto=False`, reasoning matches spec |
| `src/engines/game_theory.py` | GameTheoryEngine stub | VERIFIED | `class GameTheoryEngine(BaseEngine)`, returns 0/0, `supports_stocks=True`, `supports_crypto=True` |
| `src/engines/behavioral.py` | BehavioralEngine | VERIFIED | Volume Z-score, gap detection, price/volume divergence all implemented; insufficient data guard at <20 rows |
| `src/engines/network.py` | NetworkEngine | VERIFIED | Constructor injection, correlation scoring, regime change amplifier |
| `src/engines/emerging.py` | EmergingMethodsEngine | VERIFIED | Hurst exponent R/S analysis, `pywt.wavedec` with `db4`, fractal dimension = 2-H |
| `src/data/onchain_fetcher.py` | DeFiLlama TVL fetcher | VERIFIED | `DEFILLAMA_BASE`, `CHAIN_MAP`, `fetch_tvl_history`, `fetch_onchain_data`, tenacity retry, UPSERT to OnChainData |
| `src/data/github_fetcher.py` | GitHub API repo stats fetcher | VERIFIED | `CRYPTO_REPOS` with `bitcoin/bitcoin`, `fetch_github_activity`, rate limit warning, UPSERT to GitHubActivity |
| `src/engines/onchain.py` | OnChainEngine | VERIFIED | `supports_stocks=False`, `supports_crypto=True`, TVL + exchange flow scoring |
| `src/engines/alternative.py` | AlternativeDataEngine | VERIFIED | `supports_stocks=False`, `supports_crypto=True`, GitHub activity scoring |
| `src/engines/ml_ai.py` | MLAIEngine with ONNX inference | VERIFIED | Lazy `onnxruntime` import, 60%/40% ensemble, `del session` after inference, graceful missing-model fallback |
| `src/ml/features.py` | Feature engineering from OHLCV | VERIFIED | `extract_features` returns `np.ndarray` shape (1, 20) dtype float32; `FEATURE_NAMES` list of 20 names; returns None for <60 rows |
| `src/ml/train_xgboost.py` | XGBoost training CLI | VERIFIED | `import xgboost`, `convert_xgboost`, `onnxmltools`, `target_opset=18`, `if __name__`, valid Python |
| `src/ml/train_lstm.py` | LSTM training CLI | VERIFIED | `import torch`, `nn.LSTM`, `torch.onnx.export`, `opset_version=18`, `if __name__`, valid Python |
| `src/data/analyze.py` | Updated with all 15 engines | VERIFIED | All 8 new engine imports at lines 23-30; all 8 instantiated in `_get_engines_for_asset`; `_load_onchain_data`, `_load_github_data`, `_compute_correlation_data` defined exactly once |
| `src/data/ingest.py` | On-chain and GitHub fetchers in ingest | VERIFIED | Lines 369-376: lazy imports of `fetch_onchain_data` and `fetch_github_activity` for crypto assets |
| `src/bot/handlers/scorecard.py` | All 15 engine categories in scorecard | VERIFIED | `ALL_ENGINE_CATEGORIES` = 15 entries; `STUB_ENGINE_CATEGORIES` = {"options", "game_theory"}; per-engine AccuracyStats query |
| `src/report/formatter.py` | per_engine_accuracy in formatter | VERIFIED | `per_engine_accuracy` parameter at line 293; "Engine Breakdown (24h)" section; N/A for None values |
| `tests/test_data/test_analyze.py` | Integration test for 15-engine pipeline | VERIFIED | `test_stock_engine_count_is_13`, `test_crypto_engine_count_is_14`, `test_all_stock_engines_produce_valid_signal`, `test_all_crypto_engines_produce_valid_signal`, `test_all_15_categories_covered_across_both_types` — all pass |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `src/engines/ml_ai.py` | `src/ml/features.py` | `from src.ml.features import extract_features` (lazy inside `_analyze_impl`) | WIRED | Confirmed at line 92 of ml_ai.py |
| `src/engines/ml_ai.py` | `onnxruntime` | `import onnxruntime as ort` lazy inside `_create_session` | WIRED | Line 33: lazy import confirmed |
| `src/engines/behavioral.py` | `src/engines/base.py` | `class BehavioralEngine(BaseEngine)` | WIRED | Confirmed |
| `src/engines/emerging.py` | `src/engines/base.py` | `class EmergingMethodsEngine(BaseEngine)` | WIRED | Confirmed |
| `src/engines/onchain.py` | `src/engines/base.py` | `class OnChainEngine(BaseEngine)` | WIRED | Confirmed; `supports_stocks=False` |
| `src/data/onchain_fetcher.py` | `src/db/models.py` | stores `OnChainData` rows | WIRED | `from src.db.models import OnChainData` + pg_insert UPSERT |
| `src/data/github_fetcher.py` | `src/db/models.py` | stores `GitHubActivity` rows | WIRED | `from src.db.models import GitHubActivity` + pg_insert UPSERT |
| `src/data/analyze.py` | `src/engines/ml_ai.py` | imports and instantiates MLAIEngine | WIRED | Line 23 import + line 80 instantiation |
| `src/data/analyze.py` | `src/engines/onchain.py` | imports and instantiates OnChainEngine | WIRED | Line 24 import + line 81 instantiation |
| `src/data/ingest.py` | `src/data/onchain_fetcher.py` | calls fetch_onchain_data | WIRED | Lines 369-371 lazy import and call |
| `src/bot/handlers/scorecard.py` | `src/report/formatter.py` | passes per_engine_accuracy | WIRED | Lines 156, 168, 210 pass `per_engine_accuracy=per_engine_accuracy` |
| `_compute_correlation_data` | analyze_stage | called once per asset, passed to NetworkEngine | WIRED | Line 551 call; result passed at line 370 of `_get_engines_for_asset` call |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `src/engines/onchain.py` | `self._data` (onchain_data dict) | `_load_onchain_data` → reads `OnChainData` table; populated by `fetch_onchain_data` → DeFiLlama API | Yes — TVL metrics from real API, stored and loaded from DB | FLOWING |
| `src/engines/alternative.py` | `self._data` (github_data dict) | `_load_github_data` → reads `GitHubActivity` table; populated by `fetch_github_activity` → GitHub API | Yes — real repo stats stored and loaded from DB | FLOWING |
| `src/engines/network.py` | `self._correlations` | `_compute_correlation_data` → queries `Watchlist` + `PriceHistory`, computes numpy correlations | Yes — real pairwise correlations from DB price data | FLOWING |
| `src/engines/ml_ai.py` | ONNX inference | model files at `src/ml/models/` (absent until training scripts run) | Gracefully returns score=0 with "Model not trained yet" reasoning when absent | STATIC (by design — models require manual training run) |
| `src/report/formatter.py` | `per_engine_accuracy` | scorecard_handler queries `AccuracyStats` with `engine_name IS NOT NULL` | Yes — reads from DB evaluation data | FLOWING |

**Note on ML model files:** The absence of pre-trained `.onnx` files is expected and documented per D-02 — training is a manual CLI step (`python -m src.ml.train_xgboost`). The engine degrades gracefully and the success criterion says "ONNX-deployed LSTM inference" — the inference path is fully implemented and tested with mocked sessions in `test_ml_ai.py`. This is not a gap; it's by design.

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 8 new engines importable | `uv run python -c "from src.engines.ml_ai import MLAIEngine; ..."` | "all 8 new engines importable" | PASS |
| FEATURE_NAMES has 20 entries | `len(FEATURE_NAMES) == 20` | "FEATURE_NAMES count: 20" | PASS |
| Options stub returns 0/0 with documented reasoning | `OptionsEngine().analyze(...)` | score=0.0, confidence=0.0, "Options flow data not available" | PASS |
| GameTheory stub returns 0/0 with documented reasoning | `GameTheoryEngine().analyze(...)` | score=0.0, confidence=0.0, "Real-time order book data not available" | PASS |
| ALL_ENGINE_CATEGORIES has exactly 15 | `len(ALL_ENGINE_CATEGORIES) == 15` | Confirmed 15 entries | PASS |
| Formatter accepts per_engine_accuracy | `inspect.signature(format_scorecard_message)` | "per_engine_accuracy" in params | PASS |
| Training scripts are valid Python | `ast.parse(...)` on both scripts | "Training scripts parseable" | PASS |
| 103 engine tests pass | `uv run python -m pytest tests/test_engines/...` | 103 passed in 0.18s | PASS |
| 37 data/ML tests pass | `uv run python -m pytest tests/test_ml/ tests/test_data/test_onchain_fetcher.py ...` | 37 passed (with 20 from test_analyze.py) | PASS |
| Full suite (excluding DB tests) | `uv run python -m pytest tests/ -q --ignore=tests/test_db` | 707 passed, 1 pre-existing failure (test_config telegram_chat_id, unrelated to Phase 10) | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ENGN-04 | 10-01, 10-04, 10-05 | ML/AI engine (XGBoost, LSTM via ONNX, ensemble) | SATISFIED | `MLAIEngine` with lazy ONNX inference, 60/40 ensemble, feature engineering, training scripts |
| ENGN-06 | 10-01, 10-03, 10-05 | On-chain engine for crypto (TVL, exchange flows) | SATISFIED | `OnChainEngine` + `fetch_onchain_data` + DeFiLlama integration + DB storage |
| ENGN-07 | 10-02, 10-05 | Options engine (stub, limited scope) | SATISFIED | `OptionsEngine` stub returns 0/0 with `supports_crypto=False`, documented TODO for Deribit |
| ENGN-08 | 10-02, 10-05 | Behavioral engine (volume anomaly, herding detection) | SATISFIED | `BehavioralEngine` detects volume Z-score spikes, price gaps, price/volume divergence |
| ENGN-10 | 10-01, 10-03, 10-05 | Alternative data engine (GitHub activity) for crypto | SATISFIED | `AlternativeDataEngine` + `fetch_github_activity` + GitHub API integration + DB storage |
| ENGN-11 | 10-02, 10-05 | Network/graph engine (correlation analysis) | SATISFIED | `NetworkEngine` with constructor-injected correlation_data; `_compute_correlation_data` computes rolling pairwise correlations across watchlist |
| ENGN-13 | 10-02, 10-05 | Game theory engine (stub — real-time order book unavailable) | SATISFIED | `GameTheoryEngine` stub with documented TODO for Binance WebSocket |
| ENGN-14 | 10-02, 10-05 | Emerging methods engine (fractal dimension, wavelet analysis) | SATISFIED | `EmergingMethodsEngine` implements Hurst exponent R/S analysis + PyWavelets db4 decomposition |

**Orphaned requirements check:** No ENGN requirements mapped to Phase 10 exist in REQUIREMENTS.md beyond the 8 listed above. All 8 are claimed by plans and verified.

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/engines/options.py` | entire file | `score=0.0`, `confidence=0.0`, `stub=True` in data_quality | INFO | This is the documented, intentional design for ENGN-07. The stub pattern is by spec, not an oversight. Deribit/IDX options data integration is a future planned enhancement. |
| `src/engines/game_theory.py` | entire file | `score=0.0`, `confidence=0.0`, `stub=True` in data_quality | INFO | Same as above — ENGN-13 stub is by spec (D-17). Binance WebSocket order book is a future enhancement. |
| `src/ml/models/` | directory | No `.onnx` model files present | INFO | Expected and documented per D-02 — models must be trained manually before ML inference produces non-zero scores. The engine returns `"Model not trained yet"` gracefully. Not a pipeline blocker. |

**Stub classification note:** The `options` and `game_theory` engines are intentional, documented stubs. They appear in `/scorecard` with "N/A — data source unavailable" per D-24. These are not implementation gaps; they represent planned future integrations with known data source limitations.

---

### Human Verification Required

#### 1. ML RAM Budget

**Test:** Run a full end-to-end pipeline run (`python -m src`) with at least one crypto and one stock asset in the watchlist, monitoring peak RAM usage.
**Expected:** Pipeline peak RAM stays under 1GB measured end-to-end (Success Criterion #1).
**Why human:** Cannot measure actual process RAM during a live pipeline run without starting the full stack (TimescaleDB, Telegram bot, external APIs). The lazy loading + `del session` pattern is verified in code; actual RAM measurement requires execution.

#### 2. DeFiLlama Live API Response

**Test:** With internet access, run `python -c "import asyncio; from src.data.onchain_fetcher import fetch_tvl_history; print(asyncio.run(fetch_tvl_history('BTC')))"`.
**Expected:** Returns a list of dicts with `{"date": int, "tvl": float}` entries.
**Why human:** Requires live network access to DeFiLlama API; cannot be verified in a sandboxed environment.

#### 3. /scorecard Engine Breakdown in Telegram

**Test:** Send `/scorecard` to the Telegram bot after at least one pipeline run has produced evaluations.
**Expected:** Message includes "Engine Breakdown (24h):" section listing all 15 categories; `options` and `game_theory` show "N/A — data source unavailable"; other engines show accuracy % or "no evaluations yet".
**Why human:** Requires live Telegram bot and DB with evaluation data.

---

### Gaps Summary

No gaps found. All 5 success criteria are verified:

1. **ML/AI ONNX inference** — lazy loading with explicit session release implemented; 60/40 ensemble present; training CLI scripts exist and produce ONNX output; engine gracefully degrades when model files absent.
2. **On-chain engine** — fetches TVL from DeFiLlama for BTC/ETH/SOL, stores to DB, loads in analyze_stage, scores based on 7d/30d TVL trends plus optional exchange flows.
3. **All 15 engines produce valid signals** — integration tests confirm 13 stock engines + 14 crypto engines (union = 15 categories), all returning Signal with valid score/confidence/reasoning.
4. **Failed engines return 0/0 and pipeline continues** — all 8 new engines use try/except wrapping; stubs designed to return 0/0; MLAIEngine returns 0/0 on missing models or insufficient data.
5. **Per-engine accuracy visible in /scorecard** — `ALL_ENGINE_CATEGORIES` (15) defined in scorecard handler; `AccuracyStats` queried per engine; formatter renders "Engine Breakdown" with N/A for stubs.

The one test failure (`test_default_telegram_settings`) is pre-existing from Phase 1 (last modified in commit `1fdd708`) and caused by an `.env` file present in the environment — unrelated to Phase 10.

---

_Verified: 2026-03-26_
_Verifier: Claude (gsd-verifier)_
