"""
Live AI Infrastructure Detection & Persistent FAISS Pipeline.
Connects real incoming Windows logs & system telemetry to existing Stage 1-4 modules:
- InfrastructureLogParser (src/parser.py)
- RootCauseAnalysisEngine (src/rca_engine.py) + Windows Event Log fault patterns
- PredictiveFailureDetector (src/predictive_failure.py) + Hardware Telemetry Trend Forecasting
- InfrastructureHealthScorer (src/health_score.py)
- SelfHealingEngine (src/self_healing.py)
- LogEmbeddingEngine & FaissVectorStore (src/embedding_engine.py, src/vector_store.py)
- InfrastructureAIAssistant (src/assistant_engine.py)
"""
import hashlib
import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import faiss
import numpy as np
import pandas as pd

from config import EMBEDDING_DIMENSION
from src.parser import InfrastructureLogParser
from src.telemetry import TelemetryAnalyzer
from src.rca_engine import RootCauseAnalysisEngine, INCIDENT_PATTERNS
from src.predictive_failure import PredictiveFailureDetector
from src.health_score import InfrastructureHealthScorer
from src.self_healing import SelfHealingEngine
from src.embedding_engine import LogEmbeddingEngine
from src.vector_store import FaissVectorStore, SIMILARITY_DISCLAIMER
from src.assistant_engine import InfrastructureAIAssistant

from backend.database import (
    BASE_DIR,
    get_events,
    get_telemetry_history,
    update_device_ai_scores,
    upsert_incident,
)

# Supplemental Windows-specific patterns mapped cleanly onto the 6 core RCA categories
WINDOWS_RCA_PATTERNS: Dict[str, List[str]] = {
    "STORAGE_FAILURE": [
        r"ntfs.*(corrupt|bad block|delayed write|error)",
        r"disk.*(bad block|controller error|predictive failure|surprise removed)",
        r"event_id=(7|11|51|55|98|140|153)\b",
        r"low disk space",
        r"volume.*dirty bit",
        r"storahci|iaStor|nvme.*reset",
    ],
    "MEMORY_LEAK_OOM": [
        r"resource-exhaustion-detector",
        r"virtual memory.*minimum.*low",
        r"out of virtual memory",
        r"application popup.*low on memory",
        r"event_id=(2004)\b",
        r"exception code:\s*0xc0000005",
        r"faulting application name",
    ],
    "CPU_OVERLOAD": [
        r"processor.*thermal|throttl",
        r"service control manager.*did not respond in a timely fashion",
        r"event_id=(7000|7001|7009|7011|7022|7023|7024|7031|7034)\b",
        r"application hang",
        r"event_id=(1002)\b",
    ],
    "AUTHENTICATION_FAILURE": [
        r"event_id=(4625|4740|4771|4776)\b",
        r"logon failure",
        r"account locked out",
        r"kerberos.*(error|pre-authentication failed)",
        r"audit failure",
        r"access is denied",
    ],
    "NETWORK_LATENCY": [
        r"dns client events.*(timed out|name resolution)",
        r"event_id=(1014|4201|4202|4227)\b",
        r"network link is disconnected",
        r"dhcp.*(lost lease|unable to contact|nack)",
        r"tcpip.*(exhausted|failed to allocate)",
        r"winhttp.*timed out",
    ],
    "DATABASE_FAILURE": [
        r"mssql|sqlserver|postgres|mysql|sqlite.*(error|corrupt|deadlock|failed|timeout)",
        r"esent.*(database|log).*error",
        r"event_id=(455|489|490|1022)\b",
    ],
}


def compute_event_uid(device_id: str, ev: Dict[str, Any]) -> str:
    """Deterministic fingerprint for duplicate event prevention."""
    parts = [
        device_id,
        str(ev.get("source_type", "")),
        str(ev.get("channel", "")),
        str(ev.get("record_number") if ev.get("record_number") is not None else ""),
        str(ev.get("event_id") if ev.get("event_id") is not None else ""),
        str(ev.get("timestamp", "")),
        str(ev.get("service", "")),
        str(ev.get("message", "")),
    ]
    return hashlib.sha256("|".join(parts).encode("utf-8", errors="replace")).hexdigest()


