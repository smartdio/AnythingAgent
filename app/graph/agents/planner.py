
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.types import Command
from langchain_core.messages import HumanMessage, SystemMessage
from typing import Callable, Awaitable, Optional
from app.graph.agents.types import NEXT
from app.graph.states.base_state import BaseState
from app.graph.states.config import Config
from app.graph.agents.utils import (
    extract_json_from_text
)


def planner(agent:str,role:str,task:str,llm:BaseChatModel,callback:Callable[[str], Awaitable[None]]):
    """
    创建规划智能体，负责规划任务。
    
    Args:
        agent: 智能体名称
        role: 角色定义
        task: 任务描述
        llm: 语言模型
        callback: 回调函数
    Returns:
        规划智能体函数
    """
        
    async def _planner_impl(state: BaseState) -> Command:
        print("start planner_agent")
        agent_prompt = role.format(members=state.members)
        task_prompt = task.format(message=state.message,members=state.members)
        system_message = SystemMessage(content=agent_prompt, name=agent)
        task_message = HumanMessage(content=task_prompt, name="user")
        response = await llm.ainvoke([system_message,task_message])
        json_content = response.content
        json_obj = extract_json_from_text(json_content)

        if callback:
            await callback(json_content)
            await callback("\n\n")
        return Command(goto=NEXT, update={"tasks": [json_obj],'completed_tasks':[],'next':NEXT})
    
    return _planner_impl
    
