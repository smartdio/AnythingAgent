from app.models.langchain_analyzer.state import AnalyzerState
from app.models.langchain_analyzer.state import AnalyzerConfig
from typing import Callable, Awaitable

def message_node(config: AnalyzerConfig) -> Callable[[AnalyzerState], Awaitable[AnalyzerState]]:
    async def message_node_impl(state: AnalyzerState) -> AnalyzerState:

        print(f"message_node: {state}")
        if state["thinking"]:
            await config.callback("</think>\n")
            state["thinking"] = False
        if state["message"]:
            await config.callback(state["message"])
        else:
            await config.callback("")
        return state
    return message_node_impl