def compute_hardware_trend_forecast(telemetry_history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes linear trend slopes across recent real telemetry snapshots
    to predict RAM, CPU, or Disk saturation risks before full exhaustion.
    """
    if len(telemetry_history) < 3:
        return {
            "status": "INSUFFICIENT_TELEMETRY",
            "samples": len(telemetry_history),
            "cpu_slope_per_sample": 0.0,
            "ram_slope_per_sample": 0.0,
            "disk_slope_per_sample": 0.0,
            "risk_penalty": 0.0,
            "warnings": [],
        }

    recent = telemetry_history[-20:]
    x = np.arange(len(recent), dtype=np.float64)
    cpu_vals = np.array([float(r.get("cpu_percent", 0.0)) for r in recent], dtype=np.float64)
    ram_vals = np.array([float(r.get("ram_percent", 0.0)) for r in recent], dtype=np.float64)
    disk_vals = np.array([float(r.get("disk_percent", 0.0)) for r in recent], dtype=np.float64)

    cpu_slope = float(np.polyfit(x, cpu_vals, 1)[0])
    ram_slope = float(np.polyfit(x, ram_vals, 1)[0])
    disk_slope = float(np.polyfit(x, disk_vals, 1)[0])

    warnings: List[str] = []
    risk_penalty = 0.0

    # Sustained CPU pressure across recent samples
    high_cpu_count = int(np.sum(cpu_vals >= 85.0))
    if high_cpu_count >= max(3, len(recent) // 2):
        risk_penalty += 15.0
        warnings.append(f"Sustained high CPU (>85%) across {high_cpu_count}/{len(recent)} samples (avg {cpu_vals.mean():.1f}%).")
    elif cpu_slope > 2.0 and cpu_vals[-1] > 65.0:
        risk_penalty += 8.0
        warnings.append(f"CPU load accelerating (+{cpu_slope:.1f}%/sample, currently {cpu_vals[-1]:.1f}%).")

    # Memory leak / steady RAM climb trajectory
    if ram_slope > 0.8 and ram_vals[-1] >= 75.0:
        steps_to_98 = max(1.0, (98.0 - ram_vals[-1]) / ram_slope)
        risk_penalty += 18.0
        warnings.append(
            f"Rising RAM trajectory (+{ram_slope:.2f}%/sample, currently {ram_vals[-1]:.1f}% — ~{steps_to_98:.0f} intervals to critical 98% if trend persists)."
        )

    # Disk growth trajectory
    if disk_slope > 0.25 and disk_vals[-1] >= 80.0:
        steps_to_98 = max(1.0, (98.0 - disk_vals[-1]) / disk_slope)
        risk_penalty += 15.0
        warnings.append(
            f"Disk utilization climbing (+{disk_slope:.2f}%/sample, currently {disk_vals[-1]:.1f}% — ~{steps_to_98:.0f} intervals to 98% capacity)."
        )

    return {
        "status": "ANALYZED",
        "samples": len(recent),
        "cpu_slope_per_sample": round(cpu_slope, 3),
        "ram_slope_per_sample": round(ram_slope, 3),
        "disk_slope_per_sample": round(disk_slope, 3),
        "risk_penalty": round(min(risk_penalty, 35.0), 1),
        "warnings": warnings,
    }


def _lightweight_384_embed(texts: List[str]) -> np.ndarray:
    """
    Low-memory (~2 MB RAM) 384-dim L2-normalized word+trigram hash embeddings for 512 MB cloud containers.
    Compatible with FAISS IndexFlatIP(384) when PyTorch/SentenceTransformer exceeds container RAM limits.
    """
    vecs = np.zeros((len(texts), EMBEDDING_DIMENSION), dtype=np.float32)
    for row_idx, text in enumerate(texts):
        clean = (text or "").lower()
        tokens = re.findall(r"[a-z0-9_]+", clean)
        grams = list(tokens)
        for t in tokens:
            if len(t) >= 4:
                grams.extend(t[i : i + 3] for i in range(len(t) - 2))
        if not grams:
            grams = [clean or "empty"]
        for g in grams:
            digest = hashlib.blake2b(g.encode("utf-8"), digest_size=8).digest()
            val = int.from_bytes(digest, "little")
            bucket = val % EMBEDDING_DIMENSION
            sign = 1.0 if ((val >> 16) & 1) == 0 else -1.0
            vecs[row_idx, bucket] += sign
        norm = float(np.linalg.norm(vecs[row_idx]))
        if norm > 0.0:
            vecs[row_idx] /= norm
    return vecs


def _is_low_memory_mode() -> bool:
    return os.environ.get("LOW_MEMORY_MODE", "false").strip().lower() in ("1", "true", "yes")


def _encode_texts(texts: List[str]) -> np.ndarray:
    if not texts:
        return np.empty((0, EMBEDDING_DIMENSION), dtype=np.float32)
    if _is_low_memory_mode():
        return _lightweight_384_embed(texts)
    model = LogEmbeddingEngine.get_model()
    embs = model.encode(texts, batch_size=8, show_progress_bar=False, normalize_embeddings=True)
    return np.asarray(embs, dtype=np.float32)


class PersistentLiveVectorStore:
    """
    Thread-safe live FAISS vector index backed by disk files for cross-restart historical similarity search.
    Uses the same SentenceTransformer ('all-MiniLM-L6-v2') and IndexFlatIP design as FaissVectorStore.
    """

    def __init__(self, index_dir: Optional[Path] = None):
        env_dir = os.environ.get("MONITOR_FAISS_DIR", "").strip()
        self.index_dir = Path(env_dir) if env_dir else (index_dir or (BASE_DIR / "data" / "faiss_live"))
        self.index_path = self.index_dir / "live.index"
        self.meta_path = self.index_dir / "live_meta.json"
        self._lock = threading.Lock()
        self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
        self.metadata: List[Dict[str, Any]] = []
        self._known_uids: set = set()
        self.load()

    def load(self) -> None:
        with self._lock:
            self.index_dir.mkdir(parents=True, exist_ok=True)
            if self.index_path.exists() and self.meta_path.exists():
                try:
                    self.index = faiss.read_index(str(self.index_path))
                    self.metadata = json.loads(self.meta_path.read_text(encoding="utf-8"))
                    self._known_uids = {m.get("event_uid") for m in self.metadata if m.get("event_uid")}
                    return
                except Exception:
                    pass
            self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
            self.metadata = []
            self._known_uids = set()

    def save(self) -> None:
        self.index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        self.meta_path.write_text(json.dumps(self.metadata, default=str), encoding="utf-8")

    def rebuild_from_db_if_empty(self, limit: int = 5000) -> int:
        """
        On ephemeral cloud filesystems (e.g. Render without persistent disk),
        rebuilds the FAISS index from events persisted in PostgreSQL/SQLite.
        """
        with self._lock:
            if self.index.ntotal > 0:
                return 0
        persisted = get_events(limit=limit)
        if not persisted:
            return 0
        # Add oldest -> newest
        return self.add_events(list(reversed(persisted)))

    def add_events(self, events: List[Dict[str, Any]]) -> int:
        if not events:
            return 0
        with self._lock:
            new_records = [e for e in events if e.get("event_uid") not in self._known_uids]
            if not new_records:
                return 0
            try:
                if _is_low_memory_mode():
                    texts = [LogEmbeddingEngine.format_log_for_embedding(r) for r in new_records]
                    embeddings = _lightweight_384_embed(texts)
                    meta_records = new_records
                else:
                    try:
                        embeddings, meta_records = LogEmbeddingEngine.embed_logs(new_records, batch_size=8)
                    except Exception as model_exc:
                        logging.getLogger("backend.ai_pipeline").warning(
                            "SentenceTransformer unavailable (%s); falling back to lightweight 384-dim embeddings.",
                            model_exc,
                        )
                        texts = [LogEmbeddingEngine.format_log_for_embedding(r) for r in new_records]
                        embeddings = _lightweight_384_embed(texts)
                        meta_records = new_records
            except Exception as exc:
                logging.getLogger("backend.ai_pipeline").exception("FAISS embedding failed: %s", exc)
                return 0
            if embeddings.size == 0:
                return 0
            vectors = np.ascontiguousarray(embeddings, dtype=np.float32)
            self.index.add(vectors)
            for rec in meta_records:
                uid = rec.get("event_uid")
                if uid:
                    self._known_uids.add(uid)
                self.metadata.append({
                    "event_uid": uid,
                    "device_id": rec.get("device_id"),
                    "hostname": rec.get("hostname"),
                    "timestamp": rec.get("timestamp"),
                    "channel": rec.get("channel"),
                    "event_id": rec.get("event_id"),
                    "level": rec.get("level"),
                    "service": rec.get("service"),
                    "message": rec.get("message"),
                    "is_critical": rec.get("is_critical", 0),
                    "rca_category": rec.get("rca_category"),
                })
            self.save()
            return len(meta_records)

    def search(
        self,
        query: str,
        top_k: int = 5,
        exclude_uid: Optional[str] = None,
        device_id: Optional[str] = None,
        min_similarity: float = 0.25,
    ) -> Dict[str, Any]:
        clean = (query or "").strip()
        if not clean:
            return {"query": "", "status": "EMPTY_QUERY", "total_matches": 0, "results": [], "disclaimer": SIMILARITY_DISCLAIMER}

        with self._lock:
            if self.index.ntotal == 0 or not self.metadata:
                return {"query": clean, "status": "INDEX_EMPTY", "total_matches": 0, "results": [], "disclaimer": SIMILARITY_DISCLAIMER}
            try:
                if _is_low_memory_mode():
                    q_vec = _lightweight_384_embed([clean])
                else:
                    try:
                        q_vec = LogEmbeddingEngine.embed_query(clean)
                    except Exception:
                        q_vec = _lightweight_384_embed([clean])
            except Exception as e:
                return {"query": clean, "status": "ERROR", "total_matches": 0, "results": [], "message": str(e), "disclaimer": SIMILARITY_DISCLAIMER}
            if q_vec is None:
                return {"query": clean, "status": "QUERY_EMBEDDING_FAILED", "total_matches": 0, "results": [], "disclaimer": SIMILARITY_DISCLAIMER}

            search_k = min(max(top_k * 4, 15), self.index.ntotal)
            distances, indices = self.index.search(q_vec, search_k)
            results = []
            for idx, dist in zip(indices[0], distances[0]):
                idx_int = int(idx)
                if idx_int == -1 or idx_int >= len(self.metadata):
                    continue
                rec = self.metadata[idx_int]
                if exclude_uid and rec.get("event_uid") == exclude_uid:
                    continue
                if device_id and rec.get("device_id") != device_id:
                    continue
                raw_sim = float(dist)
                if raw_sim < min_similarity:
                    continue
                sim_pct = round(max(0.0, min(1.0, (raw_sim + 1.0) / 2.0)) * 100, 1)
                results.append({
                    "rank": len(results) + 1,
                    "similarity_score": round(raw_sim, 4),
                    "similarity_pct": sim_pct,
                    "line_no": idx_int + 1,
                    "event_uid": rec.get("event_uid"),
                    "device_id": rec.get("device_id"),
                    "hostname": rec.get("hostname"),
                    "timestamp": rec.get("timestamp", "N/A"),
                    "channel": rec.get("channel", ""),
                    "level": rec.get("level", "INFO"),
                    "service": rec.get("service", "unknown"),
                    "message": rec.get("message", ""),
                    "rca_category": rec.get("rca_category"),
                })
                if len(results) >= top_k:
                    break

            return {
                "query": clean,
                "status": "SUCCESS",
                "total_matches": len(results),
                "results": results,
                "disclaimer": SIMILARITY_DISCLAIMER,
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "is_indexed": self.index.ntotal > 0,
                "total_vectors": self.index.ntotal,
                "dimension": EMBEDDING_DIMENSION,
            }

    def reset(self) -> None:
        with self._lock:
            self.index = faiss.IndexFlatIP(EMBEDDING_DIMENSION)
            self.metadata = []
            self._known_uids = set()
            if self.index_path.exists():
                self.index_path.unlink(missing_ok=True)
            if self.meta_path.exists():
                self.meta_path.unlink(missing_ok=True)


class LiveAIProcessor:
    """Processes incoming real events and telemetry through all AI monitoring modules."""

    def __init__(self, vector_store: Optional[PersistentLiveVectorStore] = None):
        self.vector_store = vector_store or PersistentLiveVectorStore()

    @staticmethod
    def _classify_event_rca(ev: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        level = str(ev.get("level", "INFO")).upper()
        if level == "WARNING":
            level = "WARN"
        msg = str(ev.get("message", ""))
        svc = str(ev.get("service", "system"))
        event_id_str = f"event_id={ev.get('event_id')}" if ev.get("event_id") is not None else ""
        combined = f"{svc} {msg} {event_id_str}"

        parsed = InfrastructureLogParser.parse_line(ev.get("raw_line") or msg, line_no=1) or {}
        row_df = pd.DataFrame([{
            "line_no": 1,
            "timestamp": ev.get("timestamp", parsed.get("timestamp", "")),
            "level": level or parsed.get("level", "INFO"),
            "service": svc or parsed.get("service", "system"),
            "message": msg or parsed.get("message", ""),
            "raw_line": ev.get("raw_line") or msg,
        }])

        rca_res = RootCauseAnalysisEngine.analyze_logs(row_df)
        if rca_res.get("incidents"):
            cat = rca_res["incidents"][0]["category"]
            return True, cat

        for cat_key, patterns in WINDOWS_RCA_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, combined, re.IGNORECASE):
                    return True, cat_key

        is_crit = level in ("CRITICAL", "FATAL", "ERROR")
        return is_crit, None

    def enrich_and_classify_events(self, device: Dict[str, Any], raw_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched: List[Dict[str, Any]] = []
        for item in raw_events:
            level = str(item.get("level", "INFO")).upper()
            if level == "WARNING":
                level = "WARN"
            msg = str(item.get("message", "")).strip()
            raw_line = str(item.get("raw_line") or f"{item.get('timestamp')} [{level}] [{item.get('service')}] {msg}")

            if item.get("source_type") == "APP_LOG" and item.get("raw_line"):
                parsed = InfrastructureLogParser.parse_line(item["raw_line"], line_no=1)
                if parsed:
                    if level == "INFO" and parsed.get("level") in ("CRITICAL", "FATAL", "ERROR", "WARN"):
                        level = parsed["level"]
                    if not msg:
                        msg = parsed.get("message", raw_line)

            ev = {
                "device_id": device["device_id"],
                "hostname": device["hostname"],
                "timestamp": item["timestamp"],
                "source_type": item.get("source_type", "WINDOWS_EVENT_LOG"),
                "channel": item.get("channel", "System"),
                "event_id": item.get("event_id"),
                "record_number": item.get("record_number"),
                "level": level,
                "service": item.get("service", "system"),
                "message": msg,
                "raw_line": raw_line,
            }
            ev["event_uid"] = item.get("event_uid") or compute_event_uid(device["device_id"], ev)

            is_crit, rca_cat = self._classify_event_rca(ev)
            ev["is_critical"] = 1 if is_crit else 0
            ev["rca_category"] = rca_cat

            if is_crit:
                sim = self.vector_store.search(
                    query=f"[{ev['service']}] {ev['message']}",
                    top_k=3,
                    exclude_uid=ev["event_uid"],
                    min_similarity=0.35,
                )
                ev["similar_incidents"] = sim.get("results", [])
            else:
                ev["similar_incidents"] = []

            enriched.append(ev)
        return enriched

    def index_new_events(self, inserted_events: List[Dict[str, Any]]) -> int:
        return self.vector_store.add_events(inserted_events)

    def evaluate_device_ai_state(self, device: Dict[str, Any], latest_telemetry: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        recent_events = get_events(device_id=device["device_id"], limit=150)
        if recent_events:
            ordered = list(reversed(recent_events))
            df = pd.DataFrame([
                {
                    "line_no": idx + 1,
                    "timestamp": ev.get("timestamp", "N/A"),
                    "level": ev.get("level", "INFO"),
                    "service": ev.get("service", "system"),
                    "message": ev.get("message", ""),
                    "raw_line": ev.get("raw_line", ""),
                }
                for idx, ev in enumerate(ordered)
            ])
        else:
            df = pd.DataFrame(columns=["line_no", "timestamp", "level", "service", "message", "raw_line"])

        health_data = InfrastructureHealthScorer.calculate_health(df)
        rca_results = RootCauseAnalysisEngine.analyze_logs(df)
        risk_data = PredictiveFailureDetector.assess_risk(df, rca_results)

        tel_history = get_telemetry_history(device["device_id"], limit=20)
        trend_forecast = compute_hardware_trend_forecast(tel_history)

        health_score = float(health_data["health_score"])
        risk_score = min(100.0, round(float(risk_data["risk_score"]) + float(trend_forecast.get("risk_penalty", 0.0)), 1))

        telemetry_incidents: List[Dict[str, Any]] = []
        cfg = device.get("config", {})
        cpu_thresh = float(cfg.get("cpu_alert_threshold", 90.0))
        ram_thresh = float(cfg.get("ram_alert_threshold", 90.0))
        disk_thresh = float(cfg.get("disk_alert_threshold", 90.0))

        if latest_telemetry:
            cpu = float(latest_telemetry.get("cpu_percent", 0.0))
            ram = float(latest_telemetry.get("ram_percent", 0.0))
            disk = float(latest_telemetry.get("disk_percent", 0.0))

            if cpu >= cpu_thresh:
                health_score = max(0.0, round(health_score - 15.0, 1))
                risk_score = min(100.0, round(risk_score + 20.0, 1))
                telemetry_incidents.append({
                    "category": "CPU_OVERLOAD",
                    "title": INCIDENT_PATTERNS["CPU_OVERLOAD"]["title"],
                    "severity": "CRITICAL" if cpu >= 95.0 else "HIGH",
                    "evidence_count": 1,
                    "detected_evidence": [{
                        "line_no": 0,
                        "timestamp": latest_telemetry.get("timestamp"),
                        "service": "windows-kernel-cpu",
                        "level": "CRITICAL" if cpu >= 95.0 else "WARN",
                        "message": f"Measured CPU utilization {cpu:.1f}% exceeded threshold {cpu_thresh:.1f}% on {device['hostname']}",
                    }],
                    "likely_root_cause": INCIDENT_PATTERNS["CPU_OVERLOAD"]["likely_cause"],
                    "explanation": f"Observed real CPU usage at {cpu:.1f}% (threshold {cpu_thresh:.1f}%).",
                    "confidence_pct": 92,
                    "recommended_next_steps": INCIDENT_PATTERNS["CPU_OVERLOAD"]["recommended_next_steps"],
                })

            if ram >= ram_thresh:
                health_score = max(0.0, round(health_score - 15.0, 1))
                risk_score = min(100.0, round(risk_score + 20.0, 1))
                telemetry_incidents.append({
                    "category": "MEMORY_LEAK_OOM",
                    "title": INCIDENT_PATTERNS["MEMORY_LEAK_OOM"]["title"],
                    "severity": "CRITICAL" if ram >= 95.0 else "HIGH",
                    "evidence_count": 1,
                    "detected_evidence": [{
                        "line_no": 0,
                        "timestamp": latest_telemetry.get("timestamp"),
                        "service": "windows-memory-manager",
                        "level": "CRITICAL" if ram >= 95.0 else "WARN",
                        "message": f"Measured RAM utilization {ram:.1f}% ({latest_telemetry.get('ram_used_gb', 0):.1f}/{latest_telemetry.get('ram_total_gb', 0):.1f} GB) exceeded threshold {ram_thresh:.1f}%",
                    }],
                    "likely_root_cause": INCIDENT_PATTERNS["MEMORY_LEAK_OOM"]["likely_cause"],
                    "explanation": f"Observed physical memory usage at {ram:.1f}% (threshold {ram_thresh:.1f}%).",
                    "confidence_pct": 90,
                    "recommended_next_steps": INCIDENT_PATTERNS["MEMORY_LEAK_OOM"]["recommended_next_steps"],
                })

            # Check aggregate disk OR any mounted volume exceeding threshold
            max_vol = max(
                [float(v.get("percent", 0.0)) for v in latest_telemetry.get("disk_volumes", [])] or [disk]
            )
            effective_disk = max(disk, max_vol)
            if effective_disk >= disk_thresh:
                health_score = max(0.0, round(health_score - 18.0, 1))
                risk_score = min(100.0, round(risk_score + 22.0, 1))
                telemetry_incidents.append({
                    "category": "STORAGE_FAILURE",
                    "title": INCIDENT_PATTERNS["STORAGE_FAILURE"]["title"],
                    "severity": "CRITICAL" if effective_disk >= 95.0 else "HIGH",
                    "evidence_count": 1,
                    "detected_evidence": [{
                        "line_no": 0,
                        "timestamp": latest_telemetry.get("timestamp"),
                        "service": "windows-storage",
                        "level": "CRITICAL" if effective_disk >= 95.0 else "WARN",
                        "message": f"Measured disk volume utilization {effective_disk:.1f}% exceeded threshold {disk_thresh:.1f}%",
                    }],
                    "likely_root_cause": INCIDENT_PATTERNS["STORAGE_FAILURE"]["likely_cause"],
                    "explanation": f"Observed storage utilization at {effective_disk:.1f}% (threshold {disk_thresh:.1f}%).",
                    "confidence_pct": 95,
                    "recommended_next_steps": INCIDENT_PATTERNS["STORAGE_FAILURE"]["recommended_next_steps"],
                })

        win_matched_by_cat: Dict[str, List[Dict[str, Any]]] = {}
        for ev in recent_events:
            cat = ev.get("rca_category")
            if cat and cat in INCIDENT_PATTERNS:
                win_matched_by_cat.setdefault(cat, []).append({
                    "line_no": ev.get("id", 0),
                    "timestamp": ev.get("timestamp", "N/A"),
                    "service": ev.get("service", "system"),
                    "level": ev.get("level", "ERROR"),
                    "message": ev.get("message", ""),
                })

        all_incidents = list(rca_results.get("incidents", []))
        existing_cats = {i["category"] for i in all_incidents}
        for cat, ev_list in win_matched_by_cat.items():
            if cat not in existing_cats:
                meta = INCIDENT_PATTERNS[cat]
                all_incidents.append({
                    "category": cat,
                    "title": meta["title"],
                    "severity": "CRITICAL" if any(e["level"] in ("CRITICAL", "FATAL") for e in ev_list) else meta["default_severity"],
                    "evidence_count": len(ev_list),
                    "detected_evidence": ev_list[:10],
                    "likely_root_cause": meta["likely_cause"],
                    "explanation": f"{meta['explanation']} (Matched {len(ev_list)} real Windows event traces).",
                    "confidence_pct": min(65 + len(ev_list) * 8, 96),
                    "recommended_next_steps": meta["recommended_next_steps"],
                })
                existing_cats.add(cat)

        for t_inc in telemetry_incidents:
            if t_inc["category"] not in existing_cats:
                all_incidents.append(t_inc)
                existing_cats.add(t_inc["category"])

        if health_score >= InfrastructureHealthScorer.THRESHOLD_STABLE:
            condition = "Stable"
        elif health_score >= InfrastructureHealthScorer.THRESHOLD_WARNING:
            condition = "Warning"
        else:
            condition = "Critical"

        if risk_score >= 80.0:
            risk_level = "CRITICAL"
        elif risk_score >= 55.0:
            risk_level = "HIGH"
        elif risk_score >= 30.0:
            risk_level = "ELEVATED"
        elif risk_score >= 10.0:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"

        update_device_ai_scores(device["device_id"], health_score, condition, risk_score, risk_level)

        trend_summary = " | ".join(trend_forecast["warnings"]) if trend_forecast["warnings"] else risk_data.get("summary", "")
        created_or_updated: List[Dict[str, Any]] = []
        newly_created: List[Dict[str, Any]] = []
        for inc in all_incidents:
            recs = SelfHealingEngine.generate_recommendations([inc])
            ev_summary_lines = [
                f"[{e.get('timestamp')}] [{e.get('service')}] [{e.get('level')}] {e.get('message')}"
                for e in inc.get("detected_evidence", [])[:5]
            ]
            query_str = f"{inc.get('title')} {ev_summary_lines[0] if ev_summary_lines else ''}"
            sim_hist = self.vector_store.search(query_str, top_k=3, min_similarity=0.3).get("results", [])

            saved, is_new = upsert_incident({
                "device_id": device["device_id"],
                "hostname": device["hostname"],
                "category": inc["category"],
                "title": inc["title"],
                "severity": inc["severity"],
                "evidence": inc.get("detected_evidence", [])[:15],
                "confirmed_evidence": "\n".join(ev_summary_lines),
                "possible_root_cause": inc.get("likely_root_cause", ""),
                "predicted_risk_note": f"Heuristic device risk {risk_score}/100 ({risk_level}): {trend_summary}",
                "confidence_pct": int(inc.get("confidence_pct", 70)),
                "recommendations": recs,
                "similar_history": sim_hist,
            })
            created_or_updated.append(saved)
            if is_new:
                newly_created.append(saved)

        return {
            "health_score": health_score,
            "health_condition": condition,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "trend_forecast": trend_forecast,
            "incidents": created_or_updated,
            "newly_created_incidents": newly_created,
        }

    def query_assistant(self, query: str, device_id: Optional[str] = None) -> Dict[str, Any]:
        events = get_events(device_id=device_id, limit=250)
        if not events:
            empty_df = pd.DataFrame(columns=["line_no", "timestamp", "level", "service", "message", "raw_line"])
            assistant = InfrastructureAIAssistant()
            return assistant.ask(
                query=query,
                df=empty_df,
                rca_results={"incidents": [], "total_incidents": 0},
                health_data={"health_score": 100.0, "condition": "Stable", "penalties": []},
                risk_data={"risk_score": 0.0, "risk_level": "LOW", "contributing_factors": []},
                vector_store=None,
                dataset_id=device_id or "live-fleet",
            )

        ordered = list(reversed(events))
        df = pd.DataFrame([
            {
                "line_no": idx + 1,
                "timestamp": ev.get("timestamp", "N/A"),
                "level": ev.get("level", "INFO"),
                "service": f"{ev.get('hostname', 'host')}:{ev.get('service', 'system')}",
                "message": ev.get("message", ""),
                "raw_line": ev.get("raw_line", ""),
            }
            for idx, ev in enumerate(ordered)
        ])

        rca = RootCauseAnalysisEngine.analyze_logs(df)
        health = InfrastructureHealthScorer.calculate_health(df)
        risk = PredictiveFailureDetector.assess_risk(df, rca)
        telemetry = TelemetryAnalyzer.compute_summary(df)
        health["error_rate_pct"] = telemetry.get("error_rate_pct", 0.0)
        health["penalties"] = health.get("deductions_breakdown", [])
        health["degraded_services"] = df[df["level"].isin(["CRITICAL", "FATAL", "ERROR"])]["service"].unique().tolist()

        vs = FaissVectorStore()
        try:
            if _is_low_memory_mode():
                recs = df.to_dict(orient="records")
                embs = _encode_texts([LogEmbeddingEngine.format_log_for_embedding(r) for r in recs])
            else:
                embs, recs = LogEmbeddingEngine.embed_logs(df, batch_size=8)
            if embs.size > 0:
                vs.build_index(embs, recs)
        except Exception:
            pass

        assistant = InfrastructureAIAssistant()
        return assistant.ask(
            query=query,
            df=df,
            rca_results=rca,
            health_data=health,
            risk_data=risk,
            vector_store=vs,
            dataset_id=f"live:{device_id or 'all'}",
        )
