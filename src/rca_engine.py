"""
Root Cause Analysis (RCA) & Critical Event Detection Engine.
Classifies infrastructure failures into six core incident categories:
1. Database Failure
2. CPU Overload
3. Memory Leak / OOM
4. Storage Failure
5. Authentication Failure
6. Network Latency / Instability
"""
import re
from typing import List, Dict, Any, Optional
import pandas as pd

# Incident Category Definitions with Target Signatures
INCIDENT_PATTERNS = {
    "DATABASE_FAILURE": {
        "title": "Database Connection & Query Failure",
        "patterns": [
            r"connection pool (depleted|exhausted|surged)",
            r"could not connect to (server|database)",
            r"remaining connection slots reserved",
            r"deadlock detected",
            r"fatal:.*connection",
            r"pq:.*error",
            r"pg::connectionbad",
            r"database.*down",
            r"db.*timeout",
            r"failed to start postgresql",
            r"mysql.*gone away"
        ],
        "default_severity": "CRITICAL",
        "likely_cause": "Database connection pool exhaustion, unindexed slow queries, or database service process termination.",
        "explanation": "Log signatures indicate database client connection pool depletion or failure to establish TCP handshakes with the primary database cluster.",
        "recommended_next_steps": [
            "Audit connection pool max-connections limits against current application replica counts.",
            "Inspect slow query log for locks, table scans, or unindexed joins holding connections open.",
            "Verify database host health, replica synchronization, and socket availability."
        ]
    },
    "CPU_OVERLOAD": {
        "title": "CPU Overload & Compute Saturation",
        "patterns": [
            r"cpu (utilization|usage|load).*(high|critical|saturation|\b9\d%|\b100%)",
            r"load average.*exceeded",
            r"cpu throttling",
            r"scheduler latency",
            r"thread pool exhausted",
            r"worker starvation"
        ],
        "default_severity": "HIGH",
        "likely_cause": "Unbounded concurrent compute threads, runaway worker tasks, or insufficient compute resource limits.",
        "explanation": "Compute threshold indicators show CPU utilization nearing saturation, leading to thread starvation and queue degradation.",
        "recommended_next_steps": [
            "Trigger horizontal auto-scaling (HPA) to distribute request compute load across more pods/nodes.",
            "Profile top CPU-consuming worker processes using flame graphs or APM telemetry.",
            "Apply thread pool rate limits to prevent cascading compute starvation."
        ]
    },
    "MEMORY_LEAK_OOM": {
        "title": "Memory Exhaustion & Out-Of-Memory (OOM)",
        "patterns": [
            r"oomkilled",
            r"exit code 137",
            r"out of memory",
            r"memory pressure flag set",
            r"used memory > 'maxmemory'",
            r"eviction policy.*triggered",
            r"java\.lang\.outofmemoryerror",
            r"heap space.*exhausted",
            r"free:.*[0-9]+mb"
        ],
        "default_severity": "CRITICAL",
        "likely_cause": "Unbounded in-memory caching, heap memory leak, or container cgroup memory limits configured below operational peak.",
        "explanation": "Memory utilization breached maximum allowable limits, triggering OS kernel OOM killer or cache eviction mechanisms.",
        "recommended_next_steps": [
            "Evict non-essential cache keys or execute controlled volatile memory flush.",
            "Increase container memory limit and memory reservation quotas.",
            "Capture heap dump to identify object retention and memory leak sources."
        ]
    },
    "STORAGE_FAILURE": {
        "title": "Storage Volume & Disk Failure",
        "patterns": [
            r"no space left on device",
            r"disk (full|exhausted|quota exceeded)",
            r"i/o error",
            r"filesystem.*read-only",
            r"storage failure",
            r"failed to write.*disk",
            r"volume.*detach.*error"
        ],
        "default_severity": "CRITICAL",
        "likely_cause": "Disk volume capacity exhaustion, unrotated log files, core dump accumulation, or block storage detachment.",
        "explanation": "Storage subsystem reports write refusal, I/O errors, or disk full states preventing state persistence.",
        "recommended_next_steps": [
            "Trigger automated log rotation and purge old core dumps/temporary artifacts.",
            "Expand persistent volume claim (PVC) capacity dynamically on cloud storage.",
            "Inspect disk I/O metrics and inode utilization."
        ]
    },
    "AUTHENTICATION_FAILURE": {
        "title": "Authentication & Identity Provider Failure",
        "patterns": [
            r"token verification.*(failed|timeout|error)",
            r"keycloak.*(error|unreachable|timeout)",
            r"jwt.*(expired|invalid|signature)",
            r"unauthorized.*surge",
            r"identity provider.*down",
            r"ldap.*connection refused",
            r"401 unauthorized"
        ],
        "default_severity": "HIGH",
        "likely_cause": "Identity provider (IdP) service outage, expired signing keys, or authentication microservice timeout.",
        "explanation": "Repeated failure in token validation or authentication handshakes blocking authorized client access.",
        "recommended_next_steps": [
            "Verify identity provider (Keycloak/Auth0/LDAP) network reachability and health probes.",
            "Refresh local cached public keys / certificates for JWT signature verification.",
            "Temporarily apply circuit breaker fallback or graceful degraded session bypass."
        ]
    },
    "NETWORK_LATENCY": {
        "title": "Network Latency & Upstream Timeout",
        "patterns": [
            r"504 gateway timeout",
            r"upstream timeout",
            r"connection (reset|refused|timed out)",
            r"circuit.*(open|tripped)",
            r"latency avg.*[0-9]+ms",
            r"dns resolution failed",
            r"packet drop"
        ],
        "default_severity": "HIGH",
        "likely_cause": "Network congestion, misconfigured reverse proxy timeouts, or downstream microservice unresponsiveness.",
        "explanation": "Inter-service RPC or HTTP communication timed out, triggering circuit breakers and ingress 504 gateway errors.",
        "recommended_next_steps": [
            "Inspect network hop latency and ingress controller request timeout configurations.",
            "Reset or probe half-open circuit breakers to allow service recovery.",
            "Validate internal DNS resolution and service mesh (Istio/Linkerd) sidecar proxies."
        ]
    }
}

