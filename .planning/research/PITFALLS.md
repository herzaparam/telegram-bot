# Pitfalls Research

**Domain:** Daily trading signal agent (IDX stocks + global crypto) with LLM decisions, 15 engines, self-evaluation loop
**Researched:** 2026-03-23
**Confidence:** HIGH (well-documented domain with many public post-mortems)

## Critical Pitfalls

### Pitfall 1: yfinance Is Unreliable as a Primary Data Source

**What goes wrong:**
yfinance scrapes Yahoo Finance without authentication. Yahoo changes backend endpoints without notice, breaking yfinance entirely. In February 2025, a Yahoo API change caused yfinance to return zero results for most tickers with misleading "possibly delisted" errors. In September 2025, data downloads stopped completely for a period. On a 2GB VPS running daily at 06:00, a broken yfinance means zero IDX stock data and a completely failed pipeline run.

**Why it happens:**
yfinance is the only free option for IDX (.JK suffix) stock data. Developers treat it as reliable because it works most of the time, then discover it breaks silently -- returning empty DataFrames or stale data without raising errors.

**How to avoid:**
- Validate every yfinance response: check row count, date freshness (latest date must be within 1-2 trading days), and that OHLCV values are non-null and non-zero.
- Cache aggressively in TimescaleDB -- only fetch the delta (new days since last stored date), never re-fetch full history.
- Build a data freshness monitor: if no new price data arrives for 2 trading days, alert via Telegram.
- Pin yfinance version in requirements.txt and test upgrades manually before deploying.
- Design the pipeline so stale data (from DB cache) still produces a signal with a "DATA STALE" warning rather than crashing.

**Warning signs:**
- Empty DataFrames returned without exceptions
- yfinance GitHub issues page suddenly active with "no data" reports
- Pipeline runs complete in <1 minute (fetches returned nothing)
- Last stored price date is >2 trading days old

**Phase to address:**
Phase 1 (Foundation) -- data fetching must include validation and staleness detection from day one.

---

### Pitfall 2: OOM Kills on 2GB VPS -- Death by a Thousand DataFrames

**What goes wrong:**
The pipeline loads price history, computes 130+ technical indicators via pandas-ta, runs ML inference (ONNX), and calls LLM APIs -- all within 1GB peak RAM budget alongside PostgreSQL+TimescaleDB which itself needs 300-500MB. A single leaked DataFrame reference, an unexpectedly large asset history, or TimescaleDB running an auto-compression job during the pipeline window triggers the Linux OOM killer, silently terminating the pipeline or (worse) PostgreSQL.

**Why it happens:**
Python's garbage collector does not reliably reclaim DataFrame memory due to reference counting edge cases, circular references through pandas accessors, and memory fragmentation. `gc.collect()` alone is insufficient -- the C allocator (glibc malloc) may hold onto freed pages. On a 2GB VPS, the margin between "works" and "OOM" is dangerously thin.

**How to avoid:**
- Set PostgreSQL `shared_buffers` to 256MB, `work_mem` to 4MB, `max_connections` to 20. Use `timescaledb-tune` with explicit memory cap.
- After processing each asset, explicitly `del df` every DataFrame, then call `gc.collect()` followed by `ctypes.CDLL("libc.so.6").malloc_trim(0)` to return memory to the OS.
- Set resource limits: `resource.setrlimit(resource.RLIMIT_AS, (1200 * 1024 * 1024, ...))` on the pipeline process to fail fast rather than OOM-killing PostgreSQL.
- Load only the price data you need (e.g., last 200 candles for technical indicators, not full history).
- Monitor RSS memory via `/proc/self/status` between assets and log it. Alert if >900MB.
- Disable TimescaleDB background workers during pipeline execution window, or schedule compression jobs at a different time.

**Warning signs:**
- Pipeline process killed without error logs (OOM killer leaves traces in `dmesg`)
- PostgreSQL restarts unexpectedly
- Pipeline works for 10 assets but fails at 15+
- Gradual memory increase visible in logs between asset iterations

**Phase to address:**
Phase 1 (Foundation) -- memory budget and PostgreSQL tuning. Phase 2+ must enforce per-asset cleanup discipline in every engine implementation.

