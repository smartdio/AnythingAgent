from app.models.langchain_analyzer.state import AnalyzerState, AnalyzerConfig
from typing import Dict, Any, Callable, Awaitable, Tuple
from langchain_core.messages import SystemMessage, HumanMessage
import logging
from app.models.langchain_analyzer.util import write_debug, init_llm, extract_think_tags

logger = logging.getLogger(__name__)

def _build_analyzer_prompts(
        task_config: Dict[str, Any], 
        agent_config: Dict[str, Any],
        history_context: str,
        user_message: str,
        system_message: str
    ) -> Tuple[str, str]:
        # 获取分析器配置
        role = agent_config.get("role", "信息分析专家")
        goal = agent_config.get("goal", "分析用户消息和系统消息，判断信息是否足够")
        backstory = agent_config.get("backstory", "你是一个专业的信息分析专家，能够深入理解用户需求，判断提供的信息是否足够执行任务。")
        
        # 创建分析任务提示词
        analyze_task_template = task_config.get("description", "")
        write_debug(f"analyze_task_template: {analyze_task_template}")
        analyze_task_description = analyze_task_template.format(
            history_context=history_context,
            user_message=user_message,
            system_message=system_message
        )
        # 构建系统提示词
        analyzer_system_prompt = f"""你是一个{role}。
{backstory}
你的目标是{goal}。
"""
        
        return analyzer_system_prompt, analyze_task_description


def analyzer_node(config: AnalyzerConfig) -> Callable[[AnalyzerState], Awaitable[AnalyzerState]]:
    async def analyzer_lnode_impl(state: AnalyzerState) -> AnalyzerState:
        try:

            analyzer_system_prompt, analyze_task_description = _build_analyzer_prompts(
                task_config=config.tasks.get("analyze_task", {}),
                agent_config=config.agents.get("analyzer_agent", {}),
                history_context=state["history_context"],
                user_message=state["user_message"],
                system_message=state["system_message"]
            )

            write_debug(f"analyzer_system_prompt: {analyzer_system_prompt}")
            write_debug(f"analyze_task_description: {analyze_task_description}")

            llm_config = config.llm


            await config.callback("正在分析...\n")

            llm = init_llm(llm_config)

            system_message = SystemMessage(analyzer_system_prompt)
            user_message = HumanMessage(analyze_task_description)
            write_debug(f"llm: {llm}")
            response = await llm.ainvoke([system_message, user_message])
            cleaned_text, think_content = extract_think_tags(response.content)
            state["analysis_result"] = cleaned_text
            state["message"] = cleaned_text
            await config.callback("分析完成\n")
        except Exception as e:
            write_debug(f"Error in analyzer_node: {str(e)}")
            state["message"] = f"ERROR: {str(e)}"
        return state
    return analyzer_lnode_impl