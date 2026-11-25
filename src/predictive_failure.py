"""
Predictive Failure Detection & Operational Risk Module.
Estimates infrastructure failure risk based on anomaly frequency, severity,
and multi-service cascading patterns over log timelines.

NOTE: Risk metrics are heuristic operational indicators designed for proactive
triage and early warning; they are not deterministic or scientifically validated future probabilities.
"""
from typing import Dict, Any, List, Optional
import pandas as pd

class PredictiveFailureDetector:
    """
    Evaluates log streams to compute an explainable Infrastructure Risk Index (0-100)
    and identify cascading failure trajectories before complete outage occurs.
    """

    @classmethod
    def assess_risk(cls, df: pd.DataFrame, rca_results: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Assesses operational risk from parsed infrastructure logs.
        Returns risk score, risk level, and contributing factor breakdown.
        """
        if df.empty or len(df) < 3:
            return {
                "risk_score": 0,
                "risk_level": "UNKNOWN",
                "risk_indicator": "Insufficient Data",
                "status": "INSUFFICIENT_DATA",
                "disclaimer": "Heuristic operational risk indicator for proactive triage; not a deterministic future probability.",
                "contributing_factors": [],
                "summary": "At least 3 log records are required to calculate a statistically meaningful risk trajectory."
            }

        total_logs = len(df)
        level_counts = df["level"].value_counts().to_dict()

        critical_count = level_counts.get("CRITICAL", 0) + level_counts.get("FATAL", 0)
        error_count = level_counts.get("ERROR", 0)
        warn_count = level_counts.get("WARN", 0)

        # ----------------- Factor 1: Error Density (Weight: 35) -----------------
        total_failures = critical_count + error_count
        failure_ratio = total_failures / total_logs
        score_density = round(min(failure_ratio * 70, 35.0), 1)
        factor_density = {
            "factor": "Failure Log Density",
            "score": score_density,
            "max_weight": 35.0,
            "metric": f"{total_failures}/{total_logs} failure logs ({failure_ratio * 100:.1f}%)",
            "impact": "High failure density indicates persistent service degradation rather than transient spikes."
        }

        # ----------------- Factor 2: Severity Intensity (Weight: 25) -----------------
        # Critical/Fatal events heavily penalize infrastructure stability
        crit_score = (critical_count * 8.0) + (error_count * 2.0)
        score_severity = round(min(crit_score, 25.0), 1)
        factor_severity = {
            "factor": "Critical Severity Weight",
            "score": score_severity,
            "max_weight": 25.0,
            "metric": f"{critical_count} Critical/Fatal, {error_count} Errors",
            "impact": "Unrecoverable error codes (OOM, DB connection exhaustion) drastically increase systemic collapse risk."
        }

        # ----------------- Factor 3: Cascading Multi-Service Spread (Weight: 25) -----------------
        # If failures are isolated to 1 service, risk is moderate; if spreading across 3+ services, risk is critical
        failing_services = df[df["level"].isin(["CRITICAL", "FATAL", "ERROR"])]["service"].unique()
        failing_svc_count = len(failing_services)
        if failing_svc_count == 0:
            score_spread = 0.0
        elif failing_svc_count == 1:
            score_spread = 8.0
        elif failing_svc_count == 2:
            score_spread = 16.0
        else:
            score_spread = 25.0

        factor_spread = {
            "factor": "Cascading Service Propagation",
            "score": score_spread,
            "max_weight": 25.0,
            "metric": f"{failing_svc_count} failing services ({', '.join(failing_services) if failing_svc_count else 'None'})",
            "impact": "Cross-service error propagation indicates boundary failure (e.g. cache outage cascading to database)."
        }

        # ----------------- Factor 4: Temporal Clustering & Trend (Weight: 15) -----------------
        # Check if the recent half of logs contains a higher concentration of errors than the earlier half
        halfway_idx = total_logs // 2
        earlier_errors = df.iloc[:halfway_idx]["level"].isin(["CRITICAL", "FATAL", "ERROR"]).sum()
        recent_errors = df.iloc[halfway_idx:]["level"].isin(["CRITICAL", "FATAL", "ERROR"]).sum()

        if recent_errors > earlier_errors and recent_errors > 0:
            score_temporal = min(15.0, 5.0 + (recent_errors * 2.0))
            trend_desc = f"Accelerating (+{recent_errors - earlier_errors} more errors in recent logs)"
        elif recent_errors > 0:
            score_temporal = 6.0
            trend_desc = "Steady error rate across timeline"
        else:
            score_temporal = 0.0
            trend_desc = "Zero recent errors"

        score_temporal = round(score_temporal, 1)
        factor_temporal = {
            "factor": "Temporal Acceleration & Clustering",
            "score": score_temporal,
            "max_weight": 15.0,
            "metric": trend_desc,
            "impact": "Accelerating error frequency indicates an unmitigated operational death spiral."
        }

        # ----------------- Total Risk Calculation -----------------
        total_risk_score = round(min(score_density + score_severity + score_spread + score_temporal, 100.0), 1)

        if total_risk_score >= 80.0:
            risk_level = "CRITICAL"
            risk_indicator = "Critical Outage Risk (Immediate Intervention Required)"
        elif total_risk_score >= 55.0:
            risk_level = "HIGH"
            risk_indicator = "High Instability Risk (Elevated Cascading Threat)"
        elif total_risk_score >= 30.0:
            risk_level = "ELEVATED"
            risk_indicator = "Elevated Operational Risk (Warning Thresholds Active)"
        elif total_risk_score >= 10.0:
            risk_level = "MODERATE"
            risk_indicator = "Moderate Baseline Risk (Transient Anomalies Observed)"
        else:
            risk_level = "LOW"
            risk_indicator = "Low Risk (System Operating Within Safe Tolerances)"

        contributing_factors = [factor_density, factor_severity, factor_spread, factor_temporal]

        return {
            "risk_score": total_risk_score,
            "risk_level": risk_level,
            "risk_indicator": risk_indicator,
            "status": "ASSESSED",
            "disclaimer": "Heuristic operational risk indicator for proactive triage; not a deterministic future probability.",
            "contributing_factors": contributing_factors,
            "summary": f"Calculated an Infrastructure Risk Index of {total_risk_score}/100 [{risk_level}]. Primary risk driver: {max(contributing_factors, key=lambda f: f['score'])['factor']}."
        }