---

### Pitfall 3: LLM Self-Evaluation Feedback Loop Creates Recency Bias and Overfitting

**What goes wrong:**
The self-evaluation system (F4) reviews yesterday's decisions and extracts "lessons" that feed future decisions. After a few weeks, the system accumulates contradictory lessons ("downweight technicals before macro events" vs. "trust RSI divergence signals") and develops severe recency bias -- overweighting whatever worked in the last 5-10 decisions. The LLM starts flip-flopping strategies, and its "lessons" become noise rather than signal. A study of 888 algorithmic strategies found backtested Sharpe ratios have an R-squared of less than 0.025 with real-world performance.

**Why it happens:**
Short evaluation windows produce statistically meaningless conclusions. A single correct STRONG BUY followed by a 5% gain generates a "lesson" with n=1 evidence. The LLM treats this as wisdom. Meanwhile, valid long-term patterns get drowned out by recent noise. LLMs are also prone to narrative fallacy -- constructing convincing-sounding explanations for random market movements.

**How to avoid:**
- Require minimum sample sizes before a lesson becomes active: at least 10 decisions in the same category before extracting a pattern.
- Separate lessons into tiers: "hypothesis" (n<10), "pattern" (10-30 observations), "rule" (30+ observations with statistical significance).
- Cap active lessons at 15-20 maximum. Oldest/weakest lessons expire.
- Track lesson performance: if a lesson's application doesn't improve accuracy after 30 days, demote it.
- Include a "null lesson" baseline -- track accuracy with and without lesson application.
- Never let the LLM modify engine weights directly. Lessons influence prompt context only.

**Warning signs:**
- Lesson count growing unboundedly (>30 active lessons)
- Contradictory lessons appearing ("trust X" and "don't trust X")
- Accuracy declining after lesson system goes live vs. baseline period
- LLM reasoning text references 5+ lessons per decision (information overload)

**Phase to address:**
Phase 9 (Self-Evaluation) -- but the lesson storage schema must be designed with expiration and confidence tiers from the start.

---

### Pitfall 4: LLM Structured Output Failures Crash the Pipeline

**What goes wrong:**
The LLM final decision maker (F3) must output structured data: verdict (enum), score (-1 to +1), confidence (0 to 1), reasoning (string). GPT-4o-mini's structured output compliance is imperfect -- it sometimes returns values outside enum options, omits required fields, or returns malformed JSON. LiteLLM has had its own bugs where structured output schemas were not properly forwarded to the provider. When the pipeline parses the response and hits a validation error, the entire pipeline stops.

**Why it happens:**
Developers test LLM outputs manually during development (works 99% of the time) and skip defensive parsing. In production, with 20 assets x 365 days, even a 1% failure rate means 70+ failures per year. LLM providers also degrade silently during high-traffic periods.

**How to avoid:**
- Wrap every LLM call in a retry loop (3 attempts) with exponential backoff.
- Validate LLM output with Pydantic models, but use `model.model_validate()` with try/except, not blind trust.
- On validation failure after retries, fall back to a deterministic weighted-average verdict (mean of engine scores) with a "LLM_UNAVAILABLE" flag.
- Log every raw LLM response before parsing for debugging.
- Set hard timeouts on LLM calls (30 seconds). LiteLLM supports this via `timeout` parameter.
- Test structured output compliance in CI with 50+ varied inputs, not just the happy path.

**Warning signs:**
- Pydantic validation errors in pipeline logs
- LLM latency spikes (>10 seconds indicates provider degradation)
- Verdict distribution becomes uniform (LLM returning random/default values)
- LiteLLM version upgrade breaks structured output (check changelogs before upgrading)

**Phase to address:**
Phase 1 (Foundation) -- establish the LLM call wrapper with retries and fallback. Phase 4 (LLM Decision Maker) implements the full decision logic.

---

### Pitfall 5: Look-Ahead Bias in Evaluation and Backtesting

