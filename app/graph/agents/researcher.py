"""
研究员智能体，负责信息搜索和收集。
"""

import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langgraph.graph import END
from langgraph.prebuilt import create_react_agent
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.utilities.tavily_search import TavilySearchAPIWrapper
from app.graph.agents.types import SUPERVISOR
from app.graph.states.base_state import BaseState
from app.graph.states.config import Config

logger = logging.getLogger(__name__)


def researcher(config: Config, agent:str,task:str,callback:Callable[[str], Awaitable[None]]):
    """
    创建研究员智能体，负责信息搜索和收集。
    
    Args:
        config: 配置对象
        agent: 智能体名称
        task: 任务名称
        callback: 回调函数
    Returns:
        研究员智能体函数
    """
    # 获取配置
    llm: Optional[BaseChatModel] = config.llm
    task_config = config.tasks.get(task, {})
    agent_config = config.agents.get(agent, {})
    
    config_dict = config.config

    tavily_api_key = config_dict["tavily"]["api_key"]
    print(f"tavily_api_key: {tavily_api_key}")
    tavilySearchAPIWrapper = TavilySearchAPIWrapper(tavily_api_key=tavily_api_key)
    tavily_tool = TavilySearchResults(max_results=5, api_wrapper=tavilySearchAPIWrapper)
    _research_agent = create_react_agent(
        llm, tools=[tavily_tool], prompt="You are a researcher. DO NOT do any math."
    )
    
    async def researcher_impl(state: BaseState) -> Command:
        print("start researcher_agent")
        result = await _research_agent.ainvoke(state)
        print(f"researcher_agent result: {result}")
        if callback:
            await callback(result["messages"][-1].content)
            await callback("\n\n")
        return Command(
            update={
                "messages": [
                    HumanMessage(content=result["messages"][-1].content, name=agent)
                ]
            },
            goto=SUPERVISOR,
        )
    
    return researcher_impl 