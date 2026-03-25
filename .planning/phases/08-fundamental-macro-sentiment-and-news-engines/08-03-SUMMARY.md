---
phase: 08-fundamental-macro-sentiment-and-news-engines
plan: 03
subsystem: engines
tags: [engines, fundamental, macro, sentiment, event, llm, news, zone-mapping, tdd]

requires:
  - phase: 08-fundamental-macro-sentiment-and-news-engines
    plan: 01
    provides: Settings weight fields for fundamental/macro/sentiment, NewsEvent ORM model

provides:
  - FundamentalEngine with zone-mapped P/E, P/B, ROE, revenue growth, dividend yield, D/E
  - MacroEngine with FRED indicator scoring (Fed rate, CPI, DXY, USD/IDR)
  - SentimentEngine with contrarian Fear&Greed + Reddit post engagement heuristic
  - EventEngine filtering by valid categories and asset affected_assets
  - score_news_impact() batch LLM scorer updating NewsEvent rows

affects:
  - 08-04 (analyze_stage wires all six engines for per-asset pipeline execution)

tech-stack:
  added: []
  patterns:
    - "Store-backed constructor injection: engines receive data via __init__, not from price DataFrame"
    - "Zone-mapping: module-level private functions mapping raw values to [-1,+1] sub-scores"
    - "Confidence = data_availability_ratio * agreement_ratio (engines) or available/total (macro)"
    - "try/except at analyze() top level -- never raises, returns score=0/confidence=0 on failure"
    - "Contrarian sentiment scoring: Extreme Fear -> bullish, Extreme Greed -> bearish"
    - "D-12 enforcement: confidence reduced 40% when Reddit unavailable"
    - "score_news_impact caps at 50 headlines and 200 chars, handles LLM_UNAVAILABLE gracefully"

key-files:
  created:
    - src/engines/fundamental.py
    - src/engines/macro.py
    - src/engines/sentiment.py
    - src/engines/event.py
    - src/llm/news_analyzer.py
    - tests/test_engines/test_fundamental.py
    - tests/test_engines/test_macro.py
    - tests/test_engines/test_sentiment.py
    - tests/test_engines/test_event.py
    - tests/test_llm/test_news_analyzer.py
  modified: []

key-decisions:
  - "FundamentalEngine returns score=0/confidence=0 with 'not applicable for crypto' when fundamentals=None (D-03: keep visible to LLM)"
  - "MacroEngine differentiates IDX vs crypto reasoning via _is_stock_symbol() heuristic (no slash, uppercase alpha)"
  - "SentimentEngine duck-types SentimentSnapshot to avoid circular import (accesses .fear_greed_value, .reddit_posts)"
  - "EventEngine VALID_CATEGORIES frozenset enforces category filtering at O(1) lookup"
  - "score_news_impact handles both raw JSON arrays and dict-wrapped arrays from LLM"
  - "Cherry-picked 08-01 code commits (775a660, 2301688) into worktree before implementation (they existed on sibling branch)"

patterns-established:
  - "Four new engines follow identical structure: constructor injection, zone-mappers, weighted composite, confidence, try/except"
  - "LLM news scorer follows batch pattern: query unscored, cap/truncate, call LLM, parse, update, commit"

requirements-completed: [ENGN-02, ENGN-05, ENGN-09, ENGN-12, NEWS-03]

duration: 8min
completed: 2026-03-25
---

# Phase 08 Plan 03: Four Analysis Engines and LLM News Scorer Summary

**Four BaseEngine subclasses (Fundamental, Macro, Sentiment, Event) with zone-mapping scoring plus a batch LLM news impact scorer using JSON mode.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-25T09:41:22Z
- **Completed:** 2026-03-25T09:49:38Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Implemented FundamentalEngine zone-mapping six financial ratios (P/E, P/B, ROE, revenue growth, dividend yield, D/E) with crypto-not-applicable path
- Implemented MacroEngine zone-mapping four FRED indicators with differentiated IDX vs crypto reasoning
- Implemented SentimentEngine with contrarian Fear & Greed scoring and Reddit degradation (D-12: 40% confidence reduction)
- Implemented EventEngine filtering by VALID_CATEGORIES frozenset and affected_assets dict membership
- Implemented score_news_impact() LLM batch scorer with 50-headline cap, 200-char truncation, JSON mode, and graceful LLM failure handling
- All 93 tests pass (78 engine tests + 15 news analyzer tests)

## Task Commits

Each task was committed atomically (TDD: RED, then GREEN):

1. **Task 1 RED: failing tests for four engines** - `217db2c` (test)
2. **Task 1 GREEN: four engine implementations** - `a3c5fd9` (feat)
3. **Task 2 RED: failing tests for news analyzer** - `e7e06f7` (test)
4. **Task 2 GREEN: LLM news analyzer implementation** - `6513d20` (feat)

## Files Created

- `src/engines/fundamental.py` - FundamentalEngine with 6 zone-mapping functions
- `src/engines/macro.py` - MacroEngine with 4 zone-mapping functions + FRED_SERIES reference
- `src/engines/sentiment.py` - SentimentEngine with contrarian F&G + Reddit heuristic
- `src/engines/event.py` - EventEngine with category/asset filtering
- `src/llm/news_analyzer.py` - score_news_impact() batch LLM scorer
- `tests/test_engines/test_fundamental.py` - 16+ tests
- `tests/test_engines/test_macro.py` - 14+ tests
- `tests/test_engines/test_sentiment.py` - 8+ tests
- `tests/test_engines/test_event.py` - 11+ tests
- `tests/test_llm/test_news_analyzer.py` - 15 tests

## Decisions Made

- FundamentalEngine returns "Fundamentals not applicable for crypto" (exact string from D-03) when fundamentals=None, score=0, confidence=0 — keeps engine visible to LLM decision maker
- MacroEngine uses `_is_stock_symbol()` heuristic to distinguish IDX stocks from crypto: no "/" in symbol, all uppercase alpha ≥ 3 chars
- SentimentEngine duck-types the SentimentSnapshot to avoid circular imports — accesses `.fear_greed_value`, `.fear_greed_classification`, `.reddit_posts` via `getattr()`
- EventEngine uses `frozenset` for VALID_CATEGORIES (O(1) lookup); confidence formula `min(0.8, 0.2 * n_relevant)` matches plan spec
- score_news_impact handles both bare JSON arrays and dict-wrapped arrays (LLMs sometimes wrap arrays in `{"results": [...]}`)
- Cherry-picked commits 775a660 and 2301688 (08-01 code changes) into this worktree before implementing — they existed only on a sibling worktree branch, not yet merged to main

## Deviations from Plan

### Setup Fix (not a code deviation)

**Cherry-pick of 08-01 code changes into worktree**
- **Found during:** Pre-execution checks
- **Issue:** Phase 08-01 code commits (config weight fields, ORM models) were on branch `worktree-agent-a...` but not merged to main yet
- **Fix:** `git cherry-pick 775a660 2301688` to bring those changes into this worktree
- **Impact:** None — plan executed exactly as written after setup

## Known Stubs

None. All four engines produce real scores from injected data. The Reddit sentiment heuristic (post engagement score) is intentionally simple — per plan spec, full LLM Reddit analysis happens in `analyze_stage` (outside the engine). This is documented in the code comment referencing D-10.

## Self-Check: PASSED

All created files verified present. All task commits verified:
- `217db2c`: test(08-03) RED phase for four engines
- `a3c5fd9`: feat(08-03) GREEN phase for four engines
- `e7e06f7`: test(08-03) RED phase for news analyzer
- `6513d20`: feat(08-03) GREEN phase for news analyzer
