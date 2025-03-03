from typing import List, Dict, Any, Optional, Callable, Awaitable, Union, TypedDict, Annotated
import logging
import json
import asyncio
import yaml
import re
from pathlib import Path
from datetime import datetime

from app.models.base import AnythingBaseModel
from app.models.langchain_manager import LangChainLLMManager
from app.models.langchain_analyzer.templates import (
    DEFAULT_ANALYZE_TASK_TEMPLATE,
    DEFAULT_PLANNING_TASK_TEMPLATE,
    DEFAULT_EXECUTION_TASK_TEMPLATE,
    DEFAULT_ANALYZER_SYSTEM_PROMPT,
    DEFAULT_PLANNER_SYSTEM_PROMPT,
    DEFAULT_WORKER_SYSTEM_PROMPT
)

# 导入LangGraph相关模块
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

logger = logging.getLogger(__name__)

# 定义状态类型
class AnalyzerState(TypedDict):
    """分析器状态类型"""
    messages: List[Dict[str, str]]  # 消息历史
    history_context: str  # 格式化的历史上下文
    user_message: str  # 当前用户消息
    system_message: str  # 系统消息
    analysis_result: Optional[str]  # 分析结果
    planning_result: Optional[str]  # 规划结果
    tasks: Dict[str, Dict[str, str]]  # 任务列表
    execution_results: List[str]  # 执行结果
    final_result: Optional[str]  # 最终结果
    callback: Optional[Callable[[str], Awaitable[None]]]  # 回调函数
    config: Dict[str, Any]  # 配置信息
    task_templates: Dict[str, Any]  # 任务模板
    agent_config: Dict[str, Any]  # Agent配置

