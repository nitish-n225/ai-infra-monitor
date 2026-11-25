"""
FAISS Vector Store & Semantic Similarity Search Engine.
Indexes dense log vector representations and performs high-speed sub-second similarity search.
"""
from typing import List, Dict, Any, Optional
import numpy as np
from config import EMBEDDING_DIMENSION, DEFAULT_TOP_K
from src.embedding_engine import LogEmbeddingEngine

SIMILARITY_DISCLAIMER = (
    "NOTICE: Semantic similarity measures language and contextual proximity in vector space. "
    "High similarity indicates related log phrasing, but is NOT proof of a common root cause "
    "or identical operational failure."
)

class FaissVectorStore:
    """
    Manages an in-memory FAISS CPU vector index with exact 1-to-1 position-to-metadata mapping.
    Uses Inner Product (IndexFlatIP) on L2-normalized vectors for exact cosine similarity search.
    """

    def __init__(self, dimension: int = EMBEDDING_DIMENSION):
        self.dimension = dimension
        self.index = None
        self.metadata_records: List[Dict[str, Any]] = []

    def build_index(
        self,
        embeddings: np.ndarray,
        records: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Builds a new FAISS CPU IndexFlatIP index from normalized embeddings.

        Parameters:
            embeddings: Float32 numpy array of shape (N, dimension).
            records: List of original log record dicts matching embeddings order.

        Returns:
            Status summary dictionary.
        """
        import faiss

        # Reset previous index
        self.reset()

        if embeddings.size == 0 or len(records) == 0:
            return {
                "status": "EMPTY_INPUT",
                "indexed_count": 0,
                "dimension": self.dimension,
                "message": "Zero log records provided; vector index was not initialized."
            }

        # Validate dimensional alignment
        if embeddings.ndim != 2 or embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: Expected (*, {self.dimension}), got {embeddings.shape}"
            )

        if embeddings.shape[0] != len(records):
            raise ValueError(
                f"Record count mismatch: {embeddings.shape[0]} embeddings vs {len(records)} metadata records"
            )

        # Ensure float32 dtype for FAISS
        vectors = np.ascontiguousarray(embeddings, dtype=np.float32)

        # Create Flat Inner Product index (equivalent to Cosine Similarity for unit vectors)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(vectors)
        self.metadata_records = list(records)

        return {
            "status": "INDEX_BUILT",
            "indexed_count": self.index.ntotal,
            "dimension": self.dimension,
            "message": f"Successfully indexed {self.index.ntotal} log vectors into FAISS."
        }

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        min_similarity: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Executes a semantic similarity search across indexed log vectors using a natural language query.

        Parameters:
            query: Natural language query string.
            top_k: Number of most similar log events to return.
            min_similarity: Optional minimum cosine similarity threshold (range -1.0 to 1.0).

        Returns:
            Dictionary with query, top matches, similarity scores, and metadata.
        """
        clean_query = query.strip() if query else ""
        if not clean_query:
            return {
                "query": "",
                "status": "EMPTY_QUERY",
                "total_matches": 0,
                "results": [],
                "disclaimer": SIMILARITY_DISCLAIMER,
                "message": "Please enter a non-empty search query."
            }

        if self.index is None or self.index.ntotal == 0:
            return {
                "query": clean_query,
                "status": "INDEX_EMPTY",
                "total_matches": 0,
                "results": [],
                "disclaimer": SIMILARITY_DISCLAIMER,
                "message": "The FAISS vector index is empty. Please load or upload logs first."
            }

        # Convert query to normalized sentence vector
        query_vec = LogEmbeddingEngine.embed_query(clean_query)
        if query_vec is None:
            return {
                "query": clean_query,
                "status": "QUERY_EMBEDDING_FAILED",
                "total_matches": 0,
                "results": [],
                "disclaimer": SIMILARITY_DISCLAIMER,
                "message": "Failed to generate vector embedding for the query."
            }

        # Clamp top_k within valid index bounds
        effective_k = min(max(1, top_k), self.index.ntotal)

        # Query FAISS index
        distances, indices = self.index.search(query_vec, effective_k)

        results = []
        for rank, (idx, dist) in enumerate(zip(indices[0], distances[0]), start=1):
            if idx == -1 or idx >= len(self.metadata_records):
                continue

            raw_similarity = float(dist)
            # Inner Product on normalized vectors is cosine similarity (-1.0 to 1.0)
            # Map into positive percentage (0 to 100%) for intuitive human presentation
            similarity_pct = round(max(0.0, min(1.0, (raw_similarity + 1.0) / 2.0)) * 100, 1)

            if min_similarity is None or raw_similarity >= min_similarity:
                rec = self.metadata_records[idx]
                results.append({
                    "rank": rank,
                    "similarity_score": round(raw_similarity, 4),
                    "similarity_pct": similarity_pct,
                    "line_no": rec.get("line_no", 0),
                    "timestamp": rec.get("timestamp", "N/A"),
                    "service": rec.get("service", "unknown"),
                    "level": rec.get("level", "INFO"),
                    "message": rec.get("message", ""),
                    "raw_line": rec.get("raw_line", "")
                })

        return {
            "query": clean_query,
            "status": "SUCCESS",
            "total_matches": len(results),
            "top_k": effective_k,
            "results": results,
            "disclaimer": SIMILARITY_DISCLAIMER,
            "message": f"Retrieved {len(results)} matching log records for query '{clean_query}'."
        }

    def reset(self):
        """Clears the FAISS index and associated metadata mapping."""
        self.index = None
        self.metadata_records = []

    def get_stats(self) -> Dict[str, Any]:
        """Returns diagnostic statistics about the vector store."""
        total = self.index.ntotal if self.index is not None else 0
        return {
            "is_indexed": total > 0,
            "total_vectors": total,
            "dimension": self.dimension
        }
