"""
Enterprise Hardening & UI Integrity Tests:
- Verifies Python 3.11-safe UI component imports & XSS escaping
- Verifies lightweight embedding & NumPy vector fallback (no network/PyTorch required)
- Verifies per-session isolation of RealtimeBackendBridge
- Verifies removal of legacy academic/roadmap clutter from UI views
"""
import ast
import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")


def test_ui_modules_compile_and_escape():
    from src.ui.components import (
        esc,
        resource_bar_html,
        render_metric_card,
        render_hero_header,
        render_3d_ai_neural_core,
        render_3d_gauge_pair,
        render_3d_rca_fault_graph,
        render_3d_topology_scene,
        render_3d_vector_constellation,
        render_assistant_faq_grid,
        render_voice_assistant_bar,
    )
    import src.ui.views as views
    import src.ui.live_views as live_views

    # Ensure HTML escaping neutralizes script tags
    escaped = esc('<script>alert("xss")</script>')
    assert "<script>" not in escaped
    assert "&lt;script&gt;" in escaped

    # Ensure resource bar handles None and high load cleanly
    na_bar = resource_bar_html("CPU", None)
    assert "N/A" in na_bar
    hot_bar = resource_bar_html("RAM", 92.4)
    assert "92.4%" in hot_bar and "#ef4444" in hot_bar

    # Ensure legacy roadmap clutter was removed
    app_src = (ROOT_DIR / "app.py").read_text(encoding="utf-8")
    views_src = (ROOT_DIR / "src" / "ui" / "views.py").read_text(encoding="utf-8")
    assert "render_roadmap_tab" not in app_src
    assert "render_roadmap_tab" not in views_src
    assert "College Mini-Project" not in views_src
    assert callable(render_metric_card)
    assert callable(render_hero_header)
    assert callable(render_3d_ai_neural_core)
    assert callable(render_assistant_faq_grid)
    assert callable(render_voice_assistant_bar)
    assert callable(render_3d_gauge_pair)
    assert callable(render_3d_rca_fault_graph)
    assert callable(render_3d_topology_scene)
    assert callable(render_3d_vector_constellation)
    assert hasattr(views, "render_overview_tab")
    assert hasattr(live_views, "render_live_fleet_fragment")

    # Verify app.py parses cleanly
    ast.parse(app_src)
    print("[PASS] UI modules, escaping, and clutter removal verified.")


def test_lightweight_embedding_and_numpy_fallback():
    import pandas as pd
    from src.embedding_engine import LogEmbeddingEngine, lightweight_384_embed
    from src.vector_store import FaissVectorStore

    df = pd.DataFrame([
        {"line_no": 1, "timestamp": "2026-11-26T00:00:00Z", "service": "db-postgres", "level": "CRITICAL", "message": "Database connection pool exhausted"},
        {"line_no": 2, "timestamp": "2026-11-26T00:00:01Z", "service": "cache-redis", "level": "ERROR", "message": "Out of memory limit reached"},
    ])

    old_mode = os.environ.get("LOW_MEMORY_MODE")
    os.environ["LOW_MEMORY_MODE"] = "true"
    try:
        embs, recs, mode = LogEmbeddingEngine.embed_logs_with_fallback(df)
        assert embs.shape == (2, 384)
        assert len(recs) == 2
        assert mode == "lightweight-384"

        # Force NumPy fallback by blocking faiss import
        vs = FaissVectorStore()
        with patch.dict(sys.modules, {"faiss": None}):
            build_res = vs.build_index(embs, recs)
            assert build_res["status"] == "INDEX_BUILT"
            assert build_res["indexed_count"] == 2
            with patch.object(LogEmbeddingEngine, "embed_query", side_effect=RuntimeError("No HF")):
                res = vs.search("database connection pool", top_k=1)
                assert res["status"] == "SUCCESS"
                assert res["total_matches"] == 1
                assert res["results"][0]["service"] == "db-postgres"
    finally:
        if old_mode is None:
            os.environ.pop("LOW_MEMORY_MODE", None)
        else:
            os.environ["LOW_MEMORY_MODE"] = old_mode

    vecs = lightweight_384_embed(["hello world", "empty"])
    assert vecs.shape == (2, 384)
    print("[PASS] Lightweight embeddings and NumPy vector store fallback verified.")


def test_realtime_bridge_session_isolation():
    from src.realtime_client import get_realtime_bridge, _BRIDGE_INSTANCES, _BRIDGE_LOCK

    with patch("src.realtime_client.RealtimeBackendBridge.ensure_started", return_value=None):
        b1 = get_realtime_bridge(token="operator-token-alpha", backend_url="https://example.onrender.com")
        b2 = get_realtime_bridge(token="operator-token-beta", backend_url="https://example.onrender.com")
        b1_again = get_realtime_bridge(token="operator-token-alpha", backend_url="https://example.onrender.com")
        assert b1 is not b2
        assert b1 is b1_again

    with _BRIDGE_LOCK:
        _BRIDGE_INSTANCES.clear()
    print("[PASS] Per-session RealtimeBackendBridge isolation verified.")


