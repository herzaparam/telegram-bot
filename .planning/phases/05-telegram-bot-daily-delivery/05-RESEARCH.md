# Phase 5: Telegram Bot + Daily Delivery - Research

**Researched:** 2026-03-24
**Domain:** Telegram Bot API, python-telegram-bot webhook integration, report formatting, watchlist management
**Confidence:** HIGH

## Summary

Phase 5 connects the existing pipeline output (DailyDecision records from Phase 4) to end users via Telegram. It has two independent work streams: (1) a webhook-based Telegram bot mounted on the existing FastAPI app for interactive commands (watchlist management, on-demand reports, settings), and (2) a pipeline report stage that formats and sends the daily signal report after the decide stage completes.

The core technical challenge is the two-process boundary: the bot process handles interactive commands and reads from the database, while the pipeline process runs the report stage and sends messages directly via the Telegram Bot API. Both share the bot token from Settings but never import each other's modules.

python-telegram-bot v22.7 (latest stable) provides the webhook handler with `Application.builder().updater(None).build()` for custom server integration. It mounts cleanly on FastAPI via a lifespan context manager. HTML parse mode is recommended over MarkdownV2 to avoid complex character escaping in financial data (numbers, percentages, special symbols).

**Primary recommendation:** Use python-telegram-bot v22.7 with HTML parse_mode, mount via FastAPI lifespan, and implement message splitting at asset-group boundaries for the 4096-char limit.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Webhook mode -- Telegram pushes updates to the bot via HTTPS webhook, not polling
- **D-02:** PTB webhook handler mounted on existing FastAPI app. FastAPI remains the main server; PTB registers a webhook route. Health endpoint stays at `/health`. One uvicorn process serves both
- **D-03:** Access restricted via whitelist -- only configured Telegram user/chat IDs can interact. Unauthorized messages are silently ignored
- **D-04:** Bot process uses `python-telegram-bot` v20+ as specified in ARCHITECTURE.md
- **D-05:** All report text in English. Indonesian terms only for asset names
- **D-06:** Compact card format per asset: emoji verdict badge + asset name + score + confidence + 1-line reasoning summary
- **D-07:** Report starts with market overview header: date, total assets analyzed, sentiment distribution, active risk warnings
- **D-08:** Messages exceeding 4096-char limit split by asset group. Each message self-contained with mini-header. Summary header always first message
- **D-09:** Shared watchlist for the entire group -- one watchlist, any whitelisted user can add/remove. No per-user watchlists. No user table needed
- **D-10:** Command syntax: `/add BBCA`, `/remove BBCA`, `/watchlist`
- **D-11:** Users can add assets not in seed data. Bot validates symbol via yfinance/ccxt, creates new Asset row, adds to watchlist
- **D-12:** New assets with no price history: confirm add and set expectation message
- **D-13:** Watchlist starts empty -- no auto-seeding. `/start` explains how to add assets
- **D-14:** Pipeline runs against all active assets. Watchlist only controls which assets appear in the Telegram report
- **D-15:** Report delivery is a pipeline stage (Stage 5: REPORT). After DECIDE, pipeline formats and sends report. System cron triggers pipeline daily
- **D-16:** Pipeline's report stage sends Telegram messages directly via Telegram Bot API. No bot process involvement in sending reports
- **D-17:** Default delivery time: 06:30 WIB. Configurable via `/settings` (06:00-09:00 range). Stored in settings table or config
- **D-18:** On partial pipeline failure: send report for successful assets with failure notice. On full failure: send "Pipeline failed" alert

