# Phase 13: App Monitoring - Research

**Researched:** 2026-03-28
**Domain:** Production observability (alerting, health checks, metrics, error capture)
**Confidence:** HIGH

## Summary

Phase 13 adds production observability to an existing async Python pipeline + FastAPI bot system. The codebase already has significant infrastructure to build on: `AlertCollector` batches alerts during pipeline runs (currently logs only), `send_telegram_message` sends HTML via httpx, `send_pipeline_failure_alert` handles total failure, and the `/health` endpoint returns basic status. The work is primarily integration and extension of existing patterns, not greenfield.

The key architectural challenge is the two-process boundary: the pipeline process (cron-triggered, short-lived) sends alerts directly via httpx, while the bot process (long-running FastAPI) handles health checks, `/stats` commands, and missed-run detection. The `pipeline_metrics` table in PostgreSQL is the integration bus between them, consistent with the established pattern.

**Primary recommendation:** Extend existing `AlertCollector` with Telegram delivery, add `PipelineMetrics` ORM model, enhance `/health` with DB probe + last-run timestamp, and implement missed-run detection as a periodic check in the bot process.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Deliver failure alerts via the existing Telegram bot to the same chat used for daily reports. No separate channel or external service.
- **D-02:** Alert triggers: pipeline run failure (entire run or critical asset failure), data staleness exceeding threshold (AlertCollector already detects this), individual engine crashes/no-score, and LLM unavailability (both primary and fallback down).
- **D-03:** Deduplicate alerts per asset per pipeline run to prevent spam on cascade failures. One summary alert at end of run listing all issues, not one per failure.
- **D-04:** Expand the existing `/health` endpoint to include DB connectivity status, last successful pipeline completion timestamp, and bot process uptime.
- **D-05:** Pipeline self-reports completion or failure at end of each run via Telegram message. No external uptime monitoring service — the pipeline run itself is the heartbeat.
- **D-06:** If no pipeline completion message arrives by expected time (configurable, default 1 hour after scheduled cron), the bot should have a "missed run" detection that alerts. This requires the bot to track expected run schedule.
- **D-07:** Track per-run: total duration, per-engine duration, fetch success/failure counts per asset, LLM token usage (prompt + completion tokens), and number of assets processed.
- **D-08:** Store metrics in a new DB table (`pipeline_metrics` or similar) for historical trend queries. Also log via structlog for real-time visibility.
- **D-09:** Expose metrics via a Telegram command (e.g., `/stats` or `/metrics`) showing recent pipeline performance trends.
- **D-10:** No external error tracking service (no Sentry). Use enhanced structlog with structured error capture for unhandled exceptions.
- **D-11:** Wrap pipeline and bot entry points with top-level exception handlers that capture full tracebacks, log them as structured JSON, and send a Telegram alert with error summary.
- **D-12:** Add a global `sys.excepthook` / asyncio exception handler to catch truly unhandled exceptions in both processes.

### Claude's Discretion
- DB schema design for metrics table (columns, indexes, retention policy)
- Exact alert message formatting (emoji, sections, truncation)
- Health endpoint response schema (JSON structure)
- Missed-run detection implementation approach (polling vs scheduled check)

### Deferred Ideas (OUT OF SCOPE)
None.
</user_constraints>

## Project Constraints (from CLAUDE.md)

- Two-process model enforced: bot process MUST NOT import from `src.pipeline` or `src.llm`
- Pipeline sends Telegram via httpx (not PTB) per D-16 two-process boundary
- pydantic-settings for all config fields
- Alembic for all DB schema changes
- structlog for all logging (JSON production, console dev)
- SQLAlchemy ORM with naming conventions for constraints
- Frozen dataclasses for immutable result types
- mypy strict mode
- ruff format + ruff lint
- pytest with asyncio_mode = "auto"
- HTML parse_mode for Telegram messages

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| structlog | 25.5.0+ | Structured logging, error capture | Already configured with JSON/console renderer |
| httpx | 0.28.1+ | Telegram Bot API calls from pipeline | Already used in `src/data/report.py` |
| FastAPI | 0.135.1+ | Health endpoint, webhook server | Already running bot process |
| SQLAlchemy | (existing) | ORM for pipeline_metrics table | All DB access through ORM |
| Alembic | (existing) | Migration for new table | Established migration pattern |
| pydantic-settings | 2.13.1+ | Config fields for thresholds | Existing `Settings` class |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-telegram-bot | (existing) | `/stats` command handler in bot | Bot-side command registration only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| DB polling for missed-run | APScheduler in bot | APScheduler 4 is alpha (per project decision); asyncio.create_task with sleep loop is simpler |
| structlog error capture | Sentry | D-10 explicitly forbids external error tracking |
| JSONB metrics blob | Separate columns per metric | Separate columns better for SQL queries; use typed columns |

