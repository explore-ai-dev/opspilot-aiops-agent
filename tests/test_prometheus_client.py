import json
from unittest.mock import Mock

import pytest
import requests

from integrations.prometheus_client import PrometheusClient, PrometheusQueryError


def _response(value: str | None = "1.5") -> Mock:
    result = [] if value is None else [{"metric": {}, "value": [0, value]}]
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"status": "success", "data": {"result": result}}
    return response


def test_fetch_service_metrics_uses_fixed_queries_and_formats_values():
    session = Mock()
    session.get.side_effect = [_response("2.5"), _response("0.125"), _response("1.75")]
    client = PrometheusClient(base_url="http://prometheus:9090/", session=session)

    result = client.fetch_service_metrics("demo-service", "最近15分钟")

    assert result["data_source"] == "prometheus"
    assert result["request_rate_rps"] == 2.5
    assert result["error_rate_percent"] == 12.5
    assert result["p95_latency_ms"] == 1750.0
    assert len(result["queries"]) == 3
    assert all(call.args[0] == "http://prometheus:9090/api/v1/query" for call in session.get.call_args_list)
    assert all(call.kwargs["timeout"] == 5.0 for call in session.get.call_args_list)
    serialized = json.dumps(result["queries"])
    assert "demo_http_requests_total" in serialized
    assert "demo_http_request_duration_seconds_bucket" in serialized


def test_fetch_service_metrics_rejects_unsupported_time_range():
    client = PrometheusClient(session=Mock())

    with pytest.raises(PrometheusQueryError, match="不支持的时间范围"):
        client.fetch_service_metrics("demo-service", "最近3分钟")


def test_fetch_service_metrics_reports_connection_failure():
    session = Mock()
    session.get.side_effect = requests.ConnectionError("refused")
    client = PrometheusClient(session=session)

    with pytest.raises(PrometheusQueryError, match="无法连接 Prometheus"):
        client.fetch_service_metrics("demo-service", "最近1小时")


def test_fetch_service_metrics_reports_empty_data():
    session = Mock()
    session.get.return_value = _response(None)
    client = PrometheusClient(session=session)

    with pytest.raises(PrometheusQueryError, match="没有查询到指标数据"):
        client.fetch_service_metrics("demo-service", "最近1小时")


@pytest.mark.parametrize("value", ["NaN", "+Inf", "-Inf"])
def test_fetch_service_metrics_rejects_non_finite_values(value):
    session = Mock()
    session.get.return_value = _response(value)
    client = PrometheusClient(session=session)

    with pytest.raises(PrometheusQueryError, match="指标值无效"):
        client.fetch_service_metrics("demo-service", "最近1小时")
