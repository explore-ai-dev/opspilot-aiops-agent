import math
import os

import requests


class PrometheusQueryError(RuntimeError):
    """Prometheus 查询无法提供可信数据。"""


class PrometheusClient:
    RANGE_WINDOWS = {
        "最近15分钟": "15m",
        "最近1小时": "1h",
        "最近24小时": "24h",
        "今天": "24h",
        "本周": "7d",
        "本月": "30d",
    }

    def __init__(self, base_url=None, timeout=5.0, session=None):
        self.base_url = (base_url or os.getenv("PROMETHEUS_BASE_URL", "http://localhost:9090")).rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()

    def fetch_service_metrics(self, service_name: str, time_range: str) -> dict:
        window = self.RANGE_WINDOWS.get(time_range)
        if window is None:
            supported = "、".join(self.RANGE_WINDOWS)
            raise PrometheusQueryError(f"不支持的时间范围：{time_range}；支持：{supported}")

        label = f'service="{service_name}"'
        queries = {
            "request_rate_rps": f'sum(rate(demo_http_requests_total{{{label}}}[{window}]))',
            "error_rate": (
                f'sum(rate(demo_http_requests_total{{{label},status=~"5.."}}[{window}])) '
                f'/ clamp_min(sum(rate(demo_http_requests_total{{{label}}}[{window}])), 0.000001)'
            ),
            "p95_latency_seconds": (
                "histogram_quantile(0.95, sum by (le) "
                f'(rate(demo_http_request_duration_seconds_bucket{{{label}}}[{window}])))'
            ),
        }

        request_rate = self._query(queries["request_rate_rps"])
        error_ratio = self._query(queries["error_rate"])
        p95_seconds = self._query(queries["p95_latency_seconds"])

        return {
            "service_name": service_name,
            "time_range": time_range,
            "data_source": "prometheus",
            "request_rate_rps": round(request_rate, 4),
            "error_rate_percent": round(error_ratio * 100, 4),
            "p95_latency_ms": round(p95_seconds * 1000, 2),
            "queries": queries,
        }

    def _query(self, query: str) -> float:
        try:
            response = self.session.get(
                f"{self.base_url}/api/v1/query",
                params={"query": query},
                timeout=self.timeout,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise PrometheusQueryError(f"无法连接 Prometheus：{exc}") from exc
        except ValueError as exc:
            raise PrometheusQueryError("Prometheus 返回了无法解析的响应") from exc

        if payload.get("status") != "success":
            raise PrometheusQueryError(f"Prometheus 查询失败：{payload.get('error', '未知错误')}")

        result = payload.get("data", {}).get("result", [])
        if not result:
            raise PrometheusQueryError("Prometheus 没有查询到指标数据，请先产生流量并等待采集")

        try:
            value = float(result[0]["value"][1])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise PrometheusQueryError("Prometheus 指标值格式无效") from exc

        if not math.isfinite(value):
            raise PrometheusQueryError("Prometheus 指标值无效，请先产生流量并等待采集")
        return value