### Claude's Discretion
- Exact webhook route path and PTB Application setup
- Telegram message formatting (MarkdownV2 vs HTML parse mode)
- Emoji mapping for verdict badges
- Watchlist table schema details
- Settings storage mechanism (DB table vs config)
- /start welcome message wording
- Error message formatting for invalid commands
- Report stage implementation details
- How to validate new asset symbols via yfinance/ccxt from the bot process

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WTCH-01 | User can add IDX stocks and crypto assets to watchlist via Telegram | PTB CommandHandler for `/add`, yfinance/ccxt validation, Watchlist + Asset table schema |
| WTCH-02 | User can remove assets from watchlist via Telegram | PTB CommandHandler for `/remove`, Watchlist table delete |
| WTCH-03 | User can view current watchlist via `/watchlist` command | PTB CommandHandler, query Watchlist join Asset |
| TBOT-01 | `/start` welcome + setup | PTB CommandHandler, welcome message with usage instructions |
| TBOT-02 | `/report` gets today's full report on demand | Query DailyDecision + Asset + Watchlist, format report, split messages |
| TBOT-03 | `/report BTC` gets detailed single-asset report | Query single DailyDecision, format detailed view with all signals |
| TBOT-07 | `/settings` configures notification time | BotSettings table, time validation (06:00-09:00 WIB range) |
| REPT-02 | Today's signal for each watchlist asset | Report stage reads DailyDecision + Watchlist, formats compact cards |
| REPT-04 | LLM reasoning for each decision | DailyDecision.reasoning field included in report formatting |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-telegram-bot | 22.7 | Telegram Bot API client + webhook handler | Official PTB library; v22 is latest stable; async-native; used by PTB official examples for FastAPI webhook |
| FastAPI | 0.135.1+ | HTTP server (already in project) | Already the bot service framework; PTB webhook mounts as a route |
| SQLAlchemy[asyncio] | 2.0.48+ | ORM for watchlist/settings tables | Already the project ORM; consistent patterns |
| Alembic | 1.18.4+ | Schema migrations for new tables | Already used for all schema changes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | 0.28.1+ | Direct Telegram API calls from pipeline report stage (D-16) | Pipeline report stage sends messages without PTB dependency |
| yfinance | 1.2.0+ | Validate IDX stock symbols when user adds new assets | Bot `/add` command for stock validation |
| ccxt | 4.5.44+ | Validate crypto symbols when user adds new assets | Bot `/add` command for crypto validation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| HTML parse_mode | MarkdownV2 | MarkdownV2 requires escaping 18 special characters; financial data (numbers, %, decimals) would need constant escaping. HTML is simpler and sufficient for bold/italic/code formatting |
| httpx for pipeline report | python-telegram-bot | Pipeline importing PTB would add unnecessary dependency; httpx is already in the project and Telegram sendMessage is a simple POST |
| DB settings table | Config file | DB table allows runtime updates via `/settings` without restart; aligns with shared-state-via-PostgreSQL architecture |

**Installation:**
```bash
uv add "python-telegram-bot>=22.7"
```

**Note:** python-telegram-bot v22.7 depends on httpx (already in project). No additional transitive dependencies needed.

## Architecture Patterns

### Recommended Project Structure
```
src/
├── bot/
│   ├── main.py              # FastAPI app + PTB webhook setup + lifespan
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py          # /start command
│   │   ├── watchlist.py      # /add, /remove, /watchlist commands
│   │   ├── report.py         # /report [ASSET] command
│   │   └── settings.py       # /settings command
│   ├── auth.py               # Whitelist check middleware
│   ├── formatter.py          # Report formatting + message splitting
│   └── __init__.py
├── data/
│   └── report.py             # report_stage() -- pipeline StageFunc
├── db/
│   ├── models.py             # + Watchlist, BotSettings models
│   └── migrations/versions/
│       └── 003_watchlist_bot_settings.py
└── ...
```

