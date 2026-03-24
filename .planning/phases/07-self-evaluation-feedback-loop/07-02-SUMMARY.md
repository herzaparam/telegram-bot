---
phase: 07-self-evaluation-feedback-loop
plan: 02
subsystem: pipeline, bot, report
tags: [llm, lesson-injection, telegram, decision-prompt, feedback-loop]

requires:
  - phase: 07-self-evaluation-feedback-loop
    provides: Lesson model, LessonRepository with get_relevant_lessons and get_lessons_for_display
provides:
  - Lesson injection into LLM decision prompts (ASSET-SPECIFIC and GENERAL sections)
  - lessons_applied JSONB recording on DailyDecision
  - /lessons Telegram command with asset_type and engine filters
  - Per-asset lessons applied section in daily report
affects: [daily-report, decision-maker, telegram-bot]

tech-stack:
  added: []
  patterns: [lesson-feedback-loop, prompt-augmentation-with-lessons]

key-files:
  created:
    - src/bot/handlers/lessons.py
    - tests/test_llm/test_prompts.py
    - tests/test_bot/test_lessons.py
  modified:
    - src/llm/prompts.py
    - src/data/decide.py
    - src/db/decision_repo.py
    - src/bot/main.py
    - src/report/formatter.py
    - src/data/report.py
    - tests/test_data/test_decide.py
    - tests/test_report/test_formatter.py

key-decisions:
  - "Lessons split into ASSET-SPECIFIC (non-all) and GENERAL (all) sections in prompt"
  - "Lessons accuracy and usage count shown in prompt for LLM weighting"
  - "lessons_applied stored as {id: text} dict in DailyDecision JSONB column"
  - "/lessons command uses same filter pattern as /scorecard (positional args)"

patterns-established:
  - "Prompt augmentation: lessons appended after Upcoming Events in user message"
  - "Lesson recording: update_lessons_applied + increment_times_applied after decision storage"

requirements-completed: [EVAL-04, LLM-04, TBOT-05, REPT-05]

duration: 6min
completed: 2026-03-24
---

# Phase 7 Plan 2: Lesson Injection and Feedback Loop Summary

**Lessons injected into LLM decision prompts with accuracy stats, /lessons Telegram command with filters, and daily report per-asset lessons applied section**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-24T16:17:55Z
- **Completed:** 2026-03-24T16:23:55Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- LLM decision prompt extended with ASSET-SPECIFIC and GENERAL lesson sections including accuracy and usage stats
- decide_stage queries relevant lessons, injects into prompt, records lessons_applied JSONB, and increments times_applied
- /lessons Telegram command with asset_type (stock/crypto/all) and engine filters, showing recently learned and top lessons
- Daily report asset cards include "Lessons applied" bullet list when lessons influenced a decision

## Task Commits

Each task was committed atomically:

1. **Task 1: Lesson injection into decide prompt and lessons_applied recording** - `f1df70e` (feat)
2. **Task 2: /lessons bot command and daily report lessons section** - `685a905` (feat)

## Files Created/Modified
- `src/llm/prompts.py` - Extended _SYSTEM_PROMPT, _format_engine_data, and build_decision_prompt with lessons parameter
- `src/data/decide.py` - Added lesson_repo import, lesson querying, prompt injection, and lessons_applied recording
- `src/db/decision_repo.py` - Added update_lessons_applied method for JSONB update
- `src/bot/handlers/lessons.py` - New /lessons command handler with asset_type and engine filters
- `src/bot/main.py` - Registered lessons_handler
- `src/report/formatter.py` - Added format_lessons_message and format_lessons_applied functions
- `src/data/report.py` - Modified asset card loop to append lessons_applied section
- `tests/test_llm/test_prompts.py` - TestLessonPrompt with 7 tests for prompt construction
- `tests/test_data/test_decide.py` - TestLessonInjection with 3 tests, updated existing tests to mock lesson_repo
- `tests/test_bot/test_lessons.py` - 5 handler tests (filters, invalid, empty state)
- `tests/test_report/test_formatter.py` - TestLessonsSection with 7 tests for formatter functions

## Decisions Made
- Lessons split into ASSET-SPECIFIC (non-all asset_type) and GENERAL (all asset_type) sections in the prompt
- Accuracy and usage count displayed in prompt so LLM can weight lessons appropriately
- lessons_applied stored as {lesson_id: lesson_text} dict for traceability
- /lessons command reuses the same positional arg filter pattern as /scorecard

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing decide_stage tests to mock lesson_repo**
- **Found during:** Task 1
- **Issue:** Adding lesson_repo import to decide.py caused existing tests to fail because the real lesson_repo.get_relevant_lessons was called on AsyncMock sessions
- **Fix:** Added @patch("src.data.decide.lesson_repo") to all existing TestDecideStage tests and configured mock return values
- **Files modified:** tests/test_data/test_decide.py
- **Verification:** All 33 prompt and decide tests pass
- **Committed in:** f1df70e (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary fix for existing test compatibility. No scope creep.

## Issues Encountered

- Pre-existing test failure in `tests/test_data/test_report_stage.py` (AsyncMock coroutine issue with evaluation_repo.get_recent_evaluations) -- not related to this plan's changes, documented in Plan 01 SUMMARY.

## Known Stubs

None - all functionality is fully wired.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Self-evaluation feedback loop complete: lessons are extracted (Plan 01), injected into decisions, recorded, and visible to users
- Phase 7 objectives fully met: reflect -> learn -> apply -> display cycle operational
- Ready for next phase development

---
*Phase: 07-self-evaluation-feedback-loop*
*Completed: 2026-03-24*
