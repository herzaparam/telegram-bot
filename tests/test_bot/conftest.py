"""Shared fixtures for bot tests."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.db.models import Asset, BotSettings, DailyDecision, Watchlist


@pytest.fixture()
def sample_assets() -> list[Asset]:
    """Sample assets for testing."""
    assets = []
    for i, (sym, name, atype, exch) in enumerate(
        [
            ("BBCA", "Bank Central Asia", "stock", "IDX"),
            ("BTC", "Bitcoin", "crypto", "binance"),
            ("TLKM", "Telkom Indonesia", "stock", "IDX"),
        ],
        start=1,
    ):
        a = Asset(
            id=i,
            symbol=sym,
            name=name,
            asset_type=atype,
            exchange=exch,
            is_active=True,
        )
        assets.append(a)
    return assets


@pytest.fixture()
def sample_decisions(sample_assets: list[Asset]) -> list[DailyDecision]:
    """Sample decisions for report formatting tests."""
    verdicts = [
        ("STRONG BUY", 0.85, 0.9, "Strong bullish momentum with solid fundamentals"),
        ("HOLD", 0.1, 0.6, "Mixed signals suggest waiting for clearer direction"),
        ("SELL", -0.5, 0.75, "Bearish technical indicators and weakening volume"),
    ]
    decisions = []
    for asset, (verdict, score, conf, reasoning) in zip(sample_assets, verdicts):
        d = DailyDecision(
            id=asset.id,
            asset_id=asset.id,
            date=date(2026, 3, 24),
            verdict=verdict,
            score=score,
            confidence=conf,
            reasoning=reasoning,
            key_factors={"technical": "bullish", "volume": "high"},
            risk_warning="Market volatility elevated" if verdict == "SELL" else None,
            model_used="gpt-4o-mini",
        )
        decisions.append(d)
    return decisions


@pytest.fixture()
def mock_update():
    """Create a mock Telegram Update object."""
    update = MagicMock()
    update.effective_chat = MagicMock()
    update.effective_chat.id = 12345
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture()
def mock_context():
    """Create a mock PTB CallbackContext."""
    ctx = MagicMock()
    ctx.args = []
    ctx.bot = MagicMock()
    return ctx
