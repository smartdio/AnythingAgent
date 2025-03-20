"""
主管智能体，负责协调其他智能体的工作。
"""

import logging
from typing import Dict, Any, List, TypedDict, Optional, Callable, Awaitable
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.types import Command
from langchain_core.messages import HumanMessage, SystemMessage
from app.graph.agents.types import NEXT, SUPERVISE
from app.graph.states.base_state import BaseState
from app.graph.states.config import Config
from app.graph.agents.utils import (
    build_agent_prompt,
    build_task_prompt
)

logger = logging.getLogger(__name__)



def worker(agent:str,role:str,task:str,llm:BaseChatModel,callback:Callable[[str], Awaitable[None]]):
    """
    创建工作智能体，负责执行任务。
    
    Args:
        agent: 智能体名称
        role: 角色定义
        task: 任务描述
        llm: 语言模型
        callback: 回调函数
    """
    
    # 构建提示词
    
    async def worker_impl(state: BaseState) -> Command:
        print("start worker_agent")
        # 从状态中获取任务列表
        tasks = state.tasks
        completed_tasks = state.get('completed_tasks', [])
        
        # 检查是否所有任务都已完成
        if not tasks or all(task.get('id') in [ct.get('id') for ct in completed_tasks] for task in tasks):
            print("All tasks completed")
            return Command(goto=SUPERVISE, update={})
        
        # 获取第一个未完成的任务
        current_task = None
        for task in tasks:
            task_id = task.get('id')
            if task_id not in [ct.get('id') for ct in completed_tasks]:
                current_task = task
                break
        
        # 获取任务的prompt
        task_prompt = current_task.get('prompt', '')
        print(f"Working on task: {current_task.get('title')}")


        sys_message = SystemMessage(content=role.format(members=state.members))
        task_message = HumanMessage(content=task.format(message=state.message,title=current_task.get('title'),prompt=task_prompt,members=state.members), name=agent)
        response = await llm.stream([sys_message,task_message])
        result = ''
        for chunk in response:
            result += chunk.content
            if callback:
                await callback(chunk.content)
        return Command(goto=NEXT, update={"messages": [
            HumanMessage(content=result, name=agent)
        ]})
    
    return worker_impl 