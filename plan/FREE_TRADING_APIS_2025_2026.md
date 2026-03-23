# Free APIs for Building a Trading Signal System (2025-2026)

Compiled: March 2026. All information verified via web search.

---

## 1. STOCK MARKET DATA (Price, Volume, Historical)

### yfinance (Unofficial Yahoo Finance)
- **URL:** https://github.com/ranaroussi/yfinance
- **Free tier:** Completely free, no API key needed
- **Data:** Real-time & historical OHLCV, dividends, splits, financials, options chains, institutional holders
- **Python:** `pip install yfinance` — returns pandas DataFrames natively
- **Limits:** No official rate limit, but Yahoo aggressively rate-limits scrapers. Expect 429 errors with >2000 requests/hour. IP bans are common on cloud servers.
- **Gotchas:**
  - NOT an official API — scrapes Yahoo Finance endpoints. Yahoo frequently changes its backend, causing breakage (major outage Feb 2025 when Yahoo changed API endpoints).
  - Unreliable for production systems. Great for prototyping and research.
  - Data can have gaps/errors for less liquid tickers.
  - Version 1.2.0 (Feb 2026) is current; always keep updated.

### Alpha Vantage
- **URL:** https://www.alphavantage.co/
- **Free tier:** **25 requests/day**, no credit card required
- **Data:** US & global stocks (200k+ tickers, 20+ exchanges), forex, crypto, 50+ technical indicators, fundamental data, economic indicators, commodities
- **Python:** `pip install alpha_vantage`
- **Limits:** 25 requests/day on free tier is extremely restrictive. Premium starts at $49.99/mo for 75 req/min.
- **Gotchas:**
  - 25/day is barely usable even for development. Was previously 500/day — significantly reduced.
  - 20+ years of historical daily data available.
  - Adjusted and unadjusted prices available.

### Twelve Data
- **URL:** https://twelvedata.com/
- **Free tier:** **800 requests/day**, 8 requests/minute
- **Data:** Real-time & historical OHLCV for stocks, forex, crypto, ETFs, indices. 100+ technical indicators. Coverage across global exchanges.
- **Python:** `pip install twelvedata`
- **Limits:** 800/day is generous for development. WebSocket streaming available on free tier (1 symbol).
- **Gotchas:**
  - Free tier limited to 5,000 API credits/month for some endpoints.
  - 99.95% uptime advertised — generally reliable.
  - Best free-tier stock API for active development work.

### Financial Modeling Prep (FMP)
- **URL:** https://financialmodelingprep.com/
- **Free tier:** **250 requests/day**
- **Data:** Stock prices, financial statements, ratios, DCF, earnings, SEC filings, ETFs, mutual funds, commodities, forex, crypto
- **Python:** `pip install fmpsdk` or direct REST calls
- **Limits:** 250/day with reduced data depth on free tier. Only covers major US exchanges on free tier.
- **Gotchas:**
  - Good breadth of fundamental data on free tier.
  - Historical data may be limited to 5 years on free plan.
  - One of the best "all-in-one" free APIs for fundamentals + prices.

### Polygon.io
- **URL:** https://polygon.io/
- **Free tier:** **5 API calls/minute**, end-of-day and 2 years historical data
- **Data:** US stocks, options, forex, crypto. Aggregates, trades, quotes, reference data.
- **Python:** `pip install polygon-api-client`
- **Limits:** Free tier is very restrictive — only EOD data, 5 calls/min. No real-time. Paid starts at $199/mo.
- **Gotchas:**
  - Excellent data quality and coverage on paid tiers.
  - Free tier only useful for EOD batch processing or very light historical analysis.
  - Good reference/ticker data even on free tier.

### Finnhub
- **URL:** https://finnhub.io/
- **Free tier:** **60 calls/minute** (very generous)
- **Data:** Real-time US stock quotes, company profiles, financials, earnings, IPO calendar, SEC filings, ESG scores, congressional trading, news, sentiment, forex, crypto
- **Python:** `pip install finnhub-python`
- **Limits:** 60/min is excellent. WebSocket for real-time data (50 symbols free). 30 calls/sec burst limit.
- **Gotchas:**
  - One of the most generous free tiers available.
  - Covers stocks + crypto + forex + fundamentals + news + sentiment in one API.
  - Some advanced endpoints (insider transactions, lobbying) are premium-only.
  - Real-time WebSocket limited to 50 concurrent symbols.

