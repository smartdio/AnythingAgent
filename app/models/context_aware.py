from typing import List, Dict, Optional, Callable, Awaitable
from app.models.vector_model import VectorModel

class ContextAwareModel(VectorModel):
    """
    Context-aware model.
    Capable of providing more intelligent responses based on conversation history and similarity search.
    """
    
    async def on_chat_start(self) -> None:
        """
        Handler for chat start.
        """
        await super().on_chat_start()
        # Add model description to vector store
        await self.add_to_vector_store(
            "This is a context-aware model that can remember conversation history and use similarity search to provide more intelligent responses.",
            metadata={
                "type": "context_aware",
                "capabilities": ["context_search", "history_tracking"]
            }
        )
    
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

        await self.add_context(
            query,
            metadata={
                "type": "user_message",
                "turn": len(messages)
            }
        )

        # 2. Search for relevant contexts
        if callback:
            await callback("Searching for relevant contexts...\n")
        responses.append("Searching for relevant contexts...\n")

        contexts = await self.search_similar_contexts(
            query,
            limit=3,
            metadata_filter={"model_id": self.model_id}
        )

        # 3. Build response
        if contexts:
            if callback:
                await callback("Found the following relevant contexts:\n")
            responses.append("Found the following relevant contexts:\n")

            for i, ctx in enumerate(contexts, 1):
                response = f"{i}. {ctx['metadata']['content']}\n"
                if callback:
                    await callback(response)
                responses.append(response)
        else:
            response = "No relevant historical context found.\n"
            if callback:
                await callback(response)
            responses.append(response)

        # 4. Generate final response
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
        await super().on_chat_end() 