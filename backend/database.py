"""
Persistent Storage Layer for Enterprise Autonomous AI Infrastructure Monitoring System.
Supports BOTH:
- PostgreSQL (via DATABASE_URL — recommended for Render & cloud deployments)
- SQLite WAL mode (via MONITOR_DB_PATH — default for local Windows development)

Stores devices, enrollment tokens, telemetry snapshots, deduplicated events,
AI incidents, audit logs, operator accounts, and system settings.
"""
import os
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "monitoring_system.db"

try:
    import psycopg2
    import psycopg2.extras
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    return url


def is_postgres() -> bool:
    return bool(get_database_url())


def get_db_path() -> Path:
    env_path = os.environ.get("MONITOR_DB_PATH", "").strip()
    if env_path:
        return Path(env_path)
    return DEFAULT_DB_PATH


def _translate_sql(sql: str, pg: bool) -> str:
    if not pg:
        return sql
    return sql.replace("?", "%s")


class DBConnectionWrapper:
    """Unified DB wrapper normalizing SQLite and PostgreSQL queries."""

    def __init__(self):
        db_url = get_database_url()
        self.pg = bool(db_url)
        if self.pg:
            if not HAS_PSYCOPG2:
                raise RuntimeError("DATABASE_URL is set but psycopg2-binary is not installed.")
            self.conn = psycopg2.connect(db_url, cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            db_path = get_db_path()
            db_path.parent.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(db_path), timeout=30.0, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.execute("PRAGMA foreign_keys=ON;")

    def execute(self, sql: str, params: Tuple[Any, ...] = ()):
        cur = self.conn.cursor()
        cur.execute(_translate_sql(sql, self.pg), params)
        return cur

    def insert_returning_id(self, sql_without_returning: str, params: Tuple[Any, ...] = ()) -> Optional[int]:
        cur = self.conn.cursor()
        if self.pg:
            cur.execute(_translate_sql(sql_without_returning.rstrip().rstrip(";") + " RETURNING id", True), params)
            row = cur.fetchone()
            return int(row["id"]) if row else None
        cur.execute(sql_without_returning, params)
        return cur.lastrowid if cur.rowcount > 0 else None

    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()


def get_connection() -> DBConnectionWrapper:
    return DBConnectionWrapper()


def _ensure_column(db: DBConnectionWrapper, table: str, column: str, col_def: str) -> None:
    if db.pg:
        db.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_def};")
    else:
        cols = [r["name"] for r in db.execute(f"PRAGMA table_info({table})").fetchall()]
        if column not in cols:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def};")


