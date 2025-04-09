from typing import List, Dict, Any, Optional, Callable, Awaitable
from abc import ABC, abstractmethod
from pathlib import Path
import os
import sys
import yaml
import logging
import datetime
from dotenv import load_dotenv
from app.schemas.chat import Message
logger = logging.getLogger(__name__)

class AnythingBaseModel(ABC):
    """
    AnythingBaseModel是所有模型的基类，定义了模型必须实现的接口。
    提供了基础的配置加载和环境隔离功能。
    支持配置文件热更新，在初始化和方法调用时自动重新加载。
    """
    
    def __init__(self):
        # 加载环境变量
        load_dotenv()
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"init AnythingBaseModel at {current_time}")
        
        self.context = {}
        self.config = {}  # 模型配置
        self._model_dir = None  # 模型目录路径
        self.debug_file = None  # 调试文件
        
        # 加载配置
        self._load_config()
        
        # 初始化调试文件
        self._init_debug_file()
        
        # 设置环境隔离
        self._setup_isolation()
    
    def _load_config(self):
        """
        加载模型配置
        每次调用都重新从磁盘读取配置文件
        """
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        print(f"[DEBUG] {current_time} - 加载配置文件 - 实例ID: {id(self)}")
        
        if self.model_dir and (self.model_dir / "config.yaml").exists():
            config_path = self.model_dir / "config.yaml"
            print(f"[DEBUG] 找到配置文件: {config_path}")
            
            try:
                # 直接读取文件内容
                with open(config_path, 'r', encoding='utf-8') as f:
                    old_config = self.config.copy() if self.config else {}
                    self.config = yaml.safe_load(f)
                    config_changed = old_config != self.config
                    
                    # 记录日志
                    print(f"[DEBUG] 配置{'已更新' if config_changed else '未变化'}")
                    if config_changed:
                        logger.info(f"为 {self.__class__.__name__} 加载新配置")
                        self._write_debug(f"配置文件更新: {self.config}")
            except Exception as e:
                logger.error(f"加载配置文件时出错: {str(e)}")
                print(f"[DEBUG] 加载配置文件失败: {str(e)}")
        else:
            if not self.model_dir:
                print(f"[DEBUG] 模型目录未设置")
            else:
                print(f"[DEBUG] 配置文件不存在: {self.model_dir / 'config.yaml'}")
    
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
                f.write(f"配置: {yaml.dump(self.config, allow_unicode=True)}\n\n")
            
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
            try:
                # 获取模型类的模块文件路径
                class_module = self.__class__.__module__
                print(f"[DEBUG] 当前类 {self.__class__.__name__} 的模块: {class_module}")
                
                if class_module not in sys.modules:
                    print(f"[DEBUG] 错误: 模块 {class_module} 不在 sys.modules 中")
                    print(f"[DEBUG] 可用模块: {list(sys.modules.keys())[:20]}...")  # 只打印前20个避免信息过多
                    return None
                
                module_file = Path(sys.modules[class_module].__file__)
                print(f"[DEBUG] 模块文件路径: {module_file}")
                
                # 如果模块文件在 models 目录下，使用其所在目录作为模型目录
                if "models" in module_file.parts:
                    models_index = module_file.parts.index("models")
                    # 修改目录获取方式，确保获取到子类所在的具体模型目录
                    self._model_dir = Path(*module_file.parts[:models_index+2])
                    
                    # 特殊处理：如果是多级结构如 models/agent_type/agent_name
                    # 这里假设子类的实现文件放在其专属目录下
                    module_dir = module_file.parent
                    if module_dir.name != self._model_dir.name:
                        # 如果模块所在目录名与models下一级目录名不同
                        # 可能是更深层次的结构，使用模块所在目录
                        self._model_dir = module_dir
                    
                    self._model_dir = self._model_dir.resolve()  # 获取绝对路径
                    print(f"[DEBUG] 推断的模型目录: {self._model_dir}")
                    
                    # 检查推断的目录中是否存在配置文件
                    if not (self._model_dir / "config.yaml").exists():
                        print(f"[DEBUG] 警告: 推断的目录中没有找到 config.yaml 文件")
                        
                        # 尝试查找更接近实际实现的目录
                        parent_dir = module_file.parent
                        if (parent_dir / "config.yaml").exists():
                            self._model_dir = parent_dir
                            print(f"[DEBUG] 使用替代模型目录: {self._model_dir}")
                else:
                    print(f"[DEBUG] 警告: 模块文件路径中没有 'models' 目录")
            except Exception as e:
                print(f"[DEBUG] 获取模型目录时出错: {str(e)}")
                import traceback
                print(f"[DEBUG] 错误详情: {traceback.format_exc()}")
                return None
        
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
        messages: List[Message],
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
        # 在处理消息前重新加载配置
        self._load_config()
        pass

    async def on_chat_start(self) -> None:
        """
        Hook method called when chat starts.
        """
        # 在聊天开始前重新加载配置
        self._load_config()
        pass

    async def on_chat_end(self) -> None:
        """
        Hook method called when chat ends.
        """
        # 在聊天结束前重新加载配置
        self._load_config()
        pass

    async def on_chat_stop(self) -> None:
        """
        Hook method called when chat stops.
        """
        # 在聊天停止前重新加载配置
        self._load_config()
        pass

    async def on_chat_resume(self, thread: str) -> None:
        """
        Hook method called when chat resumes.

        Args:
            thread: Chat thread identifier.
        """
        # 在聊天恢复前重新加载配置
        self._load_config()
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