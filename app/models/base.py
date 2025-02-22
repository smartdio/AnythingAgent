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
        print(f"[DEBUG] Current Python path: {sys.path}")
        print(f"[DEBUG] Current working directory: {os.getcwd()}")
        
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
            python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
            site_packages = venv_path / "lib" / python_version / "site-packages"

        site_packages = site_packages.resolve()  # 获取绝对路径
        print(f"[DEBUG] Site-packages path: {site_packages}")

        if site_packages.exists():
            if str(site_packages) not in sys.path:
                print(f"[DEBUG] Adding {site_packages} to Python path")
                sys.path.insert(0, str(site_packages))
                print(f"[DEBUG] Updated Python path: {sys.path}")
            else:
                print("[DEBUG] Site-packages already in Python path")
        else:
            print("[DEBUG] Site-packages directory not found")
    
    @property
    def model_dir(self) -> Optional[Path]:
        """Get model directory path"""
        if not self._model_dir:
            # Infer model directory from module path
            module_path = Path(self.__class__.__module__.replace('.', '/'))
            if len(module_path.parts) >= 2 and module_path.parts[-2] == "models":
                self._model_dir = Path("models") / module_path.parts[-1]
                self._model_dir = self._model_dir.resolve()  # 获取绝对路径
                logger.debug(f"Inferred model directory: {self._model_dir}")
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