from app.models.langchain_analyzer.state import AnalyzerState, AnalyzerConfig
from typing import Dict, Any, Callable, Awaitable, Tuple
from langchain_core.messages import SystemMessage, HumanMessage
from app.models.langchain_analyzer.util import init_llm, extract_think_tags

def _build_worker_prompts(
        task_config: Dict[str, Any], 
        agent_config: Dict[str, Any],
        history_context: str,
        user_message: str,
        system_message: str,
        task_title: str,
        task_prompt: str
    ) -> Tuple[str, str]:
        # 获取分析器配置
        role = agent_config.get("role", "任务执行专家")
        goal = agent_config.get("goal", "执行具体任务并返回结果")
        backstory = agent_config.get("backstory", "你是一个专业的任务执行专家，能够高效准确地完成各种任务。")
        
        # 创建分析任务提示词
        task_template = task_config.get("description", "")
        task_description = task_template.format(
            history_context=history_context,
            user_message=user_message,
            system_message=system_message,
            task_title=task_title,
            task_prompt=task_prompt
        )
        
        # 构建系统提示词
        system_prompt = f"""你是一个{role}。
{backstory}
你的目标是{goal}。
"""
        
        return system_prompt, task_description
def worker_node(config: AnalyzerConfig) -> Callable[[AnalyzerState], Awaitable[AnalyzerState]]:
    async def worker_node_impl(state: AnalyzerState) -> AnalyzerState:
        """工作节点"""
        # 检查是否有已完成的任务
        if not state["tasks"]:
        # 如果没有已完成的任务，初始化执行结果列表
            state["tasks"] = []
            return state

        current_task_index = len(state["completed_tasks"]) 
        current_task = state["tasks"][current_task_index]
        task_title = current_task.get("title", "未命名任务")
        task_prompt = current_task.get("prompt", "")
        system_prompt, task_description = _build_worker_prompts(
            task_config=config.tasks.get("execution_task", {}),
            agent_config=config.agents.get("worker_agent", {}),
            history_context=state["history_context"],
            user_message=state["user_message"],
            system_message=state["system_message"],
            task_title=task_title,
            task_prompt=task_prompt
        )
        # 使用分析任务提示词和系统提示词构建分析器提示词
        llm_config = config.llm
        llm_config["streaming"] = True
        llm = init_llm(llm_config)
        system_message = SystemMessage(system_prompt)
        user_message = HumanMessage(task_description)
        responses = str()
        thinking =False
        after_think= False
        async for chunk in llm.astream([system_message, user_message]):
            # 检查是否包含思考标签
            responses += chunk.content
            chunk_content = chunk.content
            if "<think>" in chunk_content:
                 thinking = True
            if "</think>" in chunk_content and thinking:
                thinking =False
                after_think=True
                chunk_content = chunk.content.replace("</think>", "")
            if after_think:
                await config.callback(chunk_content)
        await config.callback("\n\n")
        cleaned_text, think_content = extract_think_tags(responses)
        state["completed_tasks"].append(current_task)
        state["message"] = cleaned_text
        return state

    return worker_node_impl