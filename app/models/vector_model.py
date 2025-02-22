from typing import List, Dict, Any, Optional
from app.models.base import AnythingBaseModel
from app.utils.vectorizer import vectorizer
from app.db.vector_store import vector_store
from app.utils.common import generate_id

class VectorModel(AnythingBaseModel):
    """
    Base class for models supporting vector retrieval.
    Provides context retrieval functionality based on vector similarity.
    """
    
    def __init__(self):
        super().__init__()
        self.model_id = generate_id("model-")
    
    async def add_to_vector_store(self, description: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Add model description to vector store.

        Args:
            description: Model description.
            metadata: Additional metadata.

        Returns:
            Whether the addition was successful.
        """
        vector = vectorizer.encode(description)
        return await vector_store.add_model_description(
            self.model_id,
            description,
            vector.tolist(),
            metadata
        )
    
    async def search_similar_contexts(
        self,
        query: str,
        limit: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar contexts.

        Args:
            query: Query text.
            limit: Maximum number of results to return.
            metadata_filter: Metadata filter conditions.

        Returns:
            List of similar contexts.
        """
        vector = vectorizer.encode(query)
        return await vector_store.search_contexts(
            vector.tolist(),
            limit=limit,
            metadata_filter=metadata_filter
        )
    
    async def add_context(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add context to vector store.

        Args:
            content: Context content.
            metadata: Additional metadata.

        Returns:
            Whether the addition was successful.
        """
        context_id = generate_id("ctx-")
        vector = vectorizer.encode(content)
        
        # Add model ID to metadata
        metadata = metadata or {}
        metadata["model_id"] = self.model_id
        
        return await vector_store.add_context(
            context_id,
            content,
            vector.tolist(),
            metadata
        )
    
    async def on_chat_messages(self, messages: List[Dict[str, str]]) -> str:
        """
        Process chat messages.
        This base class implementation searches for similar contexts and returns them.
        Subclasses should override this method to implement specific processing logic.

        Args:
            messages: List of messages.

        Returns:
            Response text.
        """
        # Get the last user message
        last_user_message = None
        for message in reversed(messages):
            if message["role"] == "user":
                last_user_message = message["content"]
                break
        
        if not last_user_message:
            return "No user message found."
        
        # Search for relevant contexts
        contexts = await self.search_similar_contexts(
            last_user_message,
            limit=3,
            metadata_filter={"model_id": self.model_id}
        )
        
        # Build response
        response = f"Found {len(contexts)} relevant contexts:\n\n"
        for i, ctx in enumerate(contexts, 1):
            response += f"{i}. {ctx['metadata']['content']}\n"
        
        return response 