---

## 2. CRYPTO MARKET DATA (Price, Volume, Historical)

### CoinGecko
- **URL:** https://www.coingecko.com/en/api
- **Free tier (Demo plan):** **30 calls/min**, **10,000 calls/month**
- **Data:** Prices, market cap, volume, OHLCV, exchange data, trending, DeFi, NFTs. 10,000+ coins, 600+ exchanges.
- **Python:** `pip install pycoingecko`
- **Limits:** 10,000/month (~333/day). Free tier limited to top 2,000 tokens by market cap.
- **Gotchas:**
  - The go-to free crypto API. Comprehensive and well-documented.
  - Historical data available (daily granularity for >90 days, hourly for 1-90 days, 5-min for <1 day).
  - No real-time WebSocket on free tier.
  - Attribution required for free usage.

### Binance API
- **URL:** https://binance-docs.github.io/apidocs/
- **Free tier:** Free with Binance account, **1200 request weight/minute**
- **Data:** Real-time order book, trades, OHLCV (klines), 24h ticker, WebSocket streams. All Binance-listed pairs.
- **Python:** `pip install python-binance` or `pip install binance-connector`
- **Limits:** Weight-based system — simple endpoints cost 1-5 weight, complex ones cost more. Effectively hundreds of calls/min for basic price data.
- **Gotchas:**
  - Best free real-time crypto data source. Sub-second WebSocket updates.
  - Only covers Binance-listed pairs (which is most major tokens).
  - Not available in all jurisdictions (US users need Binance.US).
  - Kline/candlestick data goes back to token listing date.
  - No API key needed for public market data endpoints.

### CryptoCompare
- **URL:** https://min-api.cryptocompare.com/
- **Free tier:** ~100,000 calls/month, ~60+ endpoints
- **Data:** Real-time and historical prices, OHLCV, social stats, blockchain data, exchanges, trading signals
- **Python:** `pip install cryptocompare`
- **Limits:** Free tier generous for most use cases. Minute-level data limited to 7 days on free tier (daily/hourly historical unlimited).
- **Gotchas:**
  - Must attribute CryptoCompare when using free tier.
  - Excellent historical daily data going back years.
  - Social/sentiment data included (Reddit, Twitter activity scores).

### CoinCap
- **URL:** https://coincap.io/ (API: https://docs.coincap.io/)
- **Free tier:** **200 requests/min** without API key, **500/min** with free key
- **Data:** Real-time prices, market cap, volume, exchanges, OHLCV candles. 2000+ assets.
- **Python:** Direct REST calls (no official library, but simple JSON API)
- **Limits:** Very generous rate limits. WebSocket available for real-time price updates.
- **Gotchas:**
  - Simple, clean API. Good for real-time price feeds.
  - Historical candle data available (1m, 5m, 15m, 30m, 1h, 2h, 4h, 8h, 12h, 1d).
  - Less comprehensive than CoinGecko for metadata but better rate limits.

### CoinMarketCap
- **URL:** https://coinmarketcap.com/api/
- **Free tier:** **10,000 calls/month**, 30 calls/min
- **Data:** Prices, market cap, volume, circulating supply, rankings, exchange info, global metrics
- **Python:** `pip install python-coinmarketcap`
- **Limits:** Free plan only includes Basic endpoints. No historical OHLCV on free tier.
- **Gotchas:**
  - Great for current snapshots and rankings.
  - Historical data requires paid plan (Hobbyist $29/mo+).
  - The most widely referenced crypto data source.

---

## 3. FUNDAMENTAL DATA (Earnings, Revenue, Ratios)

### SEC EDGAR (Official, 100% Free)
- **URL:** https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- **Free tier:** **Completely free**, no API key required
- **Data:** All SEC filings: 10-K, 10-Q, 8-K, 13-F, proxy statements, insider trades. XBRL financial data (income statements, balance sheets, cash flows).
- **Python:**
  - `pip install edgartools` (recommended — parses XBRL, no key needed, no rate limits)
  - `pip install sec-api` (freemium, more polished search)
  - `pip install sec-edgar-downloader`
