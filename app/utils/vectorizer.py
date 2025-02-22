from typing import List, Union
import numpy as np

class SimpleVectorizer:
    """
    Simple text vectorization tool.
    This is a sample implementation, in practice more advanced vectorization methods (like Sentence Transformers) should be used.
    """
    
    def __init__(self, vector_size: int = 1536):
        self.vector_size = vector_size
    
    def encode(self, text: Union[str, List[str]]) -> np.ndarray:
        """
        Encode text into vector.
        This is a simple implementation for testing only. In practice, pre-trained models should be used.

        Args:
            text: Input text or list of texts.

        Returns:
            Vector or list of vectors.
        """
        if isinstance(text, str):
            # Simple hash vectorization
            vector = np.zeros(self.vector_size, dtype=np.float32)
            for i, char in enumerate(text):
                vector[i % self.vector_size] += ord(char) / 255.0
            # Normalize
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector /= norm
            return vector
        else:
            return np.array([self.encode(t) for t in text])
    
    def decode(self, vector: np.ndarray) -> str:
        """
        Decode vector to text (for demonstration only, not typically needed in practice).

        Args:
            vector: Input vector.

        Returns:
            Decoded text (returns a placeholder here).
        """
        return "[Vector representation]"

# Create global vectorizer instance
vectorizer = SimpleVectorizer() 