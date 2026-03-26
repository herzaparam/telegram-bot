---
phase: 11-asset-discovery-due-diligence
plan: 04
subsystem: pipeline, llm, report
tags: [discovery, due-diligence, telegram, pipeline-wiring, llm-prompt]

# Dependency graph
requires:
  - phase: 11-02
    provides: "Discovery scan module (run_discovery_scan)"
  - phase: 11-03
    provides: "Due diligence computation module (compute_dd_report, DueDiligenceReport model)"
provides:
  - "Discovery scan wired into pipeline post-pipeline flow"
  - "DD computation wired into _enhanced_ingest_stage for stock assets"
  - "DD flags injected into LLM decision prompt"
  - "New Opportunities section in daily Telegram report"
  - "Discovery card, DD report, and compare table formatters"
affects: [11-05, daily-report, llm-decisions]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Post-pipeline function pattern for discovery scan (same as batch cross-cutting)"
    - "Optional parameter extension for send_daily_report (backwards-compatible)"
    - "DD flags loaded per-asset in decide_stage and passed through to LLM prompt"

key-files:
  created:
    - tests/test_report/test_formatter_discovery.py
  modified:
    - src/llm/prompts.py
    - src/report/formatter.py
    - src/pipeline/main.py
    - src/data/report.py
    - src/data/decide.py
    - tests/test_llm/test_prompts.py

key-decisions:
  - "Discovery scan runs as post-pipeline function after batch cross-cutting and before daily report"
  - "DD computation runs per stock asset in _enhanced_ingest_stage with error isolation"
  - "DD flags loaded from DueDiligenceReport in decide_stage with try/except fallback"
  - "Discovery section appended after news digest (last in daily report)"

patterns-established:
  - "Optional dd_flags parameter in LLM prompt functions for extensibility"
  - "Backwards-compatible discoveries parameter in send_daily_report"

requirements-completed: [DISC-04, LLM-06, REPT-07]

# Metrics
duration: 5min
completed: 2026-03-26
---

# Phase 11 Plan 04: Pipeline Integration Summary

**Discovery scan, DD flags in LLM prompt, and New Opportunities section wired into pipeline and daily report**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-26T04:44:32Z
- **Completed:** 2026-03-26T04:49:32Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- LLM decision prompt now includes DUE DILIGENCE FLAGS section with severity-tagged messages
- Discovery card, section, DD report, and compare table formatters added to shared formatter
- Pipeline runs discovery scan post-pipeline and DD computation per stock asset during ingest
- Daily report includes New Opportunities section (omitted when empty)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add DD flags to LLM prompt and discovery/DD formatters** - `f7526ec` (feat)
2. **Task 2: Wire discovery scan + DD computation into pipeline and daily report** - `e33b2ba` (feat)

## Files Created/Modified
- `src/llm/prompts.py` - Added dd_flags parameter to _format_engine_data and build_decision_prompt
- `src/report/formatter.py` - Added format_discovery_card, format_discovery_section, format_dd_report, format_compare_table with emoji constants
- `src/pipeline/main.py` - Wired run_discovery_scan post-pipeline and compute_dd_report in _enhanced_ingest_stage
- `src/data/report.py` - Added discoveries parameter and discovery section to send_daily_report
- `src/data/decide.py` - Added DD flags loading from DueDiligenceReport and pass-through to LLM prompt
- `tests/test_llm/test_prompts.py` - Added TestDDFlags class with 6 tests
- `tests/test_report/test_formatter_discovery.py` - Created with 14 tests for discovery/DD/compare formatters

## Decisions Made
- Discovery scan runs as post-pipeline function after batch cross-cutting and before daily report (consistent with existing pattern for cross-asset operations)
- DD computation runs per stock asset in _enhanced_ingest_stage with individual error isolation (same pattern as fetch_fundamentals)
- DD flags loaded from DueDiligenceReport in decide_stage with try/except so missing DD data never blocks decisions
- Discovery section appended after news digest as last section in daily report per UI-SPEC

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Pipeline integration complete, ready for Plan 05 (Telegram bot commands /discover, /duediligence, /compare)
- All formatters in place for bot command responses
- Discovery scan and DD computation will run automatically in next pipeline execution

---
*Phase: 11-asset-discovery-due-diligence*
*Completed: 2026-03-26*