- **Limits:** Rate limit: 10 requests/second (polite crawling expected, include User-Agent with email).
- **Gotchas:**
  - Raw filings require parsing. edgartools handles this well.
  - Only US-listed companies.
  - XBRL standardization varies between companies — cross-company comparison can be tricky.
  - This is THE authoritative source for US fundamental data.

### yfinance (Fundamentals)
- **URL:** https://github.com/ranaroussi/yfinance
- **Data:** Income statement, balance sheet, cash flow, key ratios, analyst recommendations, institutional holders, earnings dates
- **Python:** `ticker.financials`, `ticker.balance_sheet`, `ticker.cashflow`, `ticker.info`
- **Gotchas:** Same reliability issues as price data. Data sourced from Yahoo Finance which aggregates from multiple providers.

### FMP (Fundamentals — see Section 1)
- **Data on free tier:** Income statements, balance sheets, cash flows, ratios, DCF models, earnings surprises, SEC filings
- **Best for:** Quick access to standardized fundamental data via REST API

### Finnhub (Fundamentals — see Section 1)
- **Data on free tier:** Basic financials, earnings, revenue estimates, recommendation trends, insider transactions, SEC filings

---

## 4. ON-CHAIN CRYPTO DATA (MVRV, NVT, Exchange Flows)

### Glassnode
- **URL:** https://glassnode.com/
- **Free tier:** Web interface access to Tier 1 (basic) metrics at daily resolution. **API access requires paid Professional plan ($799/mo+).**
- **Data (free web):** Basic supply metrics, transaction counts, active addresses, exchange balances (Bitcoin, Ethereum)
- **Python:** API requires paid plan. For free access, scrape charts or use their free Workbench.
- **Gotchas:**
  - Industry-leading on-chain analytics but API is NOT free.
  - Free web access useful for manual research but not automated signal generation.
  - Tier 1 metrics are limited — MVRV, SOPR, NVT etc. require paid tiers.

### Blockchain.com
- **URL:** https://www.blockchain.com/explorer/api
- **Free tier:** Free, no API key for most endpoints
- **Data:** Bitcoin-specific: blocks, transactions, address info, unspent outputs, charts data (hash rate, difficulty, transaction volume, mempool size)
- **Python:** Direct REST calls
- **Limits:** Reasonable rate limits (not explicitly published).
- **Gotchas:**
  - Bitcoin-only for most useful endpoints.
  - Charts API provides pre-aggregated metrics (hash rate, miners revenue, etc.).
  - Good for Bitcoin network fundamentals.

### Mempool.space
- **URL:** https://mempool.space/docs/api
- **Free tier:** Completely free, open-source
- **Data:** Bitcoin mempool status, transaction details, fee estimates, block data, address stats (funded/spent txo counts and sums), difficulty adjustments, lightning network data
- **Python:** `pip install mempool-api` (community) or direct REST/WebSocket
- **Limits:** Public API has rate limits (not strictly published). Self-hosting removes all limits.
- **Gotchas:**
  - Bitcoin-only.
  - Best free source for Bitcoin fee market and mempool analysis.
  - Can self-host for unlimited access (requires Bitcoin full node).
  - WebSocket available at wss://mempool.space/api/v1/ws

### Etherscan API
- **URL:** https://etherscan.io/apis
- **Free tier:** **5 calls/second**, up to **100,000 calls/day**
- **Data:** Ethereum accounts, transactions, token transfers (ERC-20/721/1155), contract ABIs, gas tracker, block data, internal transactions, logs
- **Python:** `pip install etherscan-python` or `pip install web3` (for direct RPC)
- **Limits:** 5 calls/sec, 100k/day. Historical endpoints limited to 2 calls/sec.
- **Gotchas:**
  - Etherscan recently scaled back free tier coverage.
  - Similar APIs exist for other chains: BSCScan, Polygonscan, Arbiscan, etc. (same API format, separate keys).
  - Essential for Ethereum on-chain analysis.

