
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.types import Command
from typing import Callable, Awaitable, Optional
from app.graph.states.base_state import BaseState
from typing import TypedDict, List, Dict, Any
from app.graph.agents.utils import HumanMessage, SystemMessage, AIMessage, extract_messages
class Tasks(TypedDict):
    """任务列表。"""
    tasks: List[Dict[str, Any]]

def planner(name:str,agent:Dict[str,str],task:Dict[str,str],llm:BaseChatModel,callback:Callable[[str], Awaitable[None]]):
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
        history, last_user_message, last_system_message = extract_messages(state['messages'])
        agent_description = agent.get('description')
        agent_prompt = agent_description.format(message=last_user_message, prompt=last_system_message)
        task_description = task.get('description')
        task_prompt = task_description.format(message=last_user_message, prompt=last_system_message, history=history)
        system_message = SystemMessage(content=agent_prompt, name=name)
        task_message = AIMessage(content=task_prompt, name="user")
        response = await llm.with_structured_output(Tasks).ainvoke([system_message,task_message])
        tasks_str = ""
        for task_item in response['tasks']:
            tasks_str += f"- {task_item['title']}\n"
        if callback:
            for task_item in response['tasks']:
                await callback(f"- {task_item['title']}\n")
            await callback("\n\n")
        return Command(update={"tasks": response['tasks'],'completed_tasks':[]})
    
    return _planner_impl
    
