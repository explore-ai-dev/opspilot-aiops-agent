import json
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path


APP_PATH = Path(__file__).parents[1] / "demo-ops" / "demo-service" / "app.py"


class DemoServiceTests(unittest.TestCase):
    def test_source_uses_only_standard_library(self):
        source = APP_PATH.read_text(encoding="utf-8")
        self.assertIn("from http.server import", source)
        self.assertNotIn("from flask import", source)
        self.assertNotIn("prometheus_client", source)

    def test_metrics_format_contains_required_metric_names(self):
        namespace = {}
        exec(APP_PATH.read_text(encoding="utf-8"), namespace)
        namespace["record_request"]("/", 200, 0.1)
        metrics = namespace["render_metrics"]()
        self.assertIn("demo_http_requests_total", metrics)
        self.assertIn("demo_http_request_duration_seconds_bucket", metrics)
        self.assertIn('service="demo-service"', metrics)


if __name__ == "__main__":
    unittest.main()
