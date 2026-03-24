# Phase 4: LLM Decision Maker - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-24
**Phase:** 04-llm-decision-maker
**Areas discussed:** Prompt design & language, Structured output parsing, Contradiction handling, Fallback verdict logic

---

## Prompt Design & Language

### Language
| Option | Description | Selected |
|--------|-------------|----------|
| English only | All prompts and reasoning in English. Indonesian terms only for specific names. | ✓ |
| Mixed English + Indonesian | Reasoning in English but use Indonesian market terms naturally. | |
| Indonesian primary | Reasoning primarily in Bahasa Indonesia. | |

**User's choice:** English only

### Persona
| Option | Description | Selected |
|--------|-------------|----------|
| Concise analyst | Brief, data-driven. ~100-200 words per asset. Like a Bloomberg terminal note. | ✓ |
| Detailed advisor | Thorough reasoning. ~300-500 words per asset. | |
| You decide | Claude picks the balance. | |

**User's choice:** Concise analyst

### Prompt Depth
| Option | Description | Selected |
|--------|-------------|----------|
| Scores + key indicators | ~500 tokens/asset. Each engine's score, confidence, top 3 indicators. | ✓ |
| Full reasoning from each engine | ~1500 tokens/asset. Full reasoning text + all indicators. | |
| You decide | Claude picks based on token budget. | |

**User's choice:** Scores + key indicators

### LLM Batching
| Option | Description | Selected |
|--------|-------------|----------|
| One asset per call | Focused context, error isolation. Matches per-asset pipeline pattern. | ✓ |
| All assets in one call | Cross-reference possible but one failure kills all verdicts. | |

**User's choice:** One asset per call

---

## Structured Output Parsing

### Output Format
| Option | Description | Selected |
|--------|-------------|----------|
| JSON mode | litellm response_format={'type': 'json_object'}. Reliable, easy to parse. | ✓ |
| Function calling | Tool/function schema. More structured but adds complexity. | |
| Text + regex parsing | Natural text with markers. Simplest prompt but fragile. | |

**User's choice:** JSON mode

### Parse Error Handling
| Option | Description | Selected |
|--------|-------------|----------|
| Retry once, then fallback | One retry with stricter prompt. If still bad, use deterministic fallback. | ✓ |
| Fallback immediately | Treat parse failure same as API failure. | |
| You decide | Claude picks the strategy. | |

**User's choice:** Retry once, then fallback

---

## Contradiction Handling

### Contradiction Handling Style
| Option | Description | Selected |
|--------|-------------|----------|
| Flag in reasoning + lower confidence | LLM notes contradiction AND reduces confidence. | ✓ |
| Flag in reasoning only | Mention but don't mechanically adjust confidence. | |
| Pre-detect + inject | Code detects contradictions before LLM call. | |

**User's choice:** Flag in reasoning + lower confidence

### Contradiction Threshold
| Option | Description | Selected |
|--------|-------------|----------|
| Opposite signs with high confidence | Two engines with opposite signs (>+0.3 vs <-0.3) and both confidence >0.5. | ✓ |
| Any opposite signs | Any opposite directions regardless of magnitude. | |
| You decide | Claude picks the logic. | |

**User's choice:** Opposite signs with high confidence

### Prompt Instruction Style
| Option | Description | Selected |
|--------|-------------|----------|
| Explicit instruction | System prompt says: "Identify contradictions... lower confidence." | ✓ |
| Pre-computed injection | Code detects and injects into user message. | |
| Both | Code pre-detects AND system prompt instructs. | |

**User's choice:** Explicit instruction

### Contradiction Output Shape
| Option | Description | Selected |
|--------|-------------|----------|
| Reasoning text only | Contradictions appear naturally in reasoning paragraph. | ✓ |
| Separate JSON field | Add 'contradictions' array field. | |
| You decide | Claude picks. | |

**User's choice:** Reasoning text only

---

## Fallback Verdict Logic

### Fallback Computation
| Option | Description | Selected |
|--------|-------------|----------|
| Weighted average + thresholds | Confidence-weighted average, mapped to verdict thresholds. | ✓ |
| Simple average + thresholds | Unweighted average, same thresholds. | |
| You decide | Claude picks. | |

**User's choice:** Weighted average + thresholds

### Fallback Reasoning
| Option | Description | Selected |
|--------|-------------|----------|
| Auto-generated summary | Lists weighted score and each engine's contribution. | ✓ |
| Minimal marker only | Just 'LLM_UNAVAILABLE — deterministic fallback used.' | |
| You decide | Claude picks. | |

**User's choice:** Auto-generated summary

### Fallback Confidence
| Option | Description | Selected |
|--------|-------------|----------|
| Computed but capped | From engine agreement, capped at 0.5 max. | ✓ |
| Fixed low value | Always 0.3 for fallback. | |
| You decide | Claude picks. | |

**User's choice:** Computed but capped

### Fallback Data Population
| Option | Description | Selected |
|--------|-------------|----------|
| Yes, auto-generated | Populate key_factors from engine signals + risk_warning about LLM unavailability. | ✓ |
| Nulls for fallback | Leave key_factors and risk_warning as null. | |
| You decide | Claude picks. | |

**User's choice:** Yes, auto-generated

### Event Awareness
| Option | Description | Selected |
|--------|-------------|----------|
| Stub with empty context | Prompt has "Upcoming Events" section, empty until Phase 8. | ✓ |
| Skip entirely | Don't mention events at all. | |
| Basic static calendar | Hardcode known recurring events. | |

**User's choice:** Stub with empty context

---

## Claude's Discretion

- Exact system prompt wording and structure
- JSON schema field names and validation logic
- Engine weight configuration values
- Retry prompt wording for malformed JSON
- Key indicator extraction logic
- DecisionRepository implementation
- Decide stage orchestration
- all_signals JSONB shape

## Deferred Ideas

None — discussion stayed within phase scope
