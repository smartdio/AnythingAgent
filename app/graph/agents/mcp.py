from typing import Dict, Any, List, TypedDict, Optional, Callable, Awaitable
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.types import Command
from app.graph.states.base_state import BaseState
from app.graph.agents.utils import HumanMessage, SystemMessage
def mcp(name:str,agent:Dict[str,str],task:Dict[str,str],llm:BaseChatModel,mcp:Dict[str,Any],callback:Callable[[str], Awaitable[None]]):
    """
    MCP agent
    """

    async def mcp_impl(state: BaseState) -> Command:
        print(f"start {name} \n")
        # 构建提示词
        agent_description = agent.get('description')
        agent_prompt = agent_description.format(members=members,message=state['message'])
        system_message = SystemMessage(content=agent_prompt, name=name)
        user_message = HumanMessage(content=state['message'], name="user")

        pass
    return mcp_impl