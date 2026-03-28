"""Tests for src.monitoring.pushgateway push helper."""

from unittest.mock import patch


def test_push_does_nothing_when_url_empty() -> None:
    """push_pipeline_metrics() is a no-op when pushgateway URL is empty."""
    with patch("src.monitoring.pushgateway.settings") as mock_settings:
        mock_settings.prometheus_pushgateway_url = ""
        from src.monitoring.pushgateway import push_pipeline_metrics

        # Should not raise
        push_pipeline_metrics()


@patch("src.monitoring.pushgateway.push_to_gateway")
@patch("src.monitoring.pushgateway.settings")
def test_push_calls_gateway(mock_settings, mock_push) -> None:  # type: ignore[no-untyped-def]
    """push_pipeline_metrics() calls push_to_gateway with correct args when URL is set."""
    mock_settings.prometheus_pushgateway_url = "http://pushgateway:9091"
    from src.monitoring.pushgateway import push_pipeline_metrics

    push_pipeline_metrics()
    mock_push.assert_called_once()
    # Verify job name is passed correctly (positional or keyword)
    call_args = mock_push.call_args
    assert (
        call_args[1].get("job") == "trade_pipeline"
        or call_args[0][1] == "trade_pipeline"
    )
