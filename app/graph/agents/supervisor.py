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
from app.graph.agents.utils import HumanMessage, SystemMessage, extract_messages
from typing import Literal

logger = logging.getLogger(__name__)



def supervisor(name:str,agent:Dict[str,str],task:Dict[str,str],llm:BaseChatModel,members:List[str],callback:Callable[[str], Awaitable[None]]):
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
    class Router(TypedDict):
        """决定下一个执行的Agent。"""
        next: str  # 简化为 str 类型

    # 获取所有可用的Agent
    options = members + ["FINISH"]
    
    
    async def supervisor_impl(state: BaseState) -> Command:
        print(f"start {name} \n")
        # 构建提示词
        messages = state['messages']
        last_system_message = messages[0].content
        agent_description = agent.get('description')
        agent_prompt = agent_description.format(members=members, prompt=last_system_message)
        system_message = SystemMessage(content=agent_prompt, name=name)
        
        # 构建消息数组，将system_message和用户消息合并
        new_messages = [system_message] + messages

        response= await llm.with_structured_output(Router).ainvoke(new_messages)
        goto = response["next"]
        if goto not in options:
            goto = END

        if callback:
            if goto != FINISH:
                await callback("<think>\n")
        if goto == FINISH:
            goto = END

        return Command(goto=goto, update={"next": goto, "thinking": True})
    
    return supervisor_impl 