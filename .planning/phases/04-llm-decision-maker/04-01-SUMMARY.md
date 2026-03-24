---
phase: 04-llm-decision-maker
plan: 01
subsystem: llm
tags: [litellm, json-mode, decision-engine, fallback, contradiction-detection]

requires:
  - phase: 03-signal-engines
    provides: SignalRecord model, SignalRepository, analyze_stage
provides:
  - DecisionResult dataclass for LLM verdict output
  - DecisionRepository with UPSERT on (asset_id, date)
  - build_decision_prompt and build_strict_retry_prompt
  - llm_completion response_format extension
  - decide_stage function (StageFunc signature)
  - Deterministic fallback with confidence-weighted scoring
  - Contradiction detection between engine signals
affects: [04-02-pipeline-wiring, 05-self-evaluation, 09-telegram-report]

tech-stack:
  added: []
  patterns: [json-mode-llm-calls, deterministic-fallback, contradiction-detection, upsert-repository]

key-files:
  created:
    - src/data/decide.py
    - src/db/decision_repo.py
    - src/llm/prompts.py
    - tests/test_data/test_decide.py
    - tests/test_db/test_decision_repo.py
    - tests/test_llm/test_client_response_format.py
  modified:
    - src/llm/client.py
    - src/config.py

key-decisions:
  - "response_format passed via kwargs dict to litellm.acompletion for clean JSON mode support"
  - "timeout_decide_per_call=12s per LLM call so initial + retry fits within 30s stage timeout"
  - "Contradiction detection uses D-08 thresholds: score >+0.3/<-0.3 and confidence >0.5"
  - "Fallback confidence capped at 0.5 with spread-based calculation"

patterns-established:
  - "DecisionRepository UPSERT pattern: pg_insert with on_conflict_do_update on (asset_id, date)"
  - "Prompt builder pattern: system + user message list with formatted engine data"
  - "LLM retry pattern: parse failure -> strict retry prompt -> deterministic fallback"

requirements-completed: [LLM-01, LLM-02, LLM-03, LLM-05]

duration: 5min
completed: 2026-03-24
---

# Phase 04 Plan 01: LLM Decision Maker Summary

**LLM decision stage with JSON-mode structured output, contradiction detection, deterministic fallback, and DecisionRepository UPSERT**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-24T08:47:35Z
- **Completed:** 2026-03-24T08:52:20Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- DecisionRepository with UPSERT on (asset_id, date) conflict for idempotent decision storage
- LLM prompt builder with contradiction sections, event stub, and strict retry variant
- Deterministic fallback computes confidence-weighted verdict when LLM fails, capped at 0.5 confidence
- decide_stage orchestrates full flow: signals -> contradictions -> LLM JSON call -> parse/retry -> store
- 44 tests covering all components with no regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: DecisionRepository, LLM client extension, and prompt builder with tests** - `64b573a` (feat)
2. **Task 2: Decide stage with fallback, parsing, contradiction detection, and full tests** - `9f54e53` (feat)

## Files Created/Modified
- `src/data/decide.py` - DecisionResult dataclass, contradiction detection, fallback logic, LLM parsing, decide_stage
- `src/db/decision_repo.py` - DecisionRepository with UPSERT semantics
- `src/llm/prompts.py` - System/user prompt builder with contradiction and event stub sections
- `src/llm/client.py` - Extended llm_completion with response_format kwarg
- `src/config.py` - Added timeout_decide_per_call=12
- `tests/test_data/test_decide.py` - 23 tests across 4 test classes
- `tests/test_db/test_decision_repo.py` - 5 tests for decision repository
- `tests/test_llm/test_client_response_format.py` - 2 tests for response_format extension

## Decisions Made
- response_format passed via kwargs dict to litellm.acompletion for clean JSON mode support
- timeout_decide_per_call=12s per LLM call so initial + retry fits within 30s stage timeout
- Contradiction detection uses D-08 thresholds: score >+0.3/<-0.3 and confidence >0.5
- Fallback confidence capped at 0.5 with spread-based calculation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Known Stubs
- `src/llm/prompts.py` line with "Upcoming Events: No event data available yet." - intentional per D-17, to be resolved when event data pipeline is built in a future phase

## Next Phase Readiness
- decide_stage ready for pipeline wiring in 04-02
- DecisionRepository available for self-evaluation phase reads
- Prompt builder extensible for future event data integration

## Self-Check: PASSED

All 8 files verified present. Both task commits (64b573a, 9f54e53) verified in git log.

---
*Phase: 04-llm-decision-maker*
*Completed: 2026-03-24*
