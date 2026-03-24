---
phase: 5
slug: telegram-bot-daily-delivery
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-24
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + pytest-asyncio |
| **Config file** | pyproject.toml (pytest section) |
| **Quick run command** | `uv run pytest tests/test_bot/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_bot/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | WTCH-01, WTCH-02, WTCH-03 | unit | `uv run pytest tests/test_bot/test_watchlist.py -x -q` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | TBOT-01 | unit | `uv run pytest tests/test_bot/test_commands.py -x -q` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | TBOT-02, TBOT-03 | unit | `uv run pytest tests/test_bot/test_report_cmd.py -x -q` | ❌ W0 | ⬜ pending |
| 05-02-02 | 02 | 2 | REPT-02, REPT-04 | unit | `uv run pytest tests/test_bot/test_formatter.py -x -q` | ❌ W0 | ⬜ pending |
| 05-02-03 | 02 | 2 | TBOT-07 | unit | `uv run pytest tests/test_bot/test_settings.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_bot/` — directory for bot module tests
- [ ] `tests/test_bot/conftest.py` — shared fixtures (mock Telegram context, test DB session)
- [ ] Test stubs for all requirement areas above

*Existing pytest infrastructure covers framework installation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Webhook receives Telegram updates | TBOT-01 | Requires live Telegram Bot API and HTTPS endpoint | Deploy to VPS, send /start from Telegram, verify bot responds |
| Report message splitting in Telegram | Success Criteria #5 | Telegram rendering can't be fully simulated | Send report with >4096 chars, verify multi-message display |
| Two-process boundary | Success Criteria #4 | Requires runtime process inspection | Run bot + pipeline, query pg_stat_activity |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