### DeFiLlama
- **URL:** https://defillama.com/ | API docs: https://defillama.com/docs/api
- **Free tier:** Completely free, no API key required
- **Data:** TVL (Total Value Locked) for all DeFi protocols, yields/APY, stablecoin data, bridges, volumes, fees/revenue by protocol, token prices, liquidations
- **Python:** Direct REST calls (`requests` library). No official SDK.
- **Limits:** Generous but undocumented rate limits. Community reports ~300 calls/min.
- **Gotchas:**
  - THE best free DeFi data source. Open-source and community-maintained.
  - Historical TVL data for hundreds of protocols across all major chains.
  - Stablecoin flow data is excellent for macro crypto signals.
  - No authentication means easy integration.

### Dune Analytics
- **URL:** https://dune.com/
- **Free tier:** Free account with community queries. API free tier: **2,500 query executions/month**, 10 queries/min
- **Data:** Any on-chain data queryable via SQL — DEX volumes, NFT activity, whale movements, protocol metrics, custom analytics
- **Python:** `pip install dune-client`
- **Limits:** Free API tier is limited. Main value is running queries on the web UI.
- **Gotchas:**
  - Extremely powerful for custom on-chain analysis.
  - Community dashboards cover most common metrics (no need to write SQL).
  - Query execution can be slow (minutes for complex queries).
  - Results can be exported as CSV from the web UI.

### Santiment (Limited Free)
- **URL:** https://santiment.net/
- **Free tier:** Limited free API access, basic metrics only
- **Data:** On-chain metrics, social sentiment, development activity (GitHub), whale transactions, exchange flows
- **Python:** `pip install sanpy`
- **Gotchas:** Most useful metrics are behind paywall. Free tier very limited.

---

## 5. SENTIMENT & SOCIAL DATA

### Alternative.me — Crypto Fear & Greed Index
- **URL:** https://alternative.me/crypto/fear-and-greed-index/
- **Free tier:** Completely free, no API key
- **Data:** Daily Fear & Greed index (0-100) for crypto. Based on volatility, volume, social media, surveys, dominance, trends.
- **Python:** Direct REST: `GET https://api.alternative.me/fgi/?limit=30`
- **Limits:** Simple API, no known rate limits for reasonable usage.
- **Gotchas:**
  - Dead simple to integrate. One endpoint.
  - Historical data available.
  - Crypto-only (not stock market).

### CNN Fear & Greed Index (Stocks)
- **URL:** https://www.cnn.com/markets/fear-and-greed
- **Free tier:** No official API. Must scrape or use third-party wrappers.
- **Data:** Stock market Fear & Greed index based on 7 indicators (momentum, strength, breadth, put/call, junk bond demand, volatility, safe haven demand).
- **Python:** `pip install fear-and-greed` (unofficial scraper)
- **Gotchas:** Scraping-based — can break. No historical API.

### PRAW (Reddit API)
- **URL:** https://www.reddit.com/dev/api/ | https://github.com/praw-dev/praw
- **Free tier:** **100 requests/minute** (OAuth2), **10 requests/minute** (without OAuth)
- **Data:** Subreddit posts, comments, scores, awards. Key subreddits: r/wallstreetbets, r/stocks, r/cryptocurrency, r/bitcoin, r/options
- **Python:** `pip install praw`
- **Limits:** 100 req/min with OAuth. Reddit API changes in 2023 killed many third-party tools but PRAW still works with proper OAuth credentials.
- **Gotchas:**
  - Must register an app at reddit.com/prefs/apps for OAuth credentials.
  - Rate limit is per-client, not per-endpoint.
  - Historical data is limited — Reddit only serves ~1000 most recent posts per listing.
  - For historical Reddit data, consider Pushshift (if available) or academic datasets.

### Twitter/X API & Alternatives
- **URL:** https://developer.x.com/en/docs
- **Free tier:** X API free tier: **1,500 tweets/month** (write only), read access requires Basic ($200/mo) or higher
- **Python alternatives for scraping:**
  - `pip install twscrape` — free scraper, no API key, actively maintained (2025)
  - `snscrape` — free, open-source, no authentication, no limits. Status: works but development paused.
  - `pip install tweepy` — official API wrapper (requires paid X API access for read)
- **Gotchas:**
  - X/Twitter effectively killed free read API access in 2023. Free tier is write-only.
  - Scraping tools (twscrape, snscrape) work but may break with X platform changes.
  - For crypto sentiment, Twitter/X remains the most valuable social signal source.
  - Consider Farcaster/Bluesky APIs as supplementary social data (free and open).

