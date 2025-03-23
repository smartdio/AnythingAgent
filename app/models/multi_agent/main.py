from typing import List, Dict, Any, Optional, Callable, Awaitable, Union, TypedDict, Annotated
import logging
import json
import asyncio
import yaml
import re

from pathlib import Path
from app.models.base import AnythingBaseModel
from app.models.langchain_factory import LangChainLLMFactory
# 导入LangGraph相关模块
from langgraph.graph import StateGraph, END, START
from app.graph.states.config import Config
from app.graph.states.base_state import BaseState
from app.graph.agents.supervisor import supervisor
from app.graph.agents.planner import planner
from app.graph.agents.worker import worker
from app.graph.agents.chatbot import chatbot
logger = logging.getLogger(__name__)

def worker_edge(state:BaseState):
    if state['tasks'] and len(state['tasks']) > len(state['completed_tasks']):
        return "worker"
    else:
        return END

    


class MultiAgentModel(AnythingBaseModel):
    def __init__(self):
        super().__init__()
        self.config_path = Path(__file__).parent / "config.yaml"
        print(f"初始化配置，使用配置文件: {self.config_path}")
        self.cfg = Config(self.config_path)
        # self.config.load_config()
        
 
        
    def _init_workflow(self,callback:Callable[[str], Awaitable[None]]):
        """Initialize the workflow."""

        config = self.cfg.config
        try:
            llm_config = config['llm']['default']
        except Exception as e:
            logger.error(f"初始化配置时出错: {str(e)}")
            return
        llm = LangChainLLMFactory.create_llm(provider=llm_config['provider'], 
                                             model=llm_config['model'], 
                                             temperature=llm_config['temperature'], 
                                             api_key=llm_config['api_key'], 
                                             api_base=llm_config['api_base'])
        workflow = StateGraph(BaseState)
        workflow.add_edge(START, 'supervisor')
        agents = config['agents']
        tasks = config['tasks']
        workflow.add_node('supervisor', supervisor("supervisor",
                                                   agents['supervisor'],
                                                   tasks['supervisor-task'],
                                                   llm,
                                                   ['planner','worker','chat'], 
                                                   callback=callback))
        workflow.add_node('planner', planner("planner",
                                             agents['planner'],
                                             tasks['planner-task'],
                                             llm, 
                                             callback=callback))
        workflow.add_node('worker', worker("worker",
                                           agents['worker'],
                                           tasks['worker-task'],
                                           llm, 
                                           callback=callback))
        workflow.add_node('chat',chatbot("chat",
                                         agents['chat'],
                                         tasks['chat-task'],
                                         llm, 
                                         callback=callback))
        workflow.add_edge('planner', 'worker')
        workflow.add_edge('chat', END)
        workflow.add_conditional_edges('worker', worker_edge )
        graph = workflow.compile()
        return graph

    
    async def on_chat_start(self) -> None:
        pass
        
    async def on_chat_messages(
        self,
        messages: List[Dict[str, str]],
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Optional[str]:
        print("on_chat_messages")
        # 使用 reload 方法检查配置是否需要重新加载
        self.cfg.reload()
        
        state = BaseState()
        state['messages'] = messages
        state['config'] = self.cfg.config  # 传递配置字典，而不是 Config 对象
        state['message'] = messages[-1]['content']
        state['thinking'] = True
        state['next'] = 'supervisor'
        state['tasks'] = []
        state['completed_tasks'] = []  # 初始化 completed_tasks 字段
        state['members'] = ['supervisor','planner','worker','chat']

        workflow = self._init_workflow(callback)
        try:
            result = await workflow.ainvoke(state)
            return result
        except Exception as e:
            logger.error(f"执行工作流时出错: {str(e)}")
            return f"执行工作流时出错: {str(e)}"


    async def on_chat_end(self) -> None:
        pass