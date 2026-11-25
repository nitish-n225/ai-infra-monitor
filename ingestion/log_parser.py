import re
import json
from datetime import datetime
from typing import Dict, Any, Optional

# Standard Combined Log Format Regex:
# IP - - [Timestamp] "METHOD /path HTTP/1.1" STATUS_CODE BYTES "REFERER" "USER_AGENT"
COMBINED_LOG_REGEX = re.compile(
    r'^(?P<ip>\S+)\s+\S+\s+\S+\s+\[(?P<timestamp>[^\]]+)\]\s+"(?P<method>\S+)\s+(?P<endpoint>\S+)\s+(?P<protocol>[^"]+)"\s+(?P<status>\d{3})\s+(?P<size>\S+)(?:\s+"(?P<referer>[^"]*)"\s+"(?P<user_agent>[^"]*)")?'
)

class LogParser:
    """Parses raw server logs (Apache/Nginx or JSON) into structured event dictionaries."""

    @staticmethod
    def parse_line(line: str) -> Optional[Dict[str, Any]]:
        line = line.strip()
        if not line:
            return None

        # Try parsing as JSON first
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                return LogParser._normalize_json_log(data, line)
            except Exception:
                pass

        # Try Combined Log Format
        match = COMBINED_LOG_REGEX.match(line)
        if match:
            group = match.groupdict()
            status = int(group.get("status", 200))
            raw_size = group.get("size", "0")
            size = int(raw_size) if raw_size.isdigit() else 0
            
            # Format timestamp to ISO if possible
            raw_ts = group.get("timestamp", "")
            iso_ts = LogParser._parse_apache_timestamp(raw_ts)

            return {
                "client_ip": group.get("ip", "127.0.0.1"),
                "timestamp": iso_ts,
                "method": group.get("method", "GET").upper(),
                "endpoint": group.get("endpoint", "/"),
                "protocol": group.get("protocol", "HTTP/1.1"),
                "status_code": status,
                "response_size": size,
                "referer": group.get("referer", "-"),
                "user_agent": group.get("user_agent", "-"),
                "raw_log": line
            }

        # Fallback heuristic parser for custom logs
        parts = line.split()
        if len(parts) >= 5:
            return {
                "client_ip": parts[0],
                "timestamp": datetime.utcnow().isoformat(),
                "method": parts[1] if parts[1] in ["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS"] else "GET",
                "endpoint": parts[2] if len(parts) > 2 else "/",
                "status_code": int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 200,
                "response_size": int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 100,
                "user_agent": "Custom/1.0",
                "raw_log": line
            }

        return None

    @staticmethod
    def _parse_apache_timestamp(ts_str: str) -> str:
        # Example: "25/Oct/2026:10:30:15 +0000"
        try:
            # Strip timezone for parsing if needed
            clean_ts = ts_str.split()[0]
            dt = datetime.strptime(clean_ts, "%d/%b/%Y:%H:%M:%S")
            return dt.isoformat()
        except Exception:
            return datetime.utcnow().isoformat()

    @staticmethod
    def _normalize_json_log(data: Dict[str, Any], raw_log: str) -> Dict[str, Any]:
        return {
            "client_ip": data.get("ip") or data.get("client_ip", "127.0.0.1"),
            "timestamp": data.get("timestamp", datetime.utcnow().isoformat()),
            "method": data.get("method", "GET").upper(),
            "endpoint": data.get("endpoint") or data.get("url", "/"),
            "protocol": data.get("protocol", "HTTP/1.1"),
            "status_code": int(data.get("status") or data.get("status_code", 200)),
            "response_size": int(data.get("size") or data.get("response_size", 0)),
            "referer": data.get("referer", "-"),
            "user_agent": data.get("user_agent", "-"),
            "raw_log": raw_log
        }