### Pattern 1: PTB Webhook on FastAPI via Lifespan
**What:** Mount python-telegram-bot Application on existing FastAPI app using lifespan context manager
**When to use:** Bot process startup
**Example:**
```python
# Source: https://docs.python-telegram-bot.org/en/stable/ + FreeCodeCamp tutorial
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import Application, CommandHandler
from fastapi import FastAPI, Request, Response

ptb_app: Application  # module-level, initialized in lifespan

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ptb_app
    ptb_app = (
        Application.builder()
        .token(settings.telegram_bot_token.get_secret_value())
        .updater(None)  # We handle updates via FastAPI route
        .build()
    )
    # Register handlers
    ptb_app.add_handler(CommandHandler("start", start_handler))
    ptb_app.add_handler(CommandHandler("add", add_handler))
    # ... more handlers

    async with ptb_app:
        await ptb_app.start()
        # Set webhook URL (requires HTTPS in production)
        webhook_url = f"{settings.webhook_base_url}/telegram/webhook"
        await ptb_app.bot.set_webhook(url=webhook_url)
        yield
        await ptb_app.stop()

app = FastAPI(title="Trade Agent Bot", lifespan=lifespan)

@app.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> Response:
    data = await request.json()
    update = Update.de_json(data, ptb_app.bot)
    await ptb_app.process_update(update)
    return Response(status_code=200)

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### Pattern 2: Whitelist Authorization
**What:** Check incoming Telegram user/chat ID against configured whitelist before processing commands
**When to use:** Every incoming update
**Example:**
```python
# In auth.py -- used as a filter or early return in handlers
from telegram import Update
from src.config import settings

def is_authorized(update: Update) -> bool:
    """Check if the message sender is in the whitelist."""
    if not update.effective_chat:
        return False
    chat_id = str(update.effective_chat.id)
    # settings.telegram_chat_id can be comma-separated list
    allowed = {cid.strip() for cid in settings.telegram_chat_id.split(",")}
    return chat_id in allowed
```

### Pattern 3: Pipeline Report Stage (StageFunc)
**What:** Pipeline stage that formats and sends Telegram report after decide stage
**When to use:** Pipeline report stage, runs per-asset but aggregates at end
**Example:**
```python
# In src/data/report.py -- pipeline side, NOT in src/bot/
# Uses httpx directly for Telegram API, never imports PTB
import httpx
from src.config import settings

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

async def send_telegram_message(chat_id: str, text: str, parse_mode: str = "HTML") -> None:
    """Send a message via Telegram Bot API using httpx."""
    url = TELEGRAM_API.format(token=settings.telegram_bot_token.get_secret_value())
    async with httpx.AsyncClient() as client:
        await client.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        })
```

### Pattern 4: Message Splitting by Asset Group
**What:** Split reports exceeding 4096 chars at asset boundaries, each chunk self-contained
**When to use:** Report formatting (both pipeline stage and /report command)
**Example:**
```python
MAX_MESSAGE_LENGTH = 4096

def split_report(header: str, asset_cards: list[str]) -> list[str]:
    """Split report into Telegram-safe message chunks.

    Each chunk starts with a mini-header. First chunk gets full header.
    Splits at asset card boundaries, never mid-card.
    """
    messages: list[str] = []
    current = header + "\n\n"

    for card in asset_cards:
        if len(current) + len(card) + 2 > MAX_MESSAGE_LENGTH:
            messages.append(current.strip())
            current = f"<b>... continued ({len(messages) + 1})</b>\n\n"
        current += card + "\n\n"

    if current.strip():
        messages.append(current.strip())
    return messages
```

### Pattern 5: Asset Validation for /add Command
**What:** Validate user-provided symbol against yfinance (stocks) or ccxt (crypto) before creating Asset
**When to use:** `/add` command handler
**Example:**
```python
# Bot process CAN import yfinance and ccxt (they are data libraries, not pipeline modules)
# Two-process boundary prohibits: src.pipeline, src.llm imports only
import asyncio
import yfinance as yf
import ccxt

async def validate_stock_symbol(symbol: str) -> dict | None:
    """Validate IDX stock symbol via yfinance. Returns metadata or None."""
    yf_symbol = f"{symbol}.JK"
    def _check():
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info
        return info if info.get("regularMarketPrice") else None
    return await asyncio.get_event_loop().run_in_executor(None, _check)

async def validate_crypto_symbol(symbol: str) -> str | None:
    """Validate crypto symbol against Binance via ccxt. Returns ccxt_symbol or None."""
    exchange = ccxt.binance()
    await asyncio.get_event_loop().run_in_executor(None, exchange.load_markets)
    ccxt_symbol = f"{symbol}/USDT"
    return ccxt_symbol if ccxt_symbol in exchange.markets else None
