"""
Authenticated Real-Time WebSocket & HTTP Client for the Streamlit Admin Dashboard.
Maintains a background WebSocket listener thread connected to the FastAPI Central Backend (/ws/live)
with JWT/Admin-Key authentication and SSE fallback.
"""
import asyncio
import json
import os
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional
from urllib.parse import quote

import requests

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

BASE_DIR = Path(__file__).resolve().parent.parent


def get_backend_url() -> str:
    """
    Resolves Central Backend URL from BACKEND_URL, MONITOR_BACKEND_URL, or Streamlit secrets.
    Falls back to http://127.0.0.1:8000 only for local development when unset.
    """
    for key in ("BACKEND_URL", "MONITOR_BACKEND_URL"):
        val = os.environ.get(key, "").strip()
        if val:
            return val.rstrip("/")
    try:
        import streamlit as st
        for key in ("BACKEND_URL", "MONITOR_BACKEND_URL"):
            if key in st.secrets:
                val = str(st.secrets[key]).strip()
                if val:
                    return val.rstrip("/")
    except Exception:
        pass
    return "http://127.0.0.1:8000"


def is_remote_backend_configured() -> bool:
    url = get_backend_url()
    return not ("127.0.0.1" in url or "localhost" in url)


def get_admin_key() -> str:
    env_key = os.environ.get("MONITOR_ADMIN_KEY", "").strip()
    if env_key:
        return env_key
    key_file = BASE_DIR / "data" / ".admin_key"
    if key_file.exists():
        return key_file.read_text(encoding="utf-8").strip()
    return ""


class RealtimeBackendBridge:
    """Thread-safe singleton bridge between authenticated FastAPI WebSocket stream and Streamlit UI."""

    def __init__(self, backend_url: Optional[str] = None):
        self.backend_url = (backend_url or get_backend_url()).rstrip("/")
        self.base_ws_url = self.backend_url.replace("https://", "wss://").replace("http://", "ws://") + "/ws/live"
        self._lock = threading.Lock()
        self._auth_token: str = ""
        self.connected = False
        self.transport = "DISCONNECTED"
        self.last_error: Optional[str] = None
        self.last_seq: int = 0
        self.last_update_ts: float = 0.0
        self.live_push_buffer: Deque[Dict[str, Any]] = deque(maxlen=150)
        self._started = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def set_token(self, token: str) -> None:
        with self._lock:
            self._auth_token = (token or "").strip()

    def ensure_started(self, token: Optional[str] = None) -> None:
        if token:
            self.set_token(token)
        with self._lock:
            if self._started and self._thread and self._thread.is_alive():
                return
            self._started = True
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ws-dashboard-bridge")
            self._thread.start()

    def _get_token(self) -> str:
        with self._lock:
            return self._auth_token

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            tok = self._get_token()
            if not tok:
                with self._lock:
                    self.connected = False
                    self.transport = "AWAITING_AUTH"
                time.sleep(1.0)
                continue

            if HAS_WEBSOCKETS:
                try:
                    asyncio.run(self._ws_listen(tok))
                except Exception as e:
                    with self._lock:
                        self.connected = False
                        self.transport = "RECONNECTING"
                        self.last_error = str(e)
            else:
                self._sse_listen(tok)
            time.sleep(2.0)

    async def _ws_listen(self, token: str) -> None:
        ws_url = f"{self.base_ws_url}?token={quote(token)}"
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10, open_timeout=5) as ws:
            with self._lock:
                self.connected = True
                self.transport = "WEBSOCKET"
                self.last_error = None
            while not self._stop_event.is_set():
                if self._get_token() != token:
                    break
                msg_raw = await asyncio.wait_for(ws.recv(), timeout=30.0)
                data = json.loads(msg_raw)
                with self._lock:
                    self.last_seq = max(self.last_seq, int(data.get("seq", 0))) + 1
                    self.last_update_ts = time.time()
                    self.live_push_buffer.appendleft(data)

    def _sse_listen(self, token: str) -> None:
        try:
            headers = {"Authorization": f"Bearer {token}"}
            with requests.get(f"{self.backend_url}/api/v1/stream", headers=headers, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                with self._lock:
                    self.connected = True
                    self.transport = "SSE"
                    self.last_error = None
                for line in resp.iter_lines(decode_unicode=True):
                    if self._stop_event.is_set() or self._get_token() != token:
                        break
                    if line and line.startswith("data: "):
                        data = json.loads(line[6:])
                        with self._lock:
                            self.last_seq += 1
                            self.last_update_ts = time.time()
                            self.live_push_buffer.appendleft(data)
        except Exception as e:
            with self._lock:
                self.connected = False
                self.transport = "DISCONNECTED"
                self.last_error = str(e)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "connected": self.connected,
                "transport": self.transport,
                "last_seq": self.last_seq,
                "last_update_ts": self.last_update_ts,
                "last_error": self.last_error,
                "recent_pushes": list(self.live_push_buffer)[:15],
            }


