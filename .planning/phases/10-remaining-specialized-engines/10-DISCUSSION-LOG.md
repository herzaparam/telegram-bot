# Phase 10: Remaining Specialized Engines - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-25
**Phase:** 10-remaining-specialized-engines
**Areas discussed:** ML/AI engine scope, On-chain data sources, Engine depth vs stub strategy, Data fetcher wiring

---

## ML/AI Engine Scope

### Feature Engineering
| Option | Description | Selected |
|--------|-------------|----------|
| Price-derived only | OHLCV features: returns, volatility, RSI, MACD, volume ratios, lagged values | |
| Price + engine scores | OHLCV plus historical engine scores as inputs | |
| Price + fundamentals + macro | OHLCV plus fundamental ratios and macro indicators | |

**User's choice:** Price-derived only
**Notes:** Self-contained, fits daily cadence

### Training Strategy
| Option | Description | Selected |
|--------|-------------|----------|
| Offline train, ONNX deploy | Train offline, export ONNX, deploy as static models | |
| Auto-retrain weekly | Automated weekly retraining pipeline | |
| Ensemble with fallback | XGBoost primary, LSTM secondary on low confidence | |

**User's choice:** Offline train, ONNX deploy
**Notes:** Matches PROJECT.md ONNX decision

### Models Per Asset Class
| Option | Description | Selected |
|--------|-------------|----------|
| One model per class | One XGBoost + one LSTM for stocks, one of each for crypto. 4 total | |
| One model per asset | Per-ticker models | |
| Shared model, asset features | Single model with asset-type features | |

**User's choice:** One model per class

### Training Scripts
| Option | Description | Selected |
|--------|-------------|----------|
| Inference + training scripts | Include CLI training scripts that generate ONNX | |
| Inference only + dummy models | Inference code only with placeholder models | |
| Inference + auto-bootstrap | Auto-train on first run | |

**User's choice:** Inference + training scripts

### Prediction Target
| Option | Description | Selected |
|--------|-------------|----------|
| Direction + magnitude | Predict next-day return direction and magnitude | |
| Direction only | Binary up/down classification | |
| Multi-horizon | 1-day, 3-day, 7-day returns | |

**User's choice:** Direction + magnitude

### XGBoost + LSTM Combination
| Option | Description | Selected |
|--------|-------------|----------|
| Weighted average | 60% XGBoost, 40% LSTM, confidence = min of both | |
| Best confidence wins | Use whichever model has higher confidence | |
| XGBoost primary, LSTM tiebreaker | LSTM only when XGBoost confidence below threshold | |

**User's choice:** Weighted average

---

## On-Chain Data Sources

### Primary API
| Option | Description | Selected |
|--------|-------------|----------|
| DeFiLlama + free APIs | DeFiLlama for TVL, CoinGecko for exchange flow | |
| Glassnode free tier | Limited free tier, BTC only | |
| Etherscan + chain-specific | Direct blockchain queries per chain | |

**User's choice:** DeFiLlama + free APIs

### Whale Tracking
| Option | Description | Selected |
|--------|-------------|----------|
| Exchange flow proxy | Net exchange inflows/outflows as whale proxy | |
| Top wallet monitoring | Track known whale wallets | |
| Volume anomaly detection | Unusual volume spikes | |

**User's choice:** Exchange flow proxy

### NVT Overlap
| Option | Description | Selected |
|--------|-------------|----------|
| On-chain adds depth, no NVT overlap | Leave NVT to ValuationEngine | |
| On-chain owns all on-chain metrics | Move NVT from ValuationEngine | |
| Both keep NVT independently | Redundant NVT in both | |

**User's choice:** On-chain adds depth, no NVT overlap

### Crypto Asset Coverage
| Option | Description | Selected |
|--------|-------------|----------|
| BTC + ETH + SOL | Cover 3 most common watchlist cryptos | |
| All watchlist crypto | Dynamic per-asset lookups | |
| BTC only initially | Start minimal | |

**User's choice:** BTC + ETH + SOL

### TVL Scoring
| Option | Description | Selected |
|--------|-------------|----------|
| TVL trend + ratio | 7-day/30-day trends, market cap / TVL ratio | |
| TVL vs competitors | Compare against ecosystem peers | |
| TVL absolute only | Track changes without ratios | |

**User's choice:** TVL trend + ratio

