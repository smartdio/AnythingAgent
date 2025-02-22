from typing import List, Dict, Any, Optional, Callable, Awaitable
from abc import ABC, abstractmethod
from pathlib import Path

class AnythingBaseModel(ABC):
    """
    AnythingBaseModel is the base class for all models, defining the interfaces that models must implement.
    """
    
    def __init__(self):
        self.context = {}
        self.config = {}  # Model configuration
        self._model_dir = None  # Model directory path
    
    @property
    def model_dir(self) -> Optional[Path]:
        """Get model directory path"""
        if not self._model_dir:
            # Infer model directory from module path
            module_path = Path(self.__class__.__module__.replace('.', '/'))
            if len(module_path.parts) >= 2 and module_path.parts[-2] == "models":
                self._model_dir = Path("app/models") / module_path.parts[-1]
        return self._model_dir
    
    @model_dir.setter
    def model_dir(self, path: Path):
        """Set model directory path"""
        self._model_dir = path
    
    @property
    def data_dir(self) -> Optional[Path]:
        """Get model data directory path"""
        if self.model_dir:
            return self.model_dir / "data"
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