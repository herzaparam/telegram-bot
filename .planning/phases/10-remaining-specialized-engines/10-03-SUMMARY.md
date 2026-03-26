---
phase: 10-remaining-specialized-engines
plan: 03
subsystem: engines
tags: [defillama, github-api, httpx, tenacity, onchain, tvl, alternative-data]

requires:
  - phase: 10-01
    provides: "OnChainData and GitHubActivity DB models, github_token config"
provides:
  - "DeFiLlama TVL fetcher for BTC/ETH/SOL chains"
  - "GitHub activity fetcher for crypto project repos"
  - "OnChainEngine scoring crypto from TVL trends"
  - "AlternativeDataEngine scoring crypto from GitHub dev activity"
affects: [10-05-integration, pipeline-wiring]

tech-stack:
  added: []
  patterns: [constructor-injection-for-external-data, graceful-degradation-empty-dict, httpx-with-tenacity-retry, pg-insert-upsert]

key-files:
  created:
    - src/data/onchain_fetcher.py
    - src/data/github_fetcher.py
    - src/engines/onchain.py
    - src/engines/alternative.py
    - tests/test_data/test_onchain_fetcher.py
    - tests/test_data/test_github_fetcher.py
    - tests/test_engines/test_onchain.py
    - tests/test_engines/test_alternative.py
  modified: []

key-decisions:
  - "TVL-only scoring first; exchange flow data optional (CoinGecko Pro may be needed)"
  - "AlternativeDataEngine confidence fixed at 0.25 (supplementary signal, not primary)"
  - "Rate limit: 0.5s sleep between DeFiLlama chain requests, X-RateLimit-Remaining monitoring for GitHub"

patterns-established:
  - "External API fetcher pattern: httpx.AsyncClient + tenacity retry + pg_insert UPSERT + graceful degradation"
  - "Crypto-only engine: supports_stocks=False, supports_crypto=True, returns zero for non-crypto"

requirements-completed: [ENGN-06, ENGN-10]

duration: 4min
completed: 2026-03-26
---

# Phase 10 Plan 03: On-Chain and Alternative Data Engines Summary

**DeFiLlama TVL fetcher and GitHub activity fetcher with OnChainEngine and AlternativeDataEngine scoring crypto assets from external data sources**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-26T02:36:43Z
- **Completed:** 2026-03-26T02:40:50Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- DeFiLlama fetcher retrieves TVL history for BTC/ETH/SOL with tenacity retry and rate limiting
- OnChainEngine scores crypto from 7d/30d TVL trends with optional exchange flow data
- GitHub fetcher retrieves repo stats with token auth support and rate limit monitoring
- AlternativeDataEngine scores crypto from dev activity metrics (commits, stars, issues)
- All engines gracefully degrade to score=0/confidence=0 when data unavailable

## Task Commits

Each task was committed atomically:

1. **Task 1: On-chain data fetcher and OnChainEngine** - `0d40776` (feat)
2. **Task 2: GitHub activity fetcher and AlternativeDataEngine** - `e053bfe` (feat)

_TDD: Both tasks followed RED-GREEN cycle (tests written before implementation)_

## Files Created/Modified
- `src/data/onchain_fetcher.py` - DeFiLlama TVL fetcher with CHAIN_MAP and UPSERT storage
- `src/data/github_fetcher.py` - GitHub API repo stats fetcher with CRYPTO_REPOS mapping
- `src/engines/onchain.py` - OnChainEngine: TVL trend + exchange flow scoring
- `src/engines/alternative.py` - AlternativeDataEngine: GitHub dev activity scoring
- `tests/test_data/test_onchain_fetcher.py` - 6 tests for on-chain fetcher
- `tests/test_data/test_github_fetcher.py` - 5 tests for GitHub fetcher
- `tests/test_engines/test_onchain.py` - 12 tests for OnChainEngine
- `tests/test_engines/test_alternative.py` - 10 tests for AlternativeDataEngine

## Decisions Made
- TVL-only scoring implemented first; exchange flow is optional and works when present in data dict
- AlternativeDataEngine confidence fixed at 0.25 (supplementary, not primary signal)
- DeFiLlama rate limit: 0.5s sleep between chain requests
- GitHub rate limit: X-RateLimit-Remaining header monitored, warning logged when < 10

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. GitHub token is optional (60 req/hr without, 5000 with).

## Next Phase Readiness
- OnChainEngine and AlternativeDataEngine ready for integration into analyze_stage
- Fetchers ready for wiring into ingest_stage for crypto assets
- Constructor injection pattern consistent with MacroEngine for pipeline wiring

---
*Phase: 10-remaining-specialized-engines*
*Completed: 2026-03-26*
