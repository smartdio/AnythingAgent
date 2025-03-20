
from app.models.langchain_analyzer.state import AnalyzerState
from langgraph.graph import StateGraph, END
from app.models.langchain_analyzer.util import write_debug

def analyzer_route(state: AnalyzerState) :
    """路由"""

    if "NEED_PLAN" in state["analysis_result"]:
        write_debug(f"NEED_PLAN in state['analysis_result']")
        return "planner"
    else:
        write_debug(f"NEED_PLAN not in state['analysis_result']")
        return "end"


def worker_route(state:AnalyzerState):
    if state["tasks"] and len(state["tasks"]) > len(state["completed_tasks"]):
        write_debug(f"state['tasks'] and len(state['tasks']) > len(state['completed_tasks'])")
        return "executor"
    else:
        write_debug(f"state['tasks'] and len(state['tasks']) <= len(state['completed_tasks'])")
        return "end"