```

### Anti-Patterns to Avoid
- **Importing src.pipeline or src.llm from src.bot/:** Violates two-process boundary. Bot reads database only
- **Using PTB in the pipeline report stage:** Pipeline should use raw httpx for Telegram API calls (D-16). Keeps pipeline lightweight
- **MarkdownV2 for financial data:** Escaping `.`, `-`, `+`, `(`, `)` in numbers/percentages is error-prone. Use HTML parse_mode
- **Single monolithic handler file:** Split handlers by command group (watchlist, report, settings) for maintainability
- **Blocking yfinance calls in async handler:** Always wrap in `run_in_executor` since yfinance is synchronous

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Telegram Bot API client | Raw HTTP Telegram API wrapper | python-telegram-bot v22.7 (bot process) | Handles update deserialization, command parsing, reply helpers, webhook lifecycle |
| Telegram message sending from pipeline | Full PTB Application in pipeline | httpx POST to sendMessage endpoint | Pipeline only needs sendMessage; PTB is overkill and would violate separation |
| Webhook security | Custom HMAC verification | PTB's built-in `secret_token` parameter on `set_webhook` | Telegram sends `X-Telegram-Bot-Api-Secret-Token` header; PTB validates automatically |
| Message text escaping | Custom HTML entity escaper | `html.escape()` from Python stdlib | Standard library handles `<`, `>`, `&` escaping for HTML parse_mode |
| Update routing/dispatching | Custom if/elif command router | PTB's `CommandHandler` + `MessageHandler` + `Application` dispatcher | Handles argument parsing, conversation state, error handlers |

**Key insight:** PTB v22 handles all the Telegram protocol complexity (update types, serialization, rate limiting, retry). The project should only custom-build: report formatting, message splitting, watchlist CRUD, and asset validation.

## Common Pitfalls

### Pitfall 1: MarkdownV2 Escape Hell
**What goes wrong:** Financial report text contains `.`, `-`, `+`, `()`, `%` which are all MarkdownV2 special characters. Missing escapes cause `Bad Request: can't parse entities` errors.
**Why it happens:** MarkdownV2 requires escaping 18 characters: `_*[]()~`>#+-=|{}.!`
**How to avoid:** Use HTML parse_mode. Only `<`, `>`, `&` need escaping via `html.escape()`.
**Warning signs:** `telegram.error.BadRequest` with "can't parse entities" message.

### Pitfall 2: Webhook URL Must Be HTTPS
**What goes wrong:** `set_webhook` silently fails or returns error when given HTTP URL.
**Why it happens:** Telegram requires HTTPS for webhook endpoints. Local development needs a tunnel.
**How to avoid:** In production, use HTTPS behind reverse proxy. For local dev, use ngrok or skip webhook (use polling fallback for dev). Add `webhook_base_url` to Settings with no default (forces explicit configuration).
**Warning signs:** Bot appears online but never receives updates.

### Pitfall 3: PTB Application Lifecycle Mismanagement
**What goes wrong:** Bot stops receiving updates after some time, or handlers don't fire.
**Why it happens:** `Application.start()` and `Application.stop()` not properly called in FastAPI lifespan. Using `updater(None)` but forgetting `async with ptb:` context.
**How to avoid:** Follow the exact lifespan pattern: `async with ptb: await ptb.start(); yield; await ptb.stop()`. Never skip the context manager.
**Warning signs:** Handlers registered but no response to commands.

### Pitfall 4: Message Length Overflow
**What goes wrong:** `sendMessage` returns 400 error when text exceeds 4096 characters.
**Why it happens:** Reports with many assets easily exceed limit. A single-asset card with reasoning can be 200-400 chars; 10+ assets plus header overflows.
**How to avoid:** Always run report text through `split_report()` before sending. Test with worst-case asset counts.
**Warning signs:** Reports work in dev with 2 assets but fail in production with full watchlist.

