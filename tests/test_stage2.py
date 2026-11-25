"""
Automated Unit Tests for Stage 2:
Root Cause Analysis (RCA), Predictive Failure Risk, Health Scoring, and Self-Healing.
"""
import sys
import os
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.parser import InfrastructureLogParser
from src.rca_engine import RootCauseAnalysisEngine
from src.predictive_failure import PredictiveFailureDetector
from src.health_score import InfrastructureHealthScorer
from src.self_healing import SelfHealingEngine, SAFETY_POLICY_DISCLAIMER
from src.sample_data import load_sample_log

def test_six_incident_categories():
    """Verifies that all 6 incident categories are detected and classified with supporting evidence."""
    test_cases = [
        ("DATABASE_FAILURE", "2026-10-25 10:00:00 [ERROR] [db-postgres] FATAL: remaining connection slots reserved"),
        ("CPU_OVERLOAD", "2026-10-25 10:00:00 [WARN] [k8s-node-1] CPU utilization high saturation 98%"),
        ("MEMORY_LEAK_OOM", "2026-10-25 10:00:00 [FATAL] [k8s-kubelet] Pod terminated: OOMKilled exit code 137"),
        ("STORAGE_FAILURE", "2026-10-25 10:00:00 [CRITICAL] [storage-node] No space left on device disk full"),
        ("AUTHENTICATION_FAILURE", "2026-10-25 10:00:00 [ERROR] [auth-service] Token verification failed: Keycloak timeout"),
        ("NETWORK_LATENCY", "2026-10-25 10:00:00 [ERROR] [api-gateway] Upstream 504 Gateway Timeout circuit open")
    ]

    for expected_cat, log_line in test_cases:
        df = InfrastructureLogParser.parse_text(log_line)
        res = RootCauseAnalysisEngine.analyze_logs(df)
        assert res["total_incidents"] >= 1, f"Failed to detect incident for {expected_cat}"
        categories = [inc["category"] for inc in res["incidents"]]
        assert expected_cat in categories, f"Expected {expected_cat} in {categories}"
        
        # Verify evidence distinction from likely root cause
        target_inc = next(inc for inc in res["incidents"] if inc["category"] == expected_cat)
        assert len(target_inc["detected_evidence"]) >= 1
        assert target_inc["likely_root_cause"] is not None
        assert target_inc["confidence_pct"] >= 60
        assert len(target_inc["recommended_next_steps"]) >= 1

    print("[PASS] All 6 incident categories classified with evidence, likely causes, and next steps.")

def test_health_score_boundaries_and_empty():
    """Verifies health score calculations, thresholds (Stable, Warning, Critical), and empty input safety."""
    # 1. Empty input
    empty_df = pd.DataFrame()
    res_empty = InfrastructureHealthScorer.calculate_health(empty_df)
    assert res_empty["health_score"] == 100.0
    assert res_empty["condition"] == "Stable"

    # 2. Clean/Normal logs -> Stable (>= 80%)
    normal_text = load_sample_log("normal_operations.log")
    normal_df = InfrastructureLogParser.parse_text(normal_text)
    res_normal = InfrastructureHealthScorer.calculate_health(normal_df)
    assert res_normal["health_score"] >= 80.0
    assert res_normal["condition"] == "Stable"

    # 3. Cascading incident logs -> Critical (< 50%)
    incident_text = load_sample_log("production_incident.log")
    incident_df = InfrastructureLogParser.parse_text(incident_text)
    res_incident = InfrastructureHealthScorer.calculate_health(incident_df)
    assert res_incident["health_score"] < 50.0
    assert res_incident["condition"] == "Critical"
    assert len(res_incident["deductions_breakdown"]) >= 3

    # 4. Moderate warning logs -> Warning (50% - 79%)
    warning_text = (
        "2026-10-25 10:00:00 [WARN] [service-a] High memory utilization 82%\n"
        "2026-10-25 10:00:01 [WARN] [service-a] Latency rising\n"
        "2026-10-25 10:00:02 [ERROR] [service-a] Isolated query timeout\n"
        "2026-10-25 10:00:03 [ERROR] [service-a] Second retry timeout\n"
        "2026-10-25 10:00:04 [WARN] [service-a] Degrading buffer\n"
    )
    warning_df = InfrastructureLogParser.parse_text(warning_text)
    res_warning = InfrastructureHealthScorer.calculate_health(warning_df)
    assert 50.0 <= res_warning["health_score"] < 80.0
    assert res_warning["condition"] == "Warning"

    print("[PASS] Health score boundaries (Stable, Warning, Critical, and Empty Input) verified.")

def test_predictive_failure_risk():
    """Verifies predictive risk evaluation, factor explanations, and insufficient data handling."""
    # 1. Insufficient data (< 3 logs)
    tiny_df = InfrastructureLogParser.parse_text("2026-10-25 10:00:00 [INFO] [s1] OK")
    res_tiny = PredictiveFailureDetector.assess_risk(tiny_df)
    assert res_tiny["status"] == "INSUFFICIENT_DATA"
    assert res_tiny["risk_score"] == 0

    # 2. Healthy trace -> Low risk (< 20)
    normal_text = load_sample_log("normal_operations.log")
    normal_df = InfrastructureLogParser.parse_text(normal_text)
    res_normal = PredictiveFailureDetector.assess_risk(normal_df)
    assert res_normal["risk_score"] < 20.0
    assert res_normal["risk_level"] in ["LOW", "MODERATE"]

    # 3. Cascading incident trace -> High or Critical risk (> 55)
    incident_text = load_sample_log("production_incident.log")
    incident_df = InfrastructureLogParser.parse_text(incident_text)
    res_incident = PredictiveFailureDetector.assess_risk(incident_df)
    assert res_incident["risk_score"] >= 55.0
    assert res_incident["risk_level"] in ["HIGH", "CRITICAL"]
    assert len(res_incident["contributing_factors"]) == 4

    print("[PASS] Predictive risk scoring and contributing factors verified.")

def test_self_healing_recommendations_and_safety():
    """Verifies recovery recommendations, reasons, prerequisites, verification steps, and safe simulation."""
    incident_text = load_sample_log("production_incident.log")
    incident_df = InfrastructureLogParser.parse_text(incident_text)
    rca_res = RootCauseAnalysisEngine.analyze_logs(incident_df)

    recs = SelfHealingEngine.generate_recommendations(rca_res["incidents"])
    assert len(recs) >= 3

    for r in recs:
        assert r["action_id"].startswith("ACT_")
        assert len(r["title"]) > 5
        assert len(r["reason"]) > 10
        assert len(r["prerequisites"]) > 10
        assert len(r["verification_steps"]) > 10

    # Test safe simulation
    sim_res = SelfHealingEngine.simulate_action(recs[0]["action_id"])
    assert sim_res["simulation_result"] == "SUCCESS"
    assert "SAFE" in sim_res["simulation_mode"]

    print("[PASS] Self-healing recommendations, safety policy, and dry-run simulations verified.")

if __name__ == "__main__":
    print("=" * 65)
    print("Running Stage 2 Test Suite: RCA, Failure Risk, Health & Self-Healing")
    print("=" * 65)
    test_six_incident_categories()
    test_health_score_boundaries_and_empty()
    test_predictive_failure_risk()
    test_self_healing_recommendations_and_safety()
    print("=" * 65)
    print("[SUCCESS] All Stage 2 unit tests passed successfully!")
    print("=" * 65)
