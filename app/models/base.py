from typing import List, Dict, Any, Optional, Callable, Awaitable
from abc import ABC, abstractmethod
from pathlib import Path
import os
import sys
import yaml
import logging

logger = logging.getLogger(__name__)

class AnythingBaseModel(ABC):
    """
    AnythingBaseModel is the base class for all models, defining the interfaces that models must implement.
    """
    
    def __init__(self):
        self.context = {}
        self.config = {}  # Model configuration
        self._model_dir = None  # Model directory path
        self._load_config()
        self._setup_isolation()
    
    def _load_config(self):
        """Load model configuration from config.yaml"""
        if self.model_dir and (self.model_dir / "config.yaml").exists():
            with open(self.model_dir / "config.yaml", 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
                logger.debug(f"Loaded config for {self.__class__.__name__}: {self.config}")

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