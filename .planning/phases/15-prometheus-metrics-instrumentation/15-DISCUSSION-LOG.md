# Phase 15: Prometheus Metrics Instrumentation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-29
**Phase:** 15-prometheus-metrics-instrumentation
**Areas discussed:** Fetch metric placement, Engine timing approach, Data freshness calc, Bot request counting

---

## Fetch Metric Placement

| Option | Description | Selected |
|--------|-------------|----------|
| Centralized in ingest stage (Recommended) | Instrument src/data/ingest.py — one place catches all fetchers. Labels: source=yfinance\|ccxt\|coingecko, asset_type=stock\|crypto. | ✓ |
| Inside each fetcher | Add .inc() calls inside yfinance, ccxt, and coingecko fetch functions directly. More granular but spread across multiple files. | |
| You decide | Claude picks the best approach based on codebase patterns. | |

**User's choice:** Centralized in ingest stage
**Notes:** None

---

## Engine Timing Approach

| Option | Description | Selected |
|--------|-------------|----------|
| In analyze_stage loop (Recommended) | Wrap each engine.analyze() call in analyze_stage with a timer. One instrumentation point for all 15 engines. | ✓ |
| Inside each engine class | Each engine's analyze() method self-reports its duration. Requires touching 15+ files. | |
| You decide | Claude picks based on codebase patterns. | |

**User's choice:** In analyze_stage loop
**Notes:** None

---

## Data Freshness Calculation

| Option | Description | Selected |
|--------|-------------|----------|
| Hours since newest DB row (Recommended) | Query MAX(timestamp) from price_history after ingest, compute hours elapsed. Reflects actual data age. | ✓ |
| Hours since ingest completed | Set gauge to 0 after ingest, let it drift with wall clock. Simpler but doesn't reflect actual data age. | |
| You decide | Claude picks most useful for alerting. | |

**User's choice:** Hours since newest DB row
**Notes:** None

---

## Bot Request Counting

| Option | Description | Selected |
|--------|-------------|----------|
| FastAPI middleware (Recommended) | Starlette middleware incrementing BOT_REQUEST_COUNT on every request with method/endpoint/status labels. | ✓ |
| Manual per-handler | Add .inc() in each command handler and route. More control but easy to miss new handlers. | |
| You decide | Claude picks cleanest approach. | |

**User's choice:** FastAPI middleware
**Notes:** None

---

## Claude's Discretion

- Exact middleware pattern (BaseHTTPMiddleware vs raw ASGI)
- Timer implementation for ENGINE_DURATION
- DATA_FRESHNESS_HOURS DB session handling
- Test structure and mocking approach

## Deferred Ideas

None — discussion stayed within phase scope
