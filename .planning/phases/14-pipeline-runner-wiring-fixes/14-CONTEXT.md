# Phase 14: Pipeline Runner Wiring Fixes - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix pipeline runner so its default stage list includes all registered stages (especially reflect) and each stage uses its configured timeout. Gap closure from v1.0 milestone audit.

</domain>

<decisions>
## Implementation Decisions

### Default Stage List Strategy
- **D-01:** When `stages=None`, derive the stage list from `stage_funcs.keys()` instead of using a hardcoded list. Python 3.7+ guarantees dict insertion order, and `main.py` already defines stages in the correct order: `evaluate`, `reflect`, `fetch`, `analyze`, `decide`.
- **D-02:** Remove the hardcoded default `stages = ["evaluate", "fetch", "analyze", "decide", "report"]` from `runner.py:71`. Replace with `stages = list(stage_funcs.keys())` when `stages` is `None`.

### Stage Validation
- **D-03:** Add fail-fast validation: if a stage name in the `stages` list has no corresponding entry in `stage_funcs`, raise a `ValueError` immediately instead of silently skipping with a warning log. This catches configuration errors at pipeline start rather than producing mysterious missing-stage behavior.
- **D-04:** The current `no_stage_func` warning log at `runner.py:79-80` should be replaced with the ValueError raise.

### Timeout Mapping
- **D-05:** Add `"reflect": settings.timeout_reflect` to the `_get_timeout()` timeouts dict in `runner.py:305-311`. The configured value is 120s (vs the 60s fallback default).

### Claude's Discretion
- Error message wording for the ValueError
- Whether to add a log line when deriving stages from stage_funcs keys (for observability)
- Test structure and naming

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Pipeline runner
- `src/pipeline/runner.py` — PipelineRunner class, `run_pipeline()` method (line 52), `_get_timeout()` method (line 296), hardcoded default stages (line 71)
- `src/pipeline/main.py` — `async_main()` (line 286), `stage_funcs` dict (line 301-307) with correct stage ordering

### Config
- `src/config.py` — `timeout_reflect = 120` setting

### Audit
- `.planning/v1.0-MILESTONE-AUDIT.md` — Integration issues #1 (reflect stage) and #3 (timeout mapping)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `PipelineRunner` class is well-structured — changes are isolated to `run_pipeline()` and `_get_timeout()`
- Existing test suite in `tests/test_pipeline/test_runner.py` covers stage execution, idempotency, failure isolation

### Established Patterns
- Stage functions follow `StageFunc = Callable[[AsyncSession, Asset], Awaitable[None]]` contract
- `stage_funcs` dict in `main.py` uses insertion order for stage sequencing
- `_get_timeout()` uses a simple dict lookup with 60s fallback

### Integration Points
- `runner.run_pipeline()` called from `main.py:async_main()` — the only call site
- `stage_funcs` dict defined in `main.py` is the single source of truth for registered stages

</code_context>

<specifics>
## Specific Ideas

No specific requirements — straightforward wiring fix guided by audit findings.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 14-pipeline-runner-wiring-fixes*
*Context gathered: 2026-03-28*