### Google Trends (pytrends)
- **URL:** https://github.com/GeneralMills/pytrends
- **Free tier:** Free (unofficial scraper of Google Trends)
- **Data:** Search interest over time, related queries, interest by region, trending searches
- **Python:** `pip install pytrends` — **NOTE: repository archived April 2025**
- **Limits:** Google rate-limits aggressively. Expect 429 errors. Use proxies or add delays (10-60s between requests).
- **Gotchas:**
  - pytrends was archived April 2025. May still work but no updates.
  - Google released an official Trends API in July 2025 — check Google Cloud for access.
  - Data is relative (0-100 scale), not absolute search volume.
  - Excellent leading indicator for retail interest (e.g., "buy bitcoin" search trends).

### CFGI.io — Multi-Token Fear & Greed
- **URL:** https://cfgi.io/
- **Free tier:** Developer API available, updated every 15 minutes
- **Data:** Fear & Greed index for 52+ individual crypto tokens (not just BTC)
- **Python:** Direct REST calls
- **Gotchas:** Per-token sentiment is unique and valuable. Check current rate limits on their site.

---

## 6. NEWS APIs

### Finnhub (News — see Section 1)
- **Free tier:** 60 calls/min
- **Data:** Market news, company news by ticker, press releases, news sentiment scores
- **Best for:** Ticker-specific financial news with sentiment scores included

### NewsAPI
- **URL:** https://newsapi.org/
- **Free tier:** **100 requests/day**, developer use only
- **Data:** Headlines and articles from 150,000+ sources. Search by keyword, source, language, date.
- **Python:** `pip install newsapi-python`
- **Limits:** 100 req/day. Free tier: articles delayed by 24 hours, no commercial use allowed.
- **Gotchas:**
  - Free tier explicitly prohibited for production/commercial use.
  - 24-hour delay on free tier makes it unsuitable for real-time news signals.
  - Good for historical news analysis and backtesting.

### GNews API
- **URL:** https://gnews.io/
- **Free tier:** **100 requests/day**, 1 request/second
- **Data:** News articles from thousands of sources. Search by keyword, topic, country, language.
- **Python:** Direct REST calls
- **Limits:** 100/day, development/testing only. No full article content on free tier (title + description only).
- **Gotchas:** Cannot be used for commercial projects on free tier.

### NewsAPI.ai
- **URL:** https://newsapi.ai/
- **Free tier:** **2,000 searches/month**, up to 200,000 articles, last 30 days only
- **Data:** Global news from 150,000+ sources with NLP enrichment (entities, categories, sentiment)
- **Gotchas:** No historical data beyond 30 days on free tier. Good NLP features.

### RSS Feeds (Free, Unlimited)
- **URLs:**
  - Reuters: `https://www.reutersagency.com/feed/`
  - Yahoo Finance: `https://finance.yahoo.com/news/rss`
  - CNBC: `https://www.cnbc.com/id/100003114/device/rss/rss.html`
  - Seeking Alpha: `https://seekingalpha.com/feed.xml`
  - Investing.com RSS feeds
  - CoinDesk: `https://www.coindesk.com/arc/outboundfeeds/rss/`
  - CoinTelegraph: `https://cointelegraph.com/rss`
- **Python:** `pip install feedparser`
- **Limits:** No API limits — just HTTP polling. Be respectful (poll every 5-15 min).
- **Gotchas:**
  - Best truly unlimited free news source.
  - No search/filter — you get what the feed provides.
  - Combine with NLP (spaCy, transformers, FinBERT) for sentiment analysis.
  - Some feeds may be partial (title + summary only).

---

## 7. MACRO / ECONOMIC DATA

