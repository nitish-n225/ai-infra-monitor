"""
Infrastructure Telemetry & Log Statistics Module.
Calculates high-level metrics, error distributions, and service telemetry.
"""
from typing import Dict, Any, List
import pandas as pd

class TelemetryAnalyzer:
    """Extracts operational telemetry and health metrics from structured log DataFrames."""

    @staticmethod
    def compute_summary(df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates Stage 1 infrastructure telemetry summary from a parsed DataFrame."""
        if df.empty:
            return {
                "total_logs": 0,
                "critical_count": 0,
                "error_count": 0,
                "warn_count": 0,
                "info_count": 0,
                "error_rate_pct": 0.0,
                "unique_services_count": 0,
                "services": [],
                "level_counts": {},
                "service_counts": {},
                "time_range": {"start": "N/A", "end": "N/A"},
                "critical_events": []
            }

        total_logs = len(df)
        level_counts = df["level"].value_counts().to_dict()

        critical_count = level_counts.get("CRITICAL", 0) + level_counts.get("FATAL", 0)
        error_count = level_counts.get("ERROR", 0)
        warn_count = level_counts.get("WARN", 0)
        info_count = level_counts.get("INFO", 0)

        total_failures = critical_count + error_count
        error_rate_pct = round((total_failures / total_logs) * 100, 2) if total_logs > 0 else 0.0

        service_counts = df["service"].value_counts().to_dict()
        unique_services = list(service_counts.keys())

        # Extract timestamps if available
        valid_ts = df[df["timestamp"] != "N/A"]["timestamp"]
        time_range = {
            "start": valid_ts.iloc[0] if not valid_ts.empty else "N/A",
            "end": valid_ts.iloc[-1] if not valid_ts.empty else "N/A"
        }

        # Filter recent critical / fatal events for alert review
        crit_df = df[df["level"].isin(["CRITICAL", "FATAL", "ERROR"])]
        critical_events = crit_df.head(10).to_dict(orient="records")

        return {
            "total_logs": total_logs,
            "critical_count": critical_count,
            "error_count": error_count,
            "warn_count": warn_count,
            "info_count": info_count,
            "error_rate_pct": error_rate_pct,
            "unique_services_count": len(unique_services),
            "services": unique_services,
            "level_counts": level_counts,
            "service_counts": service_counts,
            "time_range": time_range,
            "critical_events": critical_events
        }
