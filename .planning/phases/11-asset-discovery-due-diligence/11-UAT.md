---
status: complete
phase: 11-asset-discovery-due-diligence
source: [11-01-SUMMARY.md, 11-02-SUMMARY.md, 11-03-SUMMARY.md, 11-04-SUMMARY.md, 11-05-SUMMARY.md, 11-06-SUMMARY.md]
started: 2026-03-27T00:00:00Z
updated: 2026-03-27T00:03:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running server/service. Clear ephemeral state. Start the application from scratch. Server boots without errors, migrations complete, and the bot responds to a basic command.
result: pass

### 2. /discover Command
expected: Sending /discover in Telegram shows top 5 discovery candidates. Each card shows trigger emojis, composite score, price and change percentage. If no scan results exist, shows "No new opportunities found today."
result: pass

### 3. /duediligence (or /dd) Command
expected: Sending /dd BBCA (or /duediligence BBCA) shows a full DD report with: sector benchmark (P/E, P/B, ROE vs sector median), management quality (score + label like Excellent/Good/Fair/Weak), ownership table with holders, competitive position with rank. If no data exists for the symbol, shows an appropriate error message.
result: pass

### 4. /compare Command
expected: Sending /compare BBCA BBRI BMRI shows a side-by-side table in formatted text with columns: P/E, P/B, ROE %, D/E, Rev CAGR %. Crown emoji on the best value per row. No Net Margin row present (removed in gap closure).
result: pass

### 5. /compare Validation
expected: /compare with fewer than 2 symbols shows an error message. /compare with more than 5 symbols shows an error message. Both reject gracefully with user-friendly text.
result: pass

### 6. Crypto Rejection on IDX-Only Commands
expected: Running /dd BTC or /compare BTC ETH shows a message that crypto assets are not supported for these commands.
result: pass

### 7. Auth Check on /discover
expected: An unauthenticated user (not in watchlist) sending /discover is rejected with an auth-required message.
result: pass

### 8. Discovery Scan in Pipeline
expected: After running the full pipeline (batch operations), discovery scan executes automatically. New DiscoveryCandidate rows appear in the database.
result: pass

### 9. DD Computation in Pipeline
expected: During pipeline ingest, DD reports are computed per stock. DueDiligenceReport rows appear in the database for ingested stocks.
result: pass

### 10. Daily Report Includes New Opportunities
expected: The daily Telegram report includes a "New Opportunities" section showing discovery candidates with trigger info and scores.
result: pass

### 11. LLM Prompt Includes DD Flags
expected: The LLM decision prompt includes a "DUE DILIGENCE FLAGS" section with severity-tagged messages (e.g., [WARNING], [CRITICAL]) when DD flags exist for an asset.
result: pass

### 12. DD Report Formatting in Telegram
expected: DD report in Telegram uses HTML formatting with proper sections, bold labels, and readable layout. Ownership data shows holders in a table format.
result: pass

## Summary

total: 12
passed: 12
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
