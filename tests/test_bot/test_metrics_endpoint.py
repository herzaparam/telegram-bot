"""Tests for /metrics endpoint on the bot."""

import httpx
import pytest

from src.bot.main import app


@pytest.mark.asyncio
async def test_metrics_endpoint() -> None:
    """GET /metrics/ returns Prometheus text format with default process metrics."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/metrics/")
        assert resp.status_code == 200
        assert "python_info" in resp.text or "process_" in resp.text


@pytest.mark.asyncio
async def test_bot_request_count_increments_on_health() -> None:
    """BOT_REQUEST_COUNT increments when /health is called."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Hit /health
        await client.get("/health")
        # Check /metrics for the counter
        resp = await client.get("/metrics/")
        assert resp.status_code == 200
        assert 'bot_http_requests_total{' in resp.text
        assert 'endpoint="/health"' in resp.text
        assert 'method="GET"' in resp.text
        assert 'status="200"' in resp.text


@pytest.mark.asyncio
async def test_bot_request_count_labels_method_endpoint_status() -> None:
    """BOT_REQUEST_COUNT records method, endpoint, and status labels."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # POST to webhook (will get 503 since ptb_app is None in tests)
        await client.post("/telegram/webhook", json={})
        resp = await client.get("/metrics/")
        assert 'bot_http_requests_total{' in resp.text
        assert 'endpoint="/telegram/webhook"' in resp.text
        assert 'method="POST"' in resp.text
        assert 'status="503"' in resp.text
