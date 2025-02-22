from typing import List, Dict, Optional, Callable, Awaitable
from app.models.base import AnythingBaseModel

class EchoModel(AnythingBaseModel):
    """
    Echo model for testing. Simply returns the user's last message with some context information.
    """
    
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
        # Get the last user message
        last_user_message = None
        for message in reversed(messages):
            if message["role"] == "user":
                last_user_message = message["content"]
                break
        
        if not last_user_message:
            response = "No user message found."
            if callback:
                await callback(response)
                return None
            return response
        
        # Get conversation turns
        conversation_turns = self.get_context("turns", 0) + 1
        self.set_context("turns", conversation_turns)
        
        # Build response
        responses = [
            f"[Echo Model - Turn {conversation_turns}]\n",
            f"I received your message: {last_user_message}\n",
            f"Current context contains {len(self.context)} key-value pairs."
        ]
        
        if callback:
            # Streaming mode: send line by line
            for response in responses:
                await callback(response)
            return None
        else:
            # Non-streaming mode: return complete response
            return "".join(responses)
    
    async def on_chat_start(self) -> None:
        """
        Handler for chat start.
        """
        self.clear_context()
        self.set_context("turns", 0)
        
    async def on_chat_end(self) -> None:
        """
        Handler for chat end.
        """
        self.clear_context() 