"""
Unit and Integration Test Suite for Stage 4: Conversational AI Infrastructure Assistant.
Enterprise Autonomous AI Infrastructure Monitoring System.
"""
import sys
import os
from pathlib import Path
import unittest
import pandas as pd
from typing import Dict, Any

# Ensure UTF-8 output encoding for Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parser import InfrastructureLogParser
from src.sample_data import load_sample_log
from src.rca_engine import RootCauseAnalysisEngine
from src.health_score import InfrastructureHealthScorer
from src.predictive_failure import PredictiveFailureDetector
from src.vector_store import FaissVectorStore
from src.assistant_engine import (
    InfrastructureAIAssistant,
    DeterministicEvidenceProvider,
    OpenAICompatibleProvider,
    BaseLLMProvider,
    SAFETY_ENFORCEMENT_NOTICE
)


class MockFailingCloudProvider(BaseLLMProvider):
    """Mock provider that simulates network/API failures to test deterministic fallback."""
    def __init__(self):
        self.provider_name = "Mock Failing Cloud LLM"
        
    def generate(self, prompt: str, system_context: str):
        raise ConnectionError("Simulated cloud LLM timeout or connection refused")


class MockSuccessfulCloudProvider(BaseLLMProvider):
    """Mock provider that returns a simulated LLM completion."""
    def __init__(self):
        self.provider_name = "Mock Cloud LLM (gpt-4o-mini)"
        
    def generate(self, prompt: str, system_context: str):
        return f"Simulated LLM answer grounded in {len(system_context)} characters of context.", self.provider_name


def setup_test_context():
    """Sets up standard production incident context for assistant testing."""
    sample_text = load_sample_log("production_incident.log")
    df = InfrastructureLogParser.parse_text(sample_text)
    rca = RootCauseAnalysisEngine.analyze_logs(df)
    health = InfrastructureHealthScorer.calculate_health(df)
    risk = PredictiveFailureDetector.assess_risk(df, rca)
    vector_store = FaissVectorStore()
    return df, rca, health, risk, vector_store


def test_incidents_and_affected_services():
    """1. Test questions about critical incidents and affected services."""
    df, rca, health, risk, vs = setup_test_context()
    assistant = InfrastructureAIAssistant()
    
    # Critical incidents question
    res_inc = assistant.ask(
        query="What are the most critical incidents?",
        df=df,
        rca_results=rca,
        health_data=health,
        risk_data=risk,
        vector_store=vs,
        dataset_id="production_incident.log"
    )
    assert res_inc["intent"] == "CRITICAL_INCIDENTS", f"Unexpected intent: {res_inc['intent']}"
    assert res_inc["confidence"] == "HIGH"
    assert "Database Connection" in res_inc["answer"]
    assert "Memory Exhaustion" in res_inc["answer"]
    assert len(res_inc["evidence"]) > 0, "Expected evidence log records attached."

    # Affected services question
    res_svc = assistant.ask(
        query="Which services are affected?",
        df=df,
        rca_results=rca,
        health_data=health,
        risk_data=risk,
        vector_store=vs,
        dataset_id="production_incident.log"
    )
    assert res_svc["intent"] == "AFFECTED_SERVICES"
    assert "db-postgres" in res_svc["answer"]
    assert "cache-redis-01" in res_svc["answer"]
    assert "auth-service" in res_svc["answer"]
    print("[PASS] Questions about incidents and affected services verified.")


