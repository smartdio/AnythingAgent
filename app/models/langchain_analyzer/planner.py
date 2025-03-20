from typing import Dict, Any, Callable, Awaitable, Tuple
from app.models.langchain_analyzer.state import AnalyzerState, AnalyzerConfig
from langchain_core.messages import SystemMessage, HumanMessage
from app.models.langchain_analyzer.util import init_llm, write_debug

def _build_planner_prompts(
        task_config: Dict[str, Any], 
        agent_config: Dict[str, Any],
        history_context: str,
        user_message: str,
        system_message: str
    ) -> Tuple[str, str]:
        # 获取分析器配置
        role = agent_config.get("role", "任务规划专家")
        goal = agent_config.get("goal", "根据用户需求，分解任务计划")
        backstory = agent_config.get("backstory", "你是一个专业的任务规划专家，能够深入理解用户需求，分解任务计划。")
        
        # 创建分析任务提示词
        task_template = task_config.get("description", "")
        task_description = task_template.format(
            history_context=history_context,
            user_message=user_message,
            system_message=system_message
        )
        
        # 构建系统提示词
        system_prompt = f"""你是一个{role}。
{backstory}
你的目标是{goal}。
"""
        
        return system_prompt, task_description
def planner_node(config: AnalyzerConfig) -> Callable[[AnalyzerState], Awaitable[AnalyzerState]]:
    async def planner_node_impl(state: AnalyzerState) -> AnalyzerState:
        write_debug("planner_node")
        system_prompt, task_description = _build_planner_prompts(
            task_config=config.tasks.get("planning_task", {}),
            agent_config=config.agents.get("planning_agent", {}),
            history_context=state["history_context"],
            user_message=state["user_message"],
            system_message=state["system_message"]
        )
        write_debug(f"system_prompt: {system_prompt}")
        write_debug(f"task_description: {task_description}")
        # 使用分析任务提示词和系统提示词构建分析器提示词
        llm_config = config.llm
        llm_config["streaming"] = True
        await config.callback("正在规划...\n")
        write_debug(f"llm_config: {llm_config}")
        llm = init_llm(llm_config)
        system_message = SystemMessage(system_prompt)
        user_message = HumanMessage(task_description)
        response = await llm.ainvoke([system_message, user_message])
        # 从响应中提取任务列表
        try:
            import json
            import re

            # 获取响应内容
            response_content = response.content if hasattr(response, 'content') else str(response)

            # 使用正则表达式查找JSON数据
            json_match = re.search(r'\[\s*\{.*?\}\s*\]', response_content, re.DOTALL)

            if json_match:
                # 提取匹配到的JSON字符串
                json_str = json_match.group(0)
                # 解析JSON数据
                tasks = json.loads(json_str)
                state["tasks"] = tasks
                for task in tasks:
                    await config.callback(f"- {task['title']}\n")
                await config.callback("\n任务规划完成\n")
            else:
                # 如果没有找到JSON格式的任务列表，记录错误并设置空任务列表
                print(f"无法从响应中提取任务列表JSON: {response_content}")
                await config.callback(f"ERROR: 无法从响应中提取任务列表JSON: {response_content}\n")
        except Exception as e:
            # 处理解析错误
            print(f"解析任务列表时出错: {str(e)}")
            await config.callback(f"ERROR: 解析任务列表时出错: {str(e)}\n")
        return state

    return planner_node_impl