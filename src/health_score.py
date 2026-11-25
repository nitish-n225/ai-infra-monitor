"""
Infrastructure Health Scoring Module.
Calculates an explainable, transparent Infrastructure Health Index (0-100%)
and classifies system condition into Stable, Warning, or Critical states.

Scoring Formula:
    Health Score = max(0, 100.0 - Total Deductions)
    Deductions:
        - Critical/Fatal Events: -18.0 pts each (capped at 50 pts)
        - Error Events: -8.0 pts each (capped at 40 pts)
        - Warning Events: -2.0 pts each (capped at 20 pts)
        - Cascading Penalty: -12.0 pts if >= 3 services have errors
        - Failure Density Penalty: -10.0 pts if error rate exceeds 20%
"""
from typing import Dict, Any, List
import pandas as pd

class InfrastructureHealthScorer:
    """Computes transparent, explainable infrastructure health percentages."""

    THRESHOLD_STABLE = 80.0
    THRESHOLD_WARNING = 50.0

    @classmethod
    def calculate_health(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates the Infrastructure Health Score from a log DataFrame.
        Returns score (0-100), condition category, and deduction breakdown.
        """
        if df.empty:
            return {
                "health_score": 100.0,
                "condition": "Stable",
                "color": "#10b981",
                "total_deductions": 0.0,
                "deductions_breakdown": [],
                "formula_summary": "Base 100.0 - 0.0 deductions = 100.0%",
                "explanation": "No operational anomalies detected in active log stream (Baseline Normal)."
            }

        total_logs = len(df)
        level_series = df.get("level", pd.Series(["INFO"] * total_logs)).fillna("INFO").str.upper()
        level_counts = level_series.value_counts().to_dict()

        critical_count = level_counts.get("CRITICAL", 0) + level_counts.get("FATAL", 0)
        error_count = level_counts.get("ERROR", 0)
        warn_count = level_counts.get("WARN", 0) + level_counts.get("WARNING", 0)

        deductions_breakdown: List[Dict[str, Any]] = []
        total_deductions = 0.0

        # 1. Critical Events Penalty
        if critical_count > 0:
            crit_deduction = min(critical_count * 18.0, 50.0)
            total_deductions += crit_deduction
            deductions_breakdown.append({
                "reason": "Critical/Fatal System Events",
                "count": critical_count,
                "deduction": round(crit_deduction, 1),
                "detail": f"{critical_count} critical incident logs detected (-18 pts/ea, max 50 pts)"
            })

        # 2. Error Events Penalty
        if error_count > 0:
            err_deduction = min(error_count * 8.0, 40.0)
            total_deductions += err_deduction
            deductions_breakdown.append({
                "reason": "Standard Application & Service Errors",
                "count": error_count,
                "deduction": round(err_deduction, 1),
                "detail": f"{error_count} error logs detected (-8 pts/ea, max 40 pts)"
            })

        # 3. Warning Events Penalty
        if warn_count > 0:
            warn_deduction = min(warn_count * 2.0, 20.0)
            total_deductions += warn_deduction
            deductions_breakdown.append({
                "reason": "Operational Warning Thresholds",
                "count": warn_count,
                "deduction": round(warn_deduction, 1),
                "detail": f"{warn_count} warning logs detected (-2 pts/ea, max 20 pts)"
            })

        # 4. Multi-Service Cascading Spread Penalty
        service_col = df.get("service", pd.Series(["unknown"] * total_logs)).fillna("unknown")
        failing_services = df[level_series.isin(["CRITICAL", "FATAL", "ERROR"])]["service"].unique() if "service" in df.columns else []
        if len(failing_services) >= 3:
            total_deductions += 12.0
            deductions_breakdown.append({
                "reason": "Multi-Service Failure Propagation",
                "count": len(failing_services),
                "deduction": 12.0,
                "detail": f"Errors spread across {len(failing_services)} services: {', '.join(failing_services)}"
            })

        # 5. High Failure Density Penalty
        failure_rate = ((critical_count + error_count) / total_logs) * 100 if total_logs > 0 else 0
        if failure_rate > 20.0:
            total_deductions += 10.0
            deductions_breakdown.append({
                "reason": "High Failure Density",
                "count": round(failure_rate, 1),
                "deduction": 10.0,
                "detail": f"Error rate ({failure_rate:.1f}%) exceeds the 20% stability threshold"
            })

        # Final score calculation clamped between 0.0 and 100.0
        final_health = round(max(0.0, min(100.0, 100.0 - total_deductions)), 1)

        # Classification into Stable, Warning, Critical
        if final_health >= cls.THRESHOLD_STABLE:
            condition = "Stable"
            color = "#10b981"
            explanation = "Infrastructure condition is stable. Services are operating within expected operational baselines."
        elif final_health >= cls.THRESHOLD_WARNING:
            condition = "Warning"
            color = "#f59e0b"
            explanation = "Infrastructure condition is degraded. Warning thresholds and localized errors require investigation."
        else:
            condition = "Critical"
            color = "#ef4444"
            explanation = "Infrastructure condition is critical! Active cascading outages detected; immediate remediation required."

        return {
            "health_score": final_health,
            "condition": condition,
            "color": color,
            "total_deductions": round(total_deductions, 1),
            "deductions_breakdown": deductions_breakdown,
            "formula_summary": f"Base 100.0 - {round(total_deductions, 1)} deductions = {final_health}%",
            "explanation": explanation
        }