def test_evidence_citations_and_root_cause():
    """2. Test root cause questions and source-line evidence citations."""
    df, rca, health, risk, vs = setup_test_context()
    assistant = InfrastructureAIAssistant()
    
    # Database failure explanation
    res_db = assistant.ask(
        query="Why is the database failing?",
        df=df,
        rca_results=rca,
        health_data=health,
        risk_data=risk,
        vector_store=vs,
        dataset_id="production_incident.log"
    )
    assert res_db["intent"] == "ROOT_CAUSE_EXPLANATION"
    assert "Database Connection" in res_db["answer"]
    assert "Observed Operational Facts" in res_db["answer"]
    assert "Inferred Root Cause" in res_db["answer"]
    
    # Verify evidence has exact line numbers and timestamps
    evidence = res_db["evidence"]
    assert len(evidence) > 0
    first_ev = evidence[0]
    assert "line_no" in first_ev and first_ev["line_no"] > 0
    assert "timestamp" in first_ev
    assert "service" in first_ev
    assert "message" in first_ev
    print("[PASS] Evidence citations and source-line mapping verified.")


def test_health_and_risk_explanations():
    """3. Test questions regarding health score calculation and risk factors."""
    df, rca, health, risk, vs = setup_test_context()
    assistant = InfrastructureAIAssistant()
    
    # Health score calculation
    res_health = assistant.ask(
        query="How was the health score calculated?",
        df=df,
        rca_results=rca,
        health_data=health,
        risk_data=risk,
        vector_store=vs,
        dataset_id="production_incident.log"
    )
    assert res_health["intent"] == "HEALTH_SCORE_EXPLANATION"
    assert "100.0%" in res_health["answer"]
    assert "Penalties" in res_health["answer"]
    
    # Risk factors
    res_risk = assistant.ask(
        query="What factors increased the infrastructure risk score?",
        df=df,
        rca_results=rca,
        health_data=health,
        risk_data=risk,
        vector_store=vs,
        dataset_id="production_incident.log"
    )
    assert res_risk["intent"] == "RISK_SCORE_EXPLANATION"
    assert "Predictive Failure Risk" in res_risk["answer"]
    assert "Weight" in res_risk["answer"]
    print("[PASS] Health score breakdown and failure risk explanation verified.")


def test_recovery_recommendations_and_safety():
    """4. Test recovery recommendations and safety execution gate."""
    df, rca, health, risk, vs = setup_test_context()
    assistant = InfrastructureAIAssistant()
    
    res_rec = assistant.ask(
        query="What recovery steps are recommended?",
        df=df,
        rca_results=rca,
        health_data=health,
        risk_data=risk,
        vector_store=vs,
        dataset_id="production_incident.log"
    )
    assert res_rec["intent"] == "RECOVERY_RECOMMENDATIONS"
    assert "Recommended Autonomous Recovery Actions" in res_rec["answer"]
    assert "Dry-Run Simulation" in res_rec["answer"]
    assert "Prerequisites" in res_rec["answer"]
    assert SAFETY_ENFORCEMENT_NOTICE in res_rec["answer"] or res_rec["advisory_notice"] == SAFETY_ENFORCEMENT_NOTICE

    # Critical Safety Test: Attempting to execute recovery action MUST raise RuntimeError
    try:
        assistant.execute_recovery_action("drain-db-pool-action")
        assert False, "Safety policy failed: action execution was not blocked!"
    except RuntimeError as e:
        assert "BLOCKED BY SAFETY POLICY" in str(e)
    print("[PASS] Recovery recommendations and strict safety execution gate verified.")


def test_unknown_queries_and_insufficient_evidence():
    """5. Test unknown queries and insufficient evidence handling without hallucinations."""
    df, rca, health, risk, vs = setup_test_context()
    assistant = InfrastructureAIAssistant()
    
    res_unknown = assistant.ask(
        query="What is the GPU thermal throttling temperature in datacenter zone 4?",
        df=df,
        rca_results=rca,
        health_data=health,
        risk_data=risk,
        vector_store=vs,
        dataset_id="production_incident.log"
    )
    assert res_unknown["intent"] == "INSUFFICIENT_EVIDENCE"
    assert res_unknown["confidence"] == "INSUFFICIENT_EVIDENCE"
    assert "Insufficient Evidence in Active Logs" in res_unknown["answer"]
    assert len(res_unknown["evidence"]) == 0
    print("[PASS] Unknown query and insufficient evidence handling verified (no hallucination).")