**What goes wrong:**
The self-evaluation system fetches "current prices" at 06:00 to compare against yesterday's decision. But "yesterday's decision" was made at 06:00 yesterday using data from market close the day before that. If evaluation uses the wrong price point (e.g., today's price instead of yesterday's close), or if engines inadvertently use data that wasn't available at decision time (future data leaking via yfinance returning partial current-day data), all accuracy metrics become inflated and meaningless.

**Why it happens:**
Time zones make this confusing. IDX trades 09:00-16:00 WIB (UTC+7). Crypto trades 24/7. A decision made at 06:00 WIB on Monday uses IDX data from Friday's close and crypto data from 06:00 WIB Monday. Evaluating that decision requires comparing against different time windows for different asset types. Developers typically use "latest price" without thinking about which timestamp matters.

**How to avoid:**
- Store the exact timestamp and prices used when each decision was made (snapshot in `decisions` table).
- Define evaluation windows explicitly: for IDX, compare decision price vs. next trading day's close. For crypto, compare vs. price 24 hours after decision.
- Never use `yfinance` with `period="1d"` for evaluation -- always specify exact date ranges.
- Include a `decision_price` and `evaluation_price` field in the schema, with timestamps.
- Build an "evaluation lag" -- evaluate decisions only after 2 trading days to ensure all price data has settled (corporate actions, adjustments).

**Warning signs:**
- Reported accuracy >70% consistently (suspiciously high for any signal system)
- Accuracy metrics swing wildly between weekdays and weekends (time-zone bug)
- IDX and crypto accuracy are identical (unlikely if evaluation windows are correct)

**Phase to address:**
Phase 1 (Foundation) -- decision schema must include price snapshots. Phase 9 (Self-Evaluation) must implement correct evaluation windows.

---

### Pitfall 6: 15 Engines Producing Noise, Not Signal

**What goes wrong:**
With 15 analysis engines, many will produce low-quality or redundant signals. The "Emerging" engine (fractal dimension, wavelet analysis) and "Game Theory" engine (order book imbalance) sound sophisticated but require deep domain expertise to implement correctly. Poorly implemented engines don't just add noise -- they actively degrade the LLM's decision quality because the LLM treats all engine scores as equally meaningful input. The system becomes worse than using 3 well-implemented engines.

**Why it happens:**
The plan builds all 15 engines sequentially over weeks 2-8 without validation between phases. There's no mechanism to measure whether adding engine N+1 actually improved decision quality. Developers keep adding engines because it feels like progress, but each mediocre engine dilutes the signal from good ones.

**How to avoid:**
- Track per-engine accuracy independently from day one: which engines predicted direction correctly?
- After Phase 2 (Technical Engine), establish a baseline accuracy. Each subsequent engine must demonstrably improve accuracy on a held-out validation period or it stays disabled.
- Give the LLM explicit engine quality metadata: "Engine X has 62% directional accuracy over 30 days; Engine Y has 45%."
- Allow the LLM to set engine weights, but track whether its weighting improves outcomes vs. equal weighting.
- Start with Technical, Fundamental, and Macro (the three with the most reliable data sources). Add others only after proving the core loop works.

