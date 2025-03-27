"""
主管智能体，负责协调其他智能体的工作。
"""

import logging
from typing import Dict, Any, List, TypedDict, Optional, Callable, Awaitable
from langchain_core.language_models.chat_models import BaseChatModel
from langgraph.types import Command
from app.graph.states.base_state import BaseState
from app.graph.agents.utils import HumanMessage, SystemMessage, AIMessage, extract_messages
logger = logging.getLogger(__name__)



def worker(name:str,agent:Dict[str,str],task:Dict[str,str],llm:BaseChatModel,callback:Callable[[str], Awaitable[None]]):
    """
    创建工作智能体，负责执行任务。
    
    Args:
        name: 智能体名称
        agent: 智能体配置
        task: 任务描述
        llm: 语言模型
        callback: 回调函数
    """
    
    # 构建提示词
    
    async def worker_impl(state: BaseState) -> Command:
        print("start worker_agent")
        history, last_user_message, last_system_message = extract_messages(state['messages'])
        # 从状态中获取任务列表
        tasks = state['tasks']
        completed_tasks = state['completed_tasks']
        
        # 检查是否所有任务都已完成
        if not tasks or all(task.get('id') in [ct.get('id') for ct in completed_tasks] for task in tasks):
            print("All tasks completed")
            return Command(update={})
        
        # 获取第一个未完成的任务
        current_task = None
        for task_item in tasks:
            task_id = task_item.get('id')
            if task_id not in [ct.get('id') for ct in completed_tasks]:
                current_task = task_item
                break
        # 获取所有任务标题，组成一个文本列表
        task_list = ""
        for idx, task_item in enumerate(tasks, 1):
            task_list += f"- {idx}. {task_item.get('title', '未命名任务')}\n"
        # 获取所有已完成任务的标题，组成一个文本列表
        completed_task_list = ""
        for idx, task_item in enumerate(completed_tasks, 1):
            completed_task_list += f"- {idx}. {task_item.get('title', '未命名任务')}\n"
        
        # 获取任务的prompt
        task_prompt = current_task.get('prompt', '')

        messages= state['messages']

        agent_description = agent.get('description')
        sys_message = SystemMessage(content=agent_description.format(members=state['members']))

        task_description = task.get('description')
        task_message = HumanMessage(content=task_description.format(message=last_user_message,
                                                        tasks=task_list,
                                                        completed_tasks=completed_task_list,
                                                        title=current_task.get('title'),
                                                        prompt=task_prompt,members=state['members'],
                                                        history=history), 
                                                        name=name)
        # 复制 messages 给 send_message
        print(f"current_task: {current_task.get('title')}\n")
        print(f"task_message: {task_message}\n")

        if state['thinking']:
            await callback("</think>\n")
        responses = str()
        thinking =False
        after_think= False
        async for chunk in llm.astream([sys_message, task_message]):
            # 检查是否包含思考标签
            responses += chunk.content
            chunk_content = chunk.content
            if "<think>" in chunk_content:
                 thinking = True
            if "</think>" in chunk_content and thinking:
                thinking =False
                after_think=True
                chunk_content = chunk.content.replace("</think>", "")
            if after_think and callback:
                await callback(chunk_content)
        if callback:
            await callback("\n\n")
        print(f"responses: {responses}")
        # 将当前任务标记为已完成并添加到completed_tasks列表中
        current_task['status'] = 'completed'
        completed_tasks.append(current_task)
        
        # 更新状态中的completed_tasks
        return Command(update={
            "completed_tasks": completed_tasks,
            "thinking": False
            })
    
    return worker_impl 