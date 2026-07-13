from langgraph.prebuilt import create_react_agent
from model.factory import chat_model
from agent.tools.agent_tools import (
    rag_summarize,
    get_target_service,
    get_time_range,
    fetch_alert_data,
    fetch_metric_data,
    fetch_log_summary,
    fetch_service_topology,
    fetch_report_data,
    fill_context_for_report,
)
from agent.tools.middleware import (
    build_messages_modifier,
    reset_report_mode,
    AgentCallback,
)
import time


class ReactAgent:
    def __init__(self):
        self.tools = [
            rag_summarize,
            get_target_service,
            get_time_range,
            fetch_alert_data,
            fetch_metric_data,
            fetch_log_summary,
            fetch_service_topology,
            fetch_report_data,
            fill_context_for_report,
        ]

        self.agent = create_react_agent(
            model=chat_model,
            tools=self.tools,
            messages_modifier=build_messages_modifier(),
        )
        self._callback = AgentCallback()

    def _extract_text(self, result) -> str:
        if isinstance(result, dict):
            messages = result.get("messages", [])
            if messages:
                last = messages[-1]
                content = getattr(last, "content", "")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    texts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("text"):
                            texts.append(block["text"])
                        elif isinstance(block, str):
                            texts.append(block)
                    return "".join(texts)
        return str(result)

    def execute_stream(self, query: str):
        reset_report_mode()

        input_dict = {
            "messages": [
                {"role": "user", "content": query},
            ]
        }

        result = self.agent.invoke(
            input_dict,
            config={"callbacks": [self._callback]},
        )

        final_text = self._extract_text(result)

        chunk_size = 20
        for i in range(0, len(final_text), chunk_size):
            yield final_text[i:i + chunk_size]
            time.sleep(0.02)


if __name__ == '__main__':
    agent = ReactAgent()
    for chunk in agent.execute_stream("分析一下 order-service 最近1小时的异常情况"):
        print(chunk, end="", flush=True)
