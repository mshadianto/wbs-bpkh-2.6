"""
WBS BPKH AI - Embeddings Service
================================
Text embeddings for RAG using sentence-transformers.
Note: Groq free tier doesn't include embeddings, so we use local model.
"""

from typing import List, Optional
import numpy as np
from loguru import logger

# Use sentence-transformers for embeddings (free, local)
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers not available, using fallback")


class EmbeddingService:
    """
    Embedding Service for text vectorization
    
    Uses sentence-transformers for local embeddings (free, no API needed)
    """
    
    _instance: Optional['EmbeddingService'] = None
    _model = None
    
    # Model selection - multilingual for Indonesian support
    MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIM = 384
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self._initialize_model()
    
    def _initialize_model(self):
        """Initialize embedding model"""
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self._model = SentenceTransformer(self.MODEL_NAME)
                logger.info(f"Loaded embedding model: {self.MODEL_NAME}")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                self._model = None
        else:
            self._model = None
            logger.warning("Using fallback hash-based embeddings")
    
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text"""
        if self._model is not None:
            try:
                embedding = self._model.encode(text, convert_to_numpy=True)
                return embedding.tolist()
            except Exception as e:
                logger.error(f"Embedding error: {e}")
                return self._fallback_embed(text)
        return self._fallback_embed(text)
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts"""
        if self._model is not None:
            try:
                embeddings = self._model.encode(texts, convert_to_numpy=True)
                return embeddings.tolist()
            except Exception as e:
                logger.error(f"Batch embedding error: {e}")
                return [self._fallback_embed(t) for t in texts]
        return [self._fallback_embed(t) for t in texts]
    
    def _fallback_embed(self, text: str) -> List[float]:
        """
        Fallback embedding using hash-based approach
        Not ideal for semantic search but works as placeholder
        """
        # Simple hash-based embedding (for demo purposes)
        np.random.seed(hash(text) % (2**32))
        return np.random.randn(self.EMBEDDING_DIM).tolist()
    
    def cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """Calculate cosine similarity between two embeddings"""
        a = np.array(embedding1)
        b = np.array(embedding2)
        
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))
    
    def find_most_similar(
        self,
        query_embedding: List[float],
        corpus_embeddings: List[List[float]],
        top_k: int = 5
    ) -> List[tuple]:
        """Find most similar embeddings from corpus"""
        similarities = []
        for i, emb in enumerate(corpus_embeddings):
            sim = self.cosine_similarity(query_embedding, emb)
            similarities.append((i, sim))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]


class ChunkingService:
    """Service for chunking documents for embedding"""
    
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending punctuation
                for punct in ['. ', '.\n', '! ', '? ']:
                    last_punct = text[start:end].rfind(punct)
                    if last_punct > self.chunk_size // 2:
                        end = start + last_punct + len(punct)
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - self.chunk_overlap
            
            # Prevent infinite loop
            if start >= len(text):
                break
        
        return chunks
    
    def chunk_with_metadata(
        self,
        text: str,
        source: str,
        doc_type: str
    ) -> List[dict]:
        """Chunk text with metadata for each chunk"""
        chunks = self.chunk_text(text)
        
        return [
            {
                "content": chunk,
                "metadata": {
                    "source": source,
                    "doc_type": doc_type,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                }
            }
            for i, chunk in enumerate(chunks)
        ]


# Export singleton instance
embedding_service = EmbeddingService()
chunking_service = ChunkingService()
