"""
Automated Unit & Integration Tests for Stage 3:
Semantic Log Vectorization & FAISS Similarity Search.
"""
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from config import EMBEDDING_DIMENSION
from src.parser import InfrastructureLogParser
from src.embedding_engine import LogEmbeddingEngine
from src.vector_store import FaissVectorStore, SIMILARITY_DISCLAIMER
from src.sample_data import load_sample_log

def test_empty_and_malformed_inputs():
    """Verifies that the embedding engine and vector store safely handle empty and malformed inputs."""
    # 1. Empty DataFrame to embedding engine
    empty_df = pd.DataFrame()
    embeddings, meta = LogEmbeddingEngine.embed_logs(empty_df)
    assert embeddings.shape == (0, EMBEDDING_DIMENSION)
    assert meta == []

    # 2. None or invalid input
    embeddings_none, meta_none = LogEmbeddingEngine.embed_logs(None)
    assert embeddings_none.shape == (0, EMBEDDING_DIMENSION)
    assert meta_none == []

    # 3. Empty query to embed_query
    q_vec = LogEmbeddingEngine.embed_query("   ")
    assert q_vec is None

    # 4. Build index with empty input
    vs = FaissVectorStore(dimension=EMBEDDING_DIMENSION)
    res_empty = vs.build_index(np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32), [])
    assert res_empty["status"] == "EMPTY_INPUT"
    assert vs.get_stats()["total_vectors"] == 0

    # 5. Search on empty index
    res_search_empty = vs.search("database down")
    assert res_search_empty["status"] == "INDEX_EMPTY"
    assert res_search_empty["total_matches"] == 0

    # 6. Search with blank query on empty or populated index
    res_blank = vs.search("   ")
    assert res_blank["status"] == "EMPTY_QUERY"

    print("[PASS] Empty and malformed input handling verified.")

def test_faiss_indexing_and_mapping_with_mock_embeddings():
    """Verifies FAISS indexing and exact 1-to-1 position-to-metadata mapping using mock vectors."""
    dim = EMBEDDING_DIMENSION
    np.random.seed(42)

    # Generate 3 distinct normalized synthetic vectors
    v1 = np.random.randn(1, dim).astype(np.float32)
    v1 /= np.linalg.norm(v1)
    v2 = np.random.randn(1, dim).astype(np.float32)
    v2 /= np.linalg.norm(v2)
    v3 = np.random.randn(1, dim).astype(np.float32)
    v3 /= np.linalg.norm(v3)

    mock_embeddings = np.vstack([v1, v2, v3])

    records = [
        {"line_no": 1, "service": "db-postgres", "message": "Database pool exhausted"},
        {"line_no": 2, "service": "cache-redis", "message": "Memory quota reached"},
        {"line_no": 3, "service": "ingress-gw", "message": "504 Gateway Timeout"}
    ]

    vs = FaissVectorStore(dimension=dim)
    build_res = vs.build_index(mock_embeddings, records)
    assert build_res["status"] == "INDEX_BUILT"
    assert build_res["indexed_count"] == 3

    # Mock embed_query to return v1 exactly
    with patch.object(LogEmbeddingEngine, "embed_query", return_value=v1):
        search_res = vs.search("query matching record 0", top_k=2)
        assert search_res["status"] == "SUCCESS"
        assert search_res["total_matches"] == 2
        # First match must be record 0 with cosine similarity close to 1.0 (100%)
        top_match = search_res["results"][0]
        assert top_match["line_no"] == 1
        assert top_match["service"] == "db-postgres"
        assert abs(top_match["similarity_score"] - 1.0) < 1e-4

    print("[PASS] FAISS indexing and position-to-metadata mapping verified with mock vectors.")

def test_dataset_change_and_index_refresh():
    """Verifies that building a new index completely replaces the previous index and metadata."""
    dim = EMBEDDING_DIMENSION
    vs = FaissVectorStore(dimension=dim)

    # Dataset A (2 vectors)
    vecs_a = np.random.randn(2, dim).astype(np.float32)
    records_a = [{"id": "A1"}, {"id": "A2"}]
    vs.build_index(vecs_a, records_a)
    assert vs.get_stats()["total_vectors"] == 2
    assert vs.metadata_records[0]["id"] == "A1"

    # Dataset B (4 vectors) - simulate user uploading a new dataset
    vecs_b = np.random.randn(4, dim).astype(np.float32)
    records_b = [{"id": "B1"}, {"id": "B2"}, {"id": "B3"}, {"id": "B4"}]
    vs.build_index(vecs_b, records_b)
    assert vs.get_stats()["total_vectors"] == 4
    assert vs.metadata_records[0]["id"] == "B1"
    assert len(vs.metadata_records) == 4

    print("[PASS] Dataset changes and index refresh verified.")

def test_model_loading_error_handling():
    """Verifies that model-loading errors are caught gracefully with descriptive messages."""
    LogEmbeddingEngine.reset_model()

    with patch("sentence_transformers.SentenceTransformer", side_effect=ImportError("Simulated missing package")):
        try:
            LogEmbeddingEngine.get_model()
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "Failed to load embedding model" in str(e)

    # Clean up model state after test
    LogEmbeddingEngine.reset_model()
    print("[PASS] Model-loading error handling verified.")

def test_real_model_integration():
    """
    [INTEGRATION TEST]
    Tests real SentenceTransformer ('all-MiniLM-L6-v2') and FAISS vector index
    using benchmark production incident logs.
    """
    print("\n--- Running Real-Model Integration Test ---")
    log_content = load_sample_log("production_incident.log")
    assert log_content is not None
    df = InfrastructureLogParser.parse_text(log_content)
    assert len(df) > 10

    # 1. Embed logs using real model
    print("Vectorizing logs with SentenceTransformer ('all-MiniLM-L6-v2')...")
    embeddings, records = LogEmbeddingEngine.embed_logs(df)
    assert embeddings.shape[0] == len(df)
    assert embeddings.shape[1] == EMBEDDING_DIMENSION
    assert len(records) == len(df)
    print(f"-> Generated {embeddings.shape[0]} embeddings of dimension {embeddings.shape[1]}.")

    # 2. Index in FAISS
    vs = FaissVectorStore(dimension=EMBEDDING_DIMENSION)
    build_res = vs.build_index(embeddings, records)
    assert build_res["status"] == "INDEX_BUILT"
    assert vs.get_stats()["total_vectors"] == len(df)
    print("-> FAISS IndexFlatIP index built successfully.")

    # 3. Perform semantic similarity search
    query = "database connection failure slots"
    search_res = vs.search(query, top_k=3)
    assert search_res["status"] == "SUCCESS"
    assert len(search_res["results"]) == 3

    # Check top match: Should match database connection logs
    top_result = search_res["results"][0]
    print(f"-> Query: '{query}'")
    print(f"-> Top Match: [{top_result['service']}] {top_result['message']} (Score: {top_result['similarity_pct']}%)")
    assert "db" in top_result["service"].lower() or "connection" in top_result["message"].lower()

    print("[PASS] Real-model integration test passed successfully!")

if __name__ == "__main__":
    print("=" * 65)
    print("Running Stage 3 Test Suite: Semantic Vectorization & FAISS Search")
    print("=" * 65)
    test_empty_and_malformed_inputs()
    test_faiss_indexing_and_mapping_with_mock_embeddings()
    test_dataset_change_and_index_refresh()
    test_model_loading_error_handling()
    test_real_model_integration()
    print("=" * 65)
    print("[SUCCESS] All Stage 3 unit & integration tests passed successfully!")
    print("=" * 65)
