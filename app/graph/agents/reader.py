from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.types import Command
from langchain_core.messages import HumanMessage
from typing import Callable, Awaitable, Optional
from app.graph.agents.types import NEXT
from app.graph.states.base_state import BaseState


def reader(config: Config,name:str,task:str,callback:Callable[[str], Awaitable[None]]):
    """
    创建读取智能体，负责读取任务。
    
    Args:
        config: 配置对象
        name: 智能体名称
        task: 任务名称
        callback: 回调函数
    Returns:
        读取智能体函数
    """
    
    # 获取配置
    llm: Optional[BaseChatModel] = config.llm
    agent_config = config.agents.get(name, {})
    agent_prompt = build_agent_prompt(agent_config)

    async def _reader_impl(state: BaseState) -> Command:
        print("start reader_agent")
        human_message = HumanMessage(content=agent_prompt, name=name)
        task_message = HumanMessage(content=task_prompt, name=task)
        response = await llm.ainvoke([human_message,task_message])
        if callback:
            await callback(response.content)
            await callback("\n\n")
        return Command(goto=NEXT, update={"messages": [response]})
    
    return _reader_impl
