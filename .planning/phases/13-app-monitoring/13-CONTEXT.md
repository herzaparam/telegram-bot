# Phase 13: App Monitoring - Context

**Gathered:** 2026-03-28 (auto mode)
**Status:** Ready for planning

<domain>
## Phase Boundary

Add production observability to the trade-agent system: failure alerting via Telegram, health checks, pipeline metrics tracking, and error capture. The system should self-report problems so operators know when something breaks without checking logs manually.

</domain>

<decisions>
## Implementation Decisions

### Failure Alerting
- **D-01:** Deliver failure alerts via the existing Telegram bot to the same chat used for daily reports. No separate channel or external service.
- **D-02:** Alert triggers: pipeline run failure (entire run or critical asset failure), data staleness exceeding threshold (AlertCollector already detects this), individual engine crashes/no-score, and LLM unavailability (both primary and fallback down).
- **D-03:** Deduplicate alerts per asset per pipeline run to prevent spam on cascade failures. One summary alert at end of run listing all issues, not one per failure.

### Health & Uptime
- **D-04:** Expand the existing `/health` endpoint to include DB connectivity status, last successful pipeline completion timestamp, and bot process uptime.
- **D-05:** Pipeline self-reports completion or failure at end of each run via Telegram message. No external uptime monitoring service — the pipeline run itself is the heartbeat.
- **D-06:** If no pipeline completion message arrives by expected time (configurable, default 1 hour after scheduled cron), the bot should have a "missed run" detection that alerts. This requires the bot to track expected run schedule.

### Pipeline Metrics
- **D-07:** Track per-run: total duration, per-engine duration, fetch success/failure counts per asset, LLM token usage (prompt + completion tokens), and number of assets processed.
- **D-08:** Store metrics in a new DB table (`pipeline_metrics` or similar) for historical trend queries. Also log via structlog for real-time visibility.
- **D-09:** Expose metrics via a Telegram command (e.g., `/stats` or `/metrics`) showing recent pipeline performance trends.

### Error Tracking
- **D-10:** No external error tracking service (no Sentry). Use enhanced structlog with structured error capture for unhandled exceptions.
- **D-11:** Wrap pipeline and bot entry points with top-level exception handlers that capture full tracebacks, log them as structured JSON, and send a Telegram alert with error summary.
- **D-12:** Add a global `sys.excepthook` / asyncio exception handler to catch truly unhandled exceptions in both processes.

### Claude's Discretion
- DB schema design for metrics table (columns, indexes, retention policy)
- Exact alert message formatting (emoji, sections, truncation)
- Health endpoint response schema (JSON structure)
- Missed-run detection implementation approach (polling vs scheduled check)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing observability
- `src/logging.py` — Current structlog setup (JSON/console renderer, processor chain)
- `src/data/alerts.py` — AlertCollector that batches DATA_STALE and FETCH_FAILURE alerts (currently logs only, needs Telegram delivery)
- `src/bot/main.py` — FastAPI app with `/health` endpoint (currently returns basic status)

### Pipeline infrastructure
- `src/pipeline/runner.py` — PipelineRunner with per-asset checkpointing (metrics extraction points)
- `src/pipeline/main.py` — Pipeline CLI entry point (top-level exception handler location)
- `src/config.py` — Settings class (new config fields for alert thresholds, run schedule)

### Bot infrastructure
- `src/bot/handlers/report.py` — Daily report delivery pattern (reuse for alert delivery)
- `src/bot/handlers/start.py` — Command registration pattern

### Database
- `src/db/models.py` — ORM models (new metrics model goes here)
- `src/db/database.py` — Async engine and session factory

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AlertCollector` (`src/data/alerts.py`): Already batches stale/failure alerts during pipeline runs. Needs a Telegram delivery method added rather than building from scratch.
- `send_message` pattern in bot handlers: Telegram message sending is well-established across handlers — reuse for alert delivery.
- structlog JSON renderer: Already configured for production. Error tracking extends this, doesn't replace it.
- `/health` endpoint: Exists in `src/bot/main.py` — extend rather than create new.

### Established Patterns
- Two-process model: Pipeline and bot are separate processes. Pipeline alerts must go through Telegram Bot API directly (httpx call) or write to DB for bot to pick up.
- Per-asset checkpointing: `pipeline_asset_runs` table already tracks per-asset-per-stage results — metrics can build on this.
- pydantic-settings: New config fields (alert thresholds, expected run time) follow existing `Settings` class pattern.
- Alembic migrations: New tables require a new migration version.

### Integration Points
- Pipeline run completion: End of `PipelineRunner.run_pipeline()` is where metrics are captured and alerts are sent.
- Bot startup: `/stats` or `/metrics` command registration in bot handler setup.
- DB: New `pipeline_metrics` table via Alembic migration.
- Config: New settings fields for `ALERT_STALENESS_THRESHOLD_HOURS`, `EXPECTED_PIPELINE_HOUR`, etc.

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches.

</specifics>

<deferred>
## Deferred Ideas

None — analysis stayed within phase scope.

</deferred>

---

*Phase: 13-app-monitoring*
*Context gathered: 2026-03-28*
