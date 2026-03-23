"""Alert collection for data staleness and fetch failures.

Batches alerts during pipeline ingest for later summary logging
and future Telegram integration (Phase 5).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import structlog


@dataclass
class Alert:
    """A single alert event."""

    alert_type: str  # "DATA_STALE" or "FETCH_FAILURE"
    asset_symbol: str
    message: str
    timestamp: datetime


class AlertCollector:
    """Collects and batches alerts during a pipeline run."""

    def __init__(self) -> None:
        self._alerts: list[Alert] = []
        self._log = structlog.get_logger("alerts")

    def add_stale(self, asset_symbol: str, reason: str) -> None:
        """Record a DATA_STALE alert."""
        alert = Alert(
            alert_type="DATA_STALE",
            asset_symbol=asset_symbol,
            message=reason,
            timestamp=datetime.now(UTC),
        )
        self._alerts.append(alert)
        self._log.warning("data_stale", asset=asset_symbol, reason=reason)

    def add_fetch_failure(self, asset_symbol: str, reason: str) -> None:
        """Record a FETCH_FAILURE alert."""
        alert = Alert(
            alert_type="FETCH_FAILURE",
            asset_symbol=asset_symbol,
            message=reason,
            timestamp=datetime.now(UTC),
        )
        self._alerts.append(alert)
        self._log.error("fetch_failure", asset=asset_symbol, reason=reason)

    def summary(self) -> str:
        """Return a formatted summary of all batched alerts.

        Example: "3 alerts: BBCA.JK (stale), TLKM.JK (stale), SOL (fetch failed)"
        """
        if not self._alerts:
            return "0 alerts"

        parts: list[str] = []
        for a in self._alerts:
            label = "stale" if a.alert_type == "DATA_STALE" else "fetch failed"
            parts.append(f"{a.asset_symbol} ({label})")

        return f"{len(self._alerts)} alerts: {', '.join(parts)}"

    def has_alerts(self) -> bool:
        """Return True if any alerts have been recorded."""
        return len(self._alerts) > 0

    @property
    def alerts(self) -> list[Alert]:
        """Return a copy of the alerts list."""
        return list(self._alerts)
