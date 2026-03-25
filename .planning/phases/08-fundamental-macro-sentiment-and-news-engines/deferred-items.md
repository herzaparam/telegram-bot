# Deferred Items — Phase 08

## Pre-existing Test Failure (out of scope for 08-04)

**File:** `tests/test_data/test_report_stage.py::test_send_daily_report_with_decisions`

**Issue:** The test mock_session uses `session.execute()` mock but `evaluation_repo.get_recent_evaluations()` uses `session.scalars()`. The `AsyncMock` returns a coroutine for `scalars()`, and `list(coroutine.all())` raises `TypeError: 'coroutine' object is not iterable`.

**When:** Failing since Phase 07 (when `_build_scorecard_section` + `evaluation_repo.get_recent_evaluations` were added), confirmed still failing at commit `e082bb6` (before 08-04 changes).

**Fix needed:** Update mock_session fixture in test_report_stage.py to properly mock `session.scalars()` with an `AsyncMock` that returns a sync `MagicMock` with `all()` returning `[]`.

**Scope:** This should be fixed in a future plan (Phase 09 or maintenance).
