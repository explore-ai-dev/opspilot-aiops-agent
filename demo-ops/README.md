# OpsPilot 本地监控演示

本演示采用以下结构：

- `demo-service` 使用 Python 标准库直接运行在 Windows 主机的 `8000` 端口。
- Prometheus 和 Grafana 由 Docker Compose 启动。
- Prometheus 容器通过 `host.docker.internal:8000` 抓取真实指标。
- OpsPilot 通过 `http://localhost:9090` 查询 Prometheus。

## 1. 启动 demo-service

在项目根目录执行：

```bash
.venv/Scripts/python.exe demo-ops/demo-service/app.py
```

保持该终端运行，并验证：

```text
http://localhost:8000/health
http://localhost:8000/metrics
```

## 2. 启动 Prometheus 和 Grafana

另开终端，在项目根目录执行：

```bash
cd demo-ops
docker compose up -d
```

访问：

- 示例服务：http://localhost:8000
- Prometheus Targets：http://localhost:9090/targets
- Grafana：http://localhost:3000（本地演示账号 `admin` / `admin`）

Prometheus 的 `demo-service` Target 应显示为 `UP`。Grafana 中打开 **OpsPilot / OpsPilot Demo Service**。

## 3. 制造异常流量

在 `demo-ops` 目录执行：

```bash
../.venv/Scripts/python.exe generate-traffic.py
```

默认会发送正常请求、约 2 秒的慢请求以及 HTTP 500 请求。等待至少两个 Prometheus 抓取周期（约 10 秒）。

## 4. 验证真实指标工具

在项目根目录执行：

```bash
.venv/Scripts/python.exe -c "from agent.tools.agent_tools import fetch_metric_data; print(fetch_metric_data.invoke({'service_name':'demo-service','time_range':'最近15分钟'}))"
```

预期结果包含：

- `data_source: prometheus`
- `request_rate_rps`
- `error_rate_percent`
- `p95_latency_ms`
- 三条固定 PromQL 查询

`demo-service` 查询失败时会返回明确的 Prometheus 错误，不会回退到 Mock 数据。原有的 `order-service` 等演示服务仍使用 Mock 数据。

## 5. 运行 OpsPilot

确保已设置有效且账户状态正常的 `DASHSCOPE_API_KEY`，然后在项目根目录执行：

```bash
.venv/Scripts/streamlit.exe run app.py
```

在页面中提问：

```text
分析 demo-service 最近15分钟的异常情况
```

如果 DashScope 返回 `Arrearage`，表示阿里云百炼账户欠费或余额状态异常；Prometheus、Grafana 和 OpsPilot 工具层仍可独立验证。

## 停止

停止 Prometheus 和 Grafana：

```bash
cd demo-ops
docker compose down
```

在运行 demo-service 的终端按 `Ctrl+C` 停止主机服务。

## 回滚

1. 执行 `docker compose down` 并停止主机上的 demo-service。
2. 删除本次新增的 `demo-ops/`、`integrations/` 和 `tests/`。
3. 从最新的 `backups/*-prometheus-integration/` 按原目录结构恢复文件。
4. 使用该目录的 `manifest.txt` 校验 SHA-256。