**Installation:** No new dependencies required. All libraries already in the project.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── data/
│   ├── alerts.py          # EXTEND: add Telegram delivery, engine/LLM alert types
│   └── report.py          # EXTEND: add pipeline completion/failure summary message
├── monitoring/            # NEW module
│   ├── __init__.py
│   ├── metrics.py         # MetricsCollector: captures per-run metrics
│   ├── error_handler.py   # Global exception handlers (sys.excepthook, asyncio)
│   └── alert_sender.py    # Shared alert formatting + Telegram send (used by pipeline)
├── bot/
│   ├── main.py            # EXTEND: /health enhancement, missed-run checker task
│   └── handlers/
│       └── stats.py       # NEW: /stats command handler
├── db/
│   └── models.py          # EXTEND: PipelineMetrics model
├── pipeline/
│   └── main.py            # EXTEND: wrap async_main with error handler, capture metrics
└── config.py              # EXTEND: new settings fields
```

### Pattern 1: Pipeline Metrics Collection
**What:** Instrument `async_main()` in `src/pipeline/main.py` to capture timing, counts, and token usage into a `PipelineMetrics` DB row at end of run.
**When to use:** Every pipeline run.
**Example:**
```python
@dataclass(frozen=True)
class RunMetrics:
    """Collected metrics from a single pipeline run."""
    run_date: date
    total_duration_seconds: float
    stage_durations: dict[str, float]  # stage_name -> seconds
    assets_processed: int
    assets_failed: int
    fetch_success_count: int
    fetch_failure_count: int
    llm_prompt_tokens: int
    llm_completion_tokens: int
    status: str  # "completed" | "partial" | "failed"
```

### Pattern 2: Alert Summary at End of Run
**What:** After all stages complete, collect all issues (from AlertCollector + StageResults) into a single deduped summary, send one Telegram message.
**When to use:** When any failures/staleness detected during run (D-03).
**Example:**
```python
async def send_run_summary_alert(
    stage_results: list[StageResult],
    alert_collector: AlertCollector,
    run_date: date,
) -> None:
    """Send one consolidated alert for all issues in this run."""
    issues: list[str] = []
    # From stage results
    for sr in stage_results:
        if sr.assets_failed > 0:
            issues.append(f"{sr.stage}: {sr.assets_failed} assets failed")
    # From alert collector (deduped per asset)
    seen_assets: set[str] = set()
    for alert in alert_collector.alerts:
        if alert.asset_symbol not in seen_assets:
            issues.append(f"{alert.asset_symbol}: {alert.alert_type.lower()}")
            seen_assets.add(alert.asset_symbol)
    if issues:
        # Format and send single message
        ...
```

### Pattern 3: Missed-Run Detection in Bot Process
**What:** An asyncio background task in the bot process that periodically checks DB for last pipeline completion timestamp. If no run completed within the expected window, sends alert.
**When to use:** D-06 missed-run detection.
**Example:**
```python
async def missed_run_checker() -> None:
    """Periodic check for missed pipeline runs."""
    while True:
        await asyncio.sleep(900)  # Check every 15 minutes
        async with async_session_factory() as session:
            last_run = await _get_last_completed_run(session)
            if _is_run_overdue(last_run, settings.expected_pipeline_hour):
                await _send_missed_run_alert()
