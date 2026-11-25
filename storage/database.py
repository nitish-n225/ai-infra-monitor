import sqlite3
import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "threat_logs.db")

def get_db_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes SQLite database tables for logs and security alerts."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        client_ip TEXT NOT NULL,
        method TEXT NOT NULL,
        endpoint TEXT NOT NULL,
        status_code INTEGER NOT NULL,
        response_size INTEGER NOT NULL,
        user_agent TEXT,
        is_threat INTEGER DEFAULT 0,
        threat_type TEXT DEFAULT 'NORMAL',
        threat_source TEXT DEFAULT 'NONE',
        severity TEXT DEFAULT 'NONE',
        raw_log TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        client_ip TEXT NOT NULL,
        threat_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        threat_source TEXT NOT NULL,
        details TEXT NOT NULL,
        recommendation TEXT NOT NULL,
        status TEXT DEFAULT 'ACTIVE'
    )
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp);
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_logs_client_ip ON logs(client_ip);
    """)
    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp);
    """)

    conn.commit()
    conn.close()

def insert_log(log_data: Dict[str, Any]) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO logs (
        timestamp, client_ip, method, endpoint, status_code,
        response_size, user_agent, is_threat, threat_type,
        threat_source, severity, raw_log
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        log_data.get("timestamp", datetime.utcnow().isoformat()),
        log_data.get("client_ip", "127.0.0.1"),
        log_data.get("method", "GET"),
        log_data.get("endpoint", "/"),
        log_data.get("status_code", 200),
        log_data.get("response_size", 0),
        log_data.get("user_agent", ""),
        1 if log_data.get("is_threat") else 0,
        log_data.get("threat_type", "NORMAL"),
        log_data.get("threat_source", "NONE"),
        log_data.get("severity", "NONE"),
        log_data.get("raw_log", "")
    ))
    log_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return log_id

def insert_alert(alert_data: Dict[str, Any]) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO alerts (
        timestamp, client_ip, threat_type, severity,
        threat_source, details, recommendation, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        alert_data.get("timestamp", datetime.utcnow().isoformat()),
        alert_data.get("client_ip", "127.0.0.1"),
        alert_data.get("threat_type", "UNKNOWN"),
        alert_data.get("severity", "MEDIUM"),
        alert_data.get("threat_source", "RULE_ENGINE"),
        alert_data.get("details", ""),
        alert_data.get("recommendation", "Inspect client IP and enforce firewall block."),
        alert_data.get("status", "ACTIVE")
    ))
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id

def get_recent_logs(limit: int = 50, filter_threats_only: bool = False) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if filter_threats_only:
        cursor.execute("SELECT * FROM logs WHERE is_threat = 1 ORDER BY id DESC LIMIT ?", (limit,))
    else:
        cursor.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_recent_alerts(limit: int = 25) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def resolve_alert(alert_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE alerts SET status = 'RESOLVED' WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()

def get_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM logs")
    total_logs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM logs WHERE is_threat = 1")
    threat_logs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alerts WHERE status = 'ACTIVE'")
    active_alerts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM alerts WHERE severity = 'CRITICAL'")
    critical_alerts = cursor.fetchone()[0]

    # Threat type distribution
    cursor.execute("""
    SELECT threat_type, COUNT(*) as count 
    FROM logs 
    WHERE is_threat = 1 
    GROUP BY threat_type
    ORDER BY count DESC
    """)
    threat_distribution = {row["threat_type"]: row["count"] for row in cursor.fetchall()}

    # Top offending IPs
    cursor.execute("""
    SELECT client_ip, COUNT(*) as count 
    FROM logs 
    WHERE is_threat = 1 
    GROUP BY client_ip 
    ORDER BY count DESC 
    LIMIT 5
    """)
    top_ips = [{"ip": row["client_ip"], "attacks": row["count"]} for row in cursor.fetchall()]

    conn.close()
    return {
        "total_logs": total_logs,
        "threat_logs": threat_logs,
        "active_alerts": active_alerts,
        "critical_alerts": critical_alerts,
        "threat_distribution": threat_distribution,
        "top_ips": top_ips
    }

def clear_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM logs")
    cursor.execute("DELETE FROM alerts")
    conn.commit()
    conn.close()