### Pitfall 5: Synchronous yfinance Blocking the Event Loop
**What goes wrong:** Bot becomes unresponsive during `/add` symbol validation because yfinance blocks.
**Why it happens:** yfinance is synchronous; calling it directly in an async handler blocks the entire event loop.
**How to avoid:** Always use `asyncio.get_event_loop().run_in_executor(None, sync_func)` for yfinance calls.
**Warning signs:** Bot freezes for 2-5 seconds when a user runs `/add`.

### Pitfall 6: Two-Process Boundary Violation
**What goes wrong:** Bot imports `src.pipeline` or `src.llm`, pulling in heavy dependencies (pandas, pmdarima, litellm) and violating memory constraints.
**Why it happens:** Convenient to reuse pipeline code, but bot process has 192MB memory limit.
**How to avoid:** Bot MUST only import from: `src.config`, `src.logging`, `src.db`, `src.bot`. Success criterion #4 specifically tests this via `pg_stat_activity`.
**Warning signs:** Bot memory usage spikes above 192MB; import errors in bot-only deployments.

### Pitfall 7: Race Condition Between Pipeline Report and Bot /report
**What goes wrong:** Pipeline report stage and bot `/report` command format reports differently, or pipeline sends while bot is also sending.
**Why it happens:** Two independent processes accessing same data and sending to same chat.
**How to avoid:** Share the formatting logic: put `formatter.py` in `src/bot/` (bot process owns formatting). Pipeline report stage can use a simpler version or import formatting utilities that don't pull bot dependencies. Actually -- per two-process boundary, report formatting should be duplicated or placed in a shared utility module under `src/` (not under `src/bot/` or `src/pipeline/`).
**Warning signs:** Different formatting between daily report and on-demand `/report`.

## Code Examples

### Watchlist Table Schema
```python
# Source: CONTEXT.md D-09, D-14; ARCHITECTURE.md watchlist table design
class Watchlist(Base):
    """Shared watchlist linking assets to the report filter."""
    __tablename__ = "watchlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("assets.id"), unique=True, nullable=False
    )
    added_by_chat_id: Mapped[str | None] = mapped_column(String(30), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
```

### BotSettings Table Schema
```python
# Source: CONTEXT.md D-17; stores per-group settings
class BotSettings(Base):
    """Bot configuration stored in DB for runtime updates."""
    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(String(200), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

### Report Card Formatting (HTML)
```python
# Source: CONTEXT.md D-06, D-07
import html

VERDICT_EMOJI = {
    "STRONG BUY": "🟢🟢",
    "BUY": "🟢",
    "HOLD": "🟡",
    "SELL": "🔴",
    "STRONG SELL": "🔴🔴",
}

def format_asset_card(asset_symbol: str, asset_name: str, verdict: str,
                      score: float, confidence: float, reasoning: str) -> str:
    emoji = VERDICT_EMOJI.get(verdict, "⚪")
    # Truncate reasoning to ~100 chars for compact view
    short_reason = reasoning[:100].rsplit(" ", 1)[0] + "..." if len(reasoning) > 100 else reasoning
    return (
        f"{emoji} <b>{html.escape(asset_symbol)}</b> "
        f"({html.escape(asset_name)})\n"
        f"   {verdict} | Score: {score:+.2f} | Conf: {confidence:.0%}\n"
        f"   <i>{html.escape(short_reason)}</i>"
    )

def format_report_header(run_date: str, total: int,
                         distribution: dict[str, int],
                         risk_warnings: list[str]) -> str:
    dist_str = " | ".join(f"{v}: {c}" for v, c in distribution.items() if c > 0)
    header = (
        f"<b>Daily Signal Report - {run_date}</b>\n"
        f"Assets: {total} | {dist_str}"
    )
    if risk_warnings:
        header += "\n⚠️ " + " | ".join(risk_warnings)
    return header
