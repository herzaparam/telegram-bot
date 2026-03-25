---
phase: 10
slug: remaining-specialized-engines
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-25
---

# Phase 10 -- Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `python -m pytest tests/ -v --timeout=60` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run `python -m pytest tests/ -v --timeout=60`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | ENGN-04,06,10 | unit | `python -c "from src.db.models import OnChainData, GitHubActivity, MLPrediction; print('OK')"` | N/A (import check) | pending |
| 10-01-02 | 01 | 1 | ENGN-04,06,10 | unit | `python -c "import importlib, inspect; [importlib.import_module(f'src.db.migrations.versions.{n}') for n in ['009_on_chain_data','010_github_activity','011_ml_predictions']]"` | N/A (import check) | pending |
| 10-02-01 | 02 | 1 | ENGN-07,08,13 | unit | `pytest tests/test_engines/test_options.py tests/test_engines/test_game_theory.py tests/test_engines/test_behavioral.py -x -v` | W0 | pending |
| 10-02-02 | 02 | 1 | ENGN-11,14 | unit | `pytest tests/test_engines/test_network.py tests/test_engines/test_emerging.py -x -v` | W0 | pending |
| 10-03-01 | 03 | 2 | ENGN-06 | unit | `pytest tests/test_data/test_onchain_fetcher.py tests/test_engines/test_onchain.py -x -v` | W0 | pending |
| 10-03-02 | 03 | 2 | ENGN-10 | unit | `pytest tests/test_data/test_github_fetcher.py tests/test_engines/test_alternative.py -x -v` | W0 | pending |
| 10-04-01 | 04 | 2 | ENGN-04 | unit | `pytest tests/test_ml/test_features.py tests/test_engines/test_ml_ai.py -x -v` | W0 | pending |
| 10-04-02 | 04 | 2 | ENGN-04 | syntax+api | `python -c "import ast; [ast.parse(open(f).read()) for f in ['src/ml/train_xgboost.py','src/ml/train_lstm.py']]"` | N/A (syntax check) | pending |
| 10-05-01 | 05 | 3 | ALL | integration | `pytest tests/test_data/test_analyze.py -x -v` | W0 | pending |
| 10-05-02 | 05 | 3 | ALL | unit | `python -c "from src.bot.handlers.scorecard import ALL_ENGINE_CATEGORIES; assert len(ALL_ENGINE_CATEGORIES)==15"` | N/A (import check) | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_engines/test_options.py` -- OptionsEngine stub test
- [ ] `tests/test_engines/test_game_theory.py` -- GameTheoryEngine stub test
- [ ] `tests/test_engines/test_behavioral.py` -- BehavioralEngine test
- [ ] `tests/test_engines/test_network.py` -- NetworkEngine test
- [ ] `tests/test_engines/test_emerging.py` -- EmergingMethodsEngine test
- [ ] `tests/test_data/test_onchain_fetcher.py` -- DeFiLlama fetcher test
- [ ] `tests/test_data/test_github_fetcher.py` -- GitHub fetcher test
- [ ] `tests/test_engines/test_onchain.py` -- OnChainEngine test
- [ ] `tests/test_engines/test_alternative.py` -- AlternativeDataEngine test
- [ ] `tests/test_ml/test_features.py` -- Feature engineering test
- [ ] `tests/test_engines/test_ml_ai.py` -- MLAIEngine test
- [ ] `tests/test_data/test_analyze.py` -- 15-engine integration test

*Existing pytest infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| ONNX model training | ENGN-04 | Requires historical data and training time | Run training CLI script, verify ONNX model outputs |
| DeFiLlama API availability | ENGN-06 | External API may be rate-limited | Verify TVL data returned for BTC, ETH, SOL |
| /scorecard 15-engine display | ALL | Visual formatting check | Run /scorecard, verify all 15 engines listed with correct status |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
