"""
主管智能体，负责协调其他智能体的工作。
"""

import logging
from typing import Dict, Any, List, TypedDict, Optional, Callable, Awaitable
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.types import Command
from langgraph.graph import END
from app.graph.agents.types import FINISH
from app.graph.states.base_state import BaseState
from app.graph.states.config import Config
from app.graph.agents.utils import (
    build_agent_prompt,
    build_task_prompt,
    build_messages,
    stream_callback
)

logger = logging.getLogger(__name__)


class Router(TypedDict):
    """决定下一个执行的Agent。"""
    next: str


def supervisor(agent:str,role:str,task:str,llm:BaseChatModel,members:List[str],callback:Callable[[str], Awaitable[None]]):
    """
    创建主管智能体，负责协调其他智能体的工作。
    
    Args:
        agent: 智能体名称
        role: 角色定义
        task: 任务描述
        llm: 语言模型
        members: 可用的Agent列表
    Returns:
        主管智能体函数
    """
    # 获取所有可用的Agent
    options = members + ["FINISH"]
    
    
    async def supervisor_impl(state: BaseState) -> Command:
        print(f"start {agent} \n")
        # 构建提示词
        agent_prompt = role.format(members=members,message=state.message)
        response = await llm.with_structured_output(Router).ainvoke([agent_prompt])
        if callback:
            await callback(response["next"])
            await callback("\n\n")
        print(f"response: {response} \n")
        goto = response["next"]
        if goto == FINISH:
            goto = END
        return Command(goto=goto, update={"next": goto})
    
    return supervisor_impl 