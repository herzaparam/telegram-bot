"""Centralized Prometheus metric definitions for trade-agent.

All metric objects are importable from this module. They use the default
prometheus_client registry so both the /metrics endpoint (bot) and
push_to_gateway (pipeline) export the same metrics.
"""

from prometheus_client import Counter, Gauge, Histogram

# ---------------------------------------------------------------------------
# Pipeline metrics (pushed to Pushgateway after each run)
# ---------------------------------------------------------------------------

PIPELINE_DURATION = Histogram(
    "pipeline_run_duration_seconds",
    "Total pipeline run duration",
    ["stage"],
    buckets=[5, 10, 30, 60, 120, 300, 600],
)

PIPELINE_STAGE_STATUS = Counter(
    "pipeline_stage_status_total",
    "Pipeline stage completion status",
    ["stage", "status"],  # status: completed/failed/skipped/partial
)

FETCH_SUCCESS = Counter(
    "fetch_success_total",
    "Data fetch success count",
    ["source", "asset_type"],
)

FETCH_FAILURE = Counter(
    "fetch_failure_total",
    "Data fetch failure count",
    ["source", "asset_type"],
)

LLM_CALL_COUNT = Counter(
    "llm_call_total",
    "LLM API call count",
    ["model", "is_fallback"],
)

LLM_CALL_DURATION = Histogram(
    "llm_call_duration_seconds",
    "LLM API call latency",
    ["model"],
    buckets=[1, 2, 5, 10, 15, 30],
)

ENGINE_DURATION = Histogram(
    "engine_analysis_duration_seconds",
    "Per-engine analysis duration",
    ["engine_name"],
    buckets=[1, 2, 5, 10, 30],
)

DATA_FRESHNESS_HOURS = Gauge(
    "data_freshness_hours",
    "Hours since last price data ingestion",
    ["asset_type"],
)

PIPELINE_LAST_SUCCESS = Gauge(
    "pipeline_last_success_timestamp",
    "Unix timestamp of last successful pipeline completion",
)

# ---------------------------------------------------------------------------
# Bot metrics (scraped from /metrics endpoint)
# ---------------------------------------------------------------------------

BOT_REQUEST_COUNT = Counter(
    "bot_http_requests_total",
    "Total HTTP requests to bot",
    ["method", "endpoint", "status"],
)
