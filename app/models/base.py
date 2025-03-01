from typing import List, Dict, Any, Optional, Callable, Awaitable
from abc import ABC, abstractmethod
from pathlib import Path
import os
import sys
import yaml
import logging
import json
import datetime
from dotenv import load_dotenv

# 尝试导入litellm，如果不存在则设置为None
try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

logger = logging.getLogger(__name__)

class AnythingBaseModel(ABC):
    """
    AnythingBaseModel是所有模型的基类，定义了模型必须实现的接口。
    提供了基础的LLM管理功能，包括配置加载、环境变量处理和LLM调用。
    """
    
    def __init__(self):
        # 加载环境变量
        load_dotenv()
        
        self.context = {}
        self.config = {}  # 模型配置
        self._model_dir = None  # 模型目录路径
        self.llm_config = None  # LLM配置
        self.debug_file = None  # 调试文件
        
        # 加载配置
        self._load_config()
        
        # 初始化LLM配置
        self._init_llm()
        
        # 初始化调试文件
        self._init_debug_file()
        
        # 设置环境隔离
        self._setup_isolation()
    
    def _load_config(self):
        """加载模型配置"""
        if self.model_dir and (self.model_dir / "config.yaml").exists():
            try:
                with open(self.model_dir / "config.yaml", 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
                    logger.debug(f"为 {self.__class__.__name__} 加载配置: {self.config}")
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
            model_name = self.__class__.__name__.lower()
            self.debug_file = debug_dir / f"{model_name}_debug_{timestamp}.log"
            
            # 写入初始信息
            with open(self.debug_file, "w", encoding="utf-8") as f:
                f.write(f"=== {self.__class__.__name__} 调试日志 - {timestamp} ===\n\n")
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

    async def _call_llm(
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

    def _setup_isolation(self):
        """Setup environment isolation if enabled in config"""
        print(f"\n[DEBUG] Setting up isolation for {self.__class__.__name__}")
        print(f"[DEBUG] Model directory: {self.model_dir}")
        print(f"[DEBUG] Config: {self.config}")
        
        if not self.config.get("isolation", {}).get("enabled", False):
            print("[DEBUG] Isolation not enabled in config")
            return

        venv_path = self.model_dir / "venv"
        print(f"[DEBUG] Virtual environment path: {venv_path}")
        
        if not venv_path.exists():
            print("[DEBUG] Virtual environment directory not found")
            return

        # Check if virtual environment is ready
        env_ready_file = venv_path / ".env_ready"
        print(f"[DEBUG] Checking for .env_ready file: {env_ready_file}")
        if not env_ready_file.exists():
            print("[DEBUG] .env_ready file not found")
            return

        # Add virtual environment's site-packages to Python path
        if sys.platform == "win32":
            site_packages = venv_path / "Lib" / "site-packages"
        else:
            # 从配置文件中获取 Python 版本
            python_version = self.config.get("isolation", {}).get("python_version", f"{sys.version_info.major}.{sys.version_info.minor}")
            if python_version.startswith("python"):
                python_version = python_version[6:]  # 移除 "python" 前缀
            site_packages = venv_path / "lib" / f"python{python_version}" / "site-packages"

        site_packages = site_packages.resolve()  # 获取绝对路径
        print(f"[DEBUG] Site-packages path: {site_packages}")
        print(f"[DEBUG] Site-packages exists: {site_packages.exists()}")
        
        if site_packages.exists():
            print(f"[DEBUG] Site-packages contents: {list(site_packages.iterdir())}")
            
            # 清理 Python 路径，只保留系统路径和虚拟环境路径
            original_sys_path = list(sys.path)
            project_root = str(Path(__file__).parent.parent.parent)  # 项目根目录
            
            # 过滤路径，只保留 Python 3.12 相关的路径
            sys.path = [
                p for p in original_sys_path if any([
                    project_root in p,  # 项目根目录
                    "python3.12" in p,  # Python 3.12 系统路径
                    "python312.zip" in p,  # Python 3.12 标准库
                    str(site_packages) in p  # 虚拟环境路径
                ]) and not any([
                    "python3.11" in p,  # 排除 Python 3.11 路径
                    "python311" in p
                ])
            ]
            
            # 确保虚拟环境路径和项目根目录在最前面
            if project_root not in sys.path:
                sys.path.insert(0, project_root)
            if str(site_packages) not in sys.path:
                sys.path.insert(0, str(site_packages))
            
            print(f"[DEBUG] Project root: {project_root}")
            print(f"[DEBUG] Updated Python path: {sys.path}")
            
        else:
            print("[DEBUG] Site-packages directory not found")
    
    @property
    def model_dir(self) -> Optional[Path]:
        """Get model directory path"""
        if not self._model_dir:
            # 获取模型类的模块文件路径
            module_file = Path(sys.modules[self.__class__.__module__].__file__)
            print(f"[DEBUG] Module file path: {module_file}")
            
            # 如果模块文件在 models 目录下，使用其所在目录作为模型目录
            if "models" in module_file.parts:
                models_index = module_file.parts.index("models")
                self._model_dir = Path(*module_file.parts[:models_index+2])
                self._model_dir = self._model_dir.resolve()  # 获取绝对路径
                print(f"[DEBUG] Inferred model directory: {self._model_dir}")
                
        return self._model_dir
    
    @model_dir.setter
    def model_dir(self, path: Path):
        """Set model directory path"""
        self._model_dir = path
    
    @property
    def data_dir(self) -> Optional[Path]:
        """Get model data directory path"""
        if self.model_dir:
            return self.model_dir / "vocab_data"
        return None
    
    @abstractmethod
    async def on_chat_messages(
        self,
        messages: List[Dict[str, str]],
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Optional[str]:
        """
        Core method for processing chat messages.
        If callback is provided, it's streaming mode, content is sent through callback;
        If no callback is provided, it's normal mode, returns complete response.

        Args:
            messages: List of messages, each message is a dictionary containing role and content
            callback: Async callback function for streaming output. If None, non-streaming mode

        Returns:
            If non-streaming mode (callback=None), returns complete response string
            If streaming mode (callback not None), returns None, content sent through callback
        """
        pass

    async def on_chat_start(self) -> None:
        """
        Hook method called when chat starts.
        """
        pass

    async def on_chat_end(self) -> None:
        """
        Hook method called when chat ends.
        """
        pass

    async def on_chat_stop(self) -> None:
        """
        Hook method called when chat stops.
        """
        pass

    async def on_chat_resume(self, thread: str) -> None:
        """
        Hook method called when chat resumes.

        Args:
            thread: Chat thread identifier.
        """
        pass

    def set_context(self, key: str, value: Any) -> None:
        """
        Set context information.

        Args:
            key: Context key.
            value: Context value.
        """
        self.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """
        Get context information.

        Args:
            key: Context key.
            default: Default value.

        Returns:
            Context value.
        """
        return self.context.get(key, default)

    def clear_context(self) -> None:
        """
        Clear all context information.
        """
        self.context.clear() 