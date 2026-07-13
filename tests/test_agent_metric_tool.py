from unittest.mock import Mock, patch

from agent.tools.agent_tools import fetch_metric_data
from integrations.prometheus_client import PrometheusQueryError


def test_demo_service_metrics_use_prometheus():
    metrics = {
        "service_name": "demo-service",
        "data_source": "prometheus",
        "error_rate_percent": 25.0,
    }
    with patch("agent.tools.agent_tools.prometheus_client") as client:
        client.fetch_service_metrics.return_value = metrics

        result = fetch_metric_data.invoke(
            {"service_name": "demo-service", "time_range": "最近15分钟"}
        )

    client.fetch_service_metrics.assert_called_once_with("demo-service", "最近15分钟")
    assert "prometheus" in result
    assert "25.0" in result


def test_existing_service_metrics_still_use_mock_data():
    with patch("agent.tools.agent_tools.prometheus_client", Mock()) as client:
        result = fetch_metric_data.invoke(
            {"service_name": "order-service", "time_range": "最近1小时"}
        )

    client.fetch_service_metrics.assert_not_called()
    assert "83%" in result
    assert "3.8%" in result


def test_demo_service_prometheus_failure_is_explicit():
    with patch("agent.tools.agent_tools.prometheus_client") as client:
        client.fetch_service_metrics.side_effect = PrometheusQueryError("无法连接 Prometheus")

        result = fetch_metric_data.invoke(
            {"service_name": "demo-service", "time_range": "最近15分钟"}
        )

    assert "Prometheus 指标查询失败" in result
    assert "无法连接 Prometheus" in result
    assert "83%" not in result