def test_csv_and_json_array_upload_parsing():
    from src.parser import InfrastructureLogParser

    csv_text = (
        "Timestamp,Host,Channel,Level,Service,EventID,RCA,Message\n"
        "2026-11-26T09:00:00Z,WIN-01,System,CRITICAL,db-postgres,7031,DATABASE_FAILURE,Connection slots exhausted\n"
        "2026-11-26T09:00:05Z,WIN-01,Application,WARNING,cache-redis,1000,MEMORY_LEAK_OOM,Memory near maxmemory\n"
    )
    df_csv = InfrastructureLogParser.parse_text(csv_text)
    assert len(df_csv) == 2
    assert df_csv.iloc[0]["level"] == "CRITICAL"
    assert df_csv.iloc[0]["service"] == "db-postgres"
    assert df_csv.iloc[1]["level"] == "WARN"

    json_arr = '[{"timestamp": "2026-11-26T09:00:00Z", "level": "ERROR", "service": "auth", "message": "Token expired"}]'
    df_json = InfrastructureLogParser.parse_text(json_arr)
    assert len(df_json) == 1
    assert df_json.iloc[0]["service"] == "auth"
    assert df_json.iloc[0]["message"] == "Token expired"
    print("[PASS] CSV and JSON-array log upload parsing verified.")


def test_assistant_broad_general_queries():
    from src.parser import InfrastructureLogParser
    from src.sample_data import load_sample_log
    from src.rca_engine import RootCauseAnalysisEngine
    from src.health_score import InfrastructureHealthScorer
    from src.predictive_failure import PredictiveFailureDetector
    from src.assistant_engine import InfrastructureAIAssistant

    df = InfrastructureLogParser.parse_text(load_sample_log("production_incident.log"))
    rca = RootCauseAnalysisEngine.analyze_logs(df)
    health = InfrastructureHealthScorer.calculate_health(df)
    risk = PredictiveFailureDetector.assess_risk(df, rca)
    assistant = InfrastructureAIAssistant()

    # Greeting / Help
    r_hi = assistant.ask("hello", df, rca, health, risk, dataset_id="prod")
    assert r_hi["intent"] == "ASSISTANT_HELP"

    # Executive Summary
    r_sum = assistant.ask("Summarize the logs", df, rca, health, risk, dataset_id="prod")
    assert r_sum["intent"] == "EXECUTIVE_SUMMARY"
    assert str(health["health_score"]) in r_sum["answer"]

    # Chronological Timeline
    r_tl = assistant.ask("What happened first in the timeline?", df, rca, health, risk, dataset_id="prod")
    assert r_tl["intent"] == "TIMELINE_ANALYSIS"
    assert len(r_tl["evidence"]) >= 1

    # Service Deep-Dive
    r_svc = assistant.ask("Check cache-redis-01 status", df, rca, health, risk, dataset_id="prod")
    assert r_svc["intent"] == "SERVICE_INSPECTION"
    assert "cache-redis-01" in r_svc["answer"]

    # Counts & Keyword Search
    r_cnt = assistant.ask("How many errors and warnings are there?", df, rca, health, risk, dataset_id="prod")
    assert r_cnt["intent"] == "LOG_STATS_AND_FILTER"

    r_kw = assistant.ask("Tell me about exit code 137", df, rca, health, risk, dataset_id="prod")
    assert r_kw["intent"] in ("KEYWORD_LOG_SEARCH", "ROOT_CAUSE_EXPLANATION")
    assert len(r_kw["evidence"]) >= 1

    # Real health deductions & risk weights (not empty / zero)
    r_h = assistant.ask("How was the health score calculated?", df, rca, health, risk, dataset_id="prod")
    assert "-50.0 pts" in r_h["answer"] or "-18" in r_h["answer"] or "deduction" in r_h["answer"].lower()

    # Anti-hallucination guardrail preserved
    r_unk = assistant.ask("What is the GPU thermal throttling temperature in datacenter zone 4?", df, rca, health, risk, dataset_id="prod")
    assert r_unk["intent"] == "INSUFFICIENT_EVIDENCE"
    print("[PASS] Broad general AI Assistant queries and real health/risk breakdown verified.")


if __name__ == "__main__":
    print("=" * 65)
    print("Running UI Integrity & Enterprise Hardening Tests")
    print("=" * 65)
    test_ui_modules_compile_and_escape()
    test_lightweight_embedding_and_numpy_fallback()
    test_realtime_bridge_session_isolation()
    test_csv_and_json_array_upload_parsing()
    test_assistant_broad_general_queries()
    print("=" * 65)
    print("[SUCCESS] All UI & enterprise hardening checks passed!")
    print("=" * 65)

