"""
Infrastructure Log Parser Module.
Parses various enterprise infrastructure log formats into structured DataFrames.
"""
import csv
import io
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

# Regular expression patterns for common infrastructure formats:
# 1. Bracketed Level & Service: 2026-10-25 10:00:01.102 [INFO] [ingress-gateway] Message here
PATTERN_BRACKETED = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+'
    r'\[(?P<level>[A-Za-z]+)\]\s+'
    r'\[(?P<service>[^\]]+)\]\s+'
    r'(?P<message>.*)$'
)

# 2. Standard ISO + Level: 2026-10-25T10:00:01Z ERROR auth-service: Message here
PATTERN_STANDARD = re.compile(
    r'^(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+'
    r'(?P<level>INFO|WARN|WARNING|ERROR|FATAL|CRITICAL|DEBUG)\s+'
    r'(?:\[(?P<service_bracket>[^\]]+)\]|(?P<service_plain>[\w\.\-]+)[:\s])\s*'
    r'(?P<message>.*)$',
    re.IGNORECASE
)

# 3. Syslog Format: Oct 25 10:15:30 cluster-node-01 systemd[1]: Message
PATTERN_SYSLOG = re.compile(
    r'^(?P<timestamp>[A-Za-z]{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+'
    r'(?P<service>[\w\.\-]+)(?:\[\d+\])?:\s+'
    r'(?P<message>.*)$'
)

