"""
Assistant Engine for Enterprise Autonomous AI Infrastructure Monitoring System.
Stage 4: Conversational AI Infrastructure Assistant with Deterministic Local Evidence Fallback
and Optional Cloud LLM Integration.
"""
import os
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd

from src.self_healing import SelfHealingEngine, SAFETY_POLICY_DISCLAIMER
from src.vector_store import FaissVectorStore

logger = logging.getLogger(__name__)

# Safety Rule
SAFETY_ENFORCEMENT_NOTICE = (
    "SAFETY POLICY: Automated execution of recovery actions against live infrastructure is disabled. "
    "All remediation actions are advisory simulations and dry-runs only."
)

class BaseLLMProvider:
    """Base interface for AI language model providers."""
    
    def generate(self, prompt: str, system_context: str) -> Tuple[str, str]:
        """
        Generate response given user prompt and grounded system context.
        Returns: (response_text, provider_name)
        """
        raise NotImplementedError

class DeterministicEvidenceProvider(BaseLLMProvider):
    """
    Default deterministic evidence-based provider.
    Operates 100% locally and offline without requiring an API key.
    Grounded directly in parsed logs, RCA findings, health telemetry, and vector store.
    """
    
    def __init__(self):
        self.provider_name = "Deterministic Evidence-Based Engine (Offline, No API Key Required)"
        
    def generate(self, prompt: str, system_context: str) -> Tuple[str, str]:
        # Fallback raw generation if called directly
        return (
            "The deterministic engine answers queries through structured evidence extraction.",
            self.provider_name
        )

class OpenAICompatibleProvider(BaseLLMProvider):
    """
    Optional OpenAI-compatible cloud LLM provider.
    Activated when OPENAI_API_KEY environment variable is present.
    """
    
    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1"):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.provider_name = f"OpenAI Cloud LLM ({self.model_name})"
        
    def generate(self, prompt: str, system_context: str) -> Tuple[str, str]:
        import urllib.request
        import urllib.error
        
        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an enterprise AI Infrastructure Assistant. You answer questions strictly based on the "
                        "provided ground-truth operational telemetry, root cause analysis (RCA), and log evidence. "
                        "CRITICAL RULES:\n"
                        "1. Do NOT invent or hallucinate events, timestamps, or services.\n"
                        "2. Cite exact source lines, timestamps, and services whenever available.\n"
                        "3. Clearly distinguish observed log facts from inferred root causes.\n"
                        "4. If evidence is missing, explicitly state: 'Insufficient evidence in active logs.'\n"
                        "5. All recovery actions are strictly advisory simulations.\n\n"
                        f"OPERATIONAL TELEMETRY & CONTEXT:\n{system_context}"
                    )
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 1000
        }
        
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode("utf-8"))
                text = result["choices"][0]["message"]["content"]
                return text, self.provider_name
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}. Falling back to deterministic engine.")
            raise RuntimeError(f"Cloud LLM request failed: {str(e)}")

class LLMProviderFactory:
    """Factory to detect available LLM credentials or fall back to local engine."""
    
    @staticmethod
    def get_provider() -> BaseLLMProvider:
        openai_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if openai_key:
            model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
            base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            try:
                return OpenAICompatibleProvider(api_key=openai_key, model_name=model, base_url=base_url)
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")
                
        # Default local deterministic fallback
        return DeterministicEvidenceProvider()


