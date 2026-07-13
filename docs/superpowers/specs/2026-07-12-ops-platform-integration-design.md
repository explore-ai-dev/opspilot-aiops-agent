# OpsPilot 本地 Prometheus 演示设计

## 目标

在 Windows 本机用 Docker Compose 搭建可重复演示的最小 AIOps 闭环：示例服务产生真实指标，Prometheus 采集，Grafana 展示，OpsPilot 查询并分析。

## 架构

```text
流量脚本 -> demo-service:8000 -> /metrics -> Prometheus:9090
                                             |-> Grafana:3000
                                             `-> OpsPilot 指标工具
```

OpsPilot 保持在现有 Python 环境运行；示例服务、Prometheus、Grafana 使用 Docker Compose。

## 范围

新增 `demo-ops/`，包含示例服务、Compose、Prometheus、Grafana配置和故障流量脚本。示例服务提供 `/`、`/slow`、`/error`、`/health`、`/metrics`。

修改现有指标工具：当查询 `demo-service` 时，通过 `PROMETHEUS_BASE_URL`（默认 `http://localhost:9090`）查询真实请求量、错误率和延迟；其他工具暂时保持原行为。查询使用预定义 PromQL，不允许模型传入任意查询。

## 备份与回滚

修改前把所有原文件复制到 `backups/<timestamp>-prometheus-integration/`，保留目录结构，并生成包含原路径、SHA-256 和改动原因的 `manifest.txt`。回滚时停止 Compose、删除新增文件、恢复备份并校验哈希。

## 安全与错误处理

只进行只读监控查询，不授予 Agent Docker、主机或修复权限。Prometheus 连接失败、超时、无数据或服务不支持时返回明确说明，不生成虚假指标。查询设置超时。

## 验收

1. Compose 服务正常运行。
2. Prometheus Target 为 UP，Grafana可显示请求量、错误率和延迟。
3. 故障脚本能使错误率与延迟升高。
4. OpsPilot 查询 `demo-service` 最近 15 分钟时使用真实 Prometheus 数据并给出分析。
5. 停止 Prometheus 后工具返回清晰错误。
6. 原文件备份和回滚清单完整。
