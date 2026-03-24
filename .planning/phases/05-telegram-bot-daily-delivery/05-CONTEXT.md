# Phase 5: Telegram Bot + Daily Delivery - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Users receive the daily signal report automatically every morning via Telegram and can query it on demand. Watchlist management via Telegram commands (add/remove/view). Report commands (/report, /report ASSET). Basic settings (/settings for delivery time). Completes the core daily signal loop end-to-end: fetch -> analyze -> decide -> report. Does NOT include: accuracy tracking (Phase 6), self-evaluation (Phase 7), /scorecard (Phase 6), /lessons (Phase 7), /discover (Phase 11), additional engines, or advanced commands.

</domain>

<decisions>
## Implementation Decisions

### Telegram Integration
- **D-01:** Webhook mode — Telegram pushes updates to the bot via HTTPS webhook, not polling
- **D-02:** PTB (python-telegram-bot v20+) webhook handler mounted on existing FastAPI app. FastAPI remains the main server; PTB registers a webhook route (e.g., `/telegram/webhook`). Health endpoint stays at `/health`. One uvicorn process serves both
- **D-03:** Access restricted via whitelist — only configured Telegram user/chat IDs can interact. Matches the small-group-of-traders use case. Unauthorized messages are silently ignored
- **D-04:** Bot process uses `python-telegram-bot` v20+ as specified in ARCHITECTURE.md

### Report Format & Structure
- **D-05:** All report text in English. Indonesian terms only for asset names (BBCA, IHSG) — consistent with Phase 4 D-01 (English-only prompts/reasoning)
- **D-06:** Compact card format per asset: emoji verdict badge + asset name + score + confidence + 1-line reasoning summary. Dense, fits more assets per message
- **D-07:** Report starts with a market overview header: date, total assets analyzed, sentiment distribution (e.g., "3 BUY, 1 HOLD, 2 SELL"), and any active risk warnings
- **D-08:** Messages exceeding Telegram's 4096-char limit split by asset group. Each message is self-contained with its own mini-header. Summary header is always the first message

### Watchlist Management
- **D-09:** Shared watchlist for the entire group — one watchlist, any whitelisted user can add/remove. No per-user watchlists. No user table needed
- **D-10:** Command syntax: `/add BBCA` or `/add BTC` to add, `/remove BBCA` to remove, `/watchlist` to view current list. Simple top-level commands, not subcommands
- **D-11:** Users can add assets not in the seed data. Bot validates the symbol (yfinance for .JK stocks, ccxt for crypto pairs), creates a new row in the `assets` table, and adds to watchlist. Next pipeline run picks it up automatically
- **D-12:** When a new asset is added with no price history: confirm add and set expectation — "Added UNVR (Unilever Indonesia). Price data will be fetched on next pipeline run. Signals available tomorrow."
- **D-13:** Watchlist starts empty — no auto-seeding. Users build their own watchlist. `/start` welcome message explains how to add assets
- **D-14:** Pipeline continues running against all active assets in the `assets` table. Watchlist only controls which assets appear in the Telegram report. Decouples analysis from delivery

### Delivery Scheduling
- **D-15:** Report delivery is a pipeline stage (Stage 5: REPORT per ARCHITECTURE.md). After DECIDE completes, pipeline formats and sends the report. System cron triggers the pipeline daily
- **D-16:** Pipeline's report stage sends Telegram messages directly via Telegram Bot API (using python-telegram-bot or raw httpx). No bot process involvement in sending reports. Bot token from shared Settings
- **D-17:** Default delivery time: 06:30 WIB (Asia/Jakarta). Configurable via `/settings` command — users can set delivery hour (06:00-09:00 range). Stored in a settings table or config
- **D-18:** On partial pipeline failure: send report for successful assets with a failure notice (e.g., "2 assets failed analysis (TLKM, SOL). Partial report below."). On full pipeline failure: send a short "Pipeline failed" alert

