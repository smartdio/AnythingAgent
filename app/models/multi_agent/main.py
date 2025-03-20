from typing import List, Dict, Any, Optional, Callable, Awaitable, Union, TypedDict, Annotated
import logging
import json
import asyncio
import yaml
import re
from pathlib import Path
from datetime import datetime

from app.models.base import AnythingBaseModel
from app.models.langchain_factory import LangChainLLMFactory
from app.models.langchain_analyzer.state import AnalyzerState, AnalyzerConfig
from app.models.langchain_analyzer.route import analyzer_route, worker_route
from app.models.langchain_analyzer.analyzer import analyzer_node
from app.models.langchain_analyzer.planner import planner_node
from app.models.langchain_analyzer.worker import worker_node
from app.models.langchain_analyzer.think import start_thinking_node, end_thinking_node
from app.models.langchain_analyzer.message import message_node
# 导入LangGraph相关模块
from langgraph.graph import StateGraph, END, START
from langchain.chat_models import init_chat_model
from app.graph.states.config import Config
from app.graph.states.base_state import BaseState
from app.graph.agents.supervisor import supervisor
from app.graph.agents.planner import planner
from app.graph.agents.worker import worker
from app.graph.agents.chatbot import chatbot
from langgraph.types import Command
logger = logging.getLogger(__name__)

def worker_edge(state:Command)->Command:

    
    return state['planner']


class MultiAgentModel(AnythingBaseModel):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.config.load_config()
        
 
        
        # 初始化LangGraph工作流
    
    
    


    def _init_workflow(self,callback:Callable[[str], Awaitable[None]]) -> None:
        """Initialize the workflow."""
        llm_config = self.config.config['llm']['default']
        llm = LangChainLLMFactory.create_llm(provider=llm_config['provider'], 
                                             model=llm_config['model'], 
                                             temperature=llm_config['temperature'], 
                                             api_key=llm_config['api_key'], 
                                             api_base=llm_config['api_base'])
        workflow = StateGraph(BaseState)
        workflow.add_edge(START, 'supervisor')
        workflow.add_node('supervisor', supervisor("supervisor","supervisor-task",llm, self.config,  ['planner', 'worker'],callback=callback))
        workflow.add_node('planner', planner("planner","planner-task",llm, self.config,callback=callback))
        workflow.add_node('worker', worker("worker","worker-task",llm, self.config,callback=callback))
        workflow.add_node('chat',chatbot("chat",llm, self.config,callback=callback))
        



    
    async def on_chat_start(self) -> None:
        
        
    async def on_chat_messages(
        self,
        messages: List[Dict[str, str]],
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Optional[str]:
        print("on_chat_messages")



    async def on_chat_end(self) -> None: