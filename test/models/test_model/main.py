from typing import List, Dict, Optional, Callable, Awaitable
from app.models.base import AnythingBaseModel
import asyncio

class TestModel(AnythingBaseModel):
    """
    Test Model
    This is a simple model for testing the model deployment mechanism.
    It supports basic message processing and streaming output.
    """
    
    async def on_chat_start(self) -> None:
        """Handler for chat start"""
        self.clear_context()
        self.set_context("messages_count", 0)
    
    async def on_chat_messages(
        self,
        messages: List[Dict[str, str]],
        callback: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> Optional[str]:
        """
        Process chat messages, supports streaming output
        In streaming mode, there is a 1-second delay between each output segment
        """
        # Get configuration parameters
        parameters = self.config.get("parameters", {})
        temperature = parameters.get("temperature", 0.7)
        max_tokens = parameters.get("max_tokens", 100)
        top_p = parameters.get("top_p", 1.0)
        
        # Update message count
        count = self.get_context("messages_count", 0) + 1
        self.set_context("messages_count", count)
        
        # Get the last user message
        last_message = None
        for msg in reversed(messages):
            if msg["role"] == "user":
                last_message = msg["content"]
                break
        
        if not last_message:
            response = "No user message found"
            if callback:
                await callback(response)
                return None
            return response
        
        # Build response sequence
        responses = [
            f"[Test Model v{self.config.get('version', '1.0.0')}]\n",
            f"Starting processing...\n",
            f"Configuration parameters:\n",
            f"- temperature: {temperature}\n",
            f"- max_tokens: {max_tokens}\n",
            f"- top_p: {top_p}\n",
            f"This is message #{count}\n",
            f"Received user message: {last_message}\n",
            f"Processing message content...\n"
        ]
        
        # Read vocabulary file and output line by line
        vocab_file = self.data_dir / "vocab.txt"
        if vocab_file.exists():
            vocab_lines = vocab_file.read_text().strip().split('\n')
            responses.append(f"Vocabulary loaded, {len(vocab_lines)} entries in total\n")
            responses.append("Vocabulary contents:\n")
            for line in vocab_lines:
                responses.append(f"- {line}\n")
        
        # Add ending information
        responses.extend([
            "Message processing completed\n",
            "Generating final response...\n",
            "All processing completed!\n"
        ])
        
        if callback:
            # Streaming mode: send line by line with 1-second delay between lines
            for response in responses:
                await callback(response)
                await asyncio.sleep(1)  # 1-second delay
            return None
        else:
            # Normal mode: return complete response
            return "".join(responses)
    
    async def on_chat_end(self) -> None:
        """Handler for chat end"""
        self.clear_context() 