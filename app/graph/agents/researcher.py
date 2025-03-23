"""
研究员智能体，负责信息搜索和收集。
"""

import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.types import Command
from langgraph.graph import END
from langgraph.prebuilt import create_react_agent
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from app.graph.agents.types import SUPERVISOR
from app.graph.states.base_state import BaseState
from app.graph.states.config import Config
from app.graph.agents.utils import AIMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


def researcher(name:str,agent:Dict[str,str],task:Dict[str,str],llm:BaseChatModel,tavily:Dict[str,str],callback:Callable[[str], Awaitable[None]]):
    """
    创建研究员智能体，负责信息搜索和收集。
    
    Args:
        name: 智能体名称
        agent: 智能体描述
        task: 任务描述
        llm: 语言模型
        callback: 回调函数
    Returns:
        研究员智能体函数
    """
    # 获取配置
    tavily_api_key = tavily["api_key"]
    print(f"tavily_api_key: {tavily_api_key}")
    tavilySearchAPIWrapper = TavilySearchAPIWrapper(tavily_api_key=tavily_api_key)
    tavily_tool = TavilySearchResults(max_results=5, api_wrapper=tavilySearchAPIWrapper)
    
    async def researcher_impl(state: BaseState) -> Command:
        print("start researcher_agent")
        default_prompt = "You are a researcher. DO NOT do any math."
        agent_description = agent.get('description')
        if agent_description:
            agent_prompt = agent_description.format(message=state['message'])
        else:
            agent_prompt = default_prompt
        task_description = task.get('description')
        if task_description:
            task_prompt = task_description.format(message=state['message'])
        else:
            task_prompt = default_prompt
        _research_agent = create_react_agent(
            llm, tools=[tavily_tool], prompt=agent_prompt
        )
        print(f"researcher_agent prompt: {agent_prompt}")
        print(f"researcher_agent task_prompt: {task_prompt}")
        result = await _research_agent.ainvoke({"messages": [SystemMessage(content=agent_prompt),HumanMessage(content=task_prompt)]})
        print(f"researcher_agent result: {result}")
        if callback:
            await callback(result["messages"][-1].content)
            await callback("\n\n")
        return Command(
            update={
                "messages": [
                    AIMessage(content=result["messages"][-1].content, name=name)
                ]
            },
        )
    
    return researcher_impl 