class RootCauseAnalysisEngine:
    """
    Analyzes normalized infrastructure logs to detect critical events,
    classify incidents into six categories, and extract supporting evidence.
    """

    @classmethod
    def analyze_logs(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Performs root cause analysis on a structured log DataFrame.
        Returns detected incidents with exact evidence, likely causes, and confidence.
        """
        if df.empty:
            return {
                "total_incidents": 0,
                "status": "NO_DATA",
                "incidents": [],
                "summary": "No logs provided for analysis."
            }

        detected_incidents = []

        # Iterate through each category and test log messages against patterns
        for cat_key, cat_meta in INCIDENT_PATTERNS.items():
            compiled_patterns = [re.compile(p, re.IGNORECASE) for p in cat_meta["patterns"]]
            matching_evidence = []

            for _, row in df.iterrows():
                msg = str(row.get("message", ""))
                svc = str(row.get("service", "unknown"))
                lvl = str(row.get("level", "INFO")).upper()
                combined_text = f"{svc} {msg}"

                for pat in compiled_patterns:
                    match = pat.search(combined_text)
                    if match:
                        matching_evidence.append({
                            "line_no": row.get("line_no", 0),
                            "timestamp": row.get("timestamp", "N/A"),
                            "service": svc,
                            "level": lvl,
                            "message": msg,
                            "matched_pattern": pat.pattern
                        })
                        break # Avoid duplicate matches for same log line in this category

            if matching_evidence:
                # Determine severity: Elevate to CRITICAL if multiple lines or FATAL/CRITICAL level present
                has_critical_level = any(e["level"] in ["CRITICAL", "FATAL"] for e in matching_evidence)
                incident_severity = "CRITICAL" if (has_critical_level or len(matching_evidence) >= 3) else cat_meta["default_severity"]

                # Calculate rule confidence (heuristic based on evidence density: 60% base, +10% per evidence line, max 98%)
                evidence_count = len(matching_evidence)
                confidence_pct = min(60 + (evidence_count * 10), 98)

                detected_incidents.append({
                    "category": cat_key,
                    "title": cat_meta["title"],
                    "severity": incident_severity,
                    "evidence_count": evidence_count,
                    "detected_evidence": matching_evidence,
                    "likely_root_cause": cat_meta["likely_cause"],
                    "explanation": f"{cat_meta['explanation']} (Matched {evidence_count} operational log trace points).",
                    "confidence_pct": confidence_pct,
                    "confidence_label": f"{confidence_pct}% (Rule-Pattern Correlation)",
                    "recommended_next_steps": cat_meta["recommended_next_steps"]
                })

        # Sort incidents by severity: CRITICAL first, then HIGH, etc.
        severity_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        detected_incidents.sort(key=lambda x: (severity_rank.get(x["severity"], 4), -x["evidence_count"]))

        return {
            "total_incidents": len(detected_incidents),
            "status": "INCIDENTS_DETECTED" if detected_incidents else "SYSTEM_HEALTHY",
            "incidents": detected_incidents,
            "summary": f"Detected {len(detected_incidents)} critical operational incident(s) across infrastructure logs." if detected_incidents else "All services operational. No failure signatures detected."
        }