```

### Pipeline Report Stage
```python
# Source: CONTEXT.md D-15, D-16, D-18; follows StageFunc pattern
async def report_stage(session: AsyncSession, asset: Asset) -> None:
    """Report stage -- special: aggregates all assets then sends once.

    Unlike other stages, report_stage is called per-asset by PipelineRunner
    but should only send the full report after processing the LAST asset.
    Alternative: implement as a post-stage hook or standalone function.
    """
    # NOTE: The per-asset StageFunc pattern doesn't naturally fit a
    # "send one aggregated report" use case. Two approaches:
    #
    # Option A: report_stage is a no-op per asset; a separate
    #   send_report() runs after PipelineRunner completes all stages
    #
    # Option B: report_stage accumulates results and sends on last asset
    #
    # Recommendation: Option A -- add a post-pipeline hook in pipeline/main.py
    pass
```

### Webhook Secret Token Security
```python
# PTB supports secret_token for webhook verification
# Set during webhook registration:
await ptb_app.bot.set_webhook(
    url=webhook_url,
    secret_token=settings.telegram_webhook_secret,  # add to Settings
)

# PTB's built-in handling verifies X-Telegram-Bot-Api-Secret-Token header
# But since we handle the route ourselves, verify manually:
@app.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> Response:
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if secret != settings.telegram_webhook_secret:
        return Response(status_code=403)
    # ... process update
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PTB polling (`run_polling()`) | PTB webhook with custom ASGI server | PTB v20 (2023) | Webhook is push-based, lower latency, works behind reverse proxy |
| PTB v13 synchronous handlers | PTB v20+ fully async handlers | PTB v20 (2023) | All handlers are `async def`, native asyncio integration |
| PTB built-in webhook server | `updater(None)` + custom server | PTB v20+ | Allows mounting on existing FastAPI/Starlette app |
| Markdown parse_mode | HTML or MarkdownV2 | Bot API 2020 | Original Markdown deprecated; HTML recommended for simplicity |

## Open Questions

1. **Report Stage as StageFunc vs Post-Pipeline Hook**
   - What we know: StageFunc runs per-asset. Report should aggregate all assets into one message.
   - What's unclear: Whether to shoehorn report into StageFunc pattern or add a post-pipeline hook.
   - Recommendation: Implement report as a standalone async function called after `PipelineRunner.run_pipeline()` returns, NOT as a StageFunc. This avoids the per-asset pattern mismatch. The pipeline_runs table can still track a "report" stage for observability by creating the record manually.

2. **Webhook URL for Local Development**
   - What we know: Telegram requires HTTPS. Production uses reverse proxy.
   - What's unclear: How developers test webhook locally.
   - Recommendation: Add a `--polling` flag to bot startup for local dev that uses `run_polling()` instead of webhook. Or document ngrok setup.

3. **Shared Formatting Between Bot and Pipeline**
   - What we know: Both `/report` command (bot) and report stage (pipeline) format the same report.
   - What's unclear: Where to put shared formatting code given two-process boundary.
   - Recommendation: Place formatting utilities in `src/bot/formatter.py`. Pipeline report stage can duplicate the formatting logic or use a minimal shared module under `src/` root. Since pipeline report stage uses httpx (not PTB), it only needs the text formatting functions, not PTB-specific code.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| python-telegram-bot | Bot webhook + commands | Not installed | -- | Must install via `uv add` |
| FastAPI | Bot HTTP server | Installed | 0.135.1+ | -- |
| httpx | Pipeline report stage Telegram API calls | Installed | 0.28.1+ | -- |
| yfinance | Symbol validation for /add (stocks) | Installed | 1.2.0+ | -- |
| ccxt | Symbol validation for /add (crypto) | Installed | 4.5.44+ | -- |
| TimescaleDB | Watchlist/settings tables | Running (Docker) | 2.18.0-pg16 | -- |
| Alembic | Schema migrations | Installed | 1.18.4+ | -- |

**Missing dependencies with no fallback:**
- python-telegram-bot: Must be installed. First task in plan.

