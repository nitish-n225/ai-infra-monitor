"""
Autonomous Self-Healing & Safe Recovery Recommendations Module.
Generates safe, structured operational recovery playbooks for detected infrastructure incidents.

SAFETY POLICY:
    Under strict safety constraints, this module generates advisory remediation recommendations
    with explicit prerequisites and verification steps. It DOES NOT execute destructive commands,
    restart live services, delete files, or alter infrastructure configuration.
"""
from typing import List, Dict, Any, Optional

SAFETY_POLICY_DISCLAIMER = (
    "SAFETY GUARD: Advisory recovery playbook only. "
    "Autonomous actions are presented for operator approval; "
    "no live infrastructure modifications or command executions are performed."
)

RECOVERY_PLAYBOOKS = {
    "DATABASE_FAILURE": [
        {
            "action_id": "ACT_DB_01",
            "title": "Drain Idle Connection Pool & Terminate Stalled Backend Sockets",
            "reason": "Reclaims allocated connection slots currently locked by unresponsive client microservices.",
            "prerequisites": "Verify primary database health and ensure read-replica replication lag is under 1.0s.",
            "verification_steps": "Query active connection count metric to verify connection pool usage drops below 60% of max limit.",
            "safety_level": "SAFE (Non-destructive connection pool recycling)"
        },
        {
            "action_id": "ACT_DB_02",
            "title": "Temporarily Throttle Non-Critical Batch Analytics Queries",
            "reason": "Reduces contention on connection slots for high-priority user transactional requests.",
            "prerequisites": "Identify asynchronous workers using dedicated database roles.",
            "verification_steps": "Confirm transactional query wait queue size drops to zero."
        }
    ],
    "CPU_OVERLOAD": [
        {
            "action_id": "ACT_CPU_01",
            "title": "Trigger Horizontal Pod Autoscaler (HPA) Scale-Out (+2 Replicas)",
            "reason": "Distributes concurrent compute workload across additional container worker replicas.",
            "prerequisites": "Ensure Kubernetes cluster nodes have available allocatable CPU capacity.",
            "verification_steps": "Observe replica count increase and average container CPU utilization decrease below 70%.",
            "safety_level": "SAFE (Standard elasticity scaling)"
        }
    ],
    "MEMORY_LEAK_OOM": [
        {
            "action_id": "ACT_MEM_01",
            "title": "Flush Volatile Key Cache & Enforce LRU Memory Eviction",
            "reason": "Reclaims memory headroom to prevent Linux cgroup OOM killer (Exit Code 137).",
            "prerequisites": "Verify Redis RDB/AOF persistent snapshot is synchronized before memory eviction.",
            "verification_steps": "Check memory usage metric drops below 80% threshold and container crashloop terminates.",
            "safety_level": "SAFE (Volatile keys only)"
        },
        {
            "action_id": "ACT_MEM_02",
            "title": "Increase Container Cgroup Memory Limit (+25% Headroom)",
            "reason": "Provides sufficient heap buffer to accommodate operational traffic bursts without crashing.",
            "prerequisites": "Verify physical node has sufficient unreserved RAM.",
            "verification_steps": "Inspect pod memory usage over 10-minute window to verify stable operating plateau."
        }
    ],
    "STORAGE_FAILURE": [
        {
            "action_id": "ACT_STRG_01",
            "title": "Trigger Automated Log Rotation & Purge Stale Temporary Files",
            "reason": "Reclaims filesystem block capacity and inodes to prevent write refusal.",
            "prerequisites": "Ensure old rotated logs have successfully uploaded to cold object storage (S3/GCS).",
            "verification_steps": "Execute volume utilization check to confirm free disk space exceeds 20%.",
            "safety_level": "SAFE (Targeted temporary files)"
        }
    ],
    "AUTHENTICATION_FAILURE": [
        {
            "action_id": "ACT_AUTH_01",
            "title": "Reload Identity Provider JWKS Public Key Cache & Reset Handshake Keepalives",
            "reason": "Resolves token verification timeouts caused by stale signing certificate caches.",
            "prerequisites": "Verify identity provider (.well-known/openid-configuration) endpoint is reachable.",
            "verification_steps": "Execute automated synthetic token validation probe and verify HTTP 200 response.",
            "safety_level": "SAFE (Cache invalidation)"
        }
    ],
    "NETWORK_LATENCY": [
        {
            "action_id": "ACT_NET_01",
            "title": "Probe Upstream Endpoints & Transition Circuit Breaker to HALF-OPEN",
            "reason": "Enables canary traffic probes to test if degraded upstream microservice has stabilized.",
            "prerequisites": "Confirm upstream target pod health probes (/healthz) return healthy status.",
            "verification_steps": "Monitor ingress 504 Gateway Timeout rate dropping to 0.0%.",
            "safety_level": "SAFE (Circuit breaker probe)"
        }
    ]
}

class SelfHealingEngine:
    """
    Generates structured, safe recovery recommendations and simulated remediation audits.
    """

    @classmethod
    def generate_recommendations(cls, incidents: Any) -> List[Dict[str, Any]]:
        """
        Generates actionable recovery playbooks for detected incidents.
        Accepts either a list of incident dictionaries or an RCA result dictionary.
        Returns a list of structured recommendations with reasons, prerequisites, and verification steps.
        """
        if isinstance(incidents, dict):
            incidents = incidents.get("incidents", [])
        if not isinstance(incidents, list):
            incidents = []

        recommendations = []
        seen_actions = set()

        for inc in incidents:
            cat = inc.get("category", "")
            playbooks = RECOVERY_PLAYBOOKS.get(cat, [])
            
            # Find the primary service involved in this incident from evidence
            evidence = inc.get("detected_evidence", [])
            target_service = evidence[0].get("service", "infrastructure") if evidence else "infrastructure"

            for pb in playbooks:
                action_id = pb["action_id"]
                if action_id not in seen_actions:
                    seen_actions.add(action_id)
                    recommendations.append({
                        "action_id": action_id,
                        "title": pb["title"],
                        "incident_category": cat,
                        "incident_title": inc.get("title", cat),
                        "target_service": target_service,
                        "severity": inc.get("severity", "HIGH"),
                        "reason": pb["reason"],
                        "prerequisites": pb["prerequisites"],
                        "verification_steps": pb["verification_steps"],
                        "safety_level": pb.get("safety_level", "SAFE (Operator Verification Required)"),
                        "simulated_status": "READY_FOR_OPERATOR_APPROVAL"
                    })

        return recommendations

    @classmethod
    def simulate_action(cls, action_id: str) -> Dict[str, Any]:
        """
        Simulates executing a recovery action in safe dry-run mode.
        Guarantees that NO actual infrastructure or processes are modified.
        """
        return {
            "action_id": action_id,
            "simulation_result": "SUCCESS",
            "simulation_mode": "DRY_RUN (SAFE)",
            "message": f"Remediation playbook '{action_id}' simulated successfully. No live infrastructure was modified.",
            "safety_guarantee": "ZERO live commands executed; pure advisory dry-run verification."
        }
