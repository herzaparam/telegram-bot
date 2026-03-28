"""Pushgateway push helper for pipeline metrics.

After each pipeline run, call push_pipeline_metrics() to push all collected
metrics to the Prometheus Pushgateway for scraping by Prometheus.
"""

import structlog
from prometheus_client import REGISTRY, push_to_gateway

from src.config import settings

logger = structlog.get_logger(__name__)


def push_pipeline_metrics() -> None:
    """Push all collected metrics to Pushgateway after pipeline run."""
    gateway_url = settings.prometheus_pushgateway_url
    if not gateway_url:
        logger.debug("pushgateway_skip", reason="no url configured")
        return
    push_to_gateway(gateway_url, job="trade_pipeline", registry=REGISTRY)
    logger.info("pushgateway_push_complete", url=gateway_url)
