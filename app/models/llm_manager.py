from typing import Dict, Any, Optional, Callable, Awaitable
from pathlib import Path
import os
import logging
import json
import datetime
import yaml
from dotenv import load_dotenv

# 尝试导入litellm，如果不存在则设置为None
try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

logger = logging.getLogger(__name__)

class LiteLLMManager:
    """
    LiteLLMManager 负责 LLM 模型的加载、管理和调用功能。
    提供了基础的 LLM 管理功能，包括配置加载、环境变量处理和 LLM 调用。
    """
    
    def __init__(self, model_dir: Optional[Path] = None, config: Optional[Dict[str, Any]] = None):
        """
        初始化 LiteLLMManager
        
        Args:
            model_dir: 模型目录路径，用于加载配置文件
            config: 模型配置，如果提供则优先使用
        """
        # 加载环境变量
        load_dotenv()
        
        self.model_dir = model_dir
        self.config = config or {}  # 模型配置
        self.llm_config = None  # LLM配置
        self.debug_file = None  # 调试文件
        
        # 如果没有提供配置，尝试从模型目录加载
        if not config and model_dir:
            self._load_config()
        
        # 初始化LLM配置
        self._init_llm()
        
        # 初始化调试文件
        self._init_debug_file()
    
    def _load_config(self):
        """加载模型配置"""
        if self.model_dir and (self.model_dir / "config.yaml").exists():
            try:
                with open(self.model_dir / "config.yaml", 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
                    logger.debug(f"加载配置: {self.config}")
            except Exception as e:
                logger.error(f"加载配置文件时出错: {str(e)}")
                self.config = {}
    
    def _init_llm(self) -> None:
        """
        初始化LLM配置，从配置文件、环境变量或.env文件中获取
        """
        if not LITELLM_AVAILABLE:
            logger.warning("litellm未安装，LLM功能将不可用")
            return
            
        try:
            # 获取LLM配置
            llm_config = self.config.get("llm", {}).get("default", {})
            
            # 从环境变量获取配置（优先级高于配置文件）
            provider = os.environ.get("LLM_PROVIDER", llm_config.get("provider", "openai")).lower()
            model = os.environ.get("LLM_MODEL", llm_config.get("model", "gpt-4"))
            temperature = float(os.environ.get("LLM_TEMPERATURE", llm_config.get("temperature", 0.7)))
            api_key = os.environ.get("LLM_API_KEY", llm_config.get("api_key", ""))
            api_base = os.environ.get("LLM_API_BASE", llm_config.get("api_base", ""))
            
            # 如果没有提供API密钥，尝试从特定环境变量获取
            if not api_key:
                if provider == "openai":
                    api_key = os.environ.get("OPENAI_API_KEY", "")
                elif provider == "anthropic":
                    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
                elif provider == "azure":
                    api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
            
            # 如果没有提供API基础URL，尝试从特定环境变量获取
            if not api_base:
                if provider == "openai":
                    api_base = os.environ.get("OPENAI_API_BASE", "")
                elif provider == "anthropic":
                    api_base = os.environ.get("ANTHROPIC_API_BASE", "")
                elif provider == "azure":
                    api_base = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
                elif provider == "ollama":
                    api_base = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
            
            # 构建LLM配置
            self.llm_config = {
                "provider": provider,
                "model": model,
                "temperature": temperature,
                "api_key": api_key,
                "api_base": api_base
            }
            
            # 如果是Azure，添加额外配置
            if provider == "azure":
                api_version = os.environ.get("AZURE_OPENAI_API_VERSION", llm_config.get("api_version", "2023-05-15"))
                azure_deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", llm_config.get("azure_deployment", model))
                
                self.llm_config["api_version"] = api_version
                self.llm_config["azure_deployment"] = azure_deployment
            
            logger.info(f"已初始化LLM配置: {provider}/{model}")
            
        except Exception as e:
            logger.error(f"初始化LLM配置时出错: {str(e)}")
            self.llm_config = None
    
    def _init_debug_file(self) -> None:
        """
        初始化调试文件
        """
        try:
            # 检查是否启用调试
            debug_enabled = os.environ.get("DEBUG_ENABLED", "").lower() in ["true", "1", "yes"]
            if not debug_enabled and not self.config.get("debug", {}).get("enabled", False):
                return
                
            debug_dir = Path(os.environ.get("DEBUG_DIR", "debug_logs"))
            debug_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            model_name = "litellm"
            self.debug_file = debug_dir / f"{model_name}_debug_{timestamp}.log"
            
            # 写入初始信息
            with open(self.debug_file, "w", encoding="utf-8") as f:
                f.write(f"=== LiteLLM 调试日志 - {timestamp} ===\n\n")
                if self.llm_config:
                    f.write(f"LLM配置: {json.dumps(self.llm_config, ensure_ascii=False, indent=2)}\n\n")
            
            logger.info(f"调试日志将写入: {self.debug_file}")
        except Exception as e:
            logger.error(f"初始化调试文件时出错: {str(e)}")
            self.debug_file = None
    
    def _write_debug(self, message: str) -> None:
        """
        写入调试信息到文件
        
        Args:
            message: 调试信息
        """
        if not self.debug_file:
            return
        
        try:
            with open(self.debug_file, "a", encoding="utf-8") as f:
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            logger.error(f"写入调试信息时出错: {str(e)}")
    
    def set_llm(self, llm_name: str) -> bool:
        """
        设置使用的LLM
        
        Args:
            llm_name: LLM名称，对应配置文件中的alternatives键
            
        Returns:
            是否成功设置
        """
        if not LITELLM_AVAILABLE:
            logger.warning("litellm未安装，无法设置LLM")
            return False
            
        # 获取备选LLM配置
        alternatives = self.config.get("llm", {}).get("alternatives", {})
        llm_config = alternatives.get(llm_name)
        
        if not llm_config:
            logger.warning(f"未找到名为 {llm_name} 的LLM配置")
            return False
        
        provider = llm_config.get("provider", "").lower()
        model = llm_config.get("model", "")
        temperature = llm_config.get("temperature", 0.7)
        api_key = llm_config.get("api_key", "")
        api_base = llm_config.get("api_base", "")
        
        # 如果没有提供API密钥，尝试从环境变量获取
        if not api_key:
            if provider == "openai":
                api_key = os.environ.get("OPENAI_API_KEY", "")
            elif provider == "anthropic":
                api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            elif provider == "azure":
                api_key = os.environ.get("AZURE_OPENAI_API_KEY", "")
        
        # 如果没有提供API基础URL，尝试从环境变量获取
        if not api_base:
            if provider == "openai":
                api_base = os.environ.get("OPENAI_API_BASE", "")
            elif provider == "anthropic":
                api_base = os.environ.get("ANTHROPIC_API_BASE", "")
            elif provider == "azure":
                api_base = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
            elif provider == "ollama":
                api_base = os.environ.get("OLLAMA_API_BASE", "http://localhost:11434")
        
        # 构建LLM配置
        self.llm_config = {
            "provider": provider,
            "model": model,
            "temperature": temperature,
            "api_key": api_key,
            "api_base": api_base
        }
        
        # 如果是Azure，添加额外配置
        if provider == "azure":
            self.llm_config["api_version"] = llm_config.get("api_version", "2023-05-15")
            self.llm_config["azure_deployment"] = llm_config.get("azure_deployment", model)
        
        logger.info(f"已切换LLM配置: {provider}/{model}")
        return True
    
    async def _safe_callback(
        self,
        callback: Optional[Callable[[str], Awaitable[None]]],
        content: str
    ) -> None:
        """
        安全地调用回调函数，如果回调函数为空则忽略

        Args:
            callback: 回调函数，可能为None
            content: 要发送的内容
        """
        if callback:
            await callback(content)

    async def call_llm(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        stream: bool = False,
        stream_callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> str:
        """
        调用LiteLLM接口

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            stream: 是否使用流式输出
            stream_callback: 流式输出回调函数，用于处理每个内容块

        Returns:
            LLM响应内容
        """
        if not LITELLM_AVAILABLE:
            raise ImportError("litellm未安装，无法调用LLM")
            
        if not self.llm_config:
            raise ValueError("LLM配置未初始化")
            
        try:
            provider = self.llm_config["provider"]
            model = self.llm_config["model"]
            temperature = self.llm_config["temperature"]
            api_key = self.llm_config["api_key"]
            api_base = self.llm_config["api_base"]
            
            # 记录要发送给LLM的信息
            logger.info(f"发送给LLM的信息 - 模型: {provider}/{model}, 温度: {temperature}")
            logger.debug(f"系统提示词: {system_prompt}")
            logger.debug(f"用户提示词: {user_prompt}")
            
            # 写入调试文件
            self._write_debug(f"=== 发送给LLM的信息 ===")
            self._write_debug(f"模型: {provider}/{model}, 温度: {temperature}")
            self._write_debug(f"系统提示词:\n{system_prompt}")
            self._write_debug(f"用户提示词:\n{user_prompt}")
            
            # 构建完整的模型名称
            model_name = model
            if provider == "openai":
                model_name = f"openai/{model}"
            elif provider == "anthropic":
                model_name = f"anthropic/{model}"
            elif provider == "ollama":
                model_name = f"ollama/{model}"
            elif provider == "azure":
                model_name = f"azure/{model}"
            
            # 设置API基础URL
            if api_base:
                if provider == "openai":
                    os.environ["OPENAI_API_BASE"] = api_base
                elif provider == "anthropic":
                    os.environ["ANTHROPIC_API_BASE"] = api_base
                elif provider == "ollama":
                    os.environ["OLLAMA_API_BASE"] = api_base
            
            # 设置API密钥
            if api_key:
                if provider == "openai":
                    os.environ["OPENAI_API_KEY"] = api_key
                elif provider == "anthropic":
                    os.environ["ANTHROPIC_API_KEY"] = api_key
                elif provider == "azure":
                    os.environ["AZURE_OPENAI_API_KEY"] = api_key
            
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # 如果是Azure，添加额外配置
            extra_params = {}
            if provider == "azure":
                extra_params["api_version"] = self.llm_config.get("api_version", "2023-05-15")
                extra_params["azure_deployment"] = self.llm_config.get("azure_deployment", model)
                extra_params["azure_endpoint"] = api_base
            
            # 调用LiteLLM
            response = await litellm.acompletion(
                model=model_name,
                messages=messages,
                temperature=temperature,
                stream=stream,
                **extra_params
            )
            
            # 提取响应内容
            if stream:
                # 处理流式响应
                full_response = ""
                async for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content_chunk = chunk.choices[0].delta.content
                        full_response += content_chunk
                        
                        # 使用安全回调方法
                        await self._safe_callback(stream_callback, content_chunk)
                
                # 写入调试文件
                self._write_debug(f"=== LLM响应内容（流式） ===")
                self._write_debug(full_response)
                
                return full_response
            else:
                # 处理普通响应
                content = response.choices[0].message.content
                logger.debug(f"LLM响应内容: {content}")
                
                # 写入调试文件
                self._write_debug(f"=== LLM响应内容 ===")
                self._write_debug(content)
                
                return content
                
        except Exception as e:
            error_msg = f"调用LLM时出错: {str(e)}"
            logger.error(error_msg)
            self._write_debug(f"=== 错误 ===")
            self._write_debug(error_msg)
            raise 