### FRED API (Federal Reserve Economic Data)
- **URL:** https://fred.stlouisfed.org/docs/api/fred/
- **Free tier:** Completely free, **120 requests/minute**, API key required
- **Data:** 765,000+ time series: GDP, CPI, unemployment, Fed funds rate, Treasury yields, M2 money supply, housing starts, consumer confidence, and much more. US and international data.
- **Python:** `pip install fredapi`
- **Limits:** 120 req/min is extremely generous. Essentially unlimited for any reasonable use case.
- **Gotchas:**
  - THE gold standard for US macro data. Used by every serious quant.
  - Data updated on the same schedule as official releases.
  - Key series IDs to know: `DFF` (Fed funds), `CPIAUCSL` (CPI), `GDP`, `UNRATE`, `T10Y2Y` (yield curve), `M2SL` (M2), `VIXCLS` (VIX)
  - Register for free API key at https://fred.stlouisfed.org/docs/api/api_key.html

### World Bank API
- **URL:** https://datahelpdesk.worldbank.org/knowledgebase/topics/125589-developer-information
- **Free tier:** Completely free, no API key required
- **Data:** 16,000+ development indicators for 200+ countries: GDP, inflation, trade, population, education, health
- **Python:** `pip install wbgapi` or `pip install world_bank_data`
- **Limits:** No published rate limits. Generous for any reasonable use.
- **Gotchas:**
  - Best for long-term macro analysis and cross-country comparisons.
  - Data updated quarterly/annually — not useful for short-term signals.
  - Excellent for emerging market macro data.

### OECD Data API
- **URL:** https://data.oecd.org/api/
- **Free tier:** Completely free
- **Data:** Leading indicators, GDP, trade, employment, prices for OECD countries
- **Python:** Direct REST/SDMX calls or `pip install pandasdmx`
- **Gotchas:** Complementary to FRED for international macro data.

### BLS (Bureau of Labor Statistics)
- **URL:** https://www.bls.gov/developers/
- **Free tier:** Free, **v2 (registered): 500 requests/day**, **v1 (unregistered): 25/day**
- **Data:** Employment, wages, CPI (granular), PPI, productivity
- **Python:** Direct REST calls or `pip install bls`
- **Gotchas:** More granular US inflation and employment data than FRED in some cases.

---

## 8. TECHNICAL INDICATORS

### Pre-Calculated via API
- **Twelve Data:** 100+ indicators via API (SMA, EMA, RSI, MACD, Bollinger, etc.) — counts against your 800/day free limit
- **Alpha Vantage:** 50+ indicators via API — counts against your 25/day limit
- **Finnhub:** Pattern recognition (candlestick patterns, support/resistance levels)

### Local Calculation (RECOMMENDED for Production)
For a trading signal system, local calculation is strongly preferred — no API limits, no latency, full control.

| Library | Install | Notes |
|---------|---------|-------|
| **pandas-ta** | `pip install pandas_ta` | 130+ indicators. Pure Python. Works directly with pandas DataFrames. Actively maintained. **Best choice for most projects.** |
| **TA-Lib** | `pip install ta-lib` (requires C library) | 150+ indicators. Fastest execution (C-based). Industry standard. Installation can be painful (requires compiling C library or using conda). |
| **ta** | `pip install ta` | 80+ indicators. Pure Python. Simple API. Good for beginners. |
| **tulipy** | `pip install tulipy` | C-based (fast). Simpler than TA-Lib to install. |
| **finta** | `pip install finta` | 80+ indicators. Pandas-native. |

**Recommendation:** Use **pandas-ta** for ease of use, or **TA-Lib** if you need maximum performance. Calculate indicators locally from OHLCV data fetched via free APIs above.

---

## 9. OPTIONS DATA

### yfinance (Best Free Option)
- **Data:** Full option chains (calls/puts), strikes, expiration dates, Greeks (some), open interest, volume, bid/ask, implied volatility
- **Python:** `ticker.options` (expiration dates), `ticker.option_chain(date)` (full chain)
- **Gotchas:** Same reliability issues as yfinance generally. Data may be delayed 15 min.

### CBOE (Direct)
- **URL:** https://www.cboe.com/delayed_quotes/
- **Free tier:** Delayed quotes available via web (no official free API)
- **Gotchas:** Can scrape delayed data but no structured API.

### Polygon.io (Limited Free)
- **Free tier:** Options snapshots and historical data with 5 calls/min limit
- **Gotchas:** Very limited on free tier.

### Market Data App
- **URL:** https://www.marketdata.app/
- **Free tier:** **100 requests/day**
- **Data:** Real-time and historical option chains back to 2005
- **Gotchas:** 100/day sufficient for EOD options analysis.