class InfrastructureAIAssistant:
    """
    Conversational AI Assistant for Infrastructure Operations.
    Answers natural-language questions grounded in active logs, RCA results,
    health metrics, failure risk, and self-healing playbooks.
    """
    
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.provider = provider or LLMProviderFactory.get_provider()
        self.history: List[Dict[str, Any]] = []
        self.current_dataset_id: Optional[str] = None
        
    def reset_session(self, new_dataset_id: Optional[str] = None):
        """Clears conversation history and synchronizes with a new dataset."""
        self.history = []
        self.current_dataset_id = new_dataset_id
        
    def get_history(self) -> List[Dict[str, Any]]:
        return self.history
        
    def ask(
        self,
        query: str,
        df: pd.DataFrame,
        rca_results: Dict[str, Any],
        health_data: Dict[str, Any],
        risk_data: Dict[str, Any],
        vector_store: Optional[FaissVectorStore] = None,
        dataset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user question against the current infrastructure context.
        
        Returns a structured dictionary:
        {
            "query": str,
            "answer": str,
            "intent": str,
            "confidence": str ("HIGH", "MEDIUM", "LOW", "INSUFFICIENT_EVIDENCE"),
            "evidence": List[Dict[str, Any]],
            "provider": str,
            "advisory_notice": str
        }
        """
        # Validate query
        clean_query = (query or "").strip()
        if not clean_query:
            return {
                "query": query,
                "answer": "Please ask a question regarding your infrastructure logs, root cause analysis, health score, or recovery recommendations.",
                "intent": "EMPTY_QUERY",
                "confidence": "LOW",
                "evidence": [],
                "provider": self.provider.provider_name,
                "advisory_notice": SAFETY_ENFORCEMENT_NOTICE
            }
            
        # Detect dataset switch to prevent stale context
        if dataset_id and self.current_dataset_id and self.current_dataset_id != dataset_id:
            # New dataset loaded, reset history
            self.reset_session(dataset_id)
        elif dataset_id:
            self.current_dataset_id = dataset_id
            
        # Check empty logs
        if df is None or df.empty:
            answer = (
                "⚠️ **No Active Logs Found**\n\n"
                "The system does not have any parsed log records loaded. "
                "Please upload a log file in the **Log Ingestion & Upload** tab or load the default production incident dataset."
            )
            return {
                "query": clean_query,
                "answer": answer,
                "intent": "NO_DATA",
                "confidence": "INSUFFICIENT_EVIDENCE",
                "evidence": [],
                "provider": self.provider.provider_name,
                "advisory_notice": SAFETY_ENFORCEMENT_NOTICE
            }
            
        # 1. Deterministic Intent & Evidence Extraction
        intent, answer, evidence, confidence = self._generate_deterministic_response(
            query=clean_query,
            df=df,
            rca_results=rca_results,
            health_data=health_data,
            risk_data=risk_data,
            vector_store=vector_store
        )
        
        provider_name = self.provider.provider_name
        
        # 2. If Cloud LLM Provider is configured, attempt enhancement with strict grounding
        if not isinstance(self.provider, DeterministicEvidenceProvider):
            try:
                system_context = self._build_system_context(df, rca_results, health_data, risk_data, evidence)
                llm_text, p_name = self.provider.generate(clean_query, system_context)
                answer = llm_text
                provider_name = p_name
            except Exception as e:
                logger.warning(f"Cloud LLM execution failed ({e}), using deterministic evidence response.")
                provider_name = f"Deterministic Fallback (Cloud Error: {str(e)})"
                
        result = {
            "query": clean_query,
            "answer": answer,
            "intent": intent,
            "confidence": confidence,
            "evidence": evidence,
            "provider": provider_name,
            "advisory_notice": SAFETY_ENFORCEMENT_NOTICE
        }
        
        # Save to session history
        self.history.append({
            "role": "user",
            "content": clean_query
        })
        self.history.append({
            "role": "assistant",
            "content": answer,
            "evidence": evidence,
            "provider": provider_name,
            "intent": intent
        })
        
        return result

    def _generate_deterministic_response(
        self,
        query: str,
        df: pd.DataFrame,
        rca_results: Dict[str, Any],
        health_data: Dict[str, Any],
        risk_data: Dict[str, Any],
        vector_store: Optional[FaissVectorStore]
    ) -> Tuple[str, str, List[Dict[str, Any]], str]:
        """
        Parses user intent and returns: (intent, answer_text, evidence_list, confidence)
        Guarantees 100% factual accuracy grounded in active data.
        """
        q_lower = query.lower()
        evidence: List[Dict[str, Any]] = []
        
        # 1. Health Score Inquiry
        if any(w in q_lower for w in ["health score", "health index", "calculate health", "health calculated", "why is health"]):
            score = health_data.get("health_score", 100.0)
            condition = health_data.get("condition", "Stable")
            err_rate = health_data.get("error_rate_pct", 0.0)
            penalties = health_data.get("penalties", [])
            
            lines = [
                f"### 🩺 Infrastructure Health Score: **{score}%** (`{condition}`)",
                f"- **Baseline Score**: Starts at `100.0%` for a fully operational cluster.",
                f"- **Total Error Rate**: `{err_rate}%` of parsed logs are errors or fatal crashes.",
                "- **Calculation Breakdown & Penalties**:"
            ]
            if penalties:
                for p in penalties:
                    lines.append(f"  - Deduction: **-{p.get('deduction', 0)} pts** — {p.get('reason', '')}")
            else:
                lines.append("  - No deductions applied. All telemetry metrics within healthy thresholds.")
                
            lines.append("\n**Observed Telemetry Summary:**")
            lines.append(f"- Total Ingested Logs: `{len(df)}` records.")
            lines.append(f"- Degraded Services: `{len(health_data.get('degraded_services', []))}`")
            
            # Evidence from top errors
            err_df = df[df["level"].isin(["CRITICAL", "FATAL", "ERROR"])].head(3)
            for _, r in err_df.iterrows():
                evidence.append(self._row_to_evidence(r))
                
            return ("HEALTH_SCORE_EXPLANATION", "\n".join(lines), evidence, "HIGH")

        # 2. Risk Score & Contributing Factors Inquiry
        if any(w in q_lower for w in ["risk score", "failure risk", "factors increased", "contributing factors", "risk calculated", "why is risk"]):
            score = risk_data.get("risk_score", 0.0)
            level = risk_data.get("risk_level", "LOW")
            factors = risk_data.get("contributing_factors", [])
            
            lines = [
                f"### ⚡ Predictive Failure Risk: **{score}/100** (`{level} RISK`)",
                "The failure risk model synthesizes multiple operational vulnerability vectors:",
                ""
            ]
            if factors:
                for f in factors:
                    name = f.get("factor", "Unknown")
                    weight = f.get("weight", "0%")
                    detail = f.get("detail", "")
                    pts = f.get("points", 0)
                    lines.append(f"- **{name}** (Weight: `{weight}`, Impact: `+{pts} pts`): {detail}")
            else:
                lines.append("- No high-risk factors detected in the active log telemetry.")
                
            lines.append(f"\n*Summary Assessment*: Infrastructure failure probability is classified as **{level}** based on active incident cascading and severity distributions.")
            
            # Evidence from critical incidents
            crit_df = df[df["level"].isin(["CRITICAL", "FATAL"])].head(3)
            for _, r in crit_df.iterrows():
                evidence.append(self._row_to_evidence(r))
                
            return ("RISK_SCORE_EXPLANATION", "\n".join(lines), evidence, "HIGH")

        # 3. Critical Incidents Overview Inquiry
        if any(w in q_lower for w in ["most critical", "critical incident", "what incidents", "fatal errors", "what went wrong", "list incidents"]):
            incidents = rca_results.get("incidents", [])
            total_inc = rca_results.get("total_incidents", 0)
            
            if total_inc == 0:
                return (
                    "CRITICAL_INCIDENTS",
                    "✅ **No Critical or Fatal Incidents Detected**\n\nThe ingested log stream does not contain any classified system outages or fatal crashes.",
                    [],
                    "HIGH"
                )
                
            lines = [
                f"### 🚨 Detected Critical Infrastructure Incidents (`{total_inc}` Total)",
                "The Root Cause Analysis engine identified the following systemic operational failures:",
                ""
            ]
            for idx, inc in enumerate(incidents, start=1):
                cat = inc.get("title") or inc.get("category", "General Incident")
                sev = inc.get("severity", "CRITICAL")
                ev_count = inc.get("evidence_count", 0)
                summary = inc.get("explanation", "")
                likely = inc.get("likely_root_cause", "")
                lines.append(f"**{idx}. [{sev}] {cat}** ({ev_count} log evidence events)")
                lines.append(f"- *Observed Symptom*: {summary}")
                lines.append(f"- *Inferred Cause*: {likely}")
                lines.append("")
                
            # Populate evidence from RCA incidents
            for inc in incidents:
                for item in inc.get("detected_evidence", [])[:2]:
                    evidence.append(item)
                    
            return ("CRITICAL_INCIDENTS", "\n".join(lines), evidence, "HIGH")

        # 4. Service-Specific Root Cause (e.g. database, redis, memory, network, auth, cpu, storage)
        domain_keywords = {
            "database": ["database", "db", "postgres", "sql", "pool", "slots"],
            "memory": ["memory", "oom", "killed process", "ram", "leak", "redis"],
            "network": ["network", "gateway", "latency", "upstream", "timeout", "circuit breaker", "dns"],
            "cpu": ["cpu", "load", "utilization", "throttle", "throttling"],
            "auth": ["auth", "unauthorized", "token", "jwt", "permission", "credentials", "forbidden"],
            "storage": ["storage", "disk", "iops", "full", "filesystem", "space"]
        }
        
        matched_domain = None
        for dom, kws in domain_keywords.items():
            if any(k in q_lower for k in kws) and any(trigger in q_lower for trigger in ["why", "cause", "fail", "error", "down", "issue", "what happened"]):
                matched_domain = dom
                break
                
        if matched_domain:
            # Find matching RCA incident
            matching_inc = None
            for inc in rca_results.get("incidents", []):
                cat_lower = (inc.get("category", "") + " " + inc.get("title", "")).lower()
                if matched_domain in cat_lower or any(k in cat_lower for k in domain_keywords[matched_domain]):
                    matching_inc = inc
                    break
                    
            if matching_inc:
                cat = matching_inc.get("title") or matching_inc.get("category", "")
                sev = matching_inc.get("severity", "ERROR")
                summary = matching_inc.get("explanation", "")
                likely_cause = matching_inc.get("likely_root_cause", "")
                steps = matching_inc.get("recommended_next_steps", [])
                inc_ev = matching_inc.get("detected_evidence", [])
                
                lines = [
                    f"### 🔍 Root Cause Analysis: **{cat}** (`{sev}`)",
                    f"- **Observed Operational Facts**: {summary}",
                    f"- **Inferred Root Cause**: {likely_cause}",
                    "",
                    "**Recommended Diagnostic Steps**:"
                ]
                for s in steps:
                    lines.append(f"1. {s}")
                    
                lines.append("\n> **Distinction Note**: Observed log messages represent verified symptoms recorded by services. Inferred causes are derived from fault-tree correlation.")
                
                for ev_item in inc_ev:
                    evidence.append(ev_item)
                    
                return ("ROOT_CAUSE_EXPLANATION", "\n".join(lines), evidence, "HIGH")
            else:
                # Check raw logs for mentions
                domain_matches = df[df["message"].str.lower().str.contains(matched_domain, na=False)]
                if not domain_matches.empty:
                    lines = [
                        f"### ℹ️ Telemetry for **{matched_domain.capitalize()}** Components",
                        f"Found `{len(domain_matches)}` log records referencing '{matched_domain}'. However, these did not trigger a high-severity critical RCA outage signature.",
                        "",
                        "**Recent Log Snippets**:"
                    ]
                    for _, r in domain_matches.head(3).iterrows():
                        lines.append(f"- `[{r.get('timestamp', '')}]` **[{r.get('service', '')}]** `[{r.get('level', '')}]` {r.get('message', '')}")
                        evidence.append(self._row_to_evidence(r))
                    return ("DOMAIN_TELEMETRY", "\n".join(lines), evidence, "MEDIUM")
                else:
                    return (
                        "INSUFFICIENT_EVIDENCE",
                        f"⚠️ **Insufficient Evidence in Active Logs**\n\nNo operational failure or error records were found for **'{matched_domain}'** in the currently active dataset. Monitored services are: `{', '.join(df['service'].dropna().unique())}`.",
                        [],
                        "INSUFFICIENT_EVIDENCE"
                    )

        # 5. Affected Services Inquiry
        if any(w in q_lower for w in ["affected services", "services affected", "which services", "components affected", "what is down", "services down"]):
            services = df["service"].dropna().unique().tolist()
            err_df = df[df["level"].isin(["CRITICAL", "FATAL", "ERROR"])]
            affected_svcs = err_df["service"].dropna().unique().tolist()
            
            lines = [
                "### 🌐 Infrastructure Service Impact Analysis",
                f"Currently monitoring **{len(services)} unique services** in the active cluster:",
                ""
            ]
            if affected_svcs:
                lines.append(f"**🚨 Degraded / Impacted Services ({len(affected_svcs)}):**")
                for svc in affected_svcs:
                    count = len(err_df[err_df["service"] == svc])
                    max_sev = "FATAL" if "FATAL" in err_df[err_df["service"] == svc]["level"].values else ("CRITICAL" if "CRITICAL" in err_df[err_df["service"] == svc]["level"].values else "ERROR")
                    lines.append(f"- **`{svc}`**: `{count}` error events recorded (Highest Severity: `{max_sev}`)")
            else:
                lines.append("🟢 **All services are currently reporting healthy telemetry (zero error logs).**")
                
            healthy_svcs = [s for s in services if s not in affected_svcs]
            if healthy_svcs:
                lines.append("\n**🟢 Healthy Services:**")
                for s in healthy_svcs:
                    total_s = len(df[df["service"] == s])
                    lines.append(f"- `{s}`: `{total_s}` operational events")
                    
            for _, r in err_df.head(4).iterrows():
                evidence.append(self._row_to_evidence(r))
                
            return ("AFFECTED_SERVICES", "\n".join(lines), evidence, "HIGH")

        # 6. Recovery Recommendations / Playbooks Inquiry
        if any(w in q_lower for w in ["recovery steps", "recommended recovery", "how to fix", "remediation", "healing actions", "playbooks", "fix the issue"]):
            recs = SelfHealingEngine.generate_recommendations(rca_results)
            
            if not recs:
                return (
                    "RECOVERY_RECOMMENDATIONS",
                    "✅ **No Active Recovery Actions Required**\n\nNo critical incidents were detected in the active log dataset that warrant remediation.",
                    [],
                    "HIGH"
                )
                
            lines = [
                f"### 🛠️ Recommended Autonomous Recovery Actions (`{len(recs)}` Available)",
                f"> **ADVISORY NOTICE**: {SAFETY_ENFORCEMENT_NOTICE}",
                ""
            ]
            for idx, r in enumerate(recs, start=1):
                act = r.get("title", "")
                act_id = r.get("action_id", "")
                svc = r.get("target_service", "")
                r_level = r.get("severity", "HIGH")
                desc = r.get("reason", "")
                prereqs = r.get("prerequisites", "")
                v_steps = r.get("verification_steps", "")
                
                lines.append(f"**{idx}. {act}** [`{act_id}`] (Target: `{svc}`, Severity: `{r_level}`)")
                lines.append(f"- *Summary*: {desc}")
                if isinstance(prereqs, list):
                    lines.append("- *Prerequisites*:")
                    for p in prereqs:
                        lines.append(f"  - {p}")
                else:
                    lines.append(f"- *Prerequisites*: {prereqs}")
                    
                if isinstance(v_steps, list):
                    lines.append("- *Verification Steps*:")
                    for v in v_steps:
                        lines.append(f"  - {v}")
                else:
                    lines.append(f"- *Verification Steps*: {v_steps}")
                    
                lines.append(f"- *Dry-Run Simulation*: `SelfHealingEngine.simulate_action('{act_id}')`")
                lines.append("")
                
            return ("RECOVERY_RECOMMENDATIONS", "\n".join(lines), [], "HIGH")

        # 7. Evidence Request / Supporting Data Inquiry
        if any(w in q_lower for w in ["show evidence", "what is the evidence", "supporting evidence", "cite evidence", "show proof"]):
            incidents = rca_results.get("incidents", [])
            if not incidents:
                return (
                    "EVIDENCE_INQUIRY",
                    "No critical incidents or evidence records available in current logs.",
                    [],
                    "HIGH"
                )
                
            lines = [
                "### 📑 Ground-Truth Log Evidence for Suspected Outages",
                "Below are the exact log lines extracted from the dataset supporting active diagnostic classifications:",
                ""
            ]
            for inc in incidents:
                cat = inc.get("title") or inc.get("category", "")
                lines.append(f"#### Incident Category: {cat}")
                for ev_item in inc.get("detected_evidence", []):
                    lines.append(f"- **Line {ev_item.get('line_no')}** `[{ev_item.get('timestamp')}]` `[{ev_item.get('service')}]` **[{ev_item.get('level')}]**: `{ev_item.get('message')}`")
                    evidence.append(ev_item)
                lines.append("")
                
            return ("EVIDENCE_INQUIRY", "\n".join(lines), evidence, "HIGH")

        # 8. Semantic Search Query Fallback (Stage 3 FAISS Integration)
        if vector_store and vector_store.get_stats().get("total_vectors", 0) > 0:
            search_res = vector_store.search(query, top_k=3)
            if search_res and search_res.get("results"):
                top_matches = search_res["results"]
                best_match = top_matches[0]
                
                # Check relevance threshold (e.g., at least 50% match)
                if best_match.get("similarity_pct", 0) >= 50.0:
                    lines = [
                        f"### 🔎 Semantic Log Retrieval for: *\"{query}\"*",
                        "Using high-dimensional vector embeddings (`all-MiniLM-L6-v2`) and FAISS sub-second search:",
                        ""
                    ]
                    for item in top_matches:
                        lines.append(
                            f"- **#{item['rank']} (Line {item['line_no']})** `[{item['service']}]` `[{item['level']}]` — "
                            f"**{item['similarity_pct']}% Match**\n"
                            f"  `{item['message']}` *(Time: {item['timestamp']})*"
                        )
                        evidence.append({
                            "line_no": item["line_no"],
                            "timestamp": item["timestamp"],
                            "service": item["service"],
                            "level": item["level"],
                            "message": item["message"]
                        })
                        
                    lines.append("\n> **Important Distinction**: Semantic similarity measures language proximity in embedding space; it does not constitute proof of operational causality.")
                    return ("SEMANTIC_SEARCH_FALLBACK", "\n".join(lines), evidence, "MEDIUM")

        # 9. Insufficient Evidence / Unknown Query Fallback
        monitored_services = df["service"].dropna().unique().tolist()
        answer = (
            "⚠️ **Insufficient Evidence in Active Logs**\n\n"
            f"The active dataset does not contain sufficient telemetry to answer: *\"{query}\"*.\n\n"
            "**Dataset Context**:\n"
            f"- Monitored Services: `{', '.join(monitored_services) if monitored_services else 'None'}`\n"
            f"- Total Ingested Logs: `{len(df)}` records\n"
            f"- System Health Index: `{health_data.get('health_score', 100)}%`\n\n"
            "You can ask about:\n"
            "1. *What are the most critical incidents?*\n"
            "2. *Why is the database failing?*\n"
            "3. *Which services are affected?*\n"
            "4. *What factors increased the risk score?*\n"
            "5. *How was the health score calculated?*\n"
            "6. *What recovery steps are recommended?*"
        )
        return ("INSUFFICIENT_EVIDENCE", answer, [], "INSUFFICIENT_EVIDENCE")

    def _build_system_context(
        self,
        df: pd.DataFrame,
        rca_results: Dict[str, Any],
        health_data: Dict[str, Any],
        risk_data: Dict[str, Any],
        evidence: List[Dict[str, Any]]
    ) -> str:
        """Constructs concise, grounded operational telemetry context for cloud LLMs."""
        context_parts = [
            f"HEALTH SCORE: {health_data.get('health_score', 100)}% ({health_data.get('condition', 'Stable')})",
            f"PREDICTIVE RISK: {risk_data.get('risk_score', 0)}/100 ({risk_data.get('risk_level', 'LOW')})",
            f"TOTAL INCIDENTS DETECTED: {rca_results.get('total_incidents', 0)}",
            f"SERVICES MONITORED: {', '.join(df['service'].dropna().unique().tolist())}",
            "\nACTIVE INCIDENTS:"
        ]
        for inc in rca_results.get("incidents", []):
            cat = inc.get("title") or inc.get("category")
            context_parts.append(
                f"- Category: {cat} | Severity: {inc.get('severity')} | Observed: {inc.get('explanation')} | Inferred: {inc.get('likely_root_cause')}"
            )
            
        if evidence:
            context_parts.append("\nEXTRACTED LOG EVIDENCE:")
            for e in evidence:
                context_parts.append(
                    f"Line {e.get('line_no')} [{e.get('timestamp')}] [{e.get('service')}] [{e.get('level')}]: {e.get('message')}"
                )
                
        return "\n".join(context_parts)

    @staticmethod
    def _row_to_evidence(row: pd.Series) -> Dict[str, Any]:
        """Converts a DataFrame row into an evidence dictionary."""
        return {
            "line_no": int(row.get("line_no", 0)),
            "timestamp": str(row.get("timestamp", "N/A")),
            "service": str(row.get("service", "unknown")),
            "level": str(row.get("level", "INFO")),
            "message": str(row.get("message", ""))
        }

    @staticmethod
    def execute_recovery_action(action_id: str) -> None:
        """
        Safety Gate Method.
        Explicitly prevents any execution of recovery actions against real infrastructure.
        Raises RuntimeError immediately.
        """
        raise RuntimeError(
            f"BLOCKED BY SAFETY POLICY: Execution of recovery action '{action_id}' against live infrastructure "
            "is strictly disabled. Autonomous recovery actions are limited to dry-run simulations and advisory playbooks."
        )
