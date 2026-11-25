"""
Semantic Log Embedding Engine.
Converts normalized infrastructure logs into dense numerical vectors
using the SentenceTransformer 'all-MiniLM-L6-v2' model.
"""
from typing import List, Dict, Any, Tuple, Optional, Union
import numpy as np
import pandas as pd
from config import EMBEDDING_MODEL_NAME, EMBEDDING_DIMENSION

class LogEmbeddingEngine:
    """
    Manages lazy loading and batch vectorization of infrastructure log entries.
    Employs SentenceTransformer 'all-MiniLM-L6-v2' (384-dimensional dense vectors).
    """

    _model = None
    _model_error = None

    @classmethod
    def get_model(cls):
        """
        Lazily loads the SentenceTransformer model on first invocation.
        Caches the model in memory to prevent duplicate downloads and initialization overhead.
        """
        if cls._model is not None:
            return cls._model
        if cls._model_error is not None:
            raise RuntimeError(f"SentenceTransformer initialization failed previously: {cls._model_error}")

        try:
            from sentence_transformers import SentenceTransformer
            # Load all-MiniLM-L6-v2 model
            cls._model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            return cls._model
        except Exception as e:
            cls._model_error = str(e)
            raise RuntimeError(
                f"Failed to load embedding model '{EMBEDDING_MODEL_NAME}'. "
                f"Ensure internet connectivity for initial model weights download. Details: {e}"
            )

    @classmethod
    def is_model_loaded(cls) -> bool:
        """Returns True if the model has already been loaded into memory."""
        return cls._model is not None

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """Returns the current availability status of the embedding engine."""
        return {
            "model_name": EMBEDDING_MODEL_NAME,
            "dimension": EMBEDDING_DIMENSION,
            "is_loaded": cls._model is not None,
            "error": cls._model_error
        }

    @classmethod
    def reset_model(cls):
        """Resets cached model reference (used for test teardown and mock testing)."""
        cls._model = None
        cls._model_error = None

    @classmethod
    def format_log_for_embedding(cls, record: Dict[str, Any]) -> str:
        """
        Constructs a semantically contextual string from a log record.
        Format: '[service] [level] message'
        """
        service = str(record.get("service", "infrastructure")).strip()
        level = str(record.get("level", "INFO")).strip().upper()
        msg = str(record.get("message", "")).strip()
        if not msg:
            msg = str(record.get("raw_line", "")).strip()
        return f"[{service}] [{level}] {msg}"

    @classmethod
    def embed_logs(
        cls,
        logs_data: Union[pd.DataFrame, List[Dict[str, Any]]],
        batch_size: int = 32
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Converts normalized log records into L2-normalized dense sentence embeddings.

        Parameters:
            logs_data: pandas DataFrame or list of log record dicts.
            batch_size: Batch size for model inference.

        Returns:
            Tuple of:
                - embeddings (np.ndarray of shape (N, 384), float32)
                - metadata_records (List of preserved original log dicts)
        """
        # Convert DataFrame to records list if necessary
        if isinstance(logs_data, pd.DataFrame):
            if logs_data.empty:
                return np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32), []
            records = logs_data.to_dict(orient="records")
        elif isinstance(logs_data, list):
            records = [r for r in logs_data if isinstance(r, dict)]
        else:
            return np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32), []

        if not records:
            return np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32), []

        # Extract contextual texts for embedding
        texts_to_embed = [cls.format_log_for_embedding(r) for r in records]

        # Acquire model (raises descriptive error if unavailable)
        model = cls.get_model()

        # Generate L2-normalized embeddings so Inner Product equals Cosine Similarity
        embeddings = model.encode(
            texts_to_embed,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True
        )

        embeddings_np = np.asarray(embeddings, dtype=np.float32)
        return embeddings_np, records

    @classmethod
    def embed_query(cls, query: str) -> Optional[np.ndarray]:
        """
        Encodes a single natural language search query into an L2-normalized vector.

        Returns:
            np.ndarray of shape (1, 384) with float32 dtype, or None if query is blank.
        """
        clean_query = query.strip() if query else ""
        if not clean_query:
            return None

        model = cls.get_model()
        query_vec = model.encode(
            [clean_query],
            show_progress_bar=False,
            normalize_embeddings=True
        )
        return np.asarray(query_vec, dtype=np.float32)