def test_empty_logs_and_malformed_input():
    """6. Test empty logs and malformed query inputs."""
    assistant = InfrastructureAIAssistant()
    empty_df = pd.DataFrame(columns=["line_no", "timestamp", "level", "service", "message", "raw_line"])
    empty_rca = {"incidents": [], "total_incidents": 0}
    empty_health = {"health_score": 100.0, "condition": "Stable", "penalties": []}
    empty_risk = {"risk_score": 0.0, "risk_level": "LOW", "contributing_factors": []}
    
    # Empty query
    res_empty_q = assistant.ask("", empty_df, empty_rca, empty_health, empty_risk)
    assert res_empty_q["intent"] == "EMPTY_QUERY"
    assert "Please ask a question" in res_empty_q["answer"]
    
    # Empty dataset
    res_empty_data = assistant.ask("Why is DB failing?", empty_df, empty_rca, empty_health, empty_risk)
    assert res_empty_data["intent"] == "NO_DATA"
    assert "No Active Logs Found" in res_empty_data["answer"]
    print("[PASS] Empty logs and malformed input handling verified.")


def test_dataset_switching_and_session_history():
    """7. Test session history tracking and dataset switching context reset."""
    df, rca, health, risk, vs = setup_test_context()
    assistant = InfrastructureAIAssistant()
    
    # Ask first question
    assistant.ask("Why is database failing?", df, rca, health, risk, vs, dataset_id="dataset_A.log")
    assert len(assistant.get_history()) == 2 # 1 user, 1 assistant
    assert assistant.current_dataset_id == "dataset_A.log"
    
    # Ask second question on same dataset
    assistant.ask("Which services are affected?", df, rca, health, risk, vs, dataset_id="dataset_A.log")
    assert len(assistant.get_history()) == 4
    
    # Switch to dataset_B: history must reset to prevent stale context
    assistant.ask("Why is database failing?", df, rca, health, risk, vs, dataset_id="dataset_B.log")
    assert assistant.current_dataset_id == "dataset_B.log"
    assert len(assistant.get_history()) == 2 # Reset and added new Q&A
    print("[PASS] Dataset switching and session history reset verified.")


def test_provider_fallback_on_failure():
    """8. Test provider fallback when a cloud provider encounters network errors."""
    df, rca, health, risk, vs = setup_test_context()
    failing_provider = MockFailingCloudProvider()
    assistant = InfrastructureAIAssistant(provider=failing_provider)
    
    # Should not crash; must fall back to deterministic response with warning
    res = assistant.ask("Why is the database failing?", df, rca, health, risk, vs, dataset_id="production_incident.log")
    assert "Deterministic Fallback" in res["provider"]
    assert "Database Connection" in res["answer"]
    assert len(res["evidence"]) > 0

    # Test successful mock provider
    success_provider = MockSuccessfulCloudProvider()
    assistant_success = InfrastructureAIAssistant(provider=success_provider)
    res_succ = assistant_success.ask("Why is the database failing?", df, rca, health, risk, vs, dataset_id="production_incident.log")
    assert "Mock Cloud LLM" in res_succ["provider"]
    assert "Simulated LLM answer" in res_succ["answer"]
    print("[PASS] Cloud provider error handling and deterministic fallback verified.")


if __name__ == "__main__":
    print("=================================================================")
    print("Running Stage 4 Test Suite: Conversational AI Assistant")
    print("=================================================================")
    test_incidents_and_affected_services()
    test_evidence_citations_and_root_cause()
    test_health_and_risk_explanations()
    test_recovery_recommendations_and_safety()
    test_unknown_queries_and_insufficient_evidence()
    test_empty_logs_and_malformed_input()
    test_dataset_switching_and_session_history()
    test_provider_fallback_on_failure()
    print("=================================================================")
    print("[SUCCESS] All Stage 4 unit & integration tests passed successfully!")
    print("=================================================================")