_BRIDGE_INSTANCE: Optional[RealtimeBackendBridge] = None
_BRIDGE_LOCK = threading.Lock()


def get_realtime_bridge(token: Optional[str] = None) -> RealtimeBackendBridge:
    global _BRIDGE_INSTANCE
    with _BRIDGE_LOCK:
        if _BRIDGE_INSTANCE is None:
            _BRIDGE_INSTANCE = RealtimeBackendBridge()
        _BRIDGE_INSTANCE.ensure_started(token=token)
        return _BRIDGE_INSTANCE


class BackendAPIClient:
    """Synchronous REST helper for authenticated Streamlit views."""

    def __init__(self, base_url: Optional[str] = None, bearer_token: Optional[str] = None, admin_key: Optional[str] = None):
        self.base_url = (base_url or get_backend_url()).rstrip("/")
        self.bearer_token = (bearer_token or "").strip()
        self.admin_key = (admin_key if admin_key is not None else "").strip()

    def _auth_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.admin_key:
            headers["X-Admin-Key"] = self.admin_key
        return headers

    def health(self) -> Optional[Dict[str, Any]]:
        try:
            r = requests.get(f"{self.base_url}/health", timeout=2.5)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        return None

    def login(self, username: str, password: str) -> Dict[str, Any]:
        r = requests.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"username": username, "password": password},
            timeout=5,
        )
        r.raise_for_status()
        return r.json()

    def get_summary(self, client_org: Optional[str] = None) -> Dict[str, Any]:
        params = {"client_org": client_org} if (client_org and client_org != "ALL") else {}
        r = requests.get(f"{self.base_url}/api/v1/fleet/summary", headers=self._auth_headers(), params=params, timeout=4)
        r.raise_for_status()
        return r.json()

    def get_devices(self, client_org: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {"client_org": client_org} if (client_org and client_org != "ALL") else {}
        r = requests.get(f"{self.base_url}/api/v1/devices", headers=self._auth_headers(), params=params, timeout=4)
        r.raise_for_status()
        return r.json()

    def get_telemetry_history(self, device_id: str, limit: int = 60) -> List[Dict[str, Any]]:
        r = requests.get(
            f"{self.base_url}/api/v1/devices/{device_id}/telemetry",
            headers=self._auth_headers(),
            params={"limit": limit},
            timeout=4,
        )
        r.raise_for_status()
        return r.json()

    def get_device_forecast(self, device_id: str) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}/api/v1/devices/{device_id}/forecast", headers=self._auth_headers(), timeout=4)
        r.raise_for_status()
        return r.json()

    def get_events(
        self,
        device_id: Optional[str] = None,
        client_org: Optional[str] = None,
        level: Optional[str] = None,
        channel: Optional[str] = None,
        search: Optional[str] = None,
        critical_only: bool = False,
        limit: int = 150,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"limit": limit, "critical_only": critical_only}
        if device_id:
            params["device_id"] = device_id
        if client_org and client_org != "ALL":
            params["client_org"] = client_org
        if level and level != "ALL":
            params["level"] = level
        if channel and channel != "ALL":
            params["channel"] = channel
        if search:
            params["search"] = search
        r = requests.get(f"{self.base_url}/api/v1/events", headers=self._auth_headers(), params=params, timeout=5)
        r.raise_for_status()
        return r.json()

    def get_incidents(self, device_id: Optional[str] = None, client_org: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {}
        if device_id:
            params["device_id"] = device_id
        if client_org and client_org != "ALL":
            params["client_org"] = client_org
        if status and status != "ALL":
            params["status"] = status
        r = requests.get(f"{self.base_url}/api/v1/incidents", headers=self._auth_headers(), params=params, timeout=5)
        r.raise_for_status()
        return r.json()

    def update_incident_status(self, incident_id: int, status: str) -> Dict[str, Any]:
        r = requests.patch(
            f"{self.base_url}/api/v1/incidents/{incident_id}",
            headers=self._auth_headers(),
            json={"status": status},
            timeout=5,
        )
        r.raise_for_status()
        return r.json()

    def create_enrollment_token(self, label: str, client_org: str = "Default", max_uses: int = 25, expires_hours: int = 168) -> Dict[str, Any]:
        r = requests.post(
            f"{self.base_url}/api/v1/enrollment-tokens",
            headers=self._auth_headers(),
            json={"label": label, "client_org": client_org, "max_uses": max_uses, "expires_hours": expires_hours},
            timeout=5,
        )
        r.raise_for_status()
        return r.json()

    def list_enrollment_tokens(self) -> List[Dict[str, Any]]:
        r = requests.get(f"{self.base_url}/api/v1/enrollment-tokens", headers=self._auth_headers(), timeout=4)
        r.raise_for_status()
        return r.json()

    def revoke_device(self, device_id: str, reason: str) -> Dict[str, Any]:
        r = requests.post(
            f"{self.base_url}/api/v1/devices/{device_id}/revoke",
            headers=self._auth_headers(),
            json={"reason": reason},
            timeout=5,
        )
        r.raise_for_status()
        return r.json()

    def update_device_config(self, device_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        r = requests.put(
            f"{self.base_url}/api/v1/devices/{device_id}/config",
            headers=self._auth_headers(),
            json=config,
            timeout=5,
        )
        r.raise_for_status()
        return r.json()

    def semantic_search(self, query: str, top_k: int = 5, device_id: Optional[str] = None) -> Dict[str, Any]:
        r = requests.post(
            f"{self.base_url}/api/v1/search/semantic",
            headers=self._auth_headers(),
            json={"query": query, "top_k": top_k, "device_id": device_id},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def ask_assistant(self, query: str, device_id: Optional[str] = None) -> Dict[str, Any]:
        r = requests.post(
            f"{self.base_url}/api/v1/assistant/query",
            headers=self._auth_headers(),
            json={"query": query, "device_id": device_id},
            timeout=20,
        )
        r.raise_for_status()
        return r.json()

    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        r = requests.get(f"{self.base_url}/api/v1/audit-logs", headers=self._auth_headers(), params={"limit": limit}, timeout=4)
        r.raise_for_status()
        return r.json()

    def get_alert_settings(self) -> Dict[str, Any]:
        r = requests.get(f"{self.base_url}/api/v1/alerts/settings", headers=self._auth_headers(), timeout=4)
        r.raise_for_status()
        return r.json()

    def update_alert_settings(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        r = requests.put(f"{self.base_url}/api/v1/alerts/settings", headers=self._auth_headers(), json=settings, timeout=5)
        r.raise_for_status()
        return r.json()

    def test_alert_webhook(self) -> Dict[str, Any]:
        r = requests.post(f"{self.base_url}/api/v1/alerts/test", headers=self._auth_headers(), timeout=8)
        r.raise_for_status()
        return r.json()
