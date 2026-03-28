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
