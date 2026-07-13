# OpsPilot Prometheus Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在本机运行 demo-service、Prometheus、Grafana，并让 OpsPilot 对 `demo-service` 使用真实 Prometheus 指标。

**Architecture:** Docker Compose 运行三个容器；demo-service 暴露 HTTP 与 Prometheus 指标，Prometheus 采集，Grafana展示。OpsPilot 保持本机运行，通过独立 `PrometheusClient` 使用固定 PromQL 查询指标；原 Mock 服务继续兼容。

**Tech Stack:** Python 3.10+、Flask、prometheus-client、requests、Docker Compose、Prometheus、Grafana、pytest

## Global Constraints

- 修改任何原文件前，复制到 `backups/<timestamp>-prometheus-integration/` 并生成 SHA-256 清单。
- Agent 只能执行固定的只读 PromQL，不能接受任意 PromQL。
- `PROMETHEUS_BASE_URL` 默认 `http://localhost:9090`，HTTP 超时 5 秒。
- Prometheus 不可达或无数据时明确返回错误，不伪造指标。
- 不改动 RAG、模型工厂、提示词、Streamlit 主体及其他 Mock 工具。
- 当前目录不是 Git 仓库，因此跳过提交步骤，以备份清单替代回滚基线。

---

## File Structure

**Create:**
- `integrations/__init__.py`：集成包入口。
- `integrations/prometheus_client.py`：时间范围转换、固定 PromQL 和 HTTP 查询。
- `tests/test_prometheus_client.py`：适配器单元测试。
- `tests/test_agent_metric_tool.py`：工具路由测试。
- `demo-ops/docker-compose.yml`：三服务编排。
- `demo-ops/prometheus.yml`：抓取配置。
- `demo-ops/demo-service/app.py`：可制造正常、慢、错误请求的服务。
- `demo-ops/demo-service/requirements.txt`：容器依赖。
- `demo-ops/demo-service/Dockerfile`：服务镜像。
- `demo-ops/grafana/provisioning/datasources/prometheus.yml`：自动数据源。
- `demo-ops/grafana/provisioning/dashboards/provider.yml`：仪表盘提供器。
- `demo-ops/grafana/dashboards/demo-service.json`：预置仪表盘。
- `demo-ops/generate-traffic.py`：故障流量脚本。
- `demo-ops/README.md`：启动、演示、停止和回滚说明。

**Modify after backup:**
- `agent/tools/agent_tools.py:13-19,342-350`：注册 demo-service，并将其指标路由至 Prometheus。
- `requirements.txt`：增加 `requests` 与测试依赖（若环境缺失）。

---

### Task 1: Backup and Prometheus Client

**Files:**
- Create: `backups/<timestamp>-prometheus-integration/manifest.txt`
- Create: `integrations/__init__.py`
- Create: `integrations/prometheus_client.py`
- Create: `tests/test_prometheus_client.py`

**Interfaces:**
- Produces: `PrometheusClient(base_url: str | None = None, timeout: float = 5.0)`
- Produces: `PrometheusClient.fetch_service_metrics(service_name: str, time_range: str) -> dict`
- Raises: `PrometheusQueryError` for connection, response, unsupported range, or empty-data errors.

- [ ] **Step 1: Back up original files**

Copy `agent/tools/agent_tools.py` and `requirements.txt`, preserving paths. Record source, backup path, SHA-256, and reason in `manifest.txt`.

- [ ] **Step 2: Write failing adapter tests**

Tests must mock `requests.Session.get` and verify: fixed query use, URL `/api/v1/query`, timeout 5, percentage/latency formatting, unsupported range, connection failure, and empty result.

- [ ] **Step 3: Run tests and confirm failure**

Run: `.venv/Scripts/python.exe -m pytest tests/test_prometheus_client.py -v`
Expected: FAIL because module does not exist.

- [ ] **Step 4: Implement minimal adapter**

Use fixed queries for request rate, 5xx error ratio, and P95 duration based on `demo_http_requests_total` and `demo_http_request_duration_seconds_bucket`. Map `最近15分钟/最近1小时/最近24小时/今天/本周/本月` to `15m/1h/24h/24h/7d/30d`. Return keys `service_name`, `time_range`, `data_source`, `request_rate_rps`, `error_rate_percent`, `p95_latency_ms`, and `queries`.

- [ ] **Step 5: Run adapter tests**

Expected: all adapter tests PASS.

