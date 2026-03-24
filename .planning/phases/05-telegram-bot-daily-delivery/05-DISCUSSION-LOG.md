# Phase 5: Telegram Bot + Daily Delivery - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 05-telegram-bot-daily-delivery
**Areas discussed:** Telegram integration approach, Report format & structure, Watchlist management, Delivery scheduling

---

## Telegram Integration Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Polling | Simpler setup, no public URL needed, works behind NAT. ~1-2s latency | |
| Webhook via FastAPI | Telegram pushes updates to FastAPI endpoint. Lower latency, requires HTTPS | ✓ |
| You decide | Claude picks based on VPS setup | |

**User's choice:** Webhook via FastAPI
**Notes:** User initially selected polling, then corrected to webhook mode.

| Option | Description | Selected |
|--------|-------------|----------|
| PTB webhook handler mounted on FastAPI | FastAPI stays main server, PTB webhook as a route. One process | ✓ |
| PTB runs its own webserver | Separate from FastAPI, would need two servers | |
| You decide | Claude picks | |

**User's choice:** PTB webhook handler mounted on FastAPI

| Option | Description | Selected |
|--------|-------------|----------|
| python-telegram-bot v20+ | Full-featured async lib, matches ARCHITECTURE.md | ✓ |
| aiogram v3 | Alternative async framework, less adoption | |
| You decide | Claude picks | |

**User's choice:** python-telegram-bot v20+

| Option | Description | Selected |
|--------|-------------|----------|
| Whitelist by chat ID | Only configured IDs can interact | ✓ |
| Open to anyone | No access control | |
| You decide | Claude decides | |

**User's choice:** Whitelist by chat ID

---

## Report Format & Structure

| Option | Description | Selected |
|--------|-------------|----------|
| English | Matches Phase 4 D-01, all reasoning already in English | ✓ |
| Bahasa Indonesia | Report text in Indonesian | |
| Mixed | Headers Indonesian, content English | |

**User's choice:** English

| Option | Description | Selected |
|--------|-------------|----------|
| Compact card per asset | Emoji verdict + name + score + 1-line reasoning. Dense format | ✓ |
| Detailed block per asset | Full multi-line with all factors and reasoning paragraph | |
| Table format | Monospace table, reasoning separate | |

**User's choice:** Compact card per asset

| Option | Description | Selected |
|--------|-------------|----------|
| Market overview header | Date, total assets, sentiment distribution, risk warnings | ✓ |
| No summary | Jump straight to asset cards | |
| You decide | Claude picks | |

**User's choice:** Market overview header

| Option | Description | Selected |
|--------|-------------|----------|
| Split by asset group | Group assets into sub-4096 messages, each self-contained | ✓ |
| Split at natural boundaries | Split at section breaks (summary, stocks, crypto) | |
| You decide | Claude picks | |

**User's choice:** Split by asset group

---

## Watchlist Management

| Option | Description | Selected |
|--------|-------------|----------|
| Shared watchlist | One watchlist for the group, any whitelisted user can modify | ✓ |
| Per-user watchlists | Each user has own watchlist, personalized reports | |
| You decide | Claude picks | |

**User's choice:** Shared watchlist

| Option | Description | Selected |
|--------|-------------|----------|
| /add BBCA or /add BTC | Simple top-level commands with symbol | ✓ |
| /watchlist add BBCA | Subcommand style, all ops under /watchlist | |
| You decide | Claude picks | |

**User's choice:** /add BBCA or /add BTC

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — seed assets as default | All 6 seed assets auto-added | |
| No — empty watchlist | User builds from scratch, /start explains how | ✓ |
| You decide | Claude picks | |

**User's choice:** No — empty watchlist, user builds it

| Option | Description | Selected |
|--------|-------------|----------|
| Pipeline runs all active assets, report filters to watchlist | Decouples analysis from delivery | ✓ |
| Pipeline only runs watchlist assets | Saves compute but adds coupling | |
| You decide | Claude picks | |

**User's choice:** Pipeline runs all, report filters to watchlist

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — create new asset on-the-fly | Bot validates symbol, creates asset row, adds to watchlist | ✓ |
| No — only existing assets | Users limited to pre-configured assets | |
| You decide | Claude picks | |

**User's choice:** Yes — create new asset on-the-fly

| Option | Description | Selected |
|--------|-------------|----------|
| Confirm add + note 'data available next run' | Sets expectation, respects two-process model | ✓ |
| Trigger immediate backfill | Async backfill on add, crosses process boundary | |
| You decide | Claude picks | |

**User's choice:** Confirm add + note next run

---

## Delivery Scheduling

| Option | Description | Selected |
|--------|-------------|----------|
| Pipeline report stage sends via Telegram | Report is Stage 5 of pipeline, cron-triggered | ✓ |
| Bot-side scheduler sends report | Bot has own scheduler querying DB | |
| You decide | Claude picks | |

**User's choice:** Pipeline report stage

| Option | Description | Selected |
|--------|-------------|----------|
| Direct Telegram API call from pipeline | Pipeline uses PTB/httpx to send directly | ✓ |
| Pipeline writes to DB, bot polls and sends | Cleaner boundary but adds latency | |
| You decide | Claude picks | |

**User's choice:** Direct API call from pipeline

| Option | Description | Selected |
|--------|-------------|----------|
| 06:30 WIB | Matches ARCHITECTURE.md flow | |
| 08:00 WIB | Closer to market open | |
| Configurable via /settings | User sets delivery time | ✓ |

**User's choice:** Configurable via /settings

| Option | Description | Selected |
|--------|-------------|----------|
| Default 06:30 WIB, /settings sets hour only | Minimal scope, 06:00-09:00 range | ✓ |
| Full /settings with multiple options | Delivery time + preferences + verbosity | |

**User's choice:** Default 06:30 WIB, /settings sets delivery hour only

| Option | Description | Selected |
|--------|-------------|----------|
| Send partial report + failure notice | Report for successful assets + failure note | ✓ |
| Only send on full success | Error alert only on failure | |
| You decide | Claude picks | |

**User's choice:** Send partial report + failure notice

---

## Claude's Discretion

- Webhook route path and PTB Application setup details
- Telegram message formatting (MarkdownV2 vs HTML)
- Emoji verdict badge mapping
- Watchlist table schema
- Settings storage mechanism
- /start welcome message wording
- Report stage StageFunc implementation
- Symbol validation from bot process

## Deferred Ideas

None — discussion stayed within phase scope