**Missing dependencies with fallback:**
- None

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2+ with pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_bot/ -x` |
| Full suite command | `pytest` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WTCH-01 | /add creates asset + watchlist entry | unit | `pytest tests/test_bot/test_watchlist.py::TestAddCommand -x` | Wave 0 |
| WTCH-02 | /remove deletes watchlist entry | unit | `pytest tests/test_bot/test_watchlist.py::TestRemoveCommand -x` | Wave 0 |
| WTCH-03 | /watchlist shows current list | unit | `pytest tests/test_bot/test_watchlist.py::TestWatchlistCommand -x` | Wave 0 |
| TBOT-01 | /start sends welcome message | unit | `pytest tests/test_bot/test_start.py -x` | Wave 0 |
| TBOT-02 | /report returns full report | unit | `pytest tests/test_bot/test_report.py::TestFullReport -x` | Wave 0 |
| TBOT-03 | /report BTC returns single-asset detail | unit | `pytest tests/test_bot/test_report.py::TestSingleAssetReport -x` | Wave 0 |
| TBOT-07 | /settings updates delivery time | unit | `pytest tests/test_bot/test_settings.py -x` | Wave 0 |
| REPT-02 | Report includes all watchlist assets | unit | `pytest tests/test_bot/test_formatter.py::TestReportFormatting -x` | Wave 0 |
| REPT-04 | Report includes LLM reasoning | unit | `pytest tests/test_bot/test_formatter.py::TestReasoningIncluded -x` | Wave 0 |
| D-08 | Messages split at 4096 chars | unit | `pytest tests/test_bot/test_formatter.py::TestMessageSplitting -x` | Wave 0 |
| D-03 | Unauthorized users silently ignored | unit | `pytest tests/test_bot/test_auth.py -x` | Wave 0 |
| D-11 | Symbol validation for new assets | unit | `pytest tests/test_bot/test_watchlist.py::TestSymbolValidation -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_bot/ -x`
- **Per wave merge:** `pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_bot/` directory -- does not exist yet
- [ ] `tests/test_bot/__init__.py`
- [ ] `tests/test_bot/conftest.py` -- shared fixtures (mock PTB bot, mock sessions, sample assets/decisions)
- [ ] `tests/test_bot/test_formatter.py` -- report formatting + message splitting
- [ ] `tests/test_bot/test_auth.py` -- whitelist authorization
- [ ] `tests/test_bot/test_watchlist.py` -- /add, /remove, /watchlist handlers
- [ ] `tests/test_bot/test_report.py` -- /report handler
- [ ] `tests/test_bot/test_start.py` -- /start handler
- [ ] `tests/test_bot/test_settings.py` -- /settings handler
- [ ] `tests/test_data/test_report_stage.py` -- pipeline report stage
- [ ] Schema model tests for Watchlist and BotSettings in `tests/test_db/test_models.py`

## Sources

### Primary (HIGH confidence)
- python-telegram-bot v22.7 official docs -- webhook setup, Application.builder(), CommandHandler
- Telegram Bot API official docs (core.telegram.org/bots/api) -- message limits, parse modes, sendMessage
- FreeCodeCamp PTB v20 webhook tutorial -- FastAPI + PTB lifespan integration pattern
- Existing codebase: `src/bot/main.py`, `src/config.py`, `src/db/models.py`, `src/pipeline/runner.py`

### Secondary (MEDIUM confidence)
- PyPI python-telegram-bot 22.7 -- version confirmed via registry
- PTB official examples (customwebhookbot.py) -- Starlette pattern adapted for FastAPI

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - PTB v22.7 confirmed on PyPI, FastAPI/SQLAlchemy already in project
- Architecture: HIGH - Two-process model well-documented in project, PTB webhook pattern verified from official examples
- Pitfalls: HIGH - MarkdownV2 escaping, webhook HTTPS requirement, and message length limit are well-documented issues
- Report stage pattern: MEDIUM - StageFunc per-asset pattern doesn't naturally fit aggregated report; post-pipeline hook recommended but needs validation

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable libraries, slow-moving domain)