### Tradier
- **URL:** https://tradier.com/
- **Free tier:** Sandbox environment with delayed data
- **Data:** Option chains, expirations, strikes, Greeks
- **Python:** Direct REST API
- **Gotchas:** Sandbox is free but data is delayed/simulated. Live data requires brokerage account.

**Reality check:** Free options data is scarce. yfinance is the practical choice for most free projects. For serious options work, consider IBKR (Interactive Brokers) API — free with a funded account.

---

## 10. ALTERNATIVE DATA

### GitHub Activity (Crypto Projects)
- **URL:** https://api.github.com/
- **Free tier:** **60 requests/hour** (unauthenticated), **5,000/hour** (with free personal token)
- **Data:** Commits, pull requests, issues, stars, forks, contributors, release frequency for any public repo
- **Python:** `pip install PyGithub`
- **Gotchas:**
  - Track development activity for crypto projects (e.g., ethereum/go-ethereum, bitcoin/bitcoin, solana-labs/solana).
  - Dev activity is a proven leading indicator for crypto project health.
  - Santiment tracks this, but you can build it yourself with GitHub API.

### Google Trends (see Section 5)
- Retail interest proxy. "Buy Bitcoin" search volume correlates with price movements.

### Quiver Quantitative
- **URL:** https://www.quiverquant.com/
- **Free tier:** Limited free API access
- **Data:** Congressional trading (STOCK Act), corporate lobbying, government contracts, Wikipedia page views, retail trading (WSB)
- **Python:** Direct REST API
- **Gotchas:** Some data freely available on website, API access may require paid plan.

### Wikipedia Page Views
- **URL:** https://wikimedia.org/api/rest_v1/
- **Free tier:** Completely free, no API key
- **Data:** Daily page view counts for any Wikipedia article
- **Python:** `pip install mwviews` or direct REST calls
- **Gotchas:**
  - Unusual but valid alternative data signal.
  - Spike in page views for a company/crypto can indicate increased public attention.

### Unusual Whales (Limited Free)
- **URL:** https://unusualwhales.com/
- **Free tier:** Some data visible on website, API requires paid subscription
- **Data:** Unusual options activity, congressional trading, dark pool data, flow data
- **Gotchas:** Primarily a paid service. Free website shows limited recent flow data.

---

## SUMMARY: RECOMMENDED FREE STACK FOR A TRADING SIGNAL SYSTEM

### Core Price Data
| Asset Class | Primary API | Backup API |
|-------------|------------|------------|
| US Stocks | **Twelve Data** (800/day) | Finnhub (60/min) |
| Crypto | **Binance API** (free, real-time) | CoinGecko (10k/month) |
| Forex | Twelve Data | Alpha Vantage |

### Fundamentals & Macro
| Data Type | Best Free Source |
|-----------|-----------------|
| Stock fundamentals | **SEC EDGAR** (edgartools) + FMP |
| Earnings/estimates | Finnhub + yfinance |
| Macro/economic | **FRED API** (unbeatable) |
| DeFi metrics | **DeFiLlama** (free, no key) |

### Signals & Sentiment
| Signal Type | Best Free Source |
|-------------|-----------------|
| Technical indicators | **pandas-ta** (local calculation) |
| Crypto sentiment | Alternative.me Fear & Greed + CryptoCompare social |
| Stock sentiment | Reddit (PRAW) + Finnhub news sentiment |
| News | Finnhub + RSS feeds + FinBERT NLP |
| On-chain | Etherscan + Mempool.space + DeFiLlama |
| Alternative | GitHub API + Google Trends |

### Key Advice
1. **Never depend on a single free API** — they change limits, break, or shut down (see: IEX Cloud shutdown, yfinance outages).
2. **Cache aggressively** — store historical data locally to minimize API calls.
3. **Use WebSockets where available** (Binance, Finnhub, CoinCap) for real-time data instead of polling.
4. **Calculate technical indicators locally** — never waste API calls on pre-calculated indicators.
5. **Rate-limit your requests** — implement exponential backoff and respect API limits to avoid bans.
6. **SEC EDGAR + FRED are government APIs** — they are the most reliable and will not disappear or paywall their data.
