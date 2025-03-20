"""
编码员智能体，负责编写和执行代码。
"""

import logging
from typing import Dict, Any, List, Optional, Callable, Awaitable, Annotated
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langgraph.graph import END
from langgraph.prebuilt import create_react_agent
from app.graph.agents.types import NEXT
from app.graph.states.base_state import BaseState
from app.graph.states.config import Config
from app.graph.agents.utils import (
    build_agent_prompt,
)

logger = logging.getLogger(__name__)


from typing import Annotated
from langchain_core.tools import tool
from langchain_experimental.utilities import PythonREPL

@tool
def python_repl_tool(
    code: Annotated[str, "The python code to execute to generate your chart."],
):
    """Use this to execute python code and do math. If you want to see the output of a value,
    you should print it out with `print(...)`. This is visible to the user."""
    try:
        result = repl.run(code)
    except BaseException as e:
        return f"Failed to execute. Error: {repr(e)}"
    result_str = f"Successfully executed:\n```python\n{code}\n```\nStdout: {result}"
    return result_str




def pycoder(config: Config,name:str,callback:Callable[[str], Awaitable[None]]):
    # 获取配置
    llm: Optional[BaseChatModel] = config.llm
    agent_config = config.agents.get(name, {})
    agent_prompt = build_agent_prompt(agent_config)
    
    # 创建ReAct Agent
    try:
        _code_agent = create_react_agent(llm, tools=[python_repl_tool])
    except Exception as e:
        logger.error(f"创建ReAct Agent时出错: {str(e)}")
        
    
    async def coder_impl(state: BaseState) -> Command:
        print("start coder_agent")
        result = await _code_agent.ainvoke(state)
        print("coder_agent result: {result}")
        if callback:
            await callback(result["messages"][-1].content)
            await callback("\n\n")
        return Command(
            update={
                "messages": [
                    HumanMessage(content=result["messages"][-1].content, name=name)
                ],
                'next':NEXT
            },
            goto=NEXT,
        )
    
    return coder_impl 