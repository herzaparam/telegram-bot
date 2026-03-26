---
status: partial
phase: 11-asset-discovery-due-diligence
source: [11-VERIFICATION.md]
started: 2026-03-26T00:00:00Z
updated: 2026-03-26T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Live /discover Command
expected: Shows top 5 discovery candidates with trigger emojis, composite score, price and change percentage. Shows "No new opportunities found today" if scan returned empty results. Requires live pipeline execution with real yfinance + CoinGecko data; DB must have DiscoveryCandidate rows.
result: [pending]

### 2. Live /duediligence BBCA Command
expected: Full DD report with sector rank section, management quality with score/label, ownership table with holders, competitive position with rank. Requires live DB with StockFundamental data populated by prior pipeline.
result: [pending]

### 3. Live /compare BBCA BBRI BMRI Command
expected: Side-by-side table in `<pre>` block with P/E, P/B, ROE %, D/E, Rev CAGR % columns; crown emoji on best per row; no Net Margin row present.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