def init_monitoring_db() -> None:
    db = get_connection()
    pk_auto = "SERIAL PRIMARY KEY" if db.pg else "INTEGER PRIMARY KEY AUTOINCREMENT"
    real_type = "DOUBLE PRECISION" if db.pg else "REAL"
    bigint_type = "BIGINT" if db.pg else "INTEGER"

    db.execute(f"""
    CREATE TABLE IF NOT EXISTS devices (
        device_id TEXT PRIMARY KEY,
        hostname TEXT NOT NULL,
        client_org TEXT NOT NULL DEFAULT 'Default',
        tags_json TEXT NOT NULL DEFAULT '[]',
        os_name TEXT DEFAULT 'Windows',
        os_version TEXT DEFAULT '',
        architecture TEXT DEFAULT '',
        ip_address TEXT DEFAULT '',
        mac_address TEXT DEFAULT '',
        agent_version TEXT DEFAULT '2.0.0',
        token_hash TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ONLINE',
        consent_confirmed INTEGER NOT NULL DEFAULT 1,
        registered_at TEXT NOT NULL,
        last_seen TEXT NOT NULL,
        last_heartbeat TEXT NOT NULL,
        health_score {real_type} NOT NULL DEFAULT 100.0,
        health_condition TEXT NOT NULL DEFAULT 'Stable',
        risk_score {real_type} NOT NULL DEFAULT 0.0,
        risk_level TEXT NOT NULL DEFAULT 'LOW',
        config_json TEXT NOT NULL,
        revoked_at TEXT,
        revocation_reason TEXT
    )
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS enrollment_tokens (
        token_id TEXT PRIMARY KEY,
        token_hash TEXT UNIQUE NOT NULL,
        label TEXT NOT NULL,
        client_org TEXT NOT NULL DEFAULT 'Default',
        created_at TEXT NOT NULL,
        expires_at TEXT,
        max_uses INTEGER NOT NULL DEFAULT 25,
        uses_count INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1
    )
    """)

    db.execute(f"""
    CREATE TABLE IF NOT EXISTS telemetry_snapshots (
        id {pk_auto},
        device_id TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        ingested_at TEXT NOT NULL,
        cpu_percent {real_type} NOT NULL,
        cpu_cores INTEGER NOT NULL,
        ram_percent {real_type} NOT NULL,
        ram_used_gb {real_type} NOT NULL,
        ram_total_gb {real_type} NOT NULL,
        disk_percent {real_type} NOT NULL,
        disk_used_gb {real_type} NOT NULL,
        disk_total_gb {real_type} NOT NULL,
        disk_volumes_json TEXT NOT NULL DEFAULT '[]',
        net_bytes_sent {bigint_type} NOT NULL DEFAULT 0,
        net_bytes_recv {bigint_type} NOT NULL DEFAULT 0,
        net_sent_kbps {real_type} NOT NULL DEFAULT 0.0,
        net_recv_kbps {real_type} NOT NULL DEFAULT 0.0,
        process_count INTEGER NOT NULL DEFAULT 0,
        top_processes_json TEXT NOT NULL DEFAULT '[]',
        services_json TEXT NOT NULL DEFAULT '[]',
        uptime_seconds {real_type} NOT NULL DEFAULT 0.0,
        FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
    )
    """)

    db.execute(f"""
    CREATE TABLE IF NOT EXISTS events (
        id {pk_auto},
        event_uid TEXT UNIQUE NOT NULL,
        device_id TEXT NOT NULL,
        hostname TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        ingested_at TEXT NOT NULL,
        source_type TEXT NOT NULL,
        channel TEXT NOT NULL,
        event_id INTEGER,
        record_number {bigint_type},
        level TEXT NOT NULL,
        service TEXT NOT NULL,
        message TEXT NOT NULL,
        raw_line TEXT NOT NULL,
        is_critical INTEGER NOT NULL DEFAULT 0,
        rca_category TEXT,
        similar_incidents_json TEXT NOT NULL DEFAULT '[]',
        FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
    )
    """)

    db.execute(f"""
    CREATE TABLE IF NOT EXISTS incidents (
        id {pk_auto},
        device_id TEXT NOT NULL,
        hostname TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        category TEXT NOT NULL,
        title TEXT NOT NULL,
        severity TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'OPEN',
        evidence_json TEXT NOT NULL DEFAULT '[]',
        confirmed_evidence TEXT NOT NULL DEFAULT '',
        possible_root_cause TEXT NOT NULL DEFAULT '',
        predicted_risk_note TEXT NOT NULL DEFAULT '',
        confidence_pct INTEGER NOT NULL DEFAULT 60,
        recommendations_json TEXT NOT NULL DEFAULT '[]',
        similar_history_json TEXT NOT NULL DEFAULT '[]',
        FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
    )
    """)

    db.execute(f"""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id {pk_auto},
        timestamp TEXT NOT NULL,
        actor TEXT NOT NULL,
        action TEXT NOT NULL,
        target TEXT NOT NULL DEFAULT '',
        details TEXT NOT NULL DEFAULT ''
    )
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'admin',
        created_at TEXT NOT NULL
    )
    """)

    db.execute("""
    CREATE TABLE IF NOT EXISTS system_settings (
        key TEXT PRIMARY KEY,
        value_json TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    _ensure_column(db, "devices", "client_org", "TEXT NOT NULL DEFAULT 'Default'")
    _ensure_column(db, "devices", "tags_json", "TEXT NOT NULL DEFAULT '[]'")
    _ensure_column(db, "enrollment_tokens", "client_org", "TEXT NOT NULL DEFAULT 'Default'")
    _ensure_column(db, "telemetry_snapshots", "disk_volumes_json", "TEXT NOT NULL DEFAULT '[]'")

    db.execute("CREATE INDEX IF NOT EXISTS idx_events_device_ts ON events(device_id, id DESC);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_events_level ON events(level);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_events_ingested ON events(ingested_at);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_device_ts ON telemetry_snapshots(device_id, id DESC);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_telemetry_ingested ON telemetry_snapshots(ingested_at);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_incidents_device_status ON incidents(device_id, status, id DESC);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_logs(id DESC);")

    db.commit()
    db.close()


def _row_to_device(row: Any) -> Dict[str, Any]:
    d = dict(row)
    try:
        d["config"] = json.loads(d.pop("config_json", "{}"))
    except Exception:
        d["config"] = {}
    try:
        d["tags"] = json.loads(d.pop("tags_json", "[]"))
    except Exception:
        d["tags"] = []
    d.pop("token_hash", None)
    return d


def append_audit_log(actor: str, action: str, target: str = "", details: str = "") -> None:
    db = get_connection()
    db.execute(
        "INSERT INTO audit_logs (timestamp, actor, action, target, details) VALUES (?, ?, ?, ?, ?)",
        (utc_now_iso(), actor, action, target, details),
    )
    db.commit()
    db.close()


def list_audit_logs(limit: int = 100) -> List[Dict[str, Any]]:
    db = get_connection()
    rows = db.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    db.close()
    return [dict(r) for r in rows]


def upsert_user(username: str, password_hash: str, role: str = "admin") -> None:
    db = get_connection()
    db.execute(
        """
        INSERT INTO users (username, password_hash, role, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(username) DO UPDATE SET password_hash = excluded.password_hash, role = excluded.role
        """,
        (username, password_hash, role, utc_now_iso()),
    )
    db.commit()
    db.close()


def get_user(username: str) -> Optional[Dict[str, Any]]:
    db = get_connection()
    row = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    db.close()
    return dict(row) if row else None


def get_setting(key: str, default: Any = None) -> Any:
    db = get_connection()
    row = db.execute("SELECT value_json FROM system_settings WHERE key = ?", (key,)).fetchone()
    db.close()
    if not row:
        return default
    try:
        return json.loads(row["value_json"])
    except Exception:
        return default


def set_setting(key: str, value: Any) -> None:
    db = get_connection()
    db.execute(
        """
        INSERT INTO system_settings (key, value_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at
        """,
        (key, json.dumps(value), utc_now_iso()),
    )
    db.commit()
    db.close()


def create_enrollment_token(
    token_id: str,
    token_hash: str,
    label: str,
    max_uses: int,
    expires_at: Optional[str],
    client_org: str = "Default",
) -> Dict[str, Any]:
    now = utc_now_iso()
    db = get_connection()
    db.execute(
        """
        INSERT INTO enrollment_tokens (token_id, token_hash, label, client_org, created_at, expires_at, max_uses, uses_count, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, 1)
        """,
        (token_id, token_hash, label, client_org, now, expires_at, max_uses),
    )
    db.commit()
    row = db.execute(
        "SELECT token_id, label, client_org, created_at, expires_at, max_uses, uses_count, is_active FROM enrollment_tokens WHERE token_id = ?",
        (token_id,),
    ).fetchone()
    db.close()
    return dict(row)


def list_enrollment_tokens() -> List[Dict[str, Any]]:
    db = get_connection()
    rows = db.execute(
        "SELECT token_id, label, client_org, created_at, expires_at, max_uses, uses_count, is_active FROM enrollment_tokens ORDER BY created_at DESC"
    ).fetchall()
    db.close()
    return [dict(r) for r in rows]


def deactivate_enrollment_token(token_id: str) -> bool:
    db = get_connection()
    cur = db.execute("UPDATE enrollment_tokens SET is_active = 0 WHERE token_id = ?", (token_id,))
    db.commit()
    changed = cur.rowcount > 0
    db.close()
    return changed


def validate_and_consume_enrollment_token(token_hash: str) -> Optional[Dict[str, Any]]:
    now = datetime.now(timezone.utc)
    db = get_connection()
    row = db.execute(
        "SELECT * FROM enrollment_tokens WHERE token_hash = ? AND is_active = 1",
        (token_hash,),
    ).fetchone()
    if not row:
        db.close()
        return None

    if row["uses_count"] >= row["max_uses"]:
        db.close()
        return None

    if row["expires_at"]:
        try:
            exp = datetime.fromisoformat(row["expires_at"])
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if now > exp:
                db.close()
                return None
        except Exception:
            pass

    db.execute(
        "UPDATE enrollment_tokens SET uses_count = uses_count + 1 WHERE token_id = ?",
        (row["token_id"],),
    )
    db.commit()
    result = dict(row)
    db.close()
    return result


def upsert_device_registration(device_data: Dict[str, Any], token_hash: str, config: Dict[str, Any]) -> Dict[str, Any]:
    now = utc_now_iso()
    db = get_connection()
    existing = db.execute("SELECT * FROM devices WHERE device_id = ?", (device_data["device_id"],)).fetchone()
    cfg_json = json.dumps(config)
    tags_json = json.dumps(device_data.get("tags", []))
    client_org = device_data.get("client_org") or "Default"

    if existing:
        db.execute(
            """
            UPDATE devices
            SET hostname = ?, client_org = ?, tags_json = ?, os_name = ?, os_version = ?, architecture = ?,
                ip_address = ?, mac_address = ?, agent_version = ?, token_hash = ?,
                status = 'ONLINE', consent_confirmed = 1, last_seen = ?, last_heartbeat = ?,
                config_json = ?, revoked_at = NULL, revocation_reason = NULL
            WHERE device_id = ?
            """,
            (
                device_data["hostname"],
                client_org,
                tags_json,
                device_data.get("os_name", "Windows"),
                device_data.get("os_version", ""),
                device_data.get("architecture", ""),
                device_data.get("ip_address", ""),
                device_data.get("mac_address", ""),
                device_data.get("agent_version", "2.0.0"),
                token_hash,
                now,
                now,
                cfg_json,
                device_data["device_id"],
            ),
        )
    else:
        db.execute(
            """
            INSERT INTO devices (
                device_id, hostname, client_org, tags_json, os_name, os_version, architecture,
                ip_address, mac_address, agent_version, token_hash,
                status, consent_confirmed, registered_at, last_seen, last_heartbeat, config_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ONLINE', 1, ?, ?, ?, ?)
            """,
            (
                device_data["device_id"],
                device_data["hostname"],
                client_org,
                tags_json,
                device_data.get("os_name", "Windows"),
                device_data.get("os_version", ""),
                device_data.get("architecture", ""),
                device_data.get("ip_address", ""),
                device_data.get("mac_address", ""),
                device_data.get("agent_version", "2.0.0"),
                token_hash,
                now,
                now,
                now,
                cfg_json,
            ),
        )

    db.commit()
    row = db.execute("SELECT * FROM devices WHERE device_id = ?", (device_data["device_id"],)).fetchone()
    db.close()
    return _row_to_device(row)


def get_device_raw(device_id: str) -> Optional[Dict[str, Any]]:
    db = get_connection()
    row = db.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    db.close()
    return dict(row) if row else None


def get_device(device_id: str) -> Optional[Dict[str, Any]]:
    db = get_connection()
    row = db.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    db.close()
    return _row_to_device(row) if row else None


def list_devices(client_org: Optional[str] = None) -> List[Dict[str, Any]]:
    db = get_connection()
    if client_org and client_org != "ALL":
        rows = db.execute("SELECT * FROM devices WHERE client_org = ? ORDER BY last_seen DESC", (client_org,)).fetchall()
    else:
        rows = db.execute("SELECT * FROM devices ORDER BY last_seen DESC").fetchall()
    db.close()
    devices = []
    for row in rows:
        d = _row_to_device(row)
        d["latest_telemetry"] = get_latest_telemetry(d["device_id"])
        devices.append(d)
    return devices


def record_heartbeat(device_id: str, ip_address: Optional[str] = None, agent_version: Optional[str] = None) -> Optional[Dict[str, Any]]:
    now = utc_now_iso()
    db = get_connection()
    row = db.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    if not row or row["status"] == "REVOKED":
        db.close()
        return None

    db.execute(
        """
        UPDATE devices
        SET status = 'ONLINE',
            last_seen = ?,
            last_heartbeat = ?,
            ip_address = COALESCE(?, ip_address),
            agent_version = COALESCE(?, agent_version)
        WHERE device_id = ?
        """,
        (now, now, ip_address, agent_version, device_id),
    )
    db.commit()
    updated = db.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    db.close()
    return _row_to_device(updated)


def update_device_config(device_id: str, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    db = get_connection()
    cur = db.execute("UPDATE devices SET config_json = ? WHERE device_id = ?", (json.dumps(config), device_id))
    db.commit()
    if cur.rowcount == 0:
        db.close()
        return None
    row = db.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    db.close()
    return _row_to_device(row)


def update_device_ai_scores(device_id: str, health_score: float, health_condition: str, risk_score: float, risk_level: str) -> None:
    db = get_connection()
    db.execute(
        """
        UPDATE devices
        SET health_score = ?, health_condition = ?, risk_score = ?, risk_level = ?
        WHERE device_id = ?
        """,
        (health_score, health_condition, risk_score, risk_level, device_id),
    )
    db.commit()
    db.close()


def revoke_device(device_id: str, reason: str) -> Optional[Dict[str, Any]]:
    now = utc_now_iso()
    db = get_connection()
    cur = db.execute(
        """
        UPDATE devices
        SET status = 'REVOKED', revoked_at = ?, revocation_reason = ?
        WHERE device_id = ?
        """,
        (now, reason, device_id),
    )
    db.commit()
    if cur.rowcount == 0:
        db.close()
        return None
    row = db.execute("SELECT * FROM devices WHERE device_id = ?", (device_id,)).fetchone()
    db.close()
    return _row_to_device(row)


def mark_stale_devices_offline(timeout_seconds: int = 30) -> List[Dict[str, Any]]:
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
    db = get_connection()
    rows = db.execute("SELECT * FROM devices WHERE status = 'ONLINE'").fetchall()
    marked_offline: List[Dict[str, Any]] = []
    for row in rows:
        try:
            last_seen_dt = datetime.fromisoformat(row["last_seen"])
            if last_seen_dt.tzinfo is None:
                last_seen_dt = last_seen_dt.replace(tzinfo=timezone.utc)
        except Exception:
            last_seen_dt = datetime.min.replace(tzinfo=timezone.utc)

        if last_seen_dt < cutoff:
            db.execute("UPDATE devices SET status = 'OFFLINE' WHERE device_id = ?", (row["device_id"],))
            updated = db.execute("SELECT * FROM devices WHERE device_id = ?", (row["device_id"],)).fetchone()
            marked_offline.append(_row_to_device(updated))

    db.commit()
    db.close()
    return marked_offline


def insert_telemetry_snapshot(device_id: str, payload: Dict[str, Any]) -> int:
    now = utc_now_iso()
    db = get_connection()
    snap_id = db.insert_returning_id(
        """
        INSERT INTO telemetry_snapshots (
            device_id, timestamp, ingested_at, cpu_percent, cpu_cores,
            ram_percent, ram_used_gb, ram_total_gb,
            disk_percent, disk_used_gb, disk_total_gb, disk_volumes_json,
            net_bytes_sent, net_bytes_recv, net_sent_kbps, net_recv_kbps,
            process_count, top_processes_json, services_json, uptime_seconds
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            device_id,
            payload["timestamp"],
            now,
            payload["cpu_percent"],
            payload.get("cpu_cores", 1),
            payload["ram_percent"],
            payload.get("ram_used_gb", 0.0),
            payload.get("ram_total_gb", 0.0),
            payload.get("disk_percent", 0.0),
            payload.get("disk_used_gb", 0.0),
            payload.get("disk_total_gb", 0.0),
            json.dumps(payload.get("disk_volumes", [])),
            payload.get("net_bytes_sent", 0),
            payload.get("net_bytes_recv", 0),
            payload.get("net_sent_kbps", 0.0),
            payload.get("net_recv_kbps", 0.0),
            payload.get("process_count", 0),
            json.dumps(payload.get("top_processes", [])),
            json.dumps(payload.get("services", [])),
            payload.get("uptime_seconds", 0.0),
        ),
    )
    db.execute(
        "UPDATE devices SET last_seen = ?, status = CASE WHEN status='REVOKED' THEN 'REVOKED' ELSE 'ONLINE' END WHERE device_id = ?",
        (now, device_id),
    )
    db.commit()
    db.close()
    return int(snap_id or 0)


def _deserialize_telemetry(row: Any) -> Dict[str, Any]:
    d = dict(row)
    for k, target in [
        ("top_processes_json", "top_processes"),
        ("services_json", "services"),
        ("disk_volumes_json", "disk_volumes"),
    ]:
        try:
            d[target] = json.loads(d.pop(k, "[]"))
        except Exception:
            d[target] = []
    return d


def get_latest_telemetry(device_id: str) -> Optional[Dict[str, Any]]:
    db = get_connection()
    row = db.execute(
        "SELECT * FROM telemetry_snapshots WHERE device_id = ? ORDER BY id DESC LIMIT 1",
        (device_id,),
    ).fetchone()
    db.close()
    return _deserialize_telemetry(row) if row else None


def get_telemetry_history(device_id: str, limit: int = 60) -> List[Dict[str, Any]]:
    db = get_connection()
    rows = db.execute(
        "SELECT * FROM telemetry_snapshots WHERE device_id = ? ORDER BY id DESC LIMIT ?",
        (device_id, limit),
    ).fetchall()
    db.close()
    return [_deserialize_telemetry(r) for r in reversed(rows)]


def insert_events_deduplicated(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Inserts events while ignoring duplicates via event_uid UNIQUE index (SQLite & PostgreSQL)."""
    now = utc_now_iso()
    db = get_connection()
    inserted: List[Dict[str, Any]] = []
    for ev in events:
        new_id = db.insert_returning_id(
            """
            INSERT INTO events (
                event_uid, device_id, hostname, timestamp, ingested_at,
                source_type, channel, event_id, record_number,
                level, service, message, raw_line,
                is_critical, rca_category, similar_incidents_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_uid) DO NOTHING
            """,
            (
                ev["event_uid"],
                ev["device_id"],
                ev["hostname"],
                ev["timestamp"],
                now,
                ev["source_type"],
                ev["channel"],
                ev.get("event_id"),
                ev.get("record_number"),
                ev["level"],
                ev["service"],
                ev["message"],
                ev["raw_line"],
                1 if ev.get("is_critical") else 0,
                ev.get("rca_category"),
                json.dumps(ev.get("similar_incidents", [])),
            ),
        )
        if new_id is not None:
            ev_copy = dict(ev)
            ev_copy["id"] = new_id
            ev_copy["ingested_at"] = now
            inserted.append(ev_copy)

    if events:
        device_id = events[0]["device_id"]
        db.execute(
            "UPDATE devices SET last_seen = ?, status = CASE WHEN status='REVOKED' THEN 'REVOKED' ELSE 'ONLINE' END WHERE device_id = ?",
            (now, device_id),
        )
    db.commit()
    db.close()
    return inserted


def get_events(
    device_id: Optional[str] = None,
    client_org: Optional[str] = None,
    level: Optional[str] = None,
    channel: Optional[str] = None,
    search: Optional[str] = None,
    critical_only: bool = False,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    query = "SELECT e.* FROM events e LEFT JOIN devices d ON e.device_id = d.device_id WHERE 1=1"
    params: List[Any] = []
    if device_id:
        query += " AND e.device_id = ?"
        params.append(device_id)
    if client_org and client_org != "ALL":
        query += " AND d.client_org = ?"
        params.append(client_org)
    if level:
        query += " AND e.level = ?"
        params.append(level.upper())
    if channel:
        query += " AND e.channel = ?"
        params.append(channel)
    if critical_only:
        query += " AND e.is_critical = 1"
    if search:
        query += " AND (LOWER(e.message) LIKE ? OR LOWER(e.service) LIKE ? OR LOWER(e.hostname) LIKE ?)"
        s = f"%{search.lower()}%"
        params.extend([s, s, s])

    query += " ORDER BY e.id DESC LIMIT ?"
    params.append(limit)

    db = get_connection()
    rows = db.execute(query, tuple(params)).fetchall()
    db.close()

    results = []
    for row in rows:
        d = dict(row)
        try:
            d["similar_incidents"] = json.loads(d.pop("similar_incidents_json", "[]"))
        except Exception:
            d["similar_incidents"] = []
        results.append(d)
    return results


def upsert_incident(inc: Dict[str, Any]) -> tuple[Dict[str, Any], bool]:
    now = utc_now_iso()
    db = get_connection()
    existing = db.execute(
        """
        SELECT * FROM incidents
        WHERE device_id = ? AND category = ? AND status IN ('OPEN', 'ACKNOWLEDGED')
        ORDER BY id DESC LIMIT 1
        """,
        (inc["device_id"], inc["category"]),
    ).fetchone()

    is_new = False
    if existing:
        db.execute(
            """
            UPDATE incidents
            SET updated_at = ?, severity = ?, evidence_json = ?, confirmed_evidence = ?,
                possible_root_cause = ?, predicted_risk_note = ?, confidence_pct = ?,
                recommendations_json = ?, similar_history_json = ?
            WHERE id = ?
            """,
            (
                now,
                inc["severity"],
                json.dumps(inc.get("evidence", [])),
                inc.get("confirmed_evidence", ""),
                inc.get("possible_root_cause", ""),
                inc.get("predicted_risk_note", ""),
                inc.get("confidence_pct", 70),
                json.dumps(inc.get("recommendations", [])),
                json.dumps(inc.get("similar_history", [])),
                existing["id"],
            ),
        )
        inc_id = existing["id"]
    else:
        is_new = True
        inc_id = db.insert_returning_id(
            """
            INSERT INTO incidents (
                device_id, hostname, created_at, updated_at, category, title, severity, status,
                evidence_json, confirmed_evidence, possible_root_cause, predicted_risk_note,
                confidence_pct, recommendations_json, similar_history_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                inc["device_id"],
                inc["hostname"],
                now,
                now,
                inc["category"],
                inc["title"],
                inc["severity"],
                json.dumps(inc.get("evidence", [])),
                inc.get("confirmed_evidence", ""),
                inc.get("possible_root_cause", ""),
                inc.get("predicted_risk_note", ""),
                inc.get("confidence_pct", 70),
                json.dumps(inc.get("recommendations", [])),
                json.dumps(inc.get("similar_history", [])),
            ),
        )

    db.commit()
    row = db.execute("SELECT * FROM incidents WHERE id = ?", (inc_id,)).fetchone()
    db.close()
    return _deserialize_incident(row), is_new


def _deserialize_incident(row: Any) -> Dict[str, Any]:
    d = dict(row)
    for src_k, dst_k in [
        ("evidence_json", "evidence"),
        ("recommendations_json", "recommendations"),
        ("similar_history_json", "similar_history"),
    ]:
        try:
            d[dst_k] = json.loads(d.pop(src_k, "[]"))
        except Exception:
            d[dst_k] = []
    return d


def list_incidents(
    device_id: Optional[str] = None,
    client_org: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    query = "SELECT i.* FROM incidents i LEFT JOIN devices d ON i.device_id = d.device_id WHERE 1=1"
    params: List[Any] = []
    if device_id:
        query += " AND i.device_id = ?"
        params.append(device_id)
    if client_org and client_org != "ALL":
        query += " AND d.client_org = ?"
        params.append(client_org)
    if status:
        query += " AND i.status = ?"
        params.append(status.upper())
    query += " ORDER BY i.updated_at DESC LIMIT ?"
    params.append(limit)
    db = get_connection()
    rows = db.execute(query, tuple(params)).fetchall()
    db.close()
    return [_deserialize_incident(r) for r in rows]


def update_incident_status(incident_id: int, status: str) -> Optional[Dict[str, Any]]:
    now = utc_now_iso()
    db = get_connection()
    cur = db.execute("UPDATE incidents SET status = ?, updated_at = ? WHERE id = ?", (status.upper(), now, incident_id))
    db.commit()
    if cur.rowcount == 0:
        db.close()
        return None
    row = db.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
    db.close()
    return _deserialize_incident(row)


def get_fleet_summary(client_org: Optional[str] = None) -> Dict[str, Any]:
    db = get_connection()
    org_filter = " AND client_org = ?" if (client_org and client_org != "ALL") else ""
    org_params: tuple = (client_org,) if (client_org and client_org != "ALL") else ()

    def _scalar(sql: str, params: tuple = ()) -> Any:
        row = db.execute(sql, params).fetchone()
        if row is None:
            return None
        return list(dict(row).values())[0]

    total_devices = _scalar(f"SELECT COUNT(*) AS c FROM devices WHERE 1=1{org_filter}", org_params) or 0
    online_devices = _scalar(f"SELECT COUNT(*) AS c FROM devices WHERE status = 'ONLINE'{org_filter}", org_params) or 0
    offline_devices = _scalar(f"SELECT COUNT(*) AS c FROM devices WHERE status = 'OFFLINE'{org_filter}", org_params) or 0
    revoked_devices = _scalar(f"SELECT COUNT(*) AS c FROM devices WHERE status = 'REVOKED'{org_filter}", org_params) or 0

    if client_org and client_org != "ALL":
        total_events = _scalar("SELECT COUNT(*) AS c FROM events e JOIN devices d ON e.device_id=d.device_id WHERE d.client_org=?", org_params) or 0
        critical_events = _scalar("SELECT COUNT(*) AS c FROM events e JOIN devices d ON e.device_id=d.device_id WHERE e.is_critical=1 AND d.client_org=?", org_params) or 0
        open_incidents = _scalar("SELECT COUNT(*) AS c FROM incidents i JOIN devices d ON i.device_id=d.device_id WHERE i.status IN ('OPEN','ACKNOWLEDGED') AND d.client_org=?", org_params) or 0
    else:
        total_events = _scalar("SELECT COUNT(*) AS c FROM events") or 0
        critical_events = _scalar("SELECT COUNT(*) AS c FROM events WHERE is_critical = 1") or 0
        open_incidents = _scalar("SELECT COUNT(*) AS c FROM incidents WHERE status IN ('OPEN', 'ACKNOWLEDGED')") or 0

    avg_health_val = _scalar(f"SELECT AVG(health_score) AS v FROM devices WHERE status != 'REVOKED'{org_filter}", org_params)
    max_risk_val = _scalar(f"SELECT MAX(risk_score) AS v FROM devices WHERE status != 'REVOKED'{org_filter}", org_params)
    orgs = [r["client_org"] for r in db.execute("SELECT DISTINCT client_org FROM devices ORDER BY client_org").fetchall()]
    db.close()

    active_devices = online_devices + offline_devices
    avg_health = round(float(avg_health_val), 1) if (active_devices > 0 and avg_health_val is not None) else 100.0
    max_risk = round(float(max_risk_val), 1) if (active_devices > 0 and max_risk_val is not None) else 0.0

    return {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "offline_devices": offline_devices,
        "revoked_devices": revoked_devices,
        "total_events": total_events,
        "critical_events": critical_events,
        "open_incidents": open_incidents,
        "fleet_health_score": avg_health,
        "fleet_risk_score": max_risk,
        "client_orgs": orgs,
        "database_backend": "postgresql" if is_postgres() else "sqlite",
    }


def prune_old_records(event_retention_days: int = 30, telemetry_retention_days: int = 14) -> Dict[str, int]:
    """Deletes expired events & telemetry snapshots to bound production DB size."""
    ev_cutoff = (datetime.now(timezone.utc) - timedelta(days=event_retention_days)).isoformat()
    tel_cutoff = (datetime.now(timezone.utc) - timedelta(days=telemetry_retention_days)).isoformat()
    db = get_connection()
    c1 = db.execute("DELETE FROM events WHERE ingested_at < ?", (ev_cutoff,))
    c2 = db.execute("DELETE FROM telemetry_snapshots WHERE ingested_at < ?", (tel_cutoff,))
    db.commit()
    deleted_events = c1.rowcount
    deleted_telemetry = c2.rowcount
    db.close()
    return {"deleted_events": deleted_events, "deleted_telemetry": deleted_telemetry}
