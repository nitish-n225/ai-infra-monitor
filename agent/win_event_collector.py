"""
Real Windows Event Viewer Collector.
Reads actual events from Windows Event Log channels (System, Application, and permission-gated Security)
using native Win32 Event Log APIs (pywin32 win32evtlog).
Maintains persistent RecordNumber bookmarks to avoid duplicates and never fabricates events.
"""
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Set

from agent.state_store import AgentStateStore

logger = logging.getLogger("agent.win_events")

try:
    import win32evtlog
    import win32evtlogutil
    import win32con
    HAS_WIN32_EVTLOG = True
except ImportError:
    HAS_WIN32_EVTLOG = False

EVENT_TYPE_MAP = {
    1: "ERROR",      # EVENTLOG_ERROR_TYPE
    2: "WARN",       # EVENTLOG_WARNING_TYPE
    4: "INFO",       # EVENTLOG_INFORMATION_TYPE
    8: "INFO",       # EVENTLOG_AUDIT_SUCCESS
    16: "WARN",      # EVENTLOG_AUDIT_FAILURE
}


def _to_iso_utc(dt_obj: Any) -> str:
    try:
        if hasattr(dt_obj, "isoformat"):
            # pywintypes.datetime is naive local time
            return dt_obj.replace(tzinfo=None).isoformat()
    except Exception:
        pass
    return datetime.now(timezone.utc).isoformat()


def _format_event_message(channel: str, event_record: Any) -> str:
    if HAS_WIN32_EVTLOG:
        try:
            msg = win32evtlogutil.SafeFormatMessage(event_record, channel)
            if msg and msg.strip():
                return " ".join(msg.strip().splitlines())
        except Exception:
            pass
    inserts = getattr(event_record, "StringInserts", None) or ()
    cleaned = [str(s).strip() for s in inserts if s is not None and str(s).strip()]
    if cleaned:
        return " | ".join(cleaned)
    return f"Windows Event ID {int(event_record.EventID) & 0xFFFF} from {event_record.SourceName}"


class WindowsEventLogCollector:
    """Collects real Windows Event Viewer logs incrementally across configured channels."""

    def __init__(
        self,
        device_id: str,
        state_store: AgentStateStore,
        channels: Optional[List[str]] = None,
        include_security: bool = False,
        allowed_security_event_ids: Optional[List[int]] = None,
        initial_lookback: int = 20,
    ):
        self.device_id = device_id
        self.state_store = state_store
        self.channels = list(channels or ["System", "Application"])
        self.include_security = include_security
        if self.include_security and "Security" not in self.channels:
            self.channels.append("Security")
        self.allowed_security_ids: Set[int] = set(
            allowed_security_event_ids or [4624, 4625, 4634, 4648, 4720, 4726, 4740, 1102]
        )
        self.initial_lookback = max(1, initial_lookback)
        self._permission_warned_channels: Set[str] = set()

    def collect_new_events(self, max_per_channel: int = 100) -> List[Dict[str, Any]]:
        if not HAS_WIN32_EVTLOG:
            logger.warning("pywin32 (win32evtlog) is not available on this system.")
            return []

        collected: List[Dict[str, Any]] = []
        for channel in self.channels:
            if channel == "Security" and not self.include_security:
                continue
            try:
                events = self._read_channel(channel, max_records=max_per_channel)
                collected.extend(events)
            except PermissionError:
                if channel not in self._permission_warned_channels:
                    logger.warning(
                        "Permission denied reading Windows '%s' Event Log. Run agent with Administrator privileges to monitor '%s'.",
                        channel,
                        channel,
                    )
                    self._permission_warned_channels.add(channel)
            except Exception as e:
                win_err = getattr(e, "winerror", None)
                if win_err == 5 or "Access is denied" in str(e):
                    if channel not in self._permission_warned_channels:
                        logger.warning(
                            "Access denied for Windows '%s' Event Log (run elevated if Security auditing is required).",
                            channel,
                        )
                        self._permission_warned_channels.add(channel)
                else:
                    logger.error("Failed reading Windows Event Log '%s': %s", channel, e)
        return collected

    def _read_channel(self, channel: str, max_records: int = 100) -> List[Dict[str, Any]]:
        handle = win32evtlog.OpenEventLog(None, channel)
        try:
            total_records = win32evtlog.GetNumberOfEventLogRecords(handle)
            oldest_record = win32evtlog.GetOldestEventLogRecord(handle)
            if total_records == 0:
                return []

            last_bookmark = self.state_store.get_event_bookmark(channel)
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

            new_records = []
            highest_seen = last_bookmark or 0

            # Read backwards from newest until we hit bookmark or lookback cap
            while len(new_records) < max_records:
                batch = win32evtlog.ReadEventLog(handle, flags, 0)
                if not batch:
                    break
                reached_bookmark = False
                for ev in batch:
                    rec_no = int(ev.RecordNumber)
                    if rec_no > highest_seen:
                        highest_seen = rec_no

                    if last_bookmark is not None:
                        if rec_no <= last_bookmark:
                            reached_bookmark = True
                            break
                    else:
                        if len(new_records) >= self.initial_lookback:
                            reached_bookmark = True
                            break

                    event_id = int(ev.EventID) & 0xFFFF
                    if channel == "Security" and event_id not in self.allowed_security_ids:
                        continue

                    new_records.append(ev)
                    if len(new_records) >= max_records:
                        break

                if reached_bookmark:
                    break

            if highest_seen > (last_bookmark or 0):
                self.state_store.set_event_bookmark(channel, highest_seen)

            # Reverse to chronological order (oldest -> newest)
            new_records.reverse()
            formatted: List[Dict[str, Any]] = []
            for ev in new_records:
                rec_no = int(ev.RecordNumber)
                event_id = int(ev.EventID) & 0xFFFF
                level = EVENT_TYPE_MAP.get(int(ev.EventType), "INFO")
                ts_iso = _to_iso_utc(ev.TimeGenerated)
                source = str(ev.SourceName or channel)
                message = _format_event_message(channel, ev)
                if channel == "Security" and event_id in (4625, 4740, 1102):
                    level = "CRITICAL" if event_id == 1102 else "ERROR"

                uid_raw = f"{self.device_id}|WINDOWS_EVENT_LOG|{channel}|{rec_no}|{event_id}|{ts_iso}"
                event_uid = hashlib.sha256(uid_raw.encode("utf-8")).hexdigest()
                raw_line = f"{ts_iso} [{level}] [{source}] (EventID={event_id}, Record={rec_no}) {message}"

                formatted.append({
                    "event_uid": event_uid,
                    "timestamp": ts_iso,
                    "source_type": "WINDOWS_EVENT_LOG",
                    "channel": channel,
                    "event_id": event_id,
                    "record_number": rec_no,
                    "level": level,
                    "service": source,
                    "message": f"[EventID {event_id}] {message}",
                    "raw_line": raw_line,
                })
            return formatted
        finally:
            win32evtlog.CloseEventLog(handle)

