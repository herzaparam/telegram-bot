# Phase 7: Self-Evaluation Feedback Loop - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 07-self-evaluation-feedback-loop
**Areas discussed:** Lesson extraction, Lesson storage & tiers, Lesson injection, /lessons command

---

## Lesson Extraction

### Stage Design

| Option | Description | Selected |
|--------|-------------|----------|
| Extend evaluate stage | Add LLM analysis to existing evaluate_stage. Simpler — one stage does both | |
| Separate reflect stage | New stage runs after evaluate. Cleaner separation — evaluate stays deterministic | ✓ |
| You decide | Claude picks | |

**User's choice:** Separate reflect stage
**Notes:** Matches ARCHITECTURE.md's SELF-EVALUATE flow design

### Granularity

| Option | Description | Selected |
|--------|-------------|----------|
| Per-asset lessons | LLM analyzes each wrong decision individually. More specific, ~20 calls/day | |
| Batch summary | All wrong decisions at once, 1-3 cross-cutting lessons. Fewer calls | |
| Both: per-asset then batch | Per-asset first, then batch for cross-cutting patterns. ~21 calls/day | ✓ |

**User's choice:** Both: per-asset then batch

### Evaluation Windows

| Option | Description | Selected |
|--------|-------------|----------|
| 24h only | Fastest feedback window only | |
| 24h + 7d | Short-term and medium-term feedback | |
| All windows | Extract lessons at every matured window (24h, 3d, 7d, 30d) | ✓ |
| You decide | Claude picks | |

**User's choice:** All windows

### Analysis Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Mistakes only | Focus LLM budget on what went wrong | |
| Mistakes + surprising wins | Mistakes plus correct decisions where confidence < 0.4 | ✓ |
| All decisions | Analyze every decision regardless | |

**User's choice:** Mistakes + surprising wins

### LLM Output Schema

| Option | Description | Selected |
|--------|-------------|----------|
| Full ARCHITECTURE.md schema | analysis + missed_signals + overweighted + underweighted + lesson + weight_adjustments | ✓ |
| Simplified: lesson + reasoning | Just lesson text and brief analysis | |
| You decide | Claude picks | |

**User's choice:** Full ARCHITECTURE.md schema

### Batch Model

| Option | Description | Selected |
|--------|-------------|----------|
| Same model (GPT-4o-mini) | Consistent quality, negligible extra cost | ✓ |
| Cheaper model for batch | Gemini Flash or DeepSeek for cross-cutting summary | |
| You decide | Claude picks | |

**User's choice:** Same model (GPT-4o-mini)

---

## Lesson Storage & Tiers

### Categories

| Option | Description | Selected |
|--------|-------------|----------|
| Asset-type tiers only | stock, crypto, or all — matching ARCHITECTURE.md | |
| Asset-type + engine tags | Add which engines a lesson relates to | |
| Asset-type + engine + topic | Also tag by topic (momentum, volatility, macro, etc.) | ✓ |

**User's choice:** Asset-type + engine + topic

### Invalidation

| Option | Description | Selected |
|--------|-------------|----------|
| Manual only (still_valid flag) | Lessons stay valid until LLM explicitly invalidates | |
| Time-based expiry | Auto-expire after N days | |
| Performance-based | Track accuracy per lesson, auto-invalidate at threshold | ✓ |
| You decide | Claude picks | |

**User's choice:** Performance-based

### Invalidation Thresholds

| Option | Description | Selected |
|--------|-------------|----------|
| 5 applies, <40% accuracy | Conservative — gives lessons a fair chance | ✓ |
| 3 applies, <35% accuracy | Faster pruning | |
| You decide | Claude picks configurable defaults | |

**User's choice:** 5 applies, <40% accuracy

### Deduplication

| Option | Description | Selected |
|--------|-------------|----------|
| LLM dedup on extraction | Include existing lessons in context, LLM merges or creates new | ✓ |
| Periodic consolidation | Weekly batch job to merge similar lessons | |
| No dedup | Let lessons accumulate, rely on selection | |
| You decide | Claude picks | |

**User's choice:** LLM dedup on extraction

### Dedup Mode

| Option | Description | Selected |
|--------|-------------|----------|
| Merge only | Skip duplicate, bump counter | |
| Merge or strengthen | LLM can update existing lesson text with new evidence | ✓ |
| You decide | Claude picks | |

**User's choice:** Merge or strengthen

### Audit Trail

| Option | Description | Selected |
|--------|-------------|----------|
| Lesson + source_decision_id only | FK to decision, join for context. Normalized | ✓ |
| Lesson + snapshot | JSONB snapshot alongside lesson. Denormalized | |
| You decide | Claude picks | |

**User's choice:** Lesson + source_decision_id only

---

## Lesson Injection

### Quantity

| Option | Description | Selected |
|--------|-------------|----------|
| Top 10 lessons | ~200-300 extra tokens | |
| Top 20 lessons | ~400-600 extra tokens, matches ARCHITECTURE.md | |
| Dynamic (up to 20) | Inject all relevant up to 20, varies by day | ✓ |
| You decide | Claude picks | |

**User's choice:** Dynamic (up to 20)

### Ranking

| Option | Description | Selected |
|--------|-------------|----------|
| Recency + relevance | Recent lessons matching asset type | |
| Accuracy-weighted | Rank by times_applied * accuracy_rate | |
| Multi-factor scoring | Composite of recency, accuracy, asset-type match, engine relevance | ✓ |
| You decide | Claude picks | |

**User's choice:** Multi-factor scoring

### Prompt Style

| Option | Description | Selected |
|--------|-------------|----------|
| Numbered list | Simple list with accuracy stats | |
| Structured sections | Grouped by type with engine tags and stats | ✓ |
| You decide | Claude picks | |

**User's choice:** Structured sections

### Tracking

| Option | Description | Selected |
|--------|-------------|----------|
| Store lesson IDs + texts | Both IDs and text in lessons_applied JSONB | ✓ |
| Store lesson IDs only | Just IDs, join for text | |
| You decide | Claude picks | |

**User's choice:** Store lesson IDs + texts

---

## /lessons Command

### Default View

| Option | Description | Selected |
|--------|-------------|----------|
| Active lessons summary | All valid lessons with accuracy stats | |
| Recently learned + top performers | Split: last 7 days + highest accuracy | ✓ |
| You decide | Claude picks | |

**User's choice:** Recently learned + top performers

### Filters

| Option | Description | Selected |
|--------|-------------|----------|
| /lessons [asset_type] | Filter by stock, crypto, or all | |
| /lessons [asset_type] [engine] | Filter by asset type AND engine tag | ✓ |
| No filters | Just /lessons shows everything | |

**User's choice:** /lessons [asset_type] [engine]

### Daily Report — Lessons Applied

| Option | Description | Selected |
|--------|-------------|----------|
| Single highlight | Most impactful lesson with track record | |
| Full list per asset | Under each asset card, list influencing lessons | ✓ |
| Summary section | Dedicated section listing all unique lessons applied | |
| You decide | Claude picks | |

**User's choice:** Full list per asset

---

## Claude's Discretion

- Reflect stage StageFunc implementation details and error isolation
- LLM prompt wording for analysis and batch passes
- Multi-factor scoring weights for lesson selection
- Lesson topic taxonomy values
- Performance tracking computation method
- Alembic migration details
- /lessons message formatting and splitting
- Dedup prompt design

## Deferred Ideas

None — discussion stayed within phase scope