### Task 2: Demo Monitoring Stack

**Files:**
- Create all files under `demo-ops/` listed above.

**Interfaces:**
- Produces HTTP endpoints: `GET /`, `/slow`, `/error`, `/health`, `/metrics` on port 8000.
- Produces metric names: `demo_http_requests_total{service,method,path,status}` and `demo_http_request_duration_seconds_bucket{service,method,path}`.
- Produces Prometheus at port 9090 and Grafana at port 3000.

- [ ] **Step 1: Implement demo service and container files**

Flask middleware records count and histogram; `/slow` sleeps 2 seconds; `/error` returns 500; `/health` returns `{"status":"ok"}`. Pin small compatible dependency versions.

- [ ] **Step 2: Add Compose, Prometheus, and Grafana provisioning**

Use official `prom/prometheus` and `grafana/grafana` images; scrape `demo-service:8000` every 5 seconds; provision Prometheus URL `http://prometheus:9090`; provision panels for request rate, error percentage, and P95 latency.

- [ ] **Step 3: Add deterministic traffic generator**

Generate a normal baseline followed by configurable slow/error requests; use only Python standard library so it runs from the project venv.

- [ ] **Step 4: Validate Compose configuration**

Run: Docker Compose `config` in `demo-ops`.
Expected: exit 0 and resolved services `demo-service`, `prometheus`, `grafana`.

- [ ] **Step 5: Build and start the stack**

Run Compose `up -d --build`, then inspect `ps` and health endpoints.
Expected: all containers running; `/health` returns 200; Prometheus target reports `up=1`.

### Task 3: Route OpsPilot Metrics to Prometheus

**Files:**
- Modify: `agent/tools/agent_tools.py`
- Modify only if needed: `requirements.txt`
- Create: `tests/test_agent_metric_tool.py`

**Interfaces:**
- Consumes: `PrometheusClient.fetch_service_metrics(...)` from Task 1.
- Preserves: `fetch_metric_data(service_name: str, time_range: str) -> str` LangChain tool interface.
- Behavior: `demo-service` uses Prometheus; existing service names use existing Mock data.

- [ ] **Step 1: Write failing routing tests**

Verify `demo-service` calls the client and serializes returned data; existing `order-service` still returns Mock data; adapter errors become an explicit Chinese error string and log entry.

- [ ] **Step 2: Run routing tests and confirm failure**

Expected: FAIL because demo-service is not routed.

- [ ] **Step 3: Implement minimal routing**

Add `demo-service` to `service_list`, instantiate the client once, route only that name to it, catch `PrometheusQueryError`, and preserve existing Mock lookup unchanged.

- [ ] **Step 4: Run all unit tests**

Run: `.venv/Scripts/python.exe -m pytest tests -v`
Expected: all tests PASS.

### Task 4: End-to-End Demonstration and Documentation

**Files:**
- Modify: `demo-ops/README.md` as observed commands/results require.

**Interfaces:**
- Consumes the running stack and `fetch_metric_data.invoke({"service_name":"demo-service","time_range":"最近15分钟"})`.
- Produces a repeatable operator walkthrough.

- [ ] **Step 1: Generate baseline and fault traffic**

Run the traffic generator, then wait at least two 5-second scrape intervals.

- [ ] **Step 2: Verify raw monitoring evidence**

Query Prometheus API for request rate, 5xx ratio, and P95 latency. Expected: non-empty numeric values; error percentage above zero; P95 reflects slow traffic.

- [ ] **Step 3: Verify OpsPilot tool integration**

Invoke the LangChain tool directly. Expected: string containing `data_source: prometheus`, service name, rate, error percentage, latency, and fixed evidence queries.

- [ ] **Step 4: Verify failure behavior**

Temporarily stop Prometheus and invoke the tool. Expected: clear connection error with no Mock values. Restart Prometheus afterward.

- [ ] **Step 5: Exercise the full Agent when API credentials are available**

Start Streamlit and ask `分析 demo-service 最近15分钟的异常情况`. Expected: Agent calls the metric tool and cites real Prometheus values. If `DASHSCOPE_API_KEY` is absent, record this step as blocked while retaining successful direct-tool verification.

- [ ] **Step 6: Final documentation and status report**

Document exact URLs, credentials (`admin/admin` for local demo only), commands, query, expected output, stop command, and backup-based rollback. Report every passed, failed, or blocked check honestly.