### Fetch Frequency
| Option | Description | Selected |
|--------|-------------|----------|
| Daily with pipeline | Once during daily pipeline run | |
| Every 6 hours | More frequent updates | |
| Weekly cache | Save API calls | |

**User's choice:** Daily with pipeline

---

## Engine Depth vs Stub Strategy

### Stub Policy
| Option | Description | Selected |
|--------|-------------|----------|
| Lightweight stubs | Real engines where data exists, stubs for options + game theory | |
| All full engines | Proxy data for thin engines | |
| Skip thin engines | Only build engines with real data | |

**User's choice:** Lightweight stubs

### Behavioral Engine
| Option | Description | Selected |
|--------|-------------|----------|
| Volume + price anomalies | Volume spikes, price gaps, volume/price divergence | |
| Volume anomalies only | Just unusual trading volume | |
| Full herding detection | Cross-asset correlation + sector momentum | |

**User's choice:** Volume + price anomalies

### Network Engine
| Option | Description | Selected |
|--------|-------------|----------|
| Rolling correlation matrix | 30-day pairwise correlations, regime change signals | |
| Sector clustering | Group by correlation clusters | |
| Lead-lag detection | Cross-correlation lead/lag analysis | |

**User's choice:** Rolling correlation matrix

### Emerging Methods
| Option | Description | Selected |
|--------|-------------|----------|
| Fractal + wavelet | Hurst exponent + wavelet decomposition | |
| Fractal only | Just Hurst exponent | |
| Full quantitative suite | Fractal + wavelet + entropy + HMM | |

**User's choice:** Fractal + wavelet

### Alternative Data (ENGN-10)
| Option | Description | Selected |
|--------|-------------|----------|
| GitHub activity only | Commit frequency, contributors, stars for crypto projects | |
| GitHub + social metrics | GitHub + Twitter/Telegram | |
| Minimal stub | Stub for stocks, GitHub for crypto | |

**User's choice:** GitHub activity only

### Stub Detail Level
| Option | Description | Selected |
|--------|-------------|----------|
| Documented stubs | score=0/confidence=0 with reasoning + TODO comments | |
| Proxy stubs | Use available data as rough proxies | |
| Abstract-only stubs | Class skeleton returning zeros | |

**User's choice:** Documented stubs

---

## Data Fetcher Wiring

### Fetch Architecture
| Option | Description | Selected |
|--------|-------------|----------|
| Extend ingest stage | Add fetchers as sub-steps in existing ingest_stage | |
| New fetch stage | Separate specialized_fetch stage | |
| Engine-internal fetch | Each engine fetches its own data | |

**User's choice:** Extend ingest stage

### New Tables
| Option | Description | Selected |
|--------|-------------|----------|
| 2-3 tables | on_chain_data, github_activity, ml_predictions | |
| One per engine | 8 new tables | |
| Single generic table | One engine_data table with JSON | |

**User's choice:** 2-3 tables

### Memory Budget
| Option | Description | Selected |
|--------|-------------|----------|
| Lazy load + measure | Load ONNX only during analyze(), memory test asserting <1GB | |
| Engine pool | Instantiate only needed engines per asset | |
| Profile and optimize later | Build all, profile after | |

**User's choice:** Lazy load + measure

### API Keys
| Option | Description | Selected |
|--------|-------------|----------|
| Same pattern as Phase 8 | Optional in Settings, graceful degradation | |
| All required at startup | Fail fast if missing | |
| Runtime key check per engine | Each engine checks own key | |

**User's choice:** Same pattern as Phase 8

### Scorecard for Stubs
| Option | Description | Selected |
|--------|-------------|----------|
| Track all, note stubs | All 15 in /scorecard, stubs show "N/A" | |
| Only track active engines | Exclude stubs | |
| Track stubs as 0% accuracy | Misleading zero accuracy | |

**User's choice:** Track all, note stubs

### Migration Organization
| Option | Description | Selected |
|--------|-------------|----------|
| One migration per table | Separate migrations for each new table | |
| Single migration for all | One migration file | |
| Per-engine migrations | 8 migration files | |

**User's choice:** One migration per table

---

## Claude's Discretion

- XGBoost feature engineering specifics
- LSTM architecture details
- Training script CLI interface
- DeFiLlama/CoinGecko endpoint selection
- GitHub repo-to-crypto mapping
- All scoring weights and thresholds
- Library choices for wavelet/fractal analysis
- Table schemas and indexes
- Engine wiring implementation in analyze.py

## Deferred Ideas

None — discussion stayed within phase scope