```

### Pattern 4: Enhanced Health Endpoint
**What:** Extend `/health` to probe DB, report last pipeline run, and bot uptime.
**When to use:** D-04 health check enhancement.
**Example:**
```python
@app.get("/health")
async def health() -> dict:
    db_ok = False
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    last_run = None
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(PipelineMetrics)
                .order_by(PipelineMetrics.completed_at.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row:
                last_run = row.completed_at.isoformat()
    except Exception:
        pass

    return {
        "status": "ok" if db_ok else "degraded",
        "db": "connected" if db_ok else "disconnected",
        "last_pipeline_run": last_run,
        "uptime_seconds": _get_uptime(),
    }
```

### Anti-Patterns to Avoid
- **Alerting per failure as it happens:** D-03 requires deduplication. Collect all issues, send one summary at end of run.
- **Bot importing pipeline modules:** Two-process boundary. Bot reads metrics/status from DB only.
- **Using PTB in pipeline process:** Pipeline must use httpx for Telegram API calls (established pattern).
- **External monitoring dependencies:** D-05 and D-10 explicitly forbid Sentry, external uptime services.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Telegram message sending | Custom HTTP client | Existing `send_telegram_message` in `src/data/report.py` | Already handles rate limiting, error logging |
| Alert batching | New alert collection | Extend existing `AlertCollector` in `src/data/alerts.py` | Already batches DATA_STALE and FETCH_FAILURE |
| Config management | Manual env parsing | pydantic-settings `Settings` class | Validated, typed, .env support |
| DB migration | Raw SQL | Alembic migration | Reversible, version-tracked |
| Structured error logging | Custom formatter | structlog exception processor | Already configured with JSON output |

**Key insight:** This phase is almost entirely about extending existing infrastructure. The AlertCollector, send_telegram_message, /health endpoint, Settings class, and ORM model patterns are all established. New code connects these pieces rather than building from scratch.

## Common Pitfalls

### Pitfall 1: Two-Process Boundary Violation
**What goes wrong:** Bot process imports `src.pipeline` or `src.llm` modules for metrics/alert logic.
**Why it happens:** Tempting to share code directly rather than through DB.
**How to avoid:** Place shared utilities (alert formatting, metrics data classes) in `src/monitoring/` which neither pipeline nor bot "owns." Bot reads metrics from DB. Pipeline writes metrics to DB.
**Warning signs:** Any import in `src/bot/` from `src.pipeline` or `src.llm`.

### Pitfall 2: Alert Spam on Cascade Failures
**What goes wrong:** If 5 assets fail in fetch stage, and that causes 5 more failures in analyze stage, you get 10+ individual alerts.
**Why it happens:** Alerting on each failure independently without deduplication.
**How to avoid:** D-03 requires one summary alert. Collect all issues into AlertCollector, deduplicate per asset per run, send single message at end of pipeline.
**Warning signs:** Multiple Telegram messages per pipeline run for failures.

### Pitfall 3: Missed-Run Checker Running in Pipeline Process
**What goes wrong:** Missed-run detection only works while pipeline is running, which defeats the purpose (it should detect when pipeline DIDN'T run).
**Why it happens:** Putting the checker in the wrong process.
**How to avoid:** D-06 explicitly states the bot should have missed-run detection. The bot is long-running, the pipeline is short-lived.
**Warning signs:** Missed-run code in `src/pipeline/`.

### Pitfall 4: LLM Token Tracking Without litellm Callback
**What goes wrong:** Token usage is hardcoded or estimated rather than actual.
**Why it happens:** Not aware that litellm response objects contain `usage` data.
**How to avoid:** litellm `acompletion` responses include `response.usage.prompt_tokens` and `response.usage.completion_tokens`. Accumulate these in a thread-safe counter during the pipeline run.
**Warning signs:** Token counts that don't match actual usage.

### Pitfall 5: Health Endpoint Blocking on DB Query
**What goes wrong:** `/health` hangs when DB is unreachable because the query has no timeout.
**Why it happens:** Default SQLAlchemy timeouts are long.
**How to avoid:** Wrap DB probe in `asyncio.wait_for()` with a 3-5 second timeout. Return "degraded" status if timeout exceeds.
**Warning signs:** Health check taking >5 seconds.

### Pitfall 6: Global Exception Handler Swallowing Errors
**What goes wrong:** `sys.excepthook` or asyncio exception handler catches an error, tries to send Telegram alert, but Telegram send also fails (no network), and the original error is lost.
**Why it happens:** Alert sending can itself fail.
**How to avoid:** Always log the original exception to structlog FIRST, then attempt Telegram alert as best-effort. Never let alert sending failure mask the original error.
**Warning signs:** Errors disappearing from logs.

## Code Examples

### PipelineMetrics ORM Model
```python
# In src/db/models.py
class PipelineMetrics(Base):
    """Per-run pipeline performance metrics (D-07, D-08)."""

    __tablename__ = "pipeline_metrics"
    __table_args__ = (UniqueConstraint("run_date", name="uq_pipeline_metrics_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # completed/partial/failed
    total_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    stage_durations: Mapped[dict] = mapped_column(JSONB, nullable=False)  # {"fetch": 12.3, "analyze": 45.6, ...}
    assets_processed: Mapped[int] = mapped_column(Integer, nullable=False)
    assets_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fetch_success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fetch_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    llm_completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alert_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    alerts_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
```

### Global Exception Handler
```python
# In src/monitoring/error_handler.py
import sys
import asyncio
import traceback
import structlog

logger = structlog.get_logger(__name__)

def install_exception_handlers(process_name: str) -> None:
    """Install global exception handlers for unhandled errors."""

    def sync_excepthook(exc_type, exc_value, exc_tb):
        tb_str = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.critical(
            "unhandled_exception",
            process=process_name,
            exc_type=exc_type.__name__,
            exc_message=str(exc_value),
            traceback=tb_str,
        )
        # Best-effort Telegram alert (fire-and-forget)
        try:
            asyncio.get_event_loop().create_task(
                _send_error_alert(process_name, exc_type.__name__, str(exc_value))
            )
        except Exception:
            pass  # Don't let alert failure mask original error

    def asyncio_exception_handler(loop, context):
        exception = context.get("exception")
        message = context.get("message", "")
        logger.critical(
            "asyncio_unhandled_exception",
            process=process_name,
            message=message,
            exception=str(exception) if exception else None,
            traceback=traceback.format_exception(exception) if exception else None,
        )

    sys.excepthook = sync_excepthook
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(asyncio_exception_handler)
```

### Extended AlertCollector
```python
# Extended methods on existing AlertCollector
def add_engine_failure(self, asset_symbol: str, engine_name: str, reason: str) -> None:
    """Record an ENGINE_FAILURE alert."""
    alert = Alert(
        alert_type="ENGINE_FAILURE",
        asset_symbol=asset_symbol,
        message=f"{engine_name}: {reason}",
        timestamp=datetime.now(UTC),
    )
    self._alerts.append(alert)
    self._log.error("engine_failure", asset=asset_symbol, engine=engine_name, reason=reason)

def add_llm_unavailable(self, reason: str) -> None:
    """Record an LLM_UNAVAILABLE alert."""
    alert = Alert(
        alert_type="LLM_UNAVAILABLE",
        asset_symbol="GLOBAL",
        message=reason,
        timestamp=datetime.now(UTC),
    )
    self._alerts.append(alert)
    self._log.critical("llm_unavailable", reason=reason)

def deduplicated_summary(self) -> dict[str, list[str]]:
    """Return alerts deduped per asset, grouped by type."""
    grouped: dict[str, set[str]] = {}
    for a in self._alerts:
        grouped.setdefault(a.alert_type, set()).add(a.asset_symbol)
    return {k: sorted(v) for k, v in grouped.items()}
```

### New Settings Fields
```python
# In Settings class (src/config.py)
# Monitoring
alert_staleness_threshold_hours: int = 24
expected_pipeline_hour: int = 7  # Expected completion hour (UTC)
missed_run_grace_minutes: int = 60  # Alert if run not complete within this many minutes after expected hour
```

### Alembic Migration (015)
```python
# src/db/migrations/versions/015_pipeline_metrics.py
def upgrade() -> None:
    op.create_table(
        "pipeline_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("total_duration_seconds", sa.Float(), nullable=False),
        sa.Column("stage_durations", postgresql.JSONB(), nullable=False),
        sa.Column("assets_processed", sa.Integer(), nullable=False),
        sa.Column("assets_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fetch_success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fetch_failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("llm_completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alert_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("alerts_summary", postgresql.JSONB(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("run_date", name="uq_pipeline_metrics_date"),
    )

def downgrade() -> None:
    op.drop_table("pipeline_metrics")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| AlertCollector logs only | AlertCollector + Telegram delivery | This phase | Operators get notified of failures |
| Basic `/health` returning `{"status": "ok"}` | Rich health with DB, last run, uptime | This phase | External monitoring can probe meaningful state |
| No metrics capture | Per-run metrics in DB + structlog | This phase | Historical trend analysis possible |
| No global exception handling | sys.excepthook + asyncio handler | This phase | Truly unhandled exceptions captured |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio |
| Config file | `pyproject.toml` under `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_monitoring/ -x -vv` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | Alert sent to same Telegram chat | unit | `pytest tests/test_monitoring/test_alert_sender.py -x` | Wave 0 |
| D-02 | Alert triggers for all failure types | unit | `pytest tests/test_monitoring/test_alert_sender.py -x` | Wave 0 |
| D-03 | Deduplication per asset per run | unit | `pytest tests/test_data/test_alerts.py -x` | Wave 0 |
| D-04 | Enhanced /health endpoint | unit | `pytest tests/test_bot/test_health.py -x` | Wave 0 |
| D-05 | Pipeline self-reports completion | unit | `pytest tests/test_monitoring/test_metrics.py -x` | Wave 0 |
| D-06 | Missed-run detection | unit | `pytest tests/test_monitoring/test_missed_run.py -x` | Wave 0 |
| D-07 | Per-run metrics tracking | unit | `pytest tests/test_monitoring/test_metrics.py -x` | Wave 0 |
| D-08 | Metrics stored in DB table | integration | `pytest tests/test_db/test_models.py -x` | Extend existing |
| D-09 | /stats command shows trends | unit | `pytest tests/test_bot/test_stats_handler.py -x` | Wave 0 |
| D-10 | Structured error capture (no Sentry) | unit | `pytest tests/test_monitoring/test_error_handler.py -x` | Wave 0 |
| D-11 | Top-level exception handlers | unit | `pytest tests/test_monitoring/test_error_handler.py -x` | Wave 0 |
| D-12 | Global sys.excepthook + asyncio handler | unit | `pytest tests/test_monitoring/test_error_handler.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_monitoring/ tests/test_data/test_alerts.py -x -vv`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_monitoring/__init__.py` -- package init
- [ ] `tests/test_monitoring/conftest.py` -- shared fixtures (mock Telegram, mock DB session)
- [ ] `tests/test_monitoring/test_alert_sender.py` -- covers D-01, D-02
- [ ] `tests/test_monitoring/test_metrics.py` -- covers D-05, D-07
- [ ] `tests/test_monitoring/test_error_handler.py` -- covers D-10, D-11, D-12
- [ ] `tests/test_monitoring/test_missed_run.py` -- covers D-06
- [ ] `tests/test_bot/test_health.py` -- covers D-04
- [ ] `tests/test_bot/test_stats_handler.py` -- covers D-09

## Open Questions

1. **LLM Token Accumulation Mechanism**
   - What we know: litellm response objects include `usage.prompt_tokens` and `usage.completion_tokens`
   - What's unclear: How to thread-safely accumulate tokens across multiple LLM calls in the pipeline without modifying `src/llm/client.py` significantly
   - Recommendation: Add a module-level token counter in `src/monitoring/metrics.py` with `add_tokens(prompt, completion)` function. Call it from `decide_stage` after each LLM response. Simple approach, no threading concerns since pipeline is single-threaded async.

2. **Per-Engine Duration Tracking**
   - What we know: `StageResult` has `duration_seconds` per stage. D-07 wants per-engine duration.
   - What's unclear: "Per-engine" likely means per-analysis-engine (technical, fundamental, etc.) within the analyze stage
   - Recommendation: Instrument `analyze_stage` to time each engine call and store in stage_durations dict as `{"analyze.technical": 2.3, "analyze.fundamental": 1.1, ...}`. This data already flows through StageResult.

3. **Missed-Run Detection: Edge Cases**
   - What we know: Bot checks DB for last pipeline completion
   - What's unclear: What happens on weekends/holidays when pipeline may intentionally not run
   - Recommendation: Use `expected_pipeline_hour` setting + simple daily expectation. If the pipeline has a cron schedule that skips weekends, the expected hour check naturally passes (no run expected = no metric row, but also no overdue detection). Can add `pipeline_run_days` setting (default "mon-sun") if needed, but start simple.

## Sources

### Primary (HIGH confidence)
- Codebase inspection: `src/data/alerts.py`, `src/data/report.py`, `src/bot/main.py`, `src/pipeline/main.py`, `src/pipeline/runner.py`, `src/config.py`, `src/db/models.py`
- Codebase docs: `.planning/codebase/CONVENTIONS.md`, `.planning/codebase/TESTING.md`

### Secondary (MEDIUM confidence)
- structlog exception handling patterns from structlog documentation (well-known, stable API)
- Python `sys.excepthook` and asyncio exception handler documentation (stdlib, stable)

### Tertiary (LOW confidence)
- None -- this phase builds entirely on existing codebase patterns with no new external dependencies.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing libraries
- Architecture: HIGH -- extends established patterns (AlertCollector, send_telegram_message, ORM models, Settings)
- Pitfalls: HIGH -- two-process boundary and deduplication are well-documented in project history

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (stable -- no external dependency changes)
