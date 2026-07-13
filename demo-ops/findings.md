# Findings

## Incident evidence
- 用户界面显示：`InternalServerError: Error code: 503`。
- 上游错误码：`system_cpu_overloaded`。
- 报告值：CPU `93.4%`，阈值 `90%`。
- 当前可见症状：模型/代理调用异常未经恢复处理，直接作为系统运行错误展示。

## Code findings
- 待调查。
