from typing import List, Dict, Optional, Callable, Awaitable
from app.models.base import AnythingBaseModel

class ContextAwareModel(AnythingBaseModel):
    """
    Context-aware model.
    Simple implementation without vector storage dependency.
    """
    
    def __init__(self):
        super().__init__()
        self.contexts = []  # 使用简单的内存列表存储上下文
    
    async def on_chat_start(self) -> None:
        """
        Handler for chat start.
        """
        await super().on_chat_start()
    
    async def on_chat_messages(
        self,
        messages: List[Dict[str, str]],
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Optional[str]:
        """
        Process chat messages.

        Args:
            messages: List of messages.
            callback: Callback function for streaming output, if provided streaming mode is used.

        Returns:
            If non-streaming mode, returns complete response;
            If streaming mode, returns None (content sent through callback).
        """
        query = messages[-1]["content"]
        responses = []

        # 1. Add current message to context
        if callback:
            await callback("Processing your message...\n")
        responses.append("Processing your message...\n")

        # 存储上下文到内存中
        self.contexts.append({
            "content": query,
            "metadata": {
                "type": "user_message",
                "turn": len(messages)
            }
        })

        # 2. Build response directly
        if callback:
            await callback("Message received and processed.\n")
        responses.append("Message received and processed.\n")

        # 3. Generate final response
        final_response = f"\nProcessing completed for your input '{query}'."
        if callback:
            await callback(final_response)
            return None
        
        responses.append(final_response)
        return "".join(responses)
    
    async def on_chat_end(self) -> None:
        """
        Handler for chat end.
        """
        # Cleanup work can be done here
        self.contexts = []  # 清空上下文
        await super().on_chat_end() 