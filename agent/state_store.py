"""
Durable SQLite (WAL mode) Agent State & Offline Queue Store.
Crash-safe persistence for:
- Device ID & authentication token
- Windows Event Viewer channel bookmarks (RecordNumber)
- Application log file offsets & file identifiers
- Bounded offline event retry queue (survives reboots & network outages)
"""
import json
import sqlite3
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional


class AgentStateStore:
    def __init__(self, state_path: Path):
        p = Path(state_path)
        if p.suffix.lower() == ".json":
            p = p.with_suffix(".db")
        self.db_path = p
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=20.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute("""
            CREATE TABLE IF NOT EXISTS kv_store (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS event_bookmarks (
                channel TEXT PRIMARY KEY,
                record_number INTEGER NOT NULL
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS file_offsets (
                file_path TEXT PRIMARY KEY,
                offset INTEGER NOT NULL,
                file_id TEXT NOT NULL
            )
            """)
            conn.execute("""
            CREATE TABLE IF NOT EXISTS pending_events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                payload_json TEXT NOT NULL
            )
            """)
            conn.commit()
            conn.close()

    def get_credentials(self) -> tuple[Optional[str], Optional[str]]:
        with self._lock:
            conn = self._connect()
            r1 = conn.execute("SELECT value FROM kv_store WHERE key='device_id'").fetchone()
            r2 = conn.execute("SELECT value FROM kv_store WHERE key='device_token'").fetchone()
            conn.close()
            return (r1["value"] if r1 else None), (r2["value"] if r2 else None)

    def set_credentials(self, device_id: str, device_token: str) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute("INSERT OR REPLACE INTO kv_store (key, value) VALUES ('device_id', ?)", (device_id,))
            conn.execute("INSERT OR REPLACE INTO kv_store (key, value) VALUES ('device_token', ?)", (device_token,))
            conn.commit()
            conn.close()

    def clear_token(self) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute("DELETE FROM kv_store WHERE key='device_token'")
            conn.commit()
            conn.close()

    def get_event_bookmark(self, channel: str) -> Optional[int]:
        with self._lock:
            conn = self._connect()
            row = conn.execute("SELECT record_number FROM event_bookmarks WHERE channel=?", (channel,)).fetchone()
            conn.close()
            return int(row["record_number"]) if row else None

    def set_event_bookmark(self, channel: str, record_number: int) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute(
                "INSERT OR REPLACE INTO event_bookmarks (channel, record_number) VALUES (?, ?)",
                (channel, int(record_number)),
            )
            conn.commit()
            conn.close()

    def get_file_state(self, file_path: str) -> Dict[str, Any]:
        with self._lock:
            conn = self._connect()
            row = conn.execute("SELECT offset, file_id FROM file_offsets WHERE file_path=?", (file_path,)).fetchone()
            conn.close()
            return {"offset": int(row["offset"]), "file_id": row["file_id"]} if row else {}

    def set_file_state(self, file_path: str, offset: int, file_id: str) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute(
                "INSERT OR REPLACE INTO file_offsets (file_path, offset, file_id) VALUES (?, ?, ?)",
                (file_path, int(offset), file_id),
            )
            conn.commit()
            conn.close()

    def enqueue_events(self, events: List[Dict[str, Any]], max_queue: int = 10000) -> None:
        if not events:
            return
        with self._lock:
            conn = self._connect()
            conn.executemany(
                "INSERT INTO pending_events (payload_json) VALUES (?)",
                [(json.dumps(ev),) for ev in events],
            )
            total = conn.execute("SELECT COUNT(*) FROM pending_events").fetchone()[0]
            if total > max_queue:
                excess = total - max_queue
                conn.execute(
                    "DELETE FROM pending_events WHERE seq IN (SELECT seq FROM pending_events ORDER BY seq ASC LIMIT ?)",
                    (excess,),
                )
            conn.commit()
            conn.close()

    def pop_pending_events(self, batch_size: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            rows = conn.execute(
                "SELECT seq, payload_json FROM pending_events ORDER BY seq ASC LIMIT ?",
                (batch_size,),
            ).fetchall()
            if not rows:
                conn.close()
                return []
            seqs = [(r["seq"],) for r in rows]
            conn.executemany("DELETE FROM pending_events WHERE seq = ?", seqs)
            conn.commit()
            conn.close()
            out = []
            for r in rows:
                try:
                    out.append(json.loads(r["payload_json"]))
                except Exception:
                    pass
            return out

    def pending_count(self) -> int:
        with self._lock:
            conn = self._connect()
            cnt = conn.execute("SELECT COUNT(*) FROM pending_events").fetchone()[0]
            conn.close()
            return int(cnt)