### Claude's Discretion
- Exact webhook route path and PTB Application setup
- Telegram message formatting (MarkdownV2 vs HTML parse mode)
- Emoji mapping for verdict badges (STRONG BUY, BUY, HOLD, SELL, STRONG SELL)
- Watchlist table schema details (can reuse ARCHITECTURE.md's `watchlist` table or adapt)
- Settings storage mechanism (DB table vs config)
- /start welcome message wording
- Error message formatting for invalid commands
- Report stage implementation details (StageFunc signature, message construction)
- How to validate new asset symbols via yfinance/ccxt from the bot process

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Two-Process Design
- `plan/ARCHITECTURE.md` — Full system architecture, two-process model, daily execution flow (Stage 5: REPORT), watchlist table schema, bot directory structure plan
- `plan/ARCHITECTURE.md` §Key Architecture Decisions — Two-process model: bot and pipeline share PostgreSQL, bot is always-on, pipeline runs daily
- `plan/ARCHITECTURE.md` §Daily Execution Flow — Stage 5 (SEND TELEGRAM REPORT) at 06:35, after DECIDE stage

### Existing Bot Infrastructure
- `src/bot/main.py` — Current FastAPI stub with /health endpoint. Phase 5 adds PTB webhook handler here
- `src/config.py` — Settings with `telegram_bot_token`, `telegram_chat_id` already defined

### Decision Data (Phase 4 output)
- `src/db/models.py` — `DailyDecision` model with verdict, score, confidence, reasoning, key_factors, risk_warning, all_signals, model_used columns
- `src/db/models.py` — `Asset` model with symbol, name, asset_type, exchange, yfinance_symbol, ccxt_symbol, is_active
- `src/db/models.py` — `SEED_ASSETS` list (6 default assets)

### Pipeline Integration
- `src/pipeline/runner.py` — PipelineRunner with StageFunc interface, per-asset checkpointing
- `src/pipeline/main.py` — Stage registration (stage_funcs dict), CLI entry point

### Prior Phase Context
- `.planning/phases/04-llm-decision-maker/04-CONTEXT.md` — D-01: English-only prompts/reasoning, D-06: JSON schema for verdict output

### Requirements
- `.planning/REQUIREMENTS.md` — WTCH-01/02/03 (watchlist), TBOT-01/02/03/07 (bot commands), REPT-02/04 (report content)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/bot/main.py` — FastAPI app already running, PTB webhook handler mounts here
- `src/config.py` — `telegram_bot_token` and `telegram_chat_id` already in Settings
- `src/db/models.py` — `DailyDecision` has all fields needed for report formatting (verdict, score, confidence, reasoning, key_factors, risk_warning)
- `src/db/models.py` — `Asset` model with symbol metadata for display
- `src/llm/client.py` — Pattern for external API calls with retry (can inform Telegram send retry logic)
- `src/pipeline/runner.py` — StageFunc pattern for implementing report stage
- `src/data/ingest.py` — Example StageFunc implementation to follow for report stage

### Established Patterns
- StageFunc signature: `async def report_stage(session: AsyncSession, asset: Asset) -> None`
- Per-asset error isolation: failures produce fallback behavior, never crash pipeline
- structlog with component binding for logging
- pydantic-settings for configuration
- Two-process boundary: bot MUST NOT import from `src/pipeline` or `src/llm`
- Alembic for all schema migrations

### Integration Points
- Report stage plugs into PipelineRunner as `stage_funcs["report"]` in `src/pipeline/main.py`
- Reads from `daily_decisions` table (output of decide stage) and `assets` table
- New `watchlist` table (Alembic migration) links assets to the shared watchlist
- Bot webhook route mounts on existing FastAPI `app` in `src/bot/main.py`
- Bot reads from `assets`, `watchlist`, and `daily_decisions` tables via SQLAlchemy

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Follow existing patterns (StageFunc, per-asset processing, structlog logging).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-telegram-bot-daily-delivery*
*Context gathered: 2026-03-24*
