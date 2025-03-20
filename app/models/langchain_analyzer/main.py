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
from app.models.langchain_analyzer.util import write_debug
from app.models.langchain_analyzer.state import AnalyzerState
from app.models.langchain_analyzer.state import AnalyzerConfig

logger = logging.getLogger(__name__)


class LangChainAnalyzerModel(AnythingBaseModel):
    def __init__(self):
        # 设置配置文件路径
        self.config_path = Path(__file__).parent / "config.yaml"
        # 设置模型目录
        self.model_dir = Path(__file__).parent
        # 调用父类初始化方法
        super().__init__()
        # 初始化模型特定的属性
        self.context = {}
        self.state = None
        # 加载配置并初始化LLM
        self.config = self.load_config()
        self.analyzer_config = AnalyzerConfig()
        self.analyzer_config.llm = self.config.get("llm", {}).get("default", {})
        self.analyzer_config.tasks = self.config.get("tasks", {})
        self.analyzer_config.agents = self.config.get("agents", {})
        self.analyzer_config.config = self.config
        # 初始化LangGraph工作流
    
    def load_config(self) -> Dict[str, Any]:
        try:
            
            # 读取配置文件
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            return config
        except Exception as e:
            logger.error(f"加载配置时出错: {str(e)}")
            self.llm = None
            return {}
    
    
    def _format_history_context(self, history_messages: List[Dict[str, str]]) -> str:
        history_context = ""
        if history_messages:
            history_context = "历史对话：\n"
            for msg in history_messages:
                role = "用户" if msg["role"] == "user" else "助手"
                history_context += f"{role}: {msg['content']}\n"
            history_context += "\n"
            
        return history_context


    def _init_workflow(self) -> None:
        """Initialize the workflow."""
        # 获取配置数据
        task_templates, agent_config =  self.config["tasks"], self.config["agents"]
        
        if not task_templates or not agent_config:
            logger.error("Configuration is missing, workflow initialization failed")
            self.workflow = None
            return

        try:
            # Create workflow
            workflow = StateGraph(AnalyzerState)  # 使用dict类型而不是AnalyzerState
            write_debug("workflow initialized")

            # Add nodes
            workflow.add_node("start_thinking", start_thinking_node(self.analyzer_config))
            workflow.add_node("analyzer", analyzer_node(self.analyzer_config))
            workflow.add_node("planner", planner_node(self.analyzer_config))
            workflow.add_node("executor", worker_node(self.analyzer_config))
            workflow.add_node("feeback", message_node(self.analyzer_config))
            workflow.add_node("end_thinking", end_thinking_node(self.analyzer_config))


            # Add conditional edges
            workflow.add_conditional_edges("analyzer", analyzer_route, {"end": "feeback", "planner": "planner"})
            workflow.add_conditional_edges("end_thinking", worker_route, {"end": END,"executor": "executor"})
            workflow.add_conditional_edges("executor", worker_route, {"end": END,"executor": "executor"})
            # Add standard edges
            workflow.add_edge("start_thinking", "analyzer")
            workflow.add_edge("planner", "end_thinking")
            # workflow.add_edge("end_thinking", "executor")
            workflow.add_edge("feeback", END)


            # Set entry point
            workflow.set_entry_point("start_thinking")

            # Compile workflow
            self.workflow = workflow.compile()
            logger.debug("Workflow initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize workflow: {e}")
            self.workflow = None

    
    async def on_chat_start(self) -> None:
        logger.info("新的聊天会话已初始化")
        # 初始化状态，确保所有必要的字段都被初始化
        self.state = {
            "messages": [],
            "history_context": "",
            "user_message": "",
            "system_message": "",
            "analysis_result": None,
            "tasks": [],
            "completed_tasks": [],
            "final_result": None,
            "callback": None,
            "config": self.config,
            "task_config": self.config.get("tasks", {}),
            "agent_config": self.config.get("agents", {}),
            "llm": self.config.get("llm", {}).get("default", {}),
            "stream_result": ""
        }
        
        # 打印状态信息，用于调试
        logger.debug(f"State initialized with keys: {list(self.state.keys())}")
        logger.debug(f"Config: {self.config}")
        logger.debug(f"Task config: {self.state['task_config']}")
        logger.debug(f"Agent config: {self.state['agent_config']}")
        logger.debug(f"LLM config: {self.state['llm']}")
        
        
    async def on_chat_messages(
        self,
        messages: List[Dict[str, str]],
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Optional[str]:
        self.analyzer_config.callback = callback
        self._init_workflow()

        try:
            # 检查工作流是否初始化
            if not self.workflow:
                error_msg = "工作流未初始化，请检查配置"
                logger.error(error_msg)
                return error_msg
                
            # 检查消息列表是否为空
            if not messages:
                return "消息列表为空"
            
            # 获取最后一条用户消息
            user_message = messages[-1].get("content", "")
            if not user_message:
                return "用户消息为空"
            
            # 更新状态
            self.state["user_message"] = user_message
            self.state["messages"] = messages
            history_context = self._format_history_context(messages)
            self.state["history_context"] = history_context
            
            # 打印状态信息，用于调试
            logger.debug(f"State before invoking workflow: {list(self.state.keys())}")
            logger.debug(f"User message: {self.state['user_message']}")
            logger.debug(f"History context: {self.state['history_context']}")
            
            write_debug("开始处理流程")
            # 执行工作流
            try:
                # 创建一个新的字典，而不是直接传递self.state
                state = self.state
                await self.workflow.ainvoke(state)
            except Exception as e:
                logger.error(f"执行工作流时出错: {str(e)}")
                return f"执行工作流时出错: {str(e)}"
        except Exception as e:
            logger.error(f"处理消息时出错: {str(e)}")
            return str(e)



    async def on_chat_end(self) -> None:
        logger.info("聊天会话已结束")
        
        # 清理状态
        self.state=None
    
    async def on_context_update(self, context: Dict[str, Any]) -> None:
        # 合并上下文
        self.context.update(context)
        logger.info(f"已更新上下文信息，当前上下文键: {list(self.context.keys())}")
        
    async def on_context_clear(self) -> None:
        self.context = {}
        logger.info("已清除上下文信息")

            