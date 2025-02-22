from typing import List, Dict, Any, Optional
import numpy as np
import json
from app.db.base import db
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("vector_store")

class VectorStore:
    """
    Vector store manager for managing vectorized storage of model descriptions and contexts.
    """
    
    def __init__(self):
        self.models_table = db.get_table("models")
        self.contexts_table = db.get_table("contexts")
    
    async def add_model_description(
        self,
        model_id: str,
        description: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add model description and its vector representation.

        Args:
            model_id: Model ID.
            description: Model description.
            vector: Vector representation.
            metadata: Additional metadata.

        Returns:
            Whether the addition was successful.
        """
        try:
            metadata_dict = {
                "description": description,
                **(metadata or {})
            }
            data = {
                "id": model_id,
                "vector": np.array(vector, dtype=np.float32),
                "metadata": json.dumps(metadata_dict)
            }
            self.models_table.add([data])
            logger.info(f"Added model description: {model_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding model description: {e}")
            return False
    
    async def search_models(
        self,
        query_vector: List[float],
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar models.

        Args:
            query_vector: Query vector.
            limit: Maximum number of results to return.

        Returns:
            List of similar models.
        """
        try:
            results = self.models_table.search(
                query_vector,
                limit=limit
            ).to_list()
            
            # Parse metadata
            for result in results:
                if isinstance(result.get("metadata"), str):
                    result["metadata"] = json.loads(result["metadata"])
            
            return results
        except Exception as e:
            logger.error(f"Error searching models: {e}")
            return []
    
    async def add_context(
        self,
        context_id: str,
        content: str,
        vector: List[float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add context and its vector representation.

        Args:
            context_id: Context ID.
            content: Context content.
            vector: Vector representation.
            metadata: Additional metadata.

        Returns:
            Whether the addition was successful.
        """
        try:
            metadata_dict = {
                "content": content,
                **(metadata or {})
            }
            data = {
                "id": context_id,
                "vector": np.array(vector, dtype=np.float32),
                "metadata": json.dumps(metadata_dict)
            }
            self.contexts_table.add([data])
            logger.info(f"Added context: {context_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding context: {e}")
            return False
    
    async def search_contexts(
        self,
        query_vector: List[float],
        limit: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant contexts.

        Args:
            query_vector: Query vector.
            limit: Maximum number of results to return.
            metadata_filter: Metadata filter conditions.

        Returns:
            List of relevant contexts.
        """
        try:
            query = self.contexts_table.search(
                query_vector,
                limit=limit
            )
            
            results = query.to_list()
            
            # Parse metadata
            filtered_results = []
            for result in results:
                if isinstance(result.get("metadata"), str):
                    result["metadata"] = json.loads(result["metadata"])
                
                # Apply metadata filter
                if metadata_filter:
                    matches = True
                    for key, value in metadata_filter.items():
                        if result["metadata"].get(key) != value:
                            matches = False
                            break
                    if matches:
                        filtered_results.append(result)
                else:
                    filtered_results.append(result)
            
            return filtered_results
        except Exception as e:
            logger.error(f"Error searching contexts: {e}")
            return []
    
    async def delete_model(self, model_id: str) -> bool:
        """
        Delete model description.

        Args:
            model_id: Model ID.

        Returns:
            Whether the deletion was successful.
        """
        try:
            # TODO: Implement delete functionality
            logger.warning("Delete model function not implemented yet")
            return True
        except Exception as e:
            logger.error(f"Error deleting model: {e}")
            return False
    
    async def delete_context(self, context_id: str) -> bool:
        """
        Delete context.

        Args:
            context_id: Context ID.

        Returns:
            Whether the deletion was successful.
        """
        try:
            # TODO: Implement delete functionality
            logger.warning("Delete context function not implemented yet")
            return True
        except Exception as e:
            logger.error(f"Error deleting context: {e}")
            return False

# Create global vector store instance
vector_store = VectorStore() 