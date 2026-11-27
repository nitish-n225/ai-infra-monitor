"""
Kaggle-Trained Infrastructure Log Anomaly Detection Engine.

Provides leak-free feature engineering for LogHub HDFS_v1 block traces and
template sequences, plus safe runtime scoring for both structured HDFS datasets
and arbitrary infrastructure log DataFrames (Windows Event Logs / uploaded logs).
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

try:
    import joblib
except Exception:  # pragma: no cover - optional fallback if joblib unavailable
    joblib = None  # type: ignore

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = ROOT_DIR / "models" / "hdfs_log_anomaly_model.joblib"
DEFAULT_METRICS_PATH = ROOT_DIR / "models" / "hdfs_evaluation_metrics.json"

EVENT_IDS: List[str] = [f"E{i}" for i in range(1, 30)]

# Built from HDFS.log_templates.csv (pure template definitions, zero label leakage)
DEFAULT_HDFS_TEMPLATES: Dict[str, str] = {
    "E1": "Adding an already existing block",
    "E2": "Verification succeeded for",
    "E3": "Served block to",
    "E4": "Got exception while serving to",
    "E5": "Receiving block src dest",
    "E6": "Received block src dest of size",
    "E7": "writeBlock received exception",
    "E8": "PacketResponder for block Interrupted",
    "E9": "Received block of size from",
    "E10": "PacketResponder Exception",
    "E11": "PacketResponder for block terminating",
    "E12": "Exception writing block to mirror",
    "E13": "Receiving empty packet for block",
    "E14": "Exception in receiveBlock for block",
    "E15": "Changing block file offset of block from to meta file offset to",
    "E16": "Transmitted block to",
    "E17": "Failed to transfer to got",
    "E18": "Starting thread to transfer block to",
    "E19": "Reopen Block",
    "E20": "Unexpected error trying to delete block BlockInfo not found in volumeMap",
    "E21": "Deleting block file",
    "E22": "BLOCK NameSystem allocateBlock",
    "E23": "BLOCK NameSystem delete is added to invalidSet of",
    "E24": "BLOCK Removing block from neededReplications as it does not belong to any file",
    "E25": "BLOCK ask to replicate to",
    "E26": "BLOCK NameSystem addStoredBlock blockMap updated is added to size",
    "E27": "BLOCK NameSystem addStoredBlock Redundant addStoredBlock request received for on size",
    "E28": "BLOCK NameSystem addStoredBlock addStoredBlock request received for on size But it does not belong to any file",
    "E29": "PendingReplicationMonitor timed out block",
}

EXCEPTION_EVENT_IDS = ("E4", "E7", "E10", "E12", "E14")
FAILURE_EVENT_IDS = ("E8", "E13", "E17", "E20", "E28", "E29")
REPLICATION_EVENT_IDS = ("E21", "E23", "E24", "E25", "E29")

# Compiled regex matchers from HDFS templates so live/uploaded text can map into E1..E29 signals
_TEMPLATE_REGEXES: List[Tuple[str, re.Pattern[str]]] = [
    ("E1", re.compile(r"Adding an already existing block", re.I)),
    ("E2", re.compile(r"Verification succeeded for", re.I)),
    ("E3", re.compile(r"Served block\b", re.I)),
    ("E4", re.compile(r"Got exception while serving", re.I)),
    ("E5", re.compile(r"Receiving block\b.*\bsrc:", re.I)),
    ("E6", re.compile(r"Received block\b.*\bsrc:.*\bof size", re.I)),
    ("E7", re.compile(r"writeBlock received exception", re.I)),
    ("E8", re.compile(r"PacketResponder\b.*\bInterrupted", re.I)),
    ("E9", re.compile(r"Received block\b.*\bof size.*\bfrom", re.I)),
    ("E10", re.compile(r"PacketResponder\b.*\bException", re.I)),
    ("E11", re.compile(r"PacketResponder\b.*\bterminating", re.I)),
    ("E12", re.compile(r"Exception writing block", re.I)),
    ("E13", re.compile(r"Receiving empty packet", re.I)),
    ("E14", re.compile(r"Exception in receiveBlock", re.I)),
    ("E15", re.compile(r"Changing block file offset", re.I)),
    ("E16", re.compile(r"Transmitted block\b", re.I)),
    ("E17", re.compile(r"Failed to transfer\b", re.I)),
    ("E18", re.compile(r"Starting thread to transfer block", re.I)),
    ("E19", re.compile(r"Reopen Block", re.I)),
    ("E20", re.compile(r"Unexpected error trying to delete block|BlockInfo not found", re.I)),
    ("E21", re.compile(r"Deleting block\b", re.I)),
    ("E22", re.compile(r"NameSystem.*allocateBlock", re.I)),
    ("E23", re.compile(r"NameSystem.*delete.*invalidSet", re.I)),
    ("E24", re.compile(r"Removing block.*neededReplications", re.I)),
    ("E25", re.compile(r"ask\b.*\bto replicate", re.I)),
    ("E26", re.compile(r"addStoredBlock:\s*blockMap updated", re.I)),
    ("E27", re.compile(r"Redundant addStoredBlock", re.I)),
    ("E28", re.compile(r"does not belong to any file", re.I)),
    ("E29", re.compile(r"PendingReplicationMonitor timed out", re.I)),
]


def clean_template_text(raw_template: str) -> str:
    """Strips LogHub placeholder tokens `[*]` and punctuation noise for clean text modeling."""
    cleaned = re.sub(r"\[\*\]", " ", str(raw_template or ""))
    cleaned = re.sub(r"[^A-Za-z0-9_ ]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def load_template_map(templates_csv: Optional[Path] = None) -> Dict[str, str]:
    """Loads cleaned E1..E29 template text from CSV if present, otherwise uses defaults."""
    out = dict(DEFAULT_HDFS_TEMPLATES)
    if templates_csv and Path(templates_csv).exists():
        tdf = pd.read_csv(templates_csv)
        for row in tdf.itertuples(index=False):
            eid = str(getattr(row, "EventId", "")).strip()
            tpl = clean_template_text(getattr(row, "EventTemplate", ""))
            if eid and tpl:
                out[eid] = tpl
    return out


def build_event_feature_matrix(
    occurrence_df: pd.DataFrame,
    traces_df: Optional[pd.DataFrame] = None,
    include_timing: bool = False,
) -> Tuple[np.ndarray, List[str]]:
    """
    Extracts strictly leak-free numeric features from HDFS Event_occurrence_matrix (and optional Event_traces).
    Drops BlockId, Label, and Type completely so zero target/post-hoc leakage occurs.
    """
    missing_cols = [c for c in EVENT_IDS if c not in occurrence_df.columns]
    if missing_cols:
        raise ValueError(f"Missing expected event columns: {missing_cols}")

    counts = occurrence_df[EVENT_IDS].to_numpy(dtype=np.float32)
    total_events = counts.sum(axis=1, keepdims=True)
    safe_total = np.maximum(total_events, 1.0)
    unique_types = (counts > 0).sum(axis=1, keepdims=True).astype(np.float32)
    diversity = unique_types / safe_total
    max_count = counts.max(axis=1, keepdims=True)
    dominance = max_count / safe_total

    idx_map = {eid: i for i, eid in enumerate(EVENT_IDS)}
    exc_idx = [idx_map[e] for e in EXCEPTION_EVENT_IDS]
    fail_idx = [idx_map[e] for e in FAILURE_EVENT_IDS]
    rep_idx = [idx_map[e] for e in REPLICATION_EVENT_IDS]

    exc_cnt = counts[:, exc_idx].sum(axis=1, keepdims=True)
    fail_cnt = counts[:, fail_idx].sum(axis=1, keepdims=True)
    rep_cnt = counts[:, rep_idx].sum(axis=True if False else 1, keepdims=True)
    err_total = exc_cnt + fail_cnt
    err_ratio = err_total / safe_total
    has_exc = (exc_cnt > 0).astype(np.float32)
    has_fail = (fail_cnt > 0).astype(np.float32)
    ratios = counts / safe_total

    parts = [
        counts,
        ratios,
        total_events,
        unique_types,
        diversity,
        max_count,
        dominance,
        exc_cnt,
        fail_cnt,
        rep_cnt,
        err_total,
        err_ratio,
        has_exc,
        has_fail,
    ]
    names = (
        list(EVENT_IDS)
        + [f"{e}_ratio" for e in EVENT_IDS]
        + [
            "total_events",
            "unique_event_types",
            "event_diversity_ratio",
            "max_event_count",
            "max_event_dominance",
            "exception_event_count",
            "failure_interrupt_count",
            "replication_delete_count",
            "error_signal_total",
            "error_signal_ratio",
            "has_exception_flag",
            "has_failure_flag",
        ]
    )

    if include_timing and traces_df is not None:
        lat = pd.to_numeric(traces_df["Latency"], errors="coerce").fillna(0.0).to_numpy(dtype=np.float32).reshape(-1, 1)
        log_lat = np.log1p(np.maximum(lat, 0.0))
        lat_per_event = lat / safe_total
        # Parse TimeInterval strings vectorized using fast C-backed numpy fromstring
        ti_mean = np.zeros((len(traces_df), 1), dtype=np.float32)
        ti_max = np.zeros((len(traces_df), 1), dtype=np.float32)
        ti_std = np.zeros((len(traces_df), 1), dtype=np.float32)
        ti_nonzero_ratio = np.zeros((len(traces_df), 1), dtype=np.float32)
        for i, s in enumerate(traces_df["TimeInterval"].astype(str).tolist()):
            inner = s.strip()[1:-1]
            if not inner:
                continue
            arr = np.fromstring(inner, sep=",", dtype=np.float32)
            if arr.size > 0:
                ti_mean[i, 0] = float(arr.mean())
                ti_max[i, 0] = float(arr.max())
                ti_std[i, 0] = float(arr.std())
                ti_nonzero_ratio[i, 0] = float((arr > 0).mean())
        parts.extend([lat, log_lat, lat_per_event, ti_mean, np.log1p(np.maximum(ti_max, 0.0)), ti_std, ti_nonzero_ratio])
        names.extend(["latency", "log1p_latency", "latency_per_event", "ti_mean", "log1p_ti_max", "ti_std", "ti_nonzero_ratio"])

    X = np.hstack(parts).astype(np.float32)
    return X, names


def build_reconstructed_log_texts(
    occurrence_df: pd.DataFrame,
    template_map: Optional[Dict[str, str]] = None,
) -> List[str]:
    """
    Reconstructs natural-language log session documents from active EventId counts using HDFS.log_templates.csv.
    Preserves exact semantic wording without exposing BlockId, Label, or Type.
    """
    tpls = template_map or DEFAULT_HDFS_TEMPLATES
    counts = occurrence_df[EVENT_IDS].to_numpy(dtype=np.int32)
    tpl_list = [tpls[e] for e in EVENT_IDS]
    texts: List[str] = []
    for row in counts:
        # Include present template phrases (repeating up to 3x to encode elevated bursts without exploding length)
        active = []
        for idx, cnt in enumerate(row):
            if cnt > 0:
                active.append(tpl_list[idx])
                if cnt >= 5:
                    active.append(tpl_list[idx])
        texts.append(" | ".join(active) if active else "empty trace")
    return texts


class LogAnomalyScorer:
    """Runtime inference wrapper around the trained Kaggle HDFS anomaly model bundle."""

    _cached_bundle: Optional[Dict[str, Any]] = None
    _cached_metrics: Optional[Dict[str, Any]] = None

    @classmethod
    def load_bundle(cls, model_path: Path = DEFAULT_MODEL_PATH) -> Optional[Dict[str, Any]]:
        if cls._cached_bundle is not None:
            return cls._cached_bundle
        if joblib is None or not Path(model_path).exists():
            return None
        try:
            cls._cached_bundle = joblib.load(model_path)
            return cls._cached_bundle
        except Exception:
            return None

    @classmethod
    def load_evaluation_metrics(cls, metrics_path: Path = DEFAULT_METRICS_PATH) -> Optional[Dict[str, Any]]:
        if cls._cached_metrics is not None:
            return cls._cached_metrics
        if not Path(metrics_path).exists():
            return None
        try:
            cls._cached_metrics = json.loads(Path(metrics_path).read_text(encoding="utf-8"))
            return cls._cached_metrics
        except Exception:
            return None

    @classmethod
    def clear_cache(cls) -> None:
        cls._cached_bundle = None
        cls._cached_metrics = None

    @classmethod
    def score_parsed_logs(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Scores a parsed infrastructure log DataFrame (from InfrastructureLogParser or Live Events)
        using the trained Kaggle text + template ML pipeline.
        Never raises on empty DataFrames or missing optional model artifacts.
        """
        if df is None or df.empty:
            return {
                "available": Path(DEFAULT_MODEL_PATH).exists(),
                "model_name": "Kaggle HDFS_v1 Anomaly Classifier",
                "total_events": 0,
                "flagged_events": 0,
                "anomaly_rate_pct": 0.0,
                "max_anomaly_prob": 0.0,
                "mean_anomaly_prob": 0.0,
                "prediction": "NORMAL",
                "matched_templates": [],
                "flagged_samples": [],
            }

        bundle = cls.load_bundle()
        messages = df["message"].astype(str).tolist() if "message" in df.columns else [str(r) for r in df.iloc[:, 0]]
        levels = df["level"].astype(str).str.upper().tolist() if "level" in df.columns else ["INFO"] * len(messages)

        # Match HDFS templates & count signals across the log stream
        matched_counts: Dict[str, int] = {}
        for msg in messages:
            for eid, pat in _TEMPLATE_REGEXES:
                if pat.search(msg):
                    matched_counts[eid] = matched_counts.get(eid, 0) + 1

        if bundle and "text_model" in bundle:
            text_pipe = bundle["text_model"]
            thresh = float(bundle.get("text_threshold", 0.5))
            # Limit per-call inference batch size for instant UI response on huge files
            sample_msgs = messages[:2000]
            probs = text_pipe.predict_proba(sample_msgs)[:, 1]

            tfidf = text_pipe.named_steps.get("tfidf")
            clf = text_pipe.named_steps.get("clf")
            if tfidf is not None and clf is not None:
                X_tfidf = tfidf.transform(sample_msgs)
                nnz_rows = np.diff(X_tfidf.indptr)
                pos_weights = np.maximum(clf.coef_[0], 0.0)
                pos_contrib = np.asarray(X_tfidf.multiply(pos_weights).sum(axis=1)).ravel()
            else:
                nnz_rows = np.zeros(len(sample_msgs), dtype=np.int32)
                pos_contrib = np.zeros(len(sample_msgs), dtype=np.float32)

            in_hdfs_domain = len(matched_counts) >= 1 and bool(np.any(nnz_rows >= 3))
            lvls_slice = levels[: len(sample_msgs)]
            sev_boost = np.array(
                [
                    0.45 if lvl in ("CRITICAL", "FATAL") else (0.28 if lvl == "ERROR" else (0.10 if lvl in ("WARN", "WARNING") else 0.0))
                    for lvl in lvls_slice
                ],
                dtype=np.float32,
            )

            # In-domain HDFS logs use calibrated LogisticRegression probability directly.
            # Cross-domain OS/Windows logs guard against the +6.82 out-of-vocab HDFS intercept
            # by scoring strictly on learned positive anomaly token weights + log severity.
            if in_hdfs_domain:
                effective_probs = np.where(nnz_rows >= 3, probs, 0.0)
                flagged_mask = (nnz_rows >= 3) & (probs >= thresh)
                effective_thresh = thresh
                domain_mode = "HDFS_IN_DOMAIN"
            else:
                pos_signal = 1.0 - np.exp(-0.9 * pos_contrib)
                effective_probs = np.clip(pos_signal * 0.65 + sev_boost, 0.0, 1.0)
                sev_is_err = np.array([lvl in ("CRITICAL", "FATAL", "ERROR") for lvl in lvls_slice], dtype=bool)
                flagged_mask = (effective_probs >= 0.65) & (sev_is_err | (pos_contrib >= 2.0))
                effective_thresh = 0.65
                domain_mode = "CROSS_DOMAIN_TRANSFER"

            flagged_idx = np.where(flagged_mask)[0]
            flagged_samples = []
            for i in flagged_idx[np.argsort(-effective_probs[flagged_idx])[:8]]:
                flagged_samples.append({
                    "line_no": int(df.iloc[i].get("line_no", i + 1)) if "line_no" in df.columns else int(i + 1),
                    "level": levels[i],
                    "service": str(df.iloc[i].get("service", "unknown")) if "service" in df.columns else "unknown",
                    "probability_pct": round(float(effective_probs[i]) * 100.0, 1),
                    "raw_ml_prob_pct": round(float(probs[i]) * 100.0, 1),
                    "message": messages[i][:240],
                })

            max_prob = float(effective_probs.max()) if len(effective_probs) else 0.0
            mean_prob = float(effective_probs.mean()) if len(effective_probs) else 0.0
            flagged_cnt = int(flagged_mask.sum())
            rate_pct = round((flagged_cnt / max(len(sample_msgs), 1)) * 100.0, 2)
            pred = "ANOMALY_DETECTED" if flagged_cnt > 0 else "NORMAL"
            return {
                "available": True,
                "model_name": bundle.get("primary_model_name", "Kaggle HDFS_v1 Classifier"),
                "domain_mode": domain_mode,
                "evaluated_rows": len(sample_msgs),
                "total_events": len(messages),
                "flagged_events": flagged_cnt,
                "anomaly_rate_pct": rate_pct,
                "max_anomaly_prob": round(max_prob * 100.0, 1),
                "mean_anomaly_prob": round(mean_prob * 100.0, 1),
                "threshold_pct": round(effective_thresh * 100.0, 1),
                "prediction": pred,
                "matched_templates": [{"template_id": k, "count": v} for k, v in sorted(matched_counts.items())],
                "flagged_samples": flagged_samples,
            }

        return {
            "available": False,
            "model_name": "Kaggle HDFS_v1 Anomaly Classifier (Not Loaded)",
            "total_events": len(messages),
            "flagged_events": 0,
            "anomaly_rate_pct": 0.0,
            "max_anomaly_prob": 0.0,
            "mean_anomaly_prob": 0.0,
            "prediction": "UNAVAILABLE",
            "matched_templates": [{"template_id": k, "count": v} for k, v in sorted(matched_counts.items())],
            "flagged_samples": [],
        }

    @classmethod
    def score_hdfs_matrix(cls, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Scores an Event_occurrence_matrix DataFrame directly when uploaded from Kaggle."""
        if df is None or df.empty or not all(col in df.columns for col in EVENT_IDS):
            return None
        bundle = cls.load_bundle()
        if not bundle or "session_model" not in bundle:
            return None

        X, _ = build_event_feature_matrix(df, include_timing=False)
        model = bundle["session_model"]
        thresh = float(bundle.get("session_threshold", 0.5))
        probs = model.predict_proba(X)[:, 1]
        preds = (probs >= thresh).astype(int)
        return {
            "available": True,
            "model_name": bundle.get("session_model_name", "HistGradientBoostingClassifier"),
            "rows": int(len(df)),
            "predicted_anomalies": int(preds.sum()),
            "predicted_normal": int((1 - preds).sum()),
            "anomaly_rate_pct": round(float(preds.mean()) * 100.0, 2),
            "threshold": round(thresh, 4),
            "probabilities": probs,
            "predictions": preds,
        }

