"""
Incremental Application Log File Collector.
Supports:
- Configurable log file paths
- Incremental byte-offset tailing
- Log rotation & file truncation handling
- Deterministic SHA-256 duplicate prevention
"""
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List

import re
from agent.state_store import AgentStateStore

try:
    from src.parser import InfrastructureLogParser
except ImportError:
    class InfrastructureLogParser:  # type: ignore[no-redef]
        _BRACKETED = re.compile(
            r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+"
            r"\[(?P<level>[A-Za-z]+)\]\s+\[(?P<service>[^\]]+)\]\s+(?P<message>.*)$"
        )

        @staticmethod
        def parse_line(line: str, line_no: int = 1):
            raw = line.strip()
            if not raw:
                return None
            m = InfrastructureLogParser._BRACKETED.match(raw)
            if m:
                g = m.groupdict()
                return {
                    "line_no": line_no,
                    "timestamp": g["timestamp"],
                    "level": g["level"].upper(),
                    "service": g["service"],
                    "message": g["message"],
                    "raw_line": raw,
                }
            upper = raw.upper()
            level = "CRITICAL" if ("CRITICAL" in upper or "FATAL" in upper) else ("ERROR" if ("ERROR" in upper or "FAIL" in upper) else ("WARN" if "WARN" in upper else "INFO"))
            return {"line_no": line_no, "timestamp": "N/A", "level": level, "service": "app", "message": raw, "raw_line": raw}


class ApplicationLogCollector:
    """Tails configured application log files incrementally with rotation detection."""

    def __init__(self, device_id: str, state_store: AgentStateStore, log_paths: List[str]):
        self.device_id = device_id
        self.state_store = state_store
        self.log_paths = [p for p in (log_paths or []) if p and str(p).strip()]

    def update_paths(self, log_paths: List[str]) -> None:
        self.log_paths = [p for p in (log_paths or []) if p and str(p).strip()]

    @staticmethod
    def _get_file_id(stat_res: os.stat_result) -> str:
        return f"{getattr(stat_res, 'st_dev', 0)}:{getattr(stat_res, 'st_ino', 0)}"

    def collect_new_lines(self, max_lines_per_file: int = 200) -> List[Dict[str, Any]]:
        collected: List[Dict[str, Any]] = []
        for path_str in self.log_paths:
            path = Path(path_str)
            if not path.exists() or not path.is_file():
                continue

            try:
                st = path.stat()
            except OSError:
                continue

            file_id = self._get_file_id(st)
            prev_state = self.state_store.get_file_state(str(path))
            prev_offset = int(prev_state.get("offset", 0))
            prev_file_id = prev_state.get("file_id")

            # Detect log rotation or truncation
            if prev_file_id and prev_file_id != file_id:
                offset = 0
            elif st.st_size < prev_offset:
                offset = 0
            else:
                offset = prev_offset

            if st.st_size == offset:
                continue

            new_lines: List[tuple[int, str]] = []
            try:
                with open(path, "rb") as f:
                    f.seek(offset)
                    lines_read = 0
                    while lines_read < max_lines_per_file:
                        line_start = f.tell()
                        raw_bytes = f.readline()
                        if not raw_bytes:
                            break
                        # Only process complete lines ending with newline (avoid partial writes)
                        if not raw_bytes.endswith(b"\n") and f.tell() == st.st_size:
                            f.seek(line_start)
                            break
                        text_line = raw_bytes.decode("utf-8", errors="replace").strip()
                        if text_line:
                            new_lines.append((line_start, text_line))
                            lines_read += 1
                    new_offset = f.tell()
            except OSError:
                continue

            self.state_store.set_file_state(str(path), new_offset, file_id)

            for line_offset, line in new_lines:
                parsed = InfrastructureLogParser.parse_line(line, line_no=line_offset)
                ts = parsed["timestamp"] if (parsed and parsed["timestamp"] != "N/A") else datetime.now(timezone.utc).isoformat()
                level = parsed["level"] if parsed else "INFO"
                service = parsed["service"] if (parsed and parsed["service"] != "system") else path.stem
                message = parsed["message"] if parsed else line

                uid_raw = f"{self.device_id}|APP_LOG|{path}|{file_id}|{line_offset}|{line}"
                event_uid = hashlib.sha256(uid_raw.encode("utf-8", errors="replace")).hexdigest()

                collected.append({
                    "event_uid": event_uid,
                    "timestamp": ts,
                    "source_type": "APP_LOG",
                    "channel": str(path),
                    "event_id": None,
                    "record_number": line_offset,
                    "level": level,
                    "service": service,
                    "message": message,
                    "raw_line": line,
                })

        return collected