class LangChainAnalyzerModel(AnythingBaseModel):
    """
    基于 LangGraph 的深度分析模型
    
    该模型使用 LangGraph 进行深度分析，支持多阶段任务处理（分析、规划、执行）和上下文管理。
    完全对标原 LangChainAnalyzerModel 的功能，但使用 LangGraph 实现。
    """
    
    def __init__(self):
        # 设置配置文件路径
        self.config_path = Path(__file__).parent / "config.yaml"
        # 初始化配置文件修改时间
        self._config_mtime = 0
        
        # 设置模型目录
        self.model_dir = Path(__file__).parent
        
        # 调用父类初始化方法
        super().__init__()
        
        # 加载模型特定配置
        self.config = self._load_config()
        
        # 初始化 LangChainLLMManager
        self.llm_manager = LangChainLLMManager(
            model_dir=self.model_dir,
            config=self.config
        )
        
        # 初始化模型特定的属性
        self.context = {}
        self.tasks = []
        self.analysis_results = {}
        
        # 从配置中加载系统提示词
        self.system_prompt = self.config.get("prompts", {}).get(
            "system", "你是一个专业的分析助手，擅长深度分析和解决复杂问题。"
        )
        
        # 如果配置文件中有LLM配置，覆盖系统默认配置
        self._override_llm_config()
        
        # 初始化LangGraph工作流
        self._init_workflow()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        if not self.config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_path}")
            return {}
        
        try:
            # 更新配置文件修改时间
            self._config_mtime = self.config_path.stat().st_mtime
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"已加载配置文件: {self.config_path}")
                
                # 打印配置文件的主要部分
                logger.info(f"配置文件包含以下主要部分: {list(config.keys())}")
                
                # 检查是否包含任务模板
                if "task_templates" in config:
                    task_templates = config["task_templates"]
                    logger.info(f"配置文件包含任务模板: {list(task_templates.keys())}")
                    
                    # 检查每个任务模板是否包含description
                    for key, value in task_templates.items():
                        if isinstance(value, dict) and "description" in value:
                            logger.info(f"任务模板 '{key}' 包含description，长度: {len(value['description'])}")
                        else:
                            logger.warning(f"任务模板 '{key}' 不包含description或格式不正确")
                else:
                    logger.warning("配置文件不包含任务模板部分")
                
                return config
        except Exception as e:
            logger.error(f"加载配置文件时出错: {str(e)}")
            return {}
    
    def _override_llm_config(self) -> None:
        """
        从config.yaml覆盖系统默认的LLM配置
        """
        try:
            # 获取配置文件中的LLM配置
            llm_config = self.config.get("llm", {}).get("default", {})
            if not llm_config:
                logger.info("配置文件中没有LLM配置，使用系统默认配置")
                return
                
            # 重新初始化 LangChainLLMManager
            self.llm_manager = LangChainLLMManager(
                model_dir=self.model_dir,
                config=self.config
            )
            
            logger.info(f"已从配置文件加载LLM配置")
            
        except Exception as e:
            logger.error(f"覆盖LLM配置时出错: {str(e)}")
    
    def set_llm(self, llm_name: str) -> bool:
        """
        设置使用的LLM，从配置文件的alternatives中选择
        
        Args:
            llm_name: LLM配置名称
            
        Returns:
            是否成功设置
        """
        try:
            # 如果是default，使用默认配置
            if llm_name == "default":
                # 重新初始化 LangChainLLMManager
                self.llm_manager = LangChainLLMManager(
                    model_dir=self.model_dir,
                    config=self.config
                )
                logger.info(f"已切换到默认LLM配置")
                return True
            
            # 使用 LangChainLLMManager 的 set_llm 方法
            result = self.llm_manager.set_llm(llm_name)
            if result:
                logger.info(f"已切换到 {llm_name} LLM配置")
            else:
                logger.warning(f"切换到 {llm_name} LLM配置失败")
            return result
            
        except Exception as e:
            logger.error(f"设置LLM配置时出错: {str(e)}")
            return False
    
    def _reload_config(self) -> None:
        """
        重新加载配置文件，确保实时更新
        """
        if not self.config_path.exists():
            logger.warning(f"配置文件不存在: {self.config_path}")
            return
            
        # 检查文件修改时间
        current_mtime = self.config_path.stat().st_mtime
        
        # 如果文件修改时间没有变化，则不重新加载
        if current_mtime <= self._config_mtime:
            logger.debug("配置文件未修改，跳过重新加载")
            return
            
        # 记录旧配置的哈希值，用于比较是否有变化
        old_config_hash = hash(json.dumps(self.config, sort_keys=True)) if self.config else None
        
        # 重新加载配置
        self.config = self._load_config()
        
        # 计算新配置的哈希值
        new_config_hash = hash(json.dumps(self.config, sort_keys=True)) if self.config else None
        
        # 检查配置是否有变化
        if old_config_hash != new_config_hash:
            logger.info("检测到配置文件变化，已重新加载")
            self._write_debug("=== 配置文件已重新加载 ===")
            self._write_debug(f"配置文件修改时间: {datetime.fromtimestamp(current_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 如果配置文件中有LLM配置，覆盖系统默认配置
            self._override_llm_config()
        else:
            logger.debug("配置文件内容未发生变化，但文件修改时间已更新")
    
    async def on_chat_messages(
        self,
        messages: List[Dict[str, str]],
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Optional[str]:
        """
        处理聊天消息
        
        Args:
            messages: 消息列表，每个消息是包含角色和内容的字典
            callback: 用于流式输出的异步回调函数
            
        Returns:
            如果是非流式模式（callback=None），返回完整的响应字符串
            如果是流式模式（callback不为None），通过callback发送内容，返回None
        """
        if not self.llm_manager:
            response = "LLM配置未初始化，无法使用LangChain Analyzer模型。"
            await self._safe_callback(callback, response)
            return response
            
        # 重新加载配置（如果配置文件已更改）
        self._reload_config()
        
        # 提取最后一条用户消息
        user_message = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        
        # 提取最后一条系统消息（如果有）
        system_message = next((m["content"] for m in reversed(messages) if m["role"] == "system"), "")
        
        # 获取历史消息（最近10条，不包括最后一条用户消息）
        history_messages = [m for m in messages[:-1]][-10:]
        
        # 格式化历史上下文
        history_context = self._format_history_context(history_messages)
        
        # 获取配置数据
        task_templates, agent_config = self._get_config_data()
        
        # 记录基本信息
        logger.info(f"处理新消息: {user_message[:50]}..." if len(user_message) > 50 else f"处理新消息: {user_message}")
        logger.info(f"历史消息数量: {len(history_messages)}")
        
        try:
            # 初始化状态
            initial_state = {
                "messages": messages,
                "history_context": history_context,
                "user_message": user_message,
                "system_message": system_message,
                "task_templates": task_templates,
                "agent_config": agent_config,
                "callback": callback,
                "analysis_result": "",
                "planning_result": "",
                "tasks": {},
                "execution_results": [],
                "final_result": ""
            }
            
            # 确保工作流已初始化
            if not self.workflow:
                self._init_workflow()
                if not self.workflow:
                    error_message = "LangGraph工作流初始化失败"
                    logger.error(error_message)
                    await self._safe_callback(callback, error_message)
                    return error_message
            
            # 执行工作流
            logger.info("开始执行LangGraph工作流")
            
            # 如果是流式模式，结果会通过callback发送
            if callback:
                # 执行工作流
                await self.workflow.ainvoke(initial_state)
                return None
            else:
                # 非流式模式，返回最终结果
                final_state = await self.workflow.ainvoke(initial_state)
                return final_state.get("final_result", "处理完成，但没有返回结果")
                
        except Exception as e:
            error_message = f"处理消息时出错: {str(e)}"
            logger.error(error_message)
            await self._safe_callback(callback, error_message)
            return error_message
            
    def _format_history_context(self, history_messages: List[Dict[str, str]]) -> str:
        """
        格式化历史消息为上下文字符串
        
        Args:
            history_messages: 历史消息列表
            
        Returns:
            str: 格式化后的历史上下文
        """
        history_context = ""
        if history_messages:
            history_context = "历史对话：\n"
            for msg in history_messages:
                role = "用户" if msg["role"] == "user" else "助手"
                history_context += f"{role}: {msg['content']}\n"
            history_context += "\n"
            
        return history_context

    def _get_config_data(self) -> tuple:
        """
        获取配置数据，包括任务模板和Agent配置
        
        Returns:
            tuple: (task_templates, agent_config)
        """
        # 确保 self.config 不为 None
        if not self.config:
            logger.warning("配置为空，使用默认配置")
            self.config = {}
            
        # 从配置文件获取Agent和Task配置
        agent_config = self.config.get("agent", {})
        task_templates = self.config.get("task_templates", {})
        
        # 打印获取到的任务模板，用于调试
        logger.info(f"从配置文件获取的任务模板: {json.dumps(list(task_templates.keys()), ensure_ascii=False)}")
        if task_templates:
            for key in task_templates.keys():
                logger.info(f"任务模板 '{key}' 是否包含description: {bool(task_templates.get(key, {}).get('description', ''))}")
                if task_templates.get(key, {}).get('description', ''):
                    template_desc = task_templates.get(key, {}).get('description', '')
                    logger.info(f"任务模板 '{key}' 的description长度: {len(template_desc)}")
                    logger.info(f"任务模板 '{key}' 的description前100个字符: {template_desc[:100]}...")
        else:
            logger.warning("配置文件中没有找到任何任务模板")
            
        return task_templates, agent_config

    async def _safe_callback(self, callback: Optional[Callable[[str], Awaitable[None]]], content: str) -> None:
        """
        安全地调用回调函数
        
        Args:
            callback: 回调函数
            content: 要发送的内容
        """
        if callback:
            try:
                await callback(content)
            except Exception as e:
                logger.error(f"调用回调函数时出错: {str(e)}")
                
    def _write_debug(self, content: str) -> None:
        """
        写入调试信息到文件
        
        Args:
            content: 调试内容
        """
        try:
            debug_file = Path(__file__).parent / "debug.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(debug_file, "a", encoding="utf-8") as f:
                f.write(f"\n\n--- {timestamp} ---\n{content}\n")
        except Exception as e:
            logger.error(f"写入调试信息时出错: {str(e)}")
    
    async def _process_with_langchain(
        self,
        user_message: str,
        system_message: str,
        history_messages: List[Dict[str, str]],
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> str:
        """
        使用LangChain处理消息
        
        Args:
            user_message: 用户消息
            system_message: 系统消息
            history_messages: 历史消息列表
            callback: 用于流式输出的异步回调函数
            
        Returns:
            str: 处理结果
        """
        try:
            # 获取配置数据
            task_templates, agent_config = self._get_config_data()
            
            # 格式化历史上下文
            history_context = self._format_history_context(history_messages)
            
            # 记录基本信息
            logger.info(f"处理新消息: {user_message[:50]}..." if len(user_message) > 50 else f"处理新消息: {user_message}")
            logger.info(f"历史消息数量: {len(history_messages)}")
            
            # 1. 分析阶段
            logger.info("开始分析阶段")
            await self._safe_callback(callback, "<think>正在分析您的消息...\n")
            
            # 构建分析阶段提示词
            analyzer_system_prompt, analyze_task_description = self._build_analyzer_prompts(
                task_templates, 
                agent_config, 
                history_context, 
                user_message, 
                system_message
            )
            
            # 调用LangChain进行分析
            analysis_result = await self.llm_manager.call_llm(
                system_prompt=analyzer_system_prompt,
                user_prompt=analyze_task_description
            )
            
            # 打印LLM响应结果
            logger.info(f"分析阶段 - LLM响应结果: {analysis_result[:200]}..." if len(analysis_result) > 200 else f"分析阶段 - LLM响应结果: {analysis_result}")
            
            # 如果分析结果包含'NEXT-AGENT'，则继续执行后续步骤
            if 'NEXT-AGENT' in analysis_result:
                logger.info("分析结果包含'NEXT-AGENT'，继续执行后续步骤")
            else:
                await self._safe_callback(callback, f"</think>{analysis_result}\n")
                return analysis_result

            logger.info(f"分析阶段结果: {analysis_result}")
            
            # 2. 判断分析结果 - 无论结果如何，都继续执行后续步骤
            await self._safe_callback(callback, "正在规划任务...\n")
            
            # 3. 规划阶段
            logger.info("开始规划阶段")
            
            # 构建规划阶段提示词
            planner_system_prompt, planning_task_description = self._build_planner_prompts(
                task_templates, 
                agent_config, 
                history_context, 
                user_message
            )
            
            # 调用LangChain进行规划
            planning_result = await self.llm_manager.call_llm(
                system_prompt=planner_system_prompt,
                user_prompt=planning_task_description
            )
            
            # 打印LLM响应结果
            logger.info(f"规划阶段 - LLM响应结果: {planning_result[:200]}..." if len(planning_result) > 200 else f"规划阶段 - LLM响应结果: {planning_result}")
            
            # 4. 解析任务计划 - 规划阶段完成后直接进入执行阶段，不需要额外判断
            try:
                # 解析任务数据
                valid_tasks = self._parse_tasks_data(planning_result, user_message)
                
                # 5. 执行阶段
                logger.info("开始执行阶段")
                
                # 执行任务
                results = await self._execute_tasks(valid_tasks, task_templates, agent_config, history_context, callback)
                
                # 7. 整合所有结果
                if callback:
                    # 流式模式下已经输出了结果，只需要添加结束标记
                    return None
                else:
                    # 非流式模式下返回完整结果
                    final_result = "# 任务执行结果\n\n" + "\n\n### ".join(results)
                    logger.info(f"所有任务执行完成，总结果长度: {len(final_result)}")
                    return final_result
                
            except Exception as e:
                error_message = f"解析任务计划时出错: {str(e)}\n原始计划内容:\n{planning_result}"
                logger.error(error_message)
                await self._safe_callback(callback, error_message)
                return error_message
                
        except Exception as e:
            error_message = f"处理消息时出错: {str(e)}"
            logger.error(error_message)
            await self._safe_callback(callback, error_message)
            return error_message

    def _build_analyzer_prompts(
        self, 
        task_templates: Dict[str, Any], 
        agent_config: Dict[str, Any],
        history_context: str,
        user_message: str,
        system_message: str
    ) -> tuple:
        """
        构建分析阶段提示词
        
        Args:
            task_templates: 任务模板配置
            agent_config: Agent配置
            history_context: 历史对话上下文
            user_message: 用户消息
            system_message: 系统消息
            
        Returns:
            tuple: (系统提示词, 用户提示词)
        """
        # 获取分析任务模板
        analyze_task_template = ""
        if task_templates and "analyze_task_template" in task_templates and task_templates["analyze_task_template"]:
            analyze_task_template = task_templates["analyze_task_template"]
            logger.info(f"使用配置文件中的分析任务模板，长度: {len(analyze_task_template)}")
        else:
            analyze_task_template = DEFAULT_ANALYZE_TASK_TEMPLATE
            logger.info("使用默认分析任务模板")
        
        # 获取分析系统提示词
        analyzer_system_prompt = ""
        if agent_config and "analyzer_system_prompt" in agent_config and agent_config["analyzer_system_prompt"]:
            analyzer_system_prompt = agent_config["analyzer_system_prompt"]
        else:
            analyzer_system_prompt = DEFAULT_ANALYZER_SYSTEM_PROMPT
        
        # 替换模板中的变量
        analyze_task_description = analyze_task_template.format(
            history_context=history_context,
            user_message=user_message,
            system_message=system_message
        )
        
        logger.info(f"分析阶段 - 系统提示词: {analyzer_system_prompt}")
        logger.info(f"分析阶段 - 用户提示词: {analyze_task_description[:200]}..." if len(analyze_task_description) > 200 else f"分析阶段 - 用户提示词: {analyze_task_description}")
        
        return analyzer_system_prompt, analyze_task_description

    def _build_planner_prompts(
        self, 
        task_templates: Dict[str, Any], 
        agent_config: Dict[str, Any],
        history_context: str,
        user_message: str
    ) -> tuple:
        """
        构建规划阶段提示词
        
        Args:
            task_templates: 任务模板配置
            agent_config: Agent配置
            history_context: 历史对话上下文
            user_message: 用户消息
            
        Returns:
            tuple: (系统提示词, 用户提示词)
        """
        # 获取规划任务模板
        planning_task_template = ""
        if task_templates and "planning_task_template" in task_templates and task_templates["planning_task_template"]:
            planning_task_template = task_templates["planning_task_template"]
            logger.info(f"使用配置文件中的规划任务模板，长度: {len(planning_task_template)}")
        else:
            planning_task_template = DEFAULT_PLANNING_TASK_TEMPLATE
            logger.info("使用默认规划任务模板")
        
        # 获取规划系统提示词
        planner_system_prompt = ""
        if agent_config and "planner_system_prompt" in agent_config and agent_config["planner_system_prompt"]:
            planner_system_prompt = agent_config["planner_system_prompt"]
        else:
            planner_system_prompt = DEFAULT_PLANNER_SYSTEM_PROMPT
        
        # 替换模板中的变量
        planning_task_description = planning_task_template.format(
            history_context=history_context,
            user_message=user_message
        )
        
        logger.info(f"规划阶段 - 系统提示词: {planner_system_prompt}")
        logger.info(f"规划阶段 - 用户提示词: {planning_task_description[:200]}..." if len(planning_task_description) > 200 else f"规划阶段 - 用户提示词: {planning_task_description}")
        
        return planner_system_prompt, planning_task_description

    def _parse_tasks_data(self, planning_result: str, user_message: str) -> Dict[str, Dict[str, str]]:
        """
        解析任务计划数据
        
        Args:
            planning_result: 规划阶段的结果
            user_message: 用户消息，用于创建默认任务
            
        Returns:
            Dict[str, Dict[str, str]]: 解析后的任务数据
        """
        # 记录原始规划结果（仅在调试时需要）
        # self._write_debug(f"原始规划结果:\n{planning_result}")
        
        try:
            # 尝试解析JSON
            tasks_data = json.loads(planning_result)
        except json.JSONDecodeError as json_err:
            # JSON解析错误，尝试修复常见问题
            logger.error(f"JSON解析错误: {str(json_err)}")
            
            # 尝试提取JSON部分
            json_pattern = r"```json\s*([\s\S]*?)\s*```|```\s*([\s\S]*?)\s*```|\{[\s\S]*\}"
            json_match = re.search(json_pattern, planning_result)
            if json_match:
                json_content = json_match.group(0)
                # 如果匹配到的是代码块，提取内容
                if json_content.startswith("```"):
                    json_content = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", json_content).group(1)
                
                logger.info("从文本中提取JSON内容")
                try:
                    tasks_data = json.loads(json_content)
                except json.JSONDecodeError as inner_err:
                    raise ValueError(f"无法解析提取的JSON内容: {str(inner_err)}")
            else:
                # 尝试创建一个简单的任务
                logger.warning("无法解析JSON，创建默认任务")
                tasks_data = {
                    "task1": {
                        "title": "执行用户请求",
                        "prompt": user_message
                    }
                }
        
        # 验证任务数据格式
        if not tasks_data or not isinstance(tasks_data, dict):
            logger.warning("任务计划格式不正确，创建默认任务")
            tasks_data = {
                "task1": {
                    "title": "执行用户请求",
                    "prompt": user_message
                }
            }
        
        # 验证并修复任务数据
        valid_tasks = {}
        for task_id, task_info in tasks_data.items():
            if not isinstance(task_info, dict):
                logger.warning(f"任务 {task_id} 格式不正确，跳过")
                continue
                
            # 检查必要字段
            if 'title' not in task_info:
                # 尝试从其他字段获取标题
                if 'name' in task_info:
                    task_info['title'] = task_info['name']
                elif '标题' in task_info:
                    task_info['title'] = task_info['标题']
                else:
                    # 使用任务ID作为标题
                    task_info['title'] = f"任务 {task_id}"
                    
            if 'prompt' not in task_info:
                # 尝试从其他字段获取描述
                if 'description' in task_info:
                    task_info['prompt'] = task_info['description']
                elif '描述' in task_info:
                    task_info['prompt'] = task_info['描述']
                elif 'content' in task_info:
                    task_info['prompt'] = task_info['content']
                else:
                    # 使用标题作为描述
                    task_info['prompt'] = task_info.get('title', f"执行任务 {task_id}")
            
            # 添加到有效任务列表
            valid_tasks[task_id] = task_info
        
        if not valid_tasks:
            logger.warning("没有找到有效的任务，创建默认任务")
            valid_tasks = {
                "task1": {
                    "title": "执行用户请求",
                    "prompt": user_message
                }
            }
        
        logger.info(f"有效任务数量: {len(valid_tasks)}")
        
        return valid_tasks

    def _build_system_prompt(self) -> str:
        """
        构建系统提示词，包含上下文信息
        
        Returns:
            完整的系统提示词
        """
        # 基础系统提示词
        prompt = self.system_prompt
        
        # 添加上下文信息（如果有）
        if self.context:
            context_str = json.dumps(self.context, ensure_ascii=False, indent=2)
            prompt += f"\n\n当前上下文信息:\n{context_str}"
        
        # 添加任务信息（如果有）
        if self.tasks:
            tasks_str = "\n".join([f"- {task}" for task in self.tasks])
            prompt += f"\n\n当前任务列表:\n{tasks_str}"
        
        return prompt
    
    async def _handle_analysis_task(
        self,
        task_content: str,
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Optional[str]:
        """
        处理分析任务
        
        Args:
            task_content: 任务内容
            callback: 回调函数，用于流式输出
            
        Returns:
            任务处理结果
        """
        # 添加到任务列表
        task_id = f"analysis_{len(self.tasks) + 1}"
        self.tasks.append(f"{task_id}: {task_content}")
        
        # 构建分析提示词
        analysis_prompt = f"""
请对以下内容进行深度分析:

{task_content}

分析要求:
1. 提供多角度的分析
2. 考虑潜在的影响和意义
3. 给出具体的建议或结论

请以结构化的方式呈现你的分析结果。
"""
        
        # 使用LangChain进行分析
        try:
            if callback:
                await callback(f"开始分析任务 {task_id}...\n\n")
                
                # 执行分析并流式输出
                await self.llm_manager.call_llm(
                    system_prompt=self.system_prompt,
                    user_prompt=analysis_prompt,
                    stream=True,
                    stream_callback=callback
                )
                return None
            else:
                # 非流式模式
                analysis_result = await self.llm_manager.call_llm(
                    system_prompt=self.system_prompt,
                    user_prompt=analysis_prompt
                )
                
                # 保存分析结果
                self.analysis_results[task_id] = analysis_result
                
                return f"分析任务 {task_id} 完成:\n\n{analysis_result}"
                
        except Exception as e:
            error_msg = f"执行分析任务时出错: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    async def _handle_task(
        self,
        task_content: str,
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Optional[str]:
        """
        处理普通任务
        
        Args:
            task_content: 任务内容
            callback: 回调函数，用于流式输出
            
        Returns:
            任务处理结果
        """
        # 解析任务参数
        task_parts = task_content.split(" ", 1)
        task_type = task_parts[0].lower() if task_parts else ""
        task_params = task_parts[1] if len(task_parts) > 1 else ""
        
        if task_type == "add":
            # 添加任务
            self.tasks.append(task_params)
            return f"已添加任务: {task_params}"
            
        elif task_type == "list":
            # 列出所有任务
            if not self.tasks:
                return "当前没有任务"
            
            tasks_str = "\n".join([f"{i+1}. {task}" for i, task in enumerate(self.tasks)])
            return f"当前任务列表:\n{tasks_str}"
            
        elif task_type == "clear":
            # 清空任务列表
            self.tasks = []
            return "已清空任务列表"
            
        elif task_type == "execute":
            # 执行指定任务
            try:
                task_index = int(task_params) - 1
                if 0 <= task_index < len(self.tasks):
                    task = self.tasks[task_index]
                    return await self._execute_tasks([task], callback)
                else:
                    return f"任务索引无效: {task_params}"
            except ValueError:
                return f"无效的任务索引: {task_params}"
                
        elif task_type == "executeall":
            # 执行所有任务
            if not self.tasks:
                return "当前没有任务可执行"
            
            return await self._execute_tasks(self.tasks, callback)
            
        else:
            # 未知任务类型
            return f"未知的任务类型: {task_type}。支持的命令: add, list, clear, execute, executeall"
    
    async def _execute_tasks(
        self, 
        valid_tasks: Dict[str, Dict[str, str]], 
        task_templates: Dict[str, Any], 
        agent_config: Dict[str, Any],
        history_context: str,
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> List[str]:
        """
        执行任务并返回结果
        
        Args:
            valid_tasks: 有效的任务字典，键为任务ID，值为包含title和prompt的字典
            task_templates: 任务模板配置
            agent_config: Agent配置
            history_context: 历史对话上下文
            callback: 用于流式输出的异步回调函数
            
        Returns:
            List[str]: 任务执行结果列表
        """
        results = []
        
        # 输出任务标题和描述
        task_summary = "# 任务执行计划\n\n"
        for task_id, task_info in valid_tasks.items():
            task_title = task_info.get('title', f"任务 {task_id}")
            task_prompt = task_info.get('prompt', '')
            task_summary += f"- {task_title}: {task_prompt[:50]}...\n" if len(task_prompt) > 50 else f"- {task_title}: {task_prompt}\n"
        task_summary += "\n"
        await self._safe_callback(callback, task_summary)
        
        await self._safe_callback(callback, "</think>\n")
        
        # 执行任务并使用流式输出
        for task_id, task_info in valid_tasks.items():
            task_title = task_info.get('title', f"任务 {task_id}")
            task_prompt = task_info.get('prompt', '')
            
            logger.info(f"执行任务: {task_title}")
            
            # 构建执行阶段提示词
            worker_system_prompt, execution_task_description = self._build_worker_prompts(
                task_templates,
                agent_config,
                history_context,
                task_title,
                task_prompt
            )
            
            # 调用LangChain执行任务
            try:
                if callback:
                    # 流式模式
                    try:
                        # 输出任务标题
                        await callback(f"\n## {task_title}\n\n")
                        
                        # 流式输出执行结果
                        full_response = ""
                        async for chunk in self.llm_manager.call_llm_stream(
                            system_prompt=worker_system_prompt,
                            user_prompt=execution_task_description
                        ):
                            full_response += chunk
                            await callback(chunk)
                        
                        # 添加到结果列表
                        results.append(full_response)
                        results.append("\n\n")
                        
                    except Exception as e:
                        error_message = f"执行任务{task_id}时出错: {str(e)}"
                        logger.error(error_message)
                        await callback(f"\n\n**错误**: {str(e)}\n\n")
                else:
                    # 非流式模式
                    try:
                        # 调用LangChain执行任务
                        execution_result = await self.llm_manager.call_llm(
                            system_prompt=worker_system_prompt,
                            user_prompt=execution_task_description
                        )
                        
                        # 打印LLM响应结果
                        logger.info(f"执行阶段 - 任务{task_id} - LLM响应结果: {execution_result[:200]}..." if len(execution_result) > 200 else f"执行阶段 - 任务{task_id} - LLM响应结果: {execution_result}")
                        
                        logger.info(f"任务{task_id}执行完成，结果长度: {len(execution_result)}")
                        results.append(execution_result)
                        results.append("\n\n")
                    except Exception as e:
                        error_message = f"执行任务{task_id}时出错: {str(e)}"
                        logger.error(error_message)
                        results.append(f"**错误**: {str(e)}")
                        results.append("\n\n")
            except Exception as e:
                error_message = f"执行任务{task_id}时出错: {str(e)}"
                logger.error(error_message)
                if callback:
                    await callback(f"\n\n**错误**: {str(e)}\n\n")
                else:
                    results.append(f"**错误**: {str(e)}")
                    results.append("\n\n")
        
        return results

    def _build_worker_prompts(
        self, 
        task_templates: Dict[str, Any], 
        agent_config: Dict[str, Any],
        history_context: str,
        task_title: str,
        task_prompt: str
    ) -> tuple:
        """
        构建执行阶段提示词
        
        Args:
            task_templates: 任务模板配置
            agent_config: Agent配置
            history_context: 历史对话上下文
            task_title: 任务标题
            task_prompt: 任务描述
            
        Returns:
            tuple: (系统提示词, 用户提示词)
        """
        # 获取执行任务模板
        execution_task_template = ""
        if task_templates and "execution_task_template" in task_templates and task_templates["execution_task_template"]:
            execution_task_template = task_templates["execution_task_template"]
            logger.info(f"使用配置文件中的执行任务模板，长度: {len(execution_task_template)}")
        else:
            execution_task_template = DEFAULT_EXECUTION_TASK_TEMPLATE
            logger.info("使用默认执行任务模板")
        
        # 获取执行系统提示词
        worker_system_prompt = ""
        if agent_config and "worker_system_prompt" in agent_config and agent_config["worker_system_prompt"]:
            worker_system_prompt = agent_config["worker_system_prompt"]
        else:
            worker_system_prompt = DEFAULT_WORKER_SYSTEM_PROMPT
        
        # 替换模板中的变量
        execution_task_description = execution_task_template.format(
            history_context=history_context,
            task_title=task_title,
            task_prompt=task_prompt
        )
        
        logger.info(f"执行阶段 - 系统提示词: {worker_system_prompt}")
        logger.info(f"执行阶段 - 用户提示词: {execution_task_description[:200]}..." if len(execution_task_description) > 200 else f"执行阶段 - 用户提示词: {execution_task_description}")
        
        return worker_system_prompt, execution_task_description

    async def on_chat_start(self) -> None:
        """
        聊天开始时的处理
        """
        logger.info("新的聊天会话已初始化")
        
        # 初始化状态
        self.context = {}
        self.tasks = {}
        self.analysis_results = {}
        
    async def on_chat_end(self) -> None:
        """
        聊天结束时的处理
        """
        logger.info("聊天会话已结束")
        
        # 清理状态
        self.context = {}
        self.tasks = {}
        self.analysis_results = {}
    
    async def on_context_update(self, context: Dict[str, Any]) -> None:
        """
        更新上下文信息
        
        Args:
            context: 新的上下文信息
        """
        # 合并上下文
        self.context.update(context)
        logger.info(f"已更新上下文信息，当前上下文键: {list(self.context.keys())}")
        
    async def on_context_clear(self) -> None:
        """
        清除上下文信息
        """
        self.context = {}
        logger.info("已清除上下文信息")

    def _init_workflow(self) -> None:
        """
        初始化LangGraph工作流
        """
        try:
            # 创建状态图
            workflow = StateGraph(AnalyzerState)
            
            # 定义节点函数
            
            # 1. 分析节点 - 分析用户输入，判断是否需要继续执行
            async def analyzer(state: AnalyzerState) -> AnalyzerState:
                """分析用户输入，判断是否需要继续执行"""
                logger.info("执行分析节点")
                
                # 构建分析阶段提示词
                analyzer_system_prompt, analyze_task_description = self._build_analyzer_prompts(
                    state["task_templates"], 
                    state["agent_config"], 
                    state["history_context"], 
                    state["user_message"], 
                    state["system_message"]
                )
                
                # 调用LLM进行分析
                analysis_result = await self.llm_manager.call_llm(
                    system_prompt=analyzer_system_prompt,
                    user_prompt=analyze_task_description
                )
                
                # 更新状态
                state["analysis_result"] = analysis_result
                
                # 如果有回调函数，发送分析中的消息
                if state["callback"]:
                    await self._safe_callback(state["callback"], "<think>正在分析您的消息...\n")
                
                logger.info(f"分析结果: {analysis_result[:100]}..." if len(analysis_result) > 100 else f"分析结果: {analysis_result}")
                return state
            
            # 2. 规划节点 - 规划任务
            async def planner(state: AnalyzerState) -> AnalyzerState:
                """规划任务"""
                logger.info("执行规划节点")
                
                # 如果有回调函数，发送规划中的消息
                if state["callback"]:
                    await self._safe_callback(state["callback"], "正在规划任务...\n")
                
                # 构建规划阶段提示词
                planner_system_prompt, planning_task_description = self._build_planner_prompts(
                    state["task_templates"], 
                    state["agent_config"], 
                    state["history_context"], 
                    state["user_message"]
                )
                
                # 调用LLM进行规划
                planning_result = await self.llm_manager.call_llm(
                    system_prompt=planner_system_prompt,
                    user_prompt=planning_task_description
                )
                
                # 更新状态
                state["planning_result"] = planning_result
                
                # 解析任务数据
                try:
                    state["tasks"] = self._parse_tasks_data(planning_result, state["user_message"])
                except Exception as e:
                    logger.error(f"解析任务计划时出错: {str(e)}")
                    if state["callback"]:
                        await self._safe_callback(
                            state["callback"], 
                            f"解析任务计划时出错: {str(e)}\n原始计划内容:\n{planning_result}"
                        )
                    # 创建默认任务
                    state["tasks"] = {
                        "task1": {
                            "title": "执行用户请求",
                            "prompt": state["user_message"]
                        }
                    }
                
                logger.info(f"规划结果: {planning_result[:100]}..." if len(planning_result) > 100 else f"规划结果: {planning_result}")
                logger.info(f"任务数量: {len(state['tasks'])}")
                return state
            
            # 3. 执行节点 - 执行任务
            async def executor(state: AnalyzerState) -> AnalyzerState:
                """执行任务"""
                logger.info("执行任务节点")
                
                # 输出任务标题和描述
                task_summary = "# 任务执行计划\n\n"
                for task_id, task_info in state["tasks"].items():
                    task_title = task_info.get('title', f"任务 {task_id}")
                    task_prompt = task_info.get('prompt', '')
                    task_summary += f"- {task_title}: {task_prompt[:50]}...\n" if len(task_prompt) > 50 else f"- {task_title}: {task_prompt}\n"
                task_summary += "\n"
                
                if state["callback"]:
                    await self._safe_callback(state["callback"], task_summary)
                    await self._safe_callback(state["callback"], "</think>\n")
                
                # 执行任务
                results = []
                for task_id, task_info in state["tasks"].items():
                    task_title = task_info.get('title', f"任务 {task_id}")
                    task_prompt = task_info.get('prompt', '')
                    
                    logger.info(f"执行任务: {task_title}")
                    
                    # 构建执行阶段提示词
                    worker_system_prompt, execution_task_description = self._build_worker_prompts(
                        state["task_templates"],
                        state["agent_config"],
                        state["history_context"],
                        task_title,
                        task_prompt
                    )
                    
                    try:
                        if state["callback"]:
                            # 流式模式
                            # 输出任务标题
                            await self._safe_callback(state["callback"], f"\n## {task_title}\n\n")
                            
                            # 流式输出执行结果
                            full_response = ""
                            async for chunk in self.llm_manager.call_llm_stream(
                                system_prompt=worker_system_prompt,
                                user_prompt=execution_task_description
                            ):
                                full_response += chunk
                                await self._safe_callback(state["callback"], chunk)
                            
                            # 添加到结果列表
                            results.append(full_response)
                        else:
                            # 非流式模式
                            execution_result = await self.llm_manager.call_llm(
                                system_prompt=worker_system_prompt,
                                user_prompt=execution_task_description
                            )
                            
                            logger.info(f"任务{task_id}执行完成，结果长度: {len(execution_result)}")
                            results.append(execution_result)
                    except Exception as e:
                        error_message = f"执行任务{task_id}时出错: {str(e)}"
                        logger.error(error_message)
                        if state["callback"]:
                            await self._safe_callback(state["callback"], f"\n\n**错误**: {str(e)}\n\n")
                        else:
                            results.append(f"**错误**: {str(e)}")
                
                # 更新状态
                state["execution_results"] = results
                
                # 整合所有结果
                if not state["callback"]:  # 非流式模式下才需要整合结果
                    state["final_result"] = "# 任务执行结果\n\n" + "\n\n### ".join(results)
                    logger.info(f"所有任务执行完成，总结果长度: {len(state['final_result'])}")
                
                return state
            
            # 4. 直接回复节点 - 当分析结果不需要继续执行时，直接返回分析结果
            async def direct_response(state: AnalyzerState) -> AnalyzerState:
                """直接返回分析结果"""
                logger.info("执行直接回复节点")
                
                if state["callback"]:
                    await self._safe_callback(state["callback"], f"</think>{state['analysis_result']}\n")
                else:
                    state["final_result"] = state["analysis_result"]
                
                return state
            
            # 添加节点到工作流
            workflow.add_node("analyzer", analyzer)
            workflow.add_node("planner", planner)
            workflow.add_node("executor", executor)
            workflow.add_node("direct_response", direct_response)
            
            # 定义边和条件函数
            
            # 从分析节点开始
            workflow.set_entry_point("analyzer")
            
            # 添加条件边
            workflow.add_conditional_edges(
                "analyzer",
                lambda state: "planner" if "NEXT-AGENT" in state["analysis_result"] else "direct_response"
            )
            
            # 规划节点到执行节点
            workflow.add_edge("planner", "executor")
            
            # 执行节点和直接回复节点都是终点
            workflow.add_edge("executor", END)
            workflow.add_edge("direct_response", END)
            
            # 编译工作流
            self.workflow = workflow.compile()
            
            logger.info("LangGraph工作流初始化完成")
            
        except Exception as e:
            logger.error(f"初始化LangGraph工作流时出错: {str(e)}")
            self.workflow = None 