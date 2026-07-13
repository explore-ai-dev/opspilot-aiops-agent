"""提示词切换与日志中间件（使用 LangChain 回调实现，兼容 langgraph 0.2.x）"""
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import SystemMessage
from utils.prompt_loader import load_system_prompts, load_report_prompts
from utils.logger_handler import logger


class _ReportMode:
    """跟踪当前是否处于报告模式（模块级单例）"""
    def __init__(self):
        self._flag = False

    def set(self, value: bool):
        self._flag = value

    def get(self) -> bool:
        return self._flag


report_mode = _ReportMode()


class AgentCallback(BaseCallbackHandler):
    """统一回调：工具调用日志 + 模型调用日志 + 报告模式切换"""

    def on_tool_start(self, serialized, input_str, **kwargs):
        tool_name = serialized.get("name", "unknown_tool")
        logger.info(f"[tool monitor] 执行工具：{tool_name}")
        logger.info(f"[tool monitor] 传入参数：{input_str}")
        if tool_name == "fill_context_for_report":
            report_mode.set(True)

    def on_tool_end(self, output, **kwargs):
        pass

    def on_tool_error(self, error, **kwargs):
        logger.error(f"[tool monitor] 工具调用失败，原因：{str(error)}", exc_info=True)

    def on_chat_model_start(self, serialized, messages, **kwargs):
        logger.info(f"[log_before_model] 即将调用模型，带有 {len(messages)} 条消息")
        if messages:
            last = messages[-1]
            content = getattr(last, "content", "")
            if isinstance(content, str):
                logger.debug(f"[log_before_model] {type(last).__name__} | {content.strip()[:100]}")


def build_messages_modifier():
    """构建 messages_modifier 闭包，根据 report_mode 动态选择提示词"""

    def _modifier(messages):
        prompt = load_report_prompts() if report_mode.get() else load_system_prompts()
        filtered = [m for m in messages if not isinstance(m, SystemMessage)]
        return [SystemMessage(content=prompt)] + filtered

    return _modifier


def reset_report_mode():
    """每次新对话前重置报告模式"""
    report_mode.set(False)
