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
            
        # Check greeting / capability help even before checking empty logs
        q_norm = re.sub(r"[^a-z0-9\s]", "", clean_query.lower()).strip()
        if q_norm in {"hi", "hello", "hey", "hii", "help", "menu", "commands"} or any(
            p in clean_query.lower() for p in ["what can you do", "who are you", "how do you work", "help me"]
        ):
            log_cnt = 0 if df is None else len(df)
            inc_cnt = len(rca_results.get("incidents", [])) if rca_results else 0
            help_ans = (
                "### 🤖 AI Infrastructure Assistant Ready\n"
                f"Currently monitoring **`{log_cnt}`** log record(s) with **`{inc_cnt}`** detected RCA incident(s) "
                f"(Health: **`{health_data.get('health_score', 100.0)}%`**).\n\n"
                "**You can ask me anything about your infrastructure or logs, including:**\n"
                "- **Summary & Timeline:** *\"Summarize the logs\"*, *\"What happened first?\"*, *\"Show the outage timeline\"*\n"
                "- **Root Cause & Services:** *\"What are the critical incidents?\"*, *\"Why is the database failing?\"*, *\"Check auth-service\"*\n"
                "- **Metrics & Risk:** *\"How was the health score calculated?\"*, *\"How many errors and warnings are there?\"*\n"
                "- **Specific Events / Keywords:** *\"What happened at 10:03?\"*, *\"Tell me about exit code 137\"*, *\"Did autoscaler trigger?\"*\n"
                "- **Safe Recovery:** *\"What recovery steps are recommended?\"*"
            )
            return {
                "query": clean_query,
                "answer": help_ans,
                "intent": "ASSISTANT_HELP",
                "confidence": "HIGH",
                "evidence": [],
                "provider": self.provider.provider_name,
                "advisory_notice": SAFETY_ENFORCEMENT_NOTICE,
            }

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
        if any(w in q_lower for w in ["health score", "health index", "calculate health", "health calculated", "why is health", "health breakdown"]):
            score = health_data.get("health_score", 100.0)
            condition = health_data.get("condition", "Stable")
            total_logs = len(df)
            err_mask = df["level"].isin(["CRITICAL", "FATAL", "ERROR"]) if "level" in df.columns else pd.Series([False] * total_logs)
            computed_err_rate = round((int(err_mask.sum()) / total_logs) * 100, 1) if total_logs > 0 else 0.0
            err_rate = health_data.get("error_rate_pct", computed_err_rate)
            penalties = health_data.get("deductions_breakdown") or health_data.get("penalties") or []
            degraded_svcs = health_data.get("degraded_services")
            if degraded_svcs is None and "service" in df.columns:
                degraded_svcs = df[err_mask]["service"].dropna().unique().tolist()

            lines = [
                f"### 🩺 Infrastructure Health Score: **{score}%** (`{condition}`)",
                f"- **Baseline Score**: Starts at `100.0%` for a fully operational cluster.",
                f"- **Total Error Rate**: `{err_rate}%` of parsed logs are errors or fatal crashes.",
                "- **Calculation Breakdown & Penalties**:"
            ]
            if penalties:
                for p in penalties:
                    detail = p.get("detail")
                    suffix = f" ({detail})" if detail else ""
                    lines.append(f"  - Deduction: **-{p.get('deduction', 0)} pts** — {p.get('reason', '')}{suffix}")
            else:
                lines.append("  - No deductions applied. All telemetry metrics within healthy thresholds.")

            lines.append("\n**Observed Telemetry Summary:**")
            lines.append(f"- Total Ingested Logs: `{total_logs}` records.")
            lines.append(f"- Degraded Services: `{len(degraded_svcs or [])}`")

            # Evidence from top errors
            err_df = df[err_mask].head(3)
            for _, r in err_df.iterrows():
                evidence.append(self._row_to_evidence(r))

            return ("HEALTH_SCORE_EXPLANATION", "\n".join(lines), evidence, "HIGH")

        # 2. Risk Score & Contributing Factors Inquiry
        if any(w in q_lower for w in ["risk score", "failure risk", "factors increased", "contributing factors", "risk calculated", "why is risk", "risk breakdown"]):
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
                    if "max_weight" in f:
                        weight_str = f"{f.get('score', 0)}/{f.get('max_weight', 0)} pts"
                        detail = f.get("metric", "") or f.get("impact", "")
                        lines.append(f"- **{name}** (Weight: `{weight_str}`): {detail}")
                    else:
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
        if any(w in q_lower for w in ["most critical", "critical incident", "what incidents", "fatal errors", "what went wrong", "list incidents", "all incidents", "any incidents", "major issue", "outages"]):
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

        # 3b. Specific Service Name Inspection (dynamic across any monitored service in df)
        if "service" in df.columns and not any(w in q_lower for w in ["why", "root cause", "recovery", "affected services"]):
            unique_services = [str(s) for s in df["service"].dropna().unique().tolist() if str(s).strip()]
            matched_svcs = [s for s in unique_services if s.lower() in q_lower]
            if matched_svcs:
                target_svc = matched_svcs[0]
                svc_df = df[df["service"] == target_svc]
                sev_counts = svc_df["level"].value_counts().to_dict() if "level" in svc_df.columns else {}
                lines = [
                    f"### 🧩 Service Inspection: **`{target_svc}`**",
                    f"- **Total Events Recorded**: `{len(svc_df)}`",
                    f"- **Severity Breakdown**: {', '.join(f'`{k}: {v}`' for k, v in sev_counts.items()) or 'N/A'}",
                    "",
                    "**Recent Activity**:",
                ]
                for _, r in svc_df.head(5).iterrows():
                    lines.append(f"- **Line {r.get('line_no')}** `[{r.get('timestamp')}]` **[{r.get('level')}]**: `{r.get('message')}`")
                    evidence.append(self._row_to_evidence(r))
                return ("SERVICE_INSPECTION", "\n".join(lines), evidence, "HIGH")

        # 4. Service-Specific Root Cause (e.g. database, redis, memory, network, auth, cpu, storage)
        domain_keywords = {
            "database": ["database", "db", "postgres", "sql", "pool", "slots"],
            "memory": ["memory", "oom", "killed process", "ram", "leak", "redis", "maxmemory"],
            "network": ["network", "gateway", "latency", "upstream", "timeout", "circuit breaker", "dns", "504"],
            "cpu": ["cpu", "load", "utilization", "throttle", "throttling"],
            "auth": ["auth", "unauthorized", "token", "jwt", "permission", "credentials", "forbidden", "logon"],
            "storage": ["storage", "disk", "iops", "filesystem", "space", "ntfs"]
        }

        matched_domain = None
        for dom, kws in domain_keywords.items():
            has_dom_kw = any(re.search(rf"\b{re.escape(k)}\b", q_lower) if len(k) <= 3 else (k in q_lower) for k in kws)
            has_trigger = any(tr in q_lower for tr in ["why", "cause", "fail", "error", "down", "issue", "what happened", "check", "status", "about", "explain", "problem", "find", "logs", "show"])
            if has_dom_kw and (has_trigger or len(q_lower.split()) <= 3):
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
        if any(w in q_lower for w in ["affected services", "services affected", "which services", "components affected", "what is down", "services down", "list services", "all services", "healthy services"]):
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
        if any(w in q_lower for w in ["recovery", "how to fix", "remediation", "healing", "playbooks", "fix the issue", "what should i do", "mitigate", "resolve", "solve", "next steps"]):
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
        if any(w in q_lower for w in ["show evidence", "what is the evidence", "supporting evidence", "cite evidence", "show proof", "evidence supporting"]):
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

        # 7c. Executive Summary / General Status Inquiry
        if any(w in q_lower for w in ["summary", "summarize", "overview", "status", "report", "explain logs", "what is happening", "how is the system", "everything ok", "tell me about the logs", "analyze"]):
            total_logs = len(df)
            lvl_counts = df["level"].value_counts().to_dict() if "level" in df.columns else {}
            incidents = rca_results.get("incidents", [])
            svcs = df["service"].dropna().unique().tolist() if "service" in df.columns else []
            lines = [
                "### 📊 Infrastructure Executive Summary",
                f"- **Health Index**: `{health_data.get('health_score', 100.0)}%` (`{health_data.get('condition', 'Stable')}`)",
                f"- **Failure Risk**: `{risk_data.get('risk_score', 0.0)}/100` (`{risk_data.get('risk_level', 'LOW')}`)",
                f"- **Parsed Logs**: `{total_logs}` events across `{len(svcs)}` services "
                f"(`CRITICAL/FATAL: {lvl_counts.get('CRITICAL', 0) + lvl_counts.get('FATAL', 0)}`, "
                f"`ERROR: {lvl_counts.get('ERROR', 0)}`, `WARN: {lvl_counts.get('WARN', 0)}`, `INFO: {lvl_counts.get('INFO', 0)}`)",
                f"- **Active RCA Incidents**: `{len(incidents)}`",
                "",
            ]
            if incidents:
                lines.append("**Key Findings**:")
                for inc in incidents:
                    lines.append(f"- **[{inc.get('severity')}] {inc.get('title')}** — {inc.get('likely_root_cause')}")
            else:
                lines.append("🟢 All services are operating normally with zero detected failure signatures.")
            err_rows = df[df["level"].isin(["CRITICAL", "FATAL", "ERROR"])].head(4)
            if err_rows.empty:
                err_rows = df.head(3)
            for _, r in err_rows.iterrows():
                evidence.append(self._row_to_evidence(r))
            return ("EXECUTIVE_SUMMARY", "\n".join(lines), evidence, "HIGH")

        # 7d. Chronological Timeline / Cascade Inquiry
        if any(w in q_lower for w in ["timeline", "chronology", "sequence", "what happened first", "when did", "cascade", "order", "start", "normalized", "recover"]):
            anom_df = df[df["level"].isin(["WARN", "WARNING", "ERROR", "CRITICAL", "FATAL"])]
            target_df = anom_df if not anom_df.empty else df
            lines = [
                "### ⏱️ Chronological Event Timeline",
                f"Showing **{min(len(target_df), 8)}** key events in execution order:",
                "",
            ]
            for _, r in target_df.head(8).iterrows():
                lines.append(f"- **Line {r.get('line_no')}** `[{r.get('timestamp')}]` `[{r.get('service')}]` **[{r.get('level')}]**: `{r.get('message')}`")
                evidence.append(self._row_to_evidence(r))
            return ("TIMELINE_ANALYSIS", "\n".join(lines), evidence, "HIGH")

        # 7e. Log Counts / Severity Filtering Inquiry
        if any(w in q_lower for w in ["how many", "count", "warnings", "errors", "critical logs", "total logs", "show logs", "list logs", "stats", "statistics"]):
            lvl_counts = df["level"].value_counts().to_dict() if "level" in df.columns else {}
            filter_lvls = ["CRITICAL", "FATAL", "ERROR", "WARN"]
            if "warn" in q_lower and "error" not in q_lower:
                filter_lvls = ["WARN", "WARNING"]
            elif "error" in q_lower and "warn" not in q_lower:
                filter_lvls = ["ERROR", "CRITICAL", "FATAL"]
            elif "info" in q_lower:
                filter_lvls = ["INFO"]
            matched_rows = df[df["level"].isin(filter_lvls)] if "level" in df.columns else df
            lines = [
                "### 📈 Log Telemetry Statistics",
                f"- **Total Events**: `{len(df)}`",
                "- **By Severity**: " + (", ".join(f"`{k}: {v}`" for k, v in lvl_counts.items()) or "None"),
                "",
                f"**Sample Matching Events ({len(matched_rows)} total)**:",
            ]
            for _, r in matched_rows.head(5).iterrows():
                lines.append(f"- **Line {r.get('line_no')}** `[{r.get('service')}]` **[{r.get('level')}]**: `{r.get('message')}`")
                evidence.append(self._row_to_evidence(r))
            return ("LOG_STATS_AND_FILTER", "\n".join(lines), evidence, "HIGH")

        # 7f. Direct Keyword / Substring Log Search (catches arbitrary log-grounded questions!)
        stop_words = {
            "what", "when", "where", "which", "who", "whom", "whose", "why", "how",
            "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "can", "could", "should", "would", "will", "shall",
            "the", "and", "for", "with", "from", "into", "about", "there", "this",
            "that", "these", "those", "tell", "show", "find", "give", "logs", "log",
            "event", "events", "system", "infrastructure", "any", "all", "please",
        }
        tokens = [t for t in re.findall(r"[a-z0-9_.\-:]+", q_lower) if len(t) >= 3 and t not in stop_words]
        if tokens and not df.empty:
            searchable = (
                df["message"].fillna("").str.lower()
                + " " + df["service"].fillna("").str.lower()
                + " " + df["level"].fillna("").str.lower()
                + " " + df["timestamp"].fillna("").str.lower()
            )
            scores = searchable.apply(lambda txt: sum(1 for tok in tokens if tok in txt))
            hit_df = df[scores > 0].copy()
            if not hit_df.empty:
                hit_df["_hits"] = scores[scores > 0]
                hit_df = hit_df.sort_values(by=["_hits", "line_no"], ascending=[False, True])
                lines = [
                    f"### 🔍 Grounded Log Matches for *\"{query}\"*",
                    f"Found **`{len(hit_df)}`** log event(s) matching your query:",
                    "",
                ]
                for _, r in hit_df.head(5).iterrows():
                    lines.append(f"- **Line {r.get('line_no')}** `[{r.get('timestamp')}]` `[{r.get('service')}]` **[{r.get('level')}]**: `{r.get('message')}`")
                    evidence.append(self._row_to_evidence(r))
                return ("KEYWORD_LOG_SEARCH", "\n".join(lines), evidence, "HIGH")

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
