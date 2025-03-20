from app.models.langchain_analyzer.state import AnalyzerState
from app.models.langchain_analyzer.state import AnalyzerConfig
from typing import Callable, Awaitable
def start_thinking_node(config: AnalyzerConfig) -> Callable[[AnalyzerState], Awaitable[AnalyzerState]]:
    async def start_thinking_node_impl(state: AnalyzerState) -> AnalyzerState:
        await config.callback("<think>\n ...")
        state["thinking"] = True
        return state
    return start_thinking_node_impl


def end_thinking_node(config: AnalyzerConfig) -> Callable[[AnalyzerState], Awaitable[AnalyzerState]]:
    async def end_thinking_node_impl(state: AnalyzerState) -> AnalyzerState:
        await config.callback("</think>\n")
        state["thinking"] = False
        return state
    return end_thinking_node_impl

