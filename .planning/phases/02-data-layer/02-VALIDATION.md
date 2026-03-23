---
phase: 2
slug: data-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-23
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest >=9.0.2 + pytest-asyncio >=1.3.0 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` (asyncio_mode="auto") |
| **Quick run command** | `uv run pytest tests/test_data/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_data/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | DATA-01 | integration | `uv run pytest tests/test_data/test_price_repo.py -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | DATA-01 | integration | `uv run pytest tests/test_data/test_migration.py -x` | ❌ W0 | ⬜ pending |
| 02-02-01 | 02 | 1 | DATA-02 | unit | `uv run pytest tests/test_data/test_idx_fetcher.py -x` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 1 | DATA-02 | unit | `uv run pytest tests/test_data/test_validation.py -x` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02 | 1 | DATA-02 | unit | `uv run pytest tests/test_data/test_staleness.py -x` | ❌ W0 | ⬜ pending |
| 02-03-01 | 03 | 1 | DATA-03 | unit | `uv run pytest tests/test_data/test_crypto_fetcher.py -x` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 1 | DATA-03 | unit | `uv run pytest tests/test_data/test_crypto_fetcher.py::test_coingecko_fallback -x` | ❌ W0 | ⬜ pending |
| 02-04-01 | 04 | 2 | ALL | unit | `uv run pytest tests/test_data/test_price_repo.py::test_upsert_idempotent -x` | ❌ W0 | ⬜ pending |
| 02-04-02 | 04 | 2 | ALL | integration | `uv run pytest tests/test_data/test_ingest.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_data/__init__.py` — package init
- [ ] `tests/test_data/conftest.py` — shared fixtures (mock yfinance data, mock ccxt responses)
- [ ] `tests/test_data/test_validation.py` — OHLCV validation rules (DATA-01, DATA-02)
- [ ] `tests/test_data/test_idx_fetcher.py` — yfinance fetch with mocked responses (DATA-02)
- [ ] `tests/test_data/test_crypto_fetcher.py` — ccxt + CoinGecko fallback (DATA-03)
- [ ] `tests/test_data/test_staleness.py` — staleness detection logic
- [ ] `tests/test_data/test_price_repo.py` — upsert idempotency, asyncpg raw SQL
- [ ] `tests/test_data/test_ingest.py` — ingest stage integration
- [ ] `tests/test_data/test_migration.py` — hypertable + compression DDL

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| TimescaleDB compression reduces storage | DATA-01 | Requires real TimescaleDB with data aged >30 days | Run backfill, wait for compression policy, check `hypertable_compression_stats` |
| yfinance IDX `.JK` returns valid data | DATA-02 | Unofficial API, real network call | `python -c "import yfinance; print(yfinance.download('BBCA.JK', period='5d'))"` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
