from typing import List, Dict, Any, Optional, Callable, Awaitable
import logging
import yaml
import os
import json
import asyncio
from pathlib import Path
from app.models.vector_model import VectorModel
import datetime
import re
from app.models.deep_analyzer.templates import (
    DEFAULT_ANALYZE_TASK_TEMPLATE,
    DEFAULT_PLANNING_TASK_TEMPLATE,
    DEFAULT_EXECUTION_TASK_TEMPLATE,
    DEFAULT_ANALYZER_SYSTEM_PROMPT,
    DEFAULT_PLANNER_SYSTEM_PROMPT,
    DEFAULT_WORKER_SYSTEM_PROMPT
)

logger = logging.getLogger(__name__)

class DeepAnalyzerModel(VectorModel):
    """
    Deep Analyzer 模型
    基于LiteLLM实现的高级分析模型，能够深入分析用户消息和系统消息，
    判断信息是否足够，并根据分析结果进行任务分解和执行。
    """
    
    def __init__(self):
        # 设置配置文件路径
        self.config_path = Path(__file__).parent / "config.yaml"
        # 初始化配置文件修改时间
        self._config_mtime = 0
        
        # 调用父类初始化方法
        super().__init__()
        
        # 加载模型特定配置
        self.config = self._load_config()
        
        # 如果配置文件中有LLM配置，覆盖系统默认配置
        self._override_llm_config()
    
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
                
            # 只有当环境变量中没有设置时，才使用配置文件中的值
            if not os.environ.get("LLM_PROVIDER") and "provider" in llm_config:
                provider = llm_config.get("provider")
                self.llm_config["provider"] = provider
                logger.info(f"从配置文件覆盖LLM提供商: {provider}")
                
            if not os.environ.get("LLM_MODEL") and "model" in llm_config:
                model = llm_config.get("model")
                self.llm_config["model"] = model
                logger.info(f"从配置文件覆盖LLM模型: {model}")
                
            if not os.environ.get("LLM_TEMPERATURE") and "temperature" in llm_config:
                temperature = float(llm_config.get("temperature", 0.7))
                self.llm_config["temperature"] = temperature
                logger.info(f"从配置文件覆盖LLM温度: {temperature}")
                
            if not os.environ.get("LLM_API_KEY") and "api_key" in llm_config:
                api_key = llm_config.get("api_key")
                if api_key:  # 只有当配置文件中有非空值时才覆盖
                    self.llm_config["api_key"] = api_key
                    logger.info("从配置文件覆盖LLM API密钥")
                
            if not os.environ.get("LLM_API_BASE") and "api_base" in llm_config:
                api_base = llm_config.get("api_base")
                if api_base:  # 只有当配置文件中有非空值时才覆盖
                    self.llm_config["api_base"] = api_base
                    logger.info(f"从配置文件覆盖LLM API基础URL: {api_base}")
                    
            # 如果是Azure，处理额外配置
            if self.llm_config["provider"] == "azure":
                if not os.environ.get("AZURE_OPENAI_API_VERSION") and "api_version" in llm_config:
                    self.llm_config["api_version"] = llm_config.get("api_version")
                    
                if not os.environ.get("AZURE_OPENAI_DEPLOYMENT") and "azure_deployment" in llm_config:
                    self.llm_config["azure_deployment"] = llm_config.get("azure_deployment")
                    
            logger.info(f"最终LLM配置: {self.llm_config['provider']}/{self.llm_config['model']}")
            
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
                # 重新初始化LLM配置
                super()._init_llm()
                # 覆盖配置
                self._override_llm_config()
                logger.info(f"已切换到默认LLM配置: {self.llm_config['provider']}/{self.llm_config['model']}")
                return True
            
            # 从配置文件中获取备选LLM配置
            alternatives = self.config.get("llm", {}).get("alternatives", {})
            if llm_name not in alternatives:
                logger.warning(f"未找到名为 {llm_name} 的LLM配置")
                return False
                
            # 获取备选配置
            alt_config = alternatives[llm_name]
            
            # 更新LLM配置
            self.llm_config["provider"] = alt_config.get("provider", self.llm_config["provider"])
            self.llm_config["model"] = alt_config.get("model", self.llm_config["model"])
            self.llm_config["temperature"] = float(alt_config.get("temperature", self.llm_config["temperature"]))
            
            # 只有当配置中有非空值时才更新
            if "api_key" in alt_config and alt_config["api_key"]:
                self.llm_config["api_key"] = alt_config["api_key"]
                
            if "api_base" in alt_config and alt_config["api_base"]:
                self.llm_config["api_base"] = alt_config["api_base"]
                
            # 如果是Azure，处理额外配置
            if self.llm_config["provider"] == "azure":
                if "api_version" in alt_config:
                    self.llm_config["api_version"] = alt_config["api_version"]
                    
                if "azure_deployment" in alt_config:
                    self.llm_config["azure_deployment"] = alt_config["azure_deployment"]
            
            logger.info(f"已切换到 {llm_name} LLM配置: {self.llm_config['provider']}/{self.llm_config['model']}")
            return True
            
        except Exception as e:
            logger.error(f"设置LLM配置时出错: {str(e)}")
            return False
    
    async def on_chat_start(self) -> None:
        """
        聊天开始时的钩子方法
        """
        await super().on_chat_start()
        # 初始化聊天会话
        # 注意：向量存储相关逻辑已移至ModelManager处理
        
        # 每次对话开始时重新加载配置，确保实时更新
        self._reload_config()
        
        logger.info("聊天会话已初始化")
        self._write_debug("=== 新的聊天会话已初始化 ===")
    
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
            self._write_debug(f"配置文件修改时间: {datetime.datetime.fromtimestamp(current_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            
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
        处理聊天消息的主要方法

        Args:
            messages: 消息列表，每条消息是包含role和content的字典
            callback: 用于流式输出的异步回调函数，如果为None则为非流式模式

        Returns:
            如果是非流式模式（callback=None），返回完整的响应字符串
            如果是流式模式（callback不为None），通过callback发送内容，返回None
        """
        if not self.llm_config:
            response = "LLM配置未初始化，无法使用Deep Analyzer模型。"
            await self._safe_callback(callback, response)
            return None if callback else response
        
        # 获取最后一条用户消息
        user_message = None
        for message in reversed(messages):
            if message["role"] == "user":
                user_message = message["content"]
                break
        
        if not user_message:
            response = "未找到用户消息。"
            await self._safe_callback(callback, response)
            return None if callback else response
        
        # 获取系统消息（如果有）
        system_messages = [msg["content"] for msg in messages if msg["role"] == "system"]
        system_message = "\n".join(system_messages) if system_messages else ""
        
        # 获取历史用户消息（最近10条）
        history_messages = []
        for msg in messages:
            if msg["role"] == "user" or msg["role"] == "assistant":
                history_messages.append(msg)
        
        # 只保留最近的10条消息（如果超过10条）
        if len(history_messages) > 10:
            history_messages = history_messages[-10:]
        
        # 使用LiteLLM处理消息
        result = await self._process_with_litellm(user_message, system_message, history_messages, callback)
        
        return None if callback else result
    
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

    def _build_analyzer_prompts(
        self, 
        task_templates: Dict[str, Any], 
        agent_config: Dict[str, Any],
        history_context: str,
        user_message: str,
        system_message: str
    ) -> tuple:
        """
        构建分析阶段的提示词
        
        Args:
            task_templates: 任务模板配置
            agent_config: Agent配置
            history_context: 历史对话上下文
            user_message: 用户消息
            system_message: 系统消息
            
        Returns:
            tuple: (analyzer_system_prompt, analyze_task_description)
        """
        # 获取分析器配置
        analyzer_config = agent_config.get("analyzer_agent", {})
        analyzer_role = analyzer_config.get("role", "信息分析专家")
        analyzer_goal = analyzer_config.get("goal", "分析用户消息和系统消息，判断信息是否足够")
        analyzer_backstory = analyzer_config.get("backstory", "你是一个专业的信息分析专家，能够深入理解用户需求，判断提供的信息是否足够执行任务。")
        
        # 创建分析任务提示词
        analyze_task_template = ""
        if "analyze_task" in task_templates and isinstance(task_templates["analyze_task"], dict) and "description" in task_templates["analyze_task"]:
            analyze_task_template = task_templates["analyze_task"]["description"]
            logger.info(f"成功获取配置文件中的分析任务模板，长度: {len(analyze_task_template)}")
            self._write_debug(f"使用配置文件中的分析任务模板，长度: {len(analyze_task_template)}")
            logger.info(f"分析任务模板前200个字符: {analyze_task_template[:200]}...")
        else:
            logger.warning("配置文件中没有分析任务模板或格式不正确，使用默认模板")
            self._write_debug("配置文件中没有分析任务模板或格式不正确，使用默认模板")
            analyze_task_template = DEFAULT_ANALYZE_TASK_TEMPLATE
        
        # 格式化模板
        analyze_task_description = analyze_task_template.format(
            history_context=history_context,
            user_message=user_message,
            system_message=system_message
        )
        
        # 构建系统提示词
        analyzer_system_prompt = DEFAULT_ANALYZER_SYSTEM_PROMPT.format(
            analyzer_role=analyzer_role,
            analyzer_backstory=analyzer_backstory,
            analyzer_goal=analyzer_goal
        )
        
        # 打印要发送给LLM的信息
        logger.info(f"分析阶段 - 发送给LLM的信息 - 模型: {self.llm_config['provider']}/{self.llm_config['model']}")
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
        构建规划阶段的提示词
        
        Args:
            task_templates: 任务模板配置
            agent_config: Agent配置
            history_context: 历史对话上下文
            user_message: 用户消息
            
        Returns:
            tuple: (planner_system_prompt, planning_task_description)
        """
        # 获取规划器配置
        planner_config = agent_config.get("planner_agent", {})
        planner_role = planner_config.get("role", "任务规划专家")
        planner_goal = planner_config.get("goal", "根据用户需求分解任务计划")
        planner_backstory = planner_config.get("backstory", "你是一个专业的任务规划专家，能够将复杂任务分解为可执行的子任务。")
        
        # 创建规划任务提示词
        planning_task_template = ""
        if "planning_task" in task_templates and isinstance(task_templates["planning_task"], dict) and "description" in task_templates["planning_task"]:
            planning_task_template = task_templates["planning_task"]["description"]
            logger.info(f"成功获取配置文件中的规划任务模板，长度: {len(planning_task_template)}")
            self._write_debug(f"使用配置文件中的规划任务模板，长度: {len(planning_task_template)}")
            logger.info(f"规划任务模板前200个字符: {planning_task_template[:200]}...")
        else:
            logger.warning("配置文件中没有规划任务模板或格式不正确，使用默认模板")
            self._write_debug("配置文件中没有规划任务模板或格式不正确，使用默认模板")
            planning_task_template = DEFAULT_PLANNING_TASK_TEMPLATE
        
        # 格式化模板
        planning_task_description = planning_task_template.format(
            history_context=history_context,
            user_message=user_message
        )
        
        # 构建系统提示词
        planner_system_prompt = DEFAULT_PLANNER_SYSTEM_PROMPT.format(
            planner_role=planner_role,
            planner_backstory=planner_backstory,
            planner_goal=planner_goal
        )
        
        # 打印要发送给LLM的信息
        logger.info(f"规划阶段 - 发送给LLM的信息 - 模型: {self.llm_config['provider']}/{self.llm_config['model']}")
        logger.info(f"规划阶段 - 系统提示词: {planner_system_prompt}")
        logger.info(f"规划阶段 - 用户提示词: {planning_task_description[:200]}..." if len(planning_task_description) > 200 else f"规划阶段 - 用户提示词: {planning_task_description}")
        
        return planner_system_prompt, planning_task_description
    
    def _build_worker_prompts(
        self, 
        task_templates: Dict[str, Any], 
        agent_config: Dict[str, Any],
        history_context: str,
        task_title: str,
        task_prompt: str
    ) -> tuple:
        """
        构建执行阶段的提示词
        
        Args:
            task_templates: 任务模板配置
            agent_config: Agent配置
            history_context: 历史对话上下文
            task_title: 任务标题
            task_prompt: 任务描述
            
        Returns:
            tuple: (worker_system_prompt, execution_task_description)
        """
        # 获取执行器配置
        worker_config = agent_config.get("worker_agent", {})
        worker_role = worker_config.get("role", "任务执行专家")
        worker_goal = worker_config.get("goal", "执行具体任务并返回结果")
        worker_backstory = worker_config.get("backstory", "你是一个专业的任务执行专家，能够高效准确地完成各种任务。")
        
        # 构建系统提示词
        worker_system_prompt = DEFAULT_WORKER_SYSTEM_PROMPT.format(
            worker_role=worker_role,
            worker_backstory=worker_backstory,
            worker_goal=worker_goal
        )
        
        # 创建执行任务提示词
        execution_task_template = ""
        if "execution_task" in task_templates and isinstance(task_templates["execution_task"], dict) and "description" in task_templates["execution_task"]:
            execution_task_template = task_templates["execution_task"]["description"]
            logger.info(f"成功获取配置文件中的执行任务模板，长度: {len(execution_task_template)}")
            self._write_debug(f"使用配置文件中的执行任务模板，长度: {len(execution_task_template)}")
            logger.info(f"执行任务模板前200个字符: {execution_task_template[:200]}...")
        else:
            logger.warning("配置文件中没有执行任务模板或格式不正确，使用默认模板")
            self._write_debug("配置文件中没有执行任务模板或格式不正确，使用默认模板")
            execution_task_template = DEFAULT_EXECUTION_TASK_TEMPLATE
        
        # 格式化模板
        execution_task_description = execution_task_template.format(
            history_context=history_context,
            task_title=task_title,
            task_prompt=task_prompt
        )
        
        # 打印要发送给LLM的信息
        logger.info(f"执行阶段 - 任务 {task_title} - 发送给LLM的信息 - 模型: {self.llm_config['provider']}/{self.llm_config['model']}")
        logger.info(f"执行阶段 - 任务 {task_title} - 系统提示词: {worker_system_prompt}")
        logger.info(f"执行阶段 - 任务 {task_title} - 用户提示词: {execution_task_description[:200]}..." if len(execution_task_description) > 200 else f"执行阶段 - 任务 {task_title} - 用户提示词: {execution_task_description}")
        
        return worker_system_prompt, execution_task_description

    def _get_config_data(self) -> tuple:
        """
        获取配置数据，包括任务模板和Agent配置
        
        Returns:
            tuple: (task_templates, agent_config)
        """
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

    def _parse_tasks_data(self, planning_result: str, user_message: str) -> Dict[str, Dict[str, str]]:
        """
        解析任务计划数据
        
        Args:
            planning_result: 规划阶段的结果
            user_message: 用户消息，用于创建默认任务
            
        Returns:
            Dict[str, Dict[str, str]]: 解析后的任务数据
        """
        # 记录原始规划结果
        self._write_debug(f"原始规划结果:\n{planning_result}")
        
        try:
            # 尝试解析JSON
            tasks_data = json.loads(planning_result)
        except json.JSONDecodeError as json_err:
            # JSON解析错误，尝试修复常见问题
            logger.error(f"JSON解析错误: {str(json_err)}")
            self._write_debug(f"JSON解析错误: {str(json_err)}")
            
            # 尝试提取JSON部分
            json_pattern = r"```json\s*([\s\S]*?)\s*```|```\s*([\s\S]*?)\s*```|\{[\s\S]*\}"
            json_match = re.search(json_pattern, planning_result)
            if json_match:
                json_content = json_match.group(0)
                # 如果匹配到的是代码块，提取内容
                if json_content.startswith("```"):
                    json_content = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", json_content).group(1)
                
                logger.info("从文本中提取JSON内容")
                self._write_debug(f"提取的JSON内容:\n{json_content}")
                try:
                    tasks_data = json.loads(json_content)
                except json.JSONDecodeError as inner_err:
                    raise ValueError(f"无法解析提取的JSON内容: {str(inner_err)}")
            else:
                # 尝试创建一个简单的任务
                logger.warning("无法解析JSON，创建默认任务")
                self._write_debug("无法解析JSON，创建默认任务")
                tasks_data = {
                    "task1": {
                        "title": "执行用户请求",
                        "prompt": user_message
                    }
                }
        
        logger.info(f"解析到的任务数据: {tasks_data}")
        self._write_debug(f"解析到的任务数据: {json.dumps(tasks_data, ensure_ascii=False, indent=2) if tasks_data else 'None'}")
        
        # 验证任务数据格式
        if not tasks_data or not isinstance(tasks_data, dict):
            logger.warning("任务计划格式不正确，创建默认任务")
            self._write_debug("任务计划格式不正确，创建默认任务")
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
        self._write_debug(f"有效任务数量: {len(valid_tasks)}")
        self._write_debug(f"有效任务数据: {json.dumps(valid_tasks, ensure_ascii=False, indent=2)}")
        
        return valid_tasks

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
            valid_tasks: 有效的任务数据
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
            task_summary += f"- {task_title}\n"
        task_summary += "\n"
        await self._safe_callback(callback, task_summary)
        
        await self._safe_callback(callback, "</think>\n")
        
        # 执行任务并使用流式输出
        for task_id, task_info in valid_tasks.items():
            task_title = task_info.get('title', f"任务 {task_id}")
            task_prompt = task_info.get('prompt', task_title)
            
            logger.info(f"执行任务: {task_id} - {task_title}")
            self._write_debug(f"执行任务: {task_id} - {task_title}")
            
            # await self._safe_callback(callback, f"\n### {task_title}\n\n")
            
            # 构建执行阶段提示词
            worker_system_prompt, execution_task_description = self._build_worker_prompts(
                task_templates, 
                agent_config, 
                history_context, 
                task_title, 
                task_prompt
            )
            
            # 使用流式输出调用LLM
            if callback:
                # 流式模式
                try:
                    # 调用LiteLLM执行任务，使用流式输出和回调
                    full_response = await self._call_llm(
                        system_prompt=worker_system_prompt,
                        user_prompt=execution_task_description,
                        stream=True,
                        stream_callback=callback
                    )
                    
                    # 写入调试文件
                    self._write_debug(f"任务 {task_id} 执行完成，结果长度: {len(full_response)}")
                    self._write_debug(f"任务 {task_id} 执行结果:\n{full_response}")
                    
                    # 添加到结果列表
                    results.append(full_response)
                    
                except Exception as e:
                    error_message = f"执行任务 {task_id} 时出错: {str(e)}"
                    logger.error(error_message)
                    self._write_debug(error_message)
                    await self._safe_callback(callback, f"\n出错: {error_message}\n")
                    results.append(error_message)
            else:
                # 非流式模式
                try:
                    # 调用LiteLLM执行任务
                    execution_result = await self._call_llm(
                        system_prompt=worker_system_prompt,
                        user_prompt=execution_task_description
                    )
                    
                    # 打印LLM响应结果
                    logger.info(f"执行阶段 - 任务 {task_id} - LLM响应结果: {execution_result[:200]}..." if len(execution_result) > 200 else f"执行阶段 - 任务 {task_id} - LLM响应结果: {execution_result}")
                    
                    logger.info(f"任务 {task_id} 执行完成，结果长度: {len(execution_result)}")
                    self._write_debug(f"任务 {task_id} 执行完成，结果长度: {len(execution_result)}")
                    self._write_debug(f"任务 {task_id} 执行结果:\n{execution_result}")
                    results.append(execution_result)
                except Exception as e:
                    error_message = f"执行任务 {task_id} 时出错: {str(e)}"
                    logger.error(error_message)
                    self._write_debug(error_message)
                    results.append(error_message)
        
        return results

    async def _process_with_litellm(
        self,
        user_message: str,
        system_message: str,
        history_messages: List[Dict[str, str]],
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> str:
        """
        使用LiteLLM处理消息

        Args:
            user_message: 用户消息
            system_message: 系统消息
            history_messages: 历史消息列表（最近10条）
            callback: 用于流式输出的异步回调函数

        Returns:
            处理结果
        """
        try:
            # 获取配置数据
            task_templates, agent_config = self._get_config_data()
            
            # 格式化历史消息
            history_context = self._format_history_context(history_messages)
                
            logger.info(f"处理用户消息: {user_message[:100]}..." if len(user_message) > 100 else f"处理用户消息: {user_message}")
            logger.info(f"历史消息数量: {len(history_messages)}")
            
            # 写入调试文件
            self._write_debug(f"=== 开始处理新消息 ===")
            self._write_debug(f"用户消息: {user_message}")
            self._write_debug(f"历史消息数量: {len(history_messages)}")
            if history_messages:
                self._write_debug(f"历史消息内容:\n{history_context}")
            
            # 1. 分析阶段
            logger.info("开始分析阶段")
            self._write_debug("=== 开始分析阶段 ===")
            await self._safe_callback(callback, "<think>正在分析您的消息...\n")
            
            # 构建分析阶段提示词
            analyzer_system_prompt, analyze_task_description = self._build_analyzer_prompts(
                task_templates, 
                agent_config, 
                history_context, 
                user_message, 
                system_message
            )
            
            # 调用LiteLLM进行分析
            analysis_result = await self._call_llm(
                system_prompt=analyzer_system_prompt,
                user_prompt=analyze_task_description
            )
            
            # 打印LLM响应结果
            logger.info(f"分析阶段 - LLM响应结果: {analysis_result[:200]}..." if len(analysis_result) > 200 else f"分析阶段 - LLM响应结果: {analysis_result}")
            
            # 如果分析结果包含'NEXT-AGENT'，则继续执行后续步骤
            if 'NEXT-AGENT' in analysis_result:
                logger.info("分析结果包含'NEXT-AGENT'，继续执行后续步骤")
                self._write_debug(f"分析结果包含'NEXT-AGENT'，继续执行后续步骤")
            else:
                await self._safe_callback(callback, f"</think>{analysis_result}\n")
                return analysis_result

            logger.info(f"分析阶段结果: {analysis_result}")
            self._write_debug(f"分析阶段结果: {analysis_result}")
            
            # 2. 判断分析结果 - 无论结果如何，都继续执行后续步骤
            await self._safe_callback(callback, "正在规划任务...\n")
            
            # 3. 规划阶段
            logger.info("开始规划阶段")
            self._write_debug("=== 开始规划阶段 ===")
            
            # 构建规划阶段提示词
            planner_system_prompt, planning_task_description = self._build_planner_prompts(
                task_templates, 
                agent_config, 
                history_context, 
                user_message
            )
            
            # 调用LiteLLM进行规划
            planning_result = await self._call_llm(
                system_prompt=planner_system_prompt,
                user_prompt=planning_task_description
            )
            
            # 打印LLM响应结果
            logger.info(f"规划阶段 - LLM响应结果: {planning_result[:200]}..." if len(planning_result) > 200 else f"规划阶段 - LLM响应结果: {planning_result}")
            
            logger.info(f"规划阶段结果: {planning_result[:200]}..." if len(planning_result) > 200 else f"规划阶段结果: {planning_result}")
            self._write_debug(f"规划阶段结果:\n{planning_result}")
            
            # await self._safe_callback(callback, "任务规划完成，开始执行任务...\n")
            
            # 4. 解析任务计划 - 规划阶段完成后直接进入执行阶段，不需要额外判断
            try:
                # 解析任务数据
                valid_tasks = self._parse_tasks_data(planning_result, user_message)
                
                # 5. 执行阶段
                logger.info("开始执行阶段")
                self._write_debug("=== 开始执行阶段 ===")
                
                # 执行任务
                results = await self._execute_tasks(valid_tasks, task_templates, agent_config, history_context, callback)
                
                # 7. 整合所有结果
                if callback:
                    # 流式模式下已经输出了结果，只需要添加结束标记
                    # await self._safe_callback(callback, "\n\n# 任务执行完成")
                    return None
                else:
                    # 非流式模式下返回完整结果
                    final_result = "# 任务执行结果\n\n" + "\n\n### ".join(results)
                    logger.info(f"所有任务执行完成，总结果长度: {len(final_result)}")
                    self._write_debug("=== 所有任务执行完成 ===")
                    self._write_debug(f"总结果长度: {len(final_result)}")
                    return final_result
                
            except Exception as e:
                error_message = f"解析任务计划时出错: {str(e)}\n原始计划内容:\n{planning_result}"
                logger.error(error_message)
                self._write_debug(f"=== 解析任务计划时出错 ===")
                self._write_debug(error_message)
                await self._safe_callback(callback, error_message)
                return error_message
                
        except Exception as e:
            error_message = f"处理消息时出错: {str(e)}"
            logger.error(error_message)
            self._write_debug(f"=== 处理消息时出错 ===")
            self._write_debug(error_message)
            await self._safe_callback(callback, error_message)
            return error_message
    
    async def on_chat_end(self) -> None:
        """
        聊天结束时的钩子方法
        """
        # 清理工作可以在这里完成
        await super().on_chat_end() 