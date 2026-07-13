import json
import math
import threading
import time
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, math.inf)
_lock = threading.Lock()
_request_counts = defaultdict(int)
_duration_buckets = defaultdict(int)
_duration_counts = defaultdict(int)
_duration_sums = defaultdict(float)


def record_request(path: str, status: int, duration: float) -> None:
    with _lock:
        _request_counts[(path, status)] += 1
        _duration_counts[path] += 1
        _duration_sums[path] += duration
        for bucket in BUCKETS:
            if duration <= bucket:
                _duration_buckets[(path, bucket)] += 1


def _labels(path: str, extra: str = "") -> str:
    suffix = f",{extra}" if extra else ""
    return f'service="demo-service",method="GET",path="{path}"{suffix}'


def render_metrics() -> str:
    lines = [
        "# HELP demo_http_requests_total Demo service HTTP requests",
        "# TYPE demo_http_requests_total counter",
    ]
    with _lock:
        for (path, status), count in sorted(_request_counts.items()):
            status_label = f'status="{status}"'
            lines.append(f'demo_http_requests_total{{{_labels(path, status_label)}}} {count}')

        lines.extend([
            "# HELP demo_http_request_duration_seconds Demo service HTTP request duration",
            "# TYPE demo_http_request_duration_seconds histogram",
        ])
        for path in sorted(_duration_counts):
            for bucket in BUCKETS:
                le = "+Inf" if math.isinf(bucket) else str(bucket)
                count = _duration_buckets[(path, bucket)]
                le_label = f'le="{le}"'
                lines.append(
                    f'demo_http_request_duration_seconds_bucket{{{_labels(path, le_label)}}} {count}'
                )
            labels = _labels(path)
            lines.append(f"demo_http_request_duration_seconds_count{{{labels}}} {_duration_counts[path]}")
            lines.append(f"demo_http_request_duration_seconds_sum{{{labels}}} {_duration_sums[path]:.6f}")
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            self._send(200, render_metrics(), "text/plain; version=0.0.4; charset=utf-8")
            return
        if self.path == "/health":
            self._send_json(200, {"status": "ok"})
            return

        started = time.monotonic()
        if self.path == "/slow":
            time.sleep(2)
            status, body = 200, {"service": "demo-service", "status": "slow", "delay_seconds": 2}
        elif self.path == "/error":
            status, body = 500, {"service": "demo-service", "status": "error"}
        elif self.path == "/":
            status, body = 200, {"service": "demo-service", "status": "ok"}
        else:
            status, body = 404, {"error": "not found"}

        record_request(self.path, status, time.monotonic() - started)
        self._send_json(status, body)

    def _send_json(self, status, body):
        self._send(status, json.dumps(body, ensure_ascii=False), "application/json; charset=utf-8")

    def _send(self, status, body, content_type):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        print(f"[demo-service] {self.address_string()} {fmt % args}")


if __name__ == "__main__":
    print("demo-service listening on http://0.0.0.0:8000")
    ThreadingHTTPServer(("0.0.0.0", 8000), Handler).serve_forever()
