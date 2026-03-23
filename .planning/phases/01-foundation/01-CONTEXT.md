# Phase 1: Foundation - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Project infrastructure production-ready from day one: Docker Compose running three isolated services (bot, pipeline, db), config management via pydantic-settings, LLM wrapper with retry and deterministic fallback, pipeline_runs with per-asset-per-stage checkpointing, and decision schema that prevents look-ahead bias. No feature work — pure infrastructure.

</domain>

<decisions>
## Implementation Decisions

### Dev Workflow
- Local Python (uv) + Docker only for TimescaleDB during development
- uv as package manager (pyproject.toml + uv.lock already initialized)
- Python 3.13+ target (already set in pyproject.toml)
- src/ layout matching ARCHITECTURE.md (e.g., `src/config.py`, `src/bot/main.py`)
- pytest for testing (with pytest-asyncio for async code)
- ruff + mypy for code quality (linting, formatting, and type checking)
- Pre-commit hooks with ruff enabled

### Schema Scope
- Phase 1 tables only: assets, pipeline_runs, daily_decisions (plus any config/data-tier tables needed)
- Other tables (signals, evaluations, lessons, etc.) added in their respective phases via Alembic migrations
- Alembic for all database migrations, auto-generated from SQLAlchemy models
- daily_decisions includes both decision_price and evaluation_price columns with explicit timestamps from day one (look-ahead bias prevention per success criteria #5)
- Default seed data for assets table (BBCA.JK, BTC/USDT, ETH/USDT and a few others) so pipeline is testable immediately

### Checkpoint Granularity
- Per-asset-per-stage checkpointing — pipeline_runs tracks each asset's progress within each stage
- Zero wasted work on restart: if ANALYZE crashes on asset 12, restart resumes from asset 12
- When an asset fails mid-stage, continue processing remaining assets and mark the failed one for retry
- Per-asset timeouts to prevent one hung API call from stalling the entire pipeline (e.g., 60s fetch, 120s analyze, 30s LLM)

### Logging & Alerting
- structlog for structured JSON logging throughout the application
- Critical failures (pipeline crash, DB down, LLM unreachable) alert via Telegram AND log to stdout
- Default log level: INFO in production (pipeline stage starts/completions, asset processing, API call summaries)
- DEBUG available via environment variable for troubleshooting

### Claude's Discretion
- Exact Docker Compose configuration details (resource limits, health check intervals)
- LLM wrapper retry strategy (backoff timing, max retries)
- Deterministic fallback implementation when LLM is unavailable
- Per-asset timeout values (specific seconds per stage)
- structlog configuration and context binding patterns
- Pre-commit hook configuration details
- Seed data: which specific assets to include beyond BBCA.JK, BTC/USDT, ETH/USDT

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Design
- `plan/ARCHITECTURE.md` — Full system architecture, tech stack, database schema, project structure, pipeline stages, LLM integration design, deployment architecture, memory budget, error handling strategy
- `plan/ARCHITECTURE.md` §Database Schema — Complete table definitions including pipeline_runs and daily_decisions with all columns
- `plan/ARCHITECTURE.md` §Deployment Architecture — Docker Compose config, memory budget (2GB VPS), cron trigger setup

### Project Context
- `plan/PROJECT-PLAN.md` — Project overview and feature descriptions
- `plan/FREE_TRADING_APIS_2025_2026.md` — Available free trading APIs and rate limits

### Project Decisions
- `.planning/PROJECT.md` §Key Decisions — Two-process model, LiteLLM, TimescaleDB, sequential execution, ONNX Runtime, asyncpg
- `.planning/STATE.md` §Accumulated Context — Pre-Phase 1 decisions: system cron over APScheduler, pandas-ta-classic, two-process enforcement

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — codebase is a stub (`main.py` with hello world, empty `pyproject.toml`)

### Established Patterns
- None yet — Phase 1 establishes all foundational patterns

### Integration Points
- `pyproject.toml` — Already initialized with uv, Python 3.13+ target. All dependencies to be added here
- `plan/ARCHITECTURE.md` — Detailed project structure to follow for directory layout

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow ARCHITECTURE.md as the primary blueprint.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-23*