class InfrastructureLogParser:
    """Parses raw infrastructure log strings and files into normalized pandas DataFrames."""

    @staticmethod
    def parse_line(line: str, line_no: int = 1) -> Dict[str, Any]:
        """Parses a single log line into a standardized dictionary."""
        raw_line = line.strip()
        if not raw_line:
            return None

        # 1. Try parsing JSON-structured logs (Docker / Kubernetes format)
        if raw_line.startswith("{") and raw_line.endswith("}"):
            try:
                data = json.loads(raw_line)
                return {
                    "line_no": line_no,
                    "timestamp": str(data.get("time") or data.get("timestamp") or datetime.utcnow().isoformat()),
                    "level": str(data.get("level") or data.get("severity") or "INFO").upper(),
                    "service": str(data.get("service") or data.get("app") or data.get("name") or "unknown-service"),
                    "message": str(data.get("msg") or data.get("message") or ""),
                    "raw_line": raw_line
                }
            except Exception:
                pass

        # 2. Try Bracketed format (Format: YYYY-MM-DD HH:MM:SS [LEVEL] [SERVICE] MSG)
        match_bracketed = PATTERN_BRACKETED.match(raw_line)
        if match_bracketed:
            groups = match_bracketed.groupdict()
            return {
                "line_no": line_no,
                "timestamp": groups["timestamp"],
                "level": groups["level"].upper(),
                "service": groups["service"],
                "message": groups["message"],
                "raw_line": raw_line
            }

        # 3. Try Standard format
        match_standard = PATTERN_STANDARD.match(raw_line)
        if match_standard:
            groups = match_standard.groupdict()
            service = groups.get("service_bracket") or groups.get("service_plain") or "infrastructure"
            return {
                "line_no": line_no,
                "timestamp": groups["timestamp"],
                "level": groups["level"].upper(),
                "service": service.strip(),
                "message": groups["message"],
                "raw_line": raw_line
            }

        # 4. Try Syslog format
        match_syslog = PATTERN_SYSLOG.match(raw_line)
        if match_syslog:
            groups = match_syslog.groupdict()
            # Infer level from message keyword
            msg = groups["message"]
            level = "INFO"
            for kw in ["FATAL", "CRITICAL", "ERROR", "FAIL"]:
                if kw in msg.upper():
                    level = "ERROR"
                    break
            for kw in ["WARN", "WARNING"]:
                if kw in msg.upper():
                    level = "WARN"
                    break

            return {
                "line_no": line_no,
                "timestamp": groups["timestamp"],
                "level": level,
                "service": groups["service"],
                "message": msg,
                "raw_line": raw_line
            }

        # 5. Fallback unstructured line
        # Infer severity if keyword is present
        inferred_level = "INFO"
        upper_line = raw_line.upper()
        if "CRITICAL" in upper_line or "FATAL" in upper_line:
            inferred_level = "CRITICAL"
        elif "ERROR" in upper_line or "FAILED" in upper_line or "EXCEPTION" in upper_line:
            inferred_level = "ERROR"
        elif "WARN" in upper_line:
            inferred_level = "WARN"
        elif "DEBUG" in upper_line:
            inferred_level = "DEBUG"

        return {
            "line_no": line_no,
            "timestamp": "N/A",
            "level": inferred_level,
            "service": "system",
            "message": raw_line,
            "raw_line": raw_line
        }

    @staticmethod
    def _normalize_level(raw_level: Any, message: str = "", label_val: Any = None) -> str:
        """Normalizes string, Windows numeric (1-4), and anomaly-label levels to standard severities."""
        lvl_str = str(raw_level).strip().upper() if raw_level not in (None, "") else ""
        win_map = {
            "1": "CRITICAL",
            "CRITICAL": "CRITICAL",
            "FATAL": "FATAL",
            "F": "CRITICAL",
            "2": "ERROR",
            "ERROR": "ERROR",
            "ERR": "ERROR",
            "E": "ERROR",
            "3": "WARN",
            "WARN": "WARN",
            "WARNING": "WARN",
            "W": "WARN",
            "4": "INFO",
            "0": "INFO",
            "INFO": "INFO",
            "INFORMATION": "INFO",
            "I": "INFO",
            "DEBUG": "DEBUG",
            "D": "DEBUG",
        }
        if lvl_str in win_map:
            return win_map[lvl_str]

        if label_val not in (None, ""):
            lbl = str(label_val).strip().lower()
            if lbl in ("1", "true", "anomaly", "attack", "malicious", "suspicious", "error", "fail", "critical"):
                return "CRITICAL"
            if lbl in ("0", "false", "normal", "benign", "ok", "healthy"):
                return "INFO"

        upper_msg = (message or "").upper()
        if any(k in upper_msg for k in ("CRITICAL", "FATAL", "OOMKILLED", "EXIT CODE 137")):
            return "CRITICAL"
        if any(k in upper_msg for k in ("ERROR", "FAILED", "EXCEPTION", "DENIED", "TIMEOUT", "CORRUPT")):
            return "ERROR"
        if any(k in upper_msg for k in ("WARN", "HIGH", "LATENCY", "THROTTL")):
            return "WARN"
        return "INFO"

    @classmethod
    def _normalize_dict_record(cls, data: Dict[str, Any], line_no: int) -> Dict[str, Any]:
        lowered = {str(k).strip().lower(): v for k, v in data.items() if k is not None}

        ts = (
            lowered.get("time")
            or lowered.get("timestamp")
            or lowered.get("timecreated")
            or lowered.get("timegenerated")
            or lowered.get("date and time")
            or lowered.get("datetime")
            or lowered.get("created_at")
        )
        if not ts and (lowered.get("date") or lowered.get("month")):
            parts = [str(lowered.get(k)).strip() for k in ("month", "date", "time") if lowered.get(k)]
            ts = " ".join(parts)
        ts = ts or "N/A"

        svc = (
            lowered.get("service")
            or lowered.get("app")
            or lowered.get("name")
            or lowered.get("source")
            or lowered.get("provider")
            or lowered.get("providername")
            or lowered.get("component")
            or lowered.get("computer")
            or lowered.get("machinename")
            or lowered.get("node")
            or lowered.get("host")
            or "unknown-service"
        )

        msg = (
            lowered.get("msg")
            or lowered.get("message")
            or lowered.get("content")
            or lowered.get("description")
            or lowered.get("eventtemplate")
            or lowered.get("log")
            or lowered.get("raw_log")
            or ""
        )
        msg_str = str(msg).strip()
        if not msg_str:
            # Synthesize summary for Kaggle tabular telemetry/anomaly CSV rows
            skip_keys = {"line_no", "lineid", "id", "time", "timestamp", "date", "month", "service", "host"}
            kv_pairs = [f"{k}={v}" for k, v in lowered.items() if k not in skip_keys and str(v).strip() != ""]
            msg_str = ", ".join(kv_pairs[:10]) if kv_pairs else json.dumps(data, default=str)

        ev_id = lowered.get("eventid") if lowered.get("eventid") not in (None, "") else lowered.get("event_id")
        if ev_id not in (None, "") and f"eventid {ev_id}".lower() not in msg_str.lower():
            msg_str = f"[EventID {ev_id}] {msg_str}"

        raw_lvl = lowered.get("level") or lowered.get("severity") or lowered.get("entrytype") or lowered.get("levelname")
        label_val = (
            lowered.get("label")
            or lowered.get("is_anomaly")
            or lowered.get("anomaly")
            or lowered.get("attack")
            or lowered.get("status")
        )
        norm_lvl = cls._normalize_level(raw_lvl, msg_str, label_val)

        raw_line_no = lowered.get("line_no") or lowered.get("lineid") or line_no
        try:
            parsed_line_no = int(raw_line_no)
        except Exception:
            parsed_line_no = line_no

        return {
            "line_no": parsed_line_no,
            "timestamp": str(ts),
            "level": norm_lvl,
            "service": str(svc),
            "message": msg_str,
            "raw_line": json.dumps(data, default=str),
        }

    @classmethod
    def parse_text(cls, log_content: str) -> pd.DataFrame:
        """Parses multi-line text, JSON arrays, or CSV logs (including Kaggle Event/LogHub CSVs) into a DataFrame."""
        stripped = (log_content or "").strip()
        if not stripped:
            return pd.DataFrame(columns=["line_no", "timestamp", "level", "service", "message", "raw_line"])

        records = []
        # Support JSON array log files
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                arr = json.loads(stripped)
                if isinstance(arr, list):
                    for idx, item in enumerate(arr, start=1):
                        if isinstance(item, dict):
                            records.append(cls._normalize_dict_record(item, idx))
            except Exception:
                records = []

        # Support CSV log & Kaggle dataset files (Standard, Windows Event Log, LogHub, Telemetry CSVs)
        csv_signal_cols = {
            "message", "msg", "content", "description", "eventtemplate", "raw_log",
            "timecreated", "eventid", "event_id", "component", "source", "provider",
            "level", "severity", "label", "is_anomaly", "anomaly", "attack", "cpu",
        }
        if not records:
            first_line = stripped.splitlines()[0].lower()
            if "," in first_line and any(col in first_line for col in csv_signal_cols):
                try:
                    reader = csv.DictReader(io.StringIO(stripped))
                    hdrs = {str(f).strip().lower() for f in (reader.fieldnames or [])}
                    if hdrs & csv_signal_cols:
                        for idx, row in enumerate(reader, start=1):
                            records.append(cls._normalize_dict_record(row, idx))
                except Exception:
                    records = []

        if not records:
            lines = log_content.splitlines()
            for idx, line in enumerate(lines, start=1):
                parsed = cls.parse_line(line, line_no=idx)
                if parsed:
                    records.append(parsed)

        if not records:
            return pd.DataFrame(columns=["line_no", "timestamp", "level", "service", "message", "raw_line"])

        df = pd.DataFrame(records)
        # Normalize level names (e.g. WARNING -> WARN)
        df["level"] = df["level"].replace({"WARNING": "WARN"})
        return df

    @classmethod
    def parse_file(cls, file_path_or_buffer) -> pd.DataFrame:
        """Parses a file-like object or filepath."""
        if hasattr(file_path_or_buffer, "read"):
            content = file_path_or_buffer.read()
            if isinstance(content, bytes):
                content = content.decode("utf-8", errors="replace")
            return cls.parse_text(content)
        else:
            with open(file_path_or_buffer, "r", encoding="utf-8", errors="replace") as f:
                return cls.parse_text(f.read())