**Warning signs:**
- All 15 engines agree (herding -- means they're measuring the same thing)
- Adding a new engine doesn't change the LLM's verdict distribution
- Engine scores cluster near 0 (engines returning default/neutral values because implementation is incomplete)
- "Emerging" or "Game Theory" engines return constant values for weeks

**Phase to address:**
Phase 2 (First Engine) -- establish engine accuracy tracking. Every subsequent engine phase must include a validation checkpoint.

---

### Pitfall 7: Pipeline Failure Without Recovery Means Missed Morning Reports

**What goes wrong:**
The daily pipeline runs at 06:00 and must deliver reports before traders start their day (~08:00 WIB for IDX pre-market analysis). If any stage fails -- a data source is down, an engine throws an exception, the LLM API has an outage -- the entire report is missed. Users lose trust after 2-3 missed reports. The plan mentions "decoupled pipeline stages" and "idempotent restartable" stages, but this is hard to implement correctly.

**Why it happens:**
External dependencies (yfinance, Binance API, OpenAI API, RSS feeds) have independent uptime guarantees. The probability that ALL dependencies are available simultaneously at 06:00 is lower than any individual one. With 10+ external APIs, even 99.5% uptime per API means ~5% chance of at least one failure per day.

**How to avoid:**
- Implement per-stage checkpointing in the `pipeline_runs` table. Record: stage name, asset being processed, status (pending/running/success/failed), error message.
- On failure, send a partial report with whatever data succeeded, plus a clear "INCOMPLETE" flag listing what's missing.
- Add an automatic retry mechanism: if stage 2 (data fetch) fails for one source, skip it and continue. Mark affected engines as "DATA_UNAVAILABLE" rather than crashing.
- Schedule a retry run at 07:00 if the 06:00 run didn't complete fully.
- Each engine must have a graceful degradation path: if its data source is unavailable, return `score=0, confidence=0, reasoning="Data unavailable"` rather than raising an exception.
- Use a process supervisor (systemd or Docker restart policy) to ensure the pipeline process itself is restarted if it crashes.

**Warning signs:**
- Users asking "where's today's report?" in Telegram
- Pipeline log shows all-or-nothing outcomes (either full success or full failure, never partial)
- No entries in `pipeline_runs` table for failed runs (means failures aren't even being tracked)

**Phase to address:**
Phase 1 (Foundation) -- pipeline orchestrator with checkpointing must be built before any engines are added.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcoded engine weights instead of tracked/adaptive | Faster to ship | Can't identify which engines help vs. hurt | MVP only; replace in Phase 9 |
| Single `try/except Exception` around entire pipeline | Quick error handling | Hides root causes, makes debugging impossible | Never -- catch specific exceptions per stage |
| Storing LLM prompts as f-strings in engine code | Quick iteration | Prompt changes require code deploys, no A/B testing | Phase 1-3 only; move to DB-stored templates |
| Using `pd.read_sql()` instead of asyncpg for price data | Simpler code | 10-50x slower on large queries, blocks event loop | Phase 1-2 only; migrate hot paths to asyncpg |
| Skipping TimescaleDB compression setup | Less config complexity | Table size grows ~10x faster, fills VPS disk in months | Never -- enable compression in Phase 1 |
| Not pinning dependency versions | Latest features | yfinance, LiteLLM, or pandas-ta update breaks production | Never -- always pin with `pip freeze` |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| yfinance (.JK suffix) | Assuming `BBCA.JK` always returns data; not handling Yahoo rate limits | Validate response shape, implement exponential backoff, cache in TimescaleDB, check for empty/stale data |
| ccxt (Binance) | Using default timeout; not handling exchange maintenance windows | Set explicit timeouts (10s), catch `ExchangeNotAvailable` and `RequestTimeout`, use CoinGecko as fallback for price data |
| OpenAI via LiteLLM | Not handling rate limits (RPM/TPM); ignoring `context_length_exceeded` errors | Implement token counting before sending, truncate engine reasoning if needed, handle 429 with backoff |
| Telegram Bot API | Sending messages >4096 chars; not escaping MarkdownV2 special characters | Split long reports into multiple messages, use `html` parse mode (more forgiving than MarkdownV2), test with edge cases |
| FRED API | Fetching macro data during US holidays (returns stale data without error) | Check observation dates, not just response status; cache macro data (changes monthly, not daily) |
| RSS Feeds (Kontan, CNBC ID) | Parsing Indonesian text with wrong encoding; assuming feed is always available | Explicit UTF-8 handling, timeout on feed fetch, fallback to cached articles if feed is down |
| CoinGecko | Exceeding 10k calls/month free tier; mixing up "demo" vs "pro" API key behavior | Track call count, use only for metadata (not prices), implement monthly counter reset |
| TimescaleDB hypertables | Creating hypertable on existing table with data; wrong chunk interval | Create hypertable on empty table, set chunk_time_interval to 7 days for daily data (not default 1 week for high-frequency) |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading full price history into pandas for each engine run | RAM usage grows linearly with asset history length | Query only last N rows needed (200 for TA, 60 for momentum) | >1 year of history per asset with 20+ assets |
| PostgreSQL sequential scans on `price_history` | Pipeline stage 3 takes >10 minutes | Create indexes on (asset_id, timestamp DESC), use TimescaleDB `time_bucket` | >100k rows in price_history |
| LLM prompt growing as lesson count increases | Token costs increase, responses slow down, context window exceeded | Cap lessons in prompt to top 10 by relevance, summarize older lessons | >20 active lessons (prompt >3000 tokens) |
| Synchronous engine execution with no timeout | Single engine hang (e.g., waiting for HTTP response) blocks entire pipeline | Per-engine timeout (60 seconds), skip engine on timeout | Any external data fetch inside engine code |
| Docker container logging to stdout without rotation | Disk fills up with months of log output | Configure Docker log driver with max-size and max-file | After 2-3 months of daily runs |
| Not compressing TimescaleDB chunks | Disk usage grows ~10x what it should be | Enable compression policy on chunks older than 7 days | After 6 months of data for 20+ assets |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing API keys (OpenAI, Binance, Telegram) in code or docker-compose.yml | Keys leaked if repo is ever made public or VPS is compromised | Use `.env` file with pydantic-settings, never commit `.env`, use Docker secrets for production |
| Telegram bot token exposed in logs | Anyone can impersonate or hijack the bot | Sanitize all log output, never log full request/response bodies containing tokens |
| No authentication on FastAPI health endpoint | Information leakage about system state, potential attack vector | Bind FastAPI to localhost only (127.0.0.1), use Telegram webhook secret for verification |
| Running pipeline as root in Docker | Container escape = full VPS access | Use non-root user in Dockerfile, drop capabilities |
| Storing Binance API keys with trade permissions | If VPS is compromised, attacker can drain exchange account | Use read-only API keys (the system only generates signals, never trades) |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Sending all 15 engine scores in the Telegram report | Information overload; users can't find the verdict | Lead with verdict and confidence, then top 3 supporting/contradicting engines, full detail on `/report BBCA` command |
| No distinction between "HOLD because neutral" and "HOLD because engines disagree" | Users can't assess signal quality | Include a "consensus" metric: how much do engines agree? High disagreement = uncertain, not neutral |
| Report arrives at inconsistent times | Users stop checking because they can't rely on delivery time | Show pipeline progress status on `/status` command; send "processing..." message at 06:00, then actual report when ready |
| Accuracy stats without context | "55% accuracy" sounds bad but might beat random; no benchmark comparison | Show accuracy vs. buy-and-hold baseline, vs. random, and vs. a simple moving average strategy |
| Lessons shown as raw LLM text | Hard to parse, variable quality | Template lessons into structured format: "When [condition], [action] has worked [X]% of the time over [N] decisions" |

## "Looks Done But Isn't" Checklist

- [ ] **Data fetching:** Often missing validation that returned data is fresh and complete -- verify that the latest row date is within expected range, not just that the HTTP call succeeded
- [ ] **Engine scores:** Often missing normalization -- verify that all engines actually return scores in [-1, +1] range, not raw indicator values
- [ ] **LLM decision:** Often missing fallback -- verify the system produces a verdict even when the LLM API is down (deterministic weighted average)
- [ ] **Self-evaluation:** Often missing correct time alignment -- verify that evaluation compares decision-time price vs. correct future price, not "latest" price
- [ ] **Telegram report:** Often missing message splitting -- verify reports still render when an asset has unusually long reasoning text (>4096 chars)
- [ ] **Pipeline recovery:** Often missing partial completion handling -- verify that if the pipeline crashes on asset 12/20, the next run picks up from asset 12 (not restart from 1)
- [ ] **TimescaleDB compression:** Often missing compression policy -- verify that `SELECT * FROM timescaledb_information.jobs` shows active compression jobs
- [ ] **Memory cleanup:** Often missing `malloc_trim` after `gc.collect()` -- verify with `psutil.Process().memory_info().rss` that memory actually drops between assets
- [ ] **Docker restart policy:** Often missing `restart: unless-stopped` -- verify bot process survives VPS reboot

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| yfinance breaks globally | LOW | Switch to cached data + "DATA STALE" flag; monitor yfinance GitHub for fix; consider supplementing with IDX direct data scraping |
| OOM kill during pipeline | MEDIUM | Check `dmesg` for OOM logs; reduce asset count temporarily; tune PostgreSQL memory down; add memory monitoring |
| LLM feedback loop overfitting | MEDIUM | Freeze lesson application for 2 weeks; compare accuracy with/without lessons; prune lessons to statistically significant ones only |
| LLM structured output breaks after provider update | LOW | Fallback to deterministic verdict; pin LiteLLM version; test with new models in staging before switching |
| Pipeline misses morning report | LOW | Manual trigger via `/report` command; investigate failure cause in `pipeline_runs` table; schedule automatic retry |
| Engine producing garbage scores | MEDIUM | Disable engine via config flag (not code change); revert to last known good engine version; investigate data source |
| Disk full from uncompressed TimescaleDB | HIGH | Emergency: delete old uncompressed chunks; enable compression retroactively (CPU-intensive); monitor disk usage with alerts |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| yfinance unreliability | Phase 1 (Foundation) | Data freshness check returns meaningful errors; pipeline succeeds with stale cached data |
| OOM on 2GB VPS | Phase 1 (Foundation) | Pipeline processes 20 assets with peak RSS <900MB; PostgreSQL stays alive throughout |
| Feedback loop overfitting | Phase 9 (Self-Evaluation) | Lesson count capped; accuracy tracked with/without lessons; lesson confidence tiers enforced |
| LLM structured output failures | Phase 1 (Foundation) | Pipeline completes even when LLM returns garbage; 3 retries + deterministic fallback tested |
| Look-ahead bias | Phase 1 (Foundation) + Phase 9 | Decision table stores price snapshots; evaluation uses correct time windows per asset type |
| Engine noise vs. signal | Phase 2+ (Every engine phase) | Per-engine accuracy tracked; new engines must improve composite accuracy on validation set |
| Pipeline failure = missed reports | Phase 1 (Foundation) | Pipeline sends partial report on failure; retry mechanism tested; `/status` command shows pipeline state |

## Sources

- [yfinance keeps getting blocked](https://medium.com/@trading.dude/why-yfinance-keeps-getting-blocked-and-what-to-use-instead-92d84bb2cc01)
- [yfinance GitHub Issues](https://github.com/ranaroussi/yfinance/issues) -- recurring breakage pattern documented
- [yfinance data download broke Sep 2025](https://github.com/ranaroussi/yfinance/discussions/2606)
- [TimescaleDB tuning tool](https://github.com/timescale/timescaledb-tune) -- memory recommendations for constrained systems
- [PostgreSQL performance tuning parameters](https://www.timescale.com/learn/postgresql-performance-tuning-key-parameters)
- [Pandas DataFrame memory leak analysis](https://shekharsingh.com/blog/2019/03/26/analyzing-pandas-memory-leak-issue-with-fix.html)
- [Pandas memory leak with DataFrame subset deletion](https://github.com/pandas-dev/pandas/issues/49582)
- [LiteLLM structured output bug](https://github.com/BerriAI/litellm/issues/7616)
- [GPT-4o-mini structured outputs unreliable](https://community.openai.com/t/structured-outputs-not-reliable-with-gpt-4o-mini-and-gpt-4o/918735)
- [Trading bot overfitting and what backtests don't tell you](https://petrvojacek.cz/en/blog/trading-bot-risks-and-tools/)
- [Self-improving trading bot -- what went wrong](https://dev.to/up2itnow0822/our-trading-bot-rewrites-its-own-rules-heres-how-and-what-went-wrong-5dg9)
- [888 algorithmic strategies study on backtest reliability](https://www.fxreplay.com/learn/backtesting-biases-how-traders-fool-themselves-without-knowing-it)
- [TradeTrap: Are LLM-based Trading Agents Truly Reliable?](https://arxiv.org/html/2512.02261v1)
- [LLM Agent in Financial Trading survey](https://arxiv.org/abs/2408.06361)
- [APScheduler missed jobs issue](https://github.com/agronholm/apscheduler/issues/146)
- [Crypto trading bot pitfalls 2025](https://www.gate.com/news/detail/13225882)

---
*Pitfalls research for: Daily trading signal agent (IDX + crypto)*
*Researched: 2026-03-23*
