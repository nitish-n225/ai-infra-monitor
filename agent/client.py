"""
Authenticated HTTP Client for the Windows Monitoring Agent.
Handles enrollment, bearer token authentication, custom CA TLS verification, heartbeats,
log batches, telemetry, and device revocation.
"""
import logging
import platform
import socket
import uuid
from typing import Dict, Any, List, Optional

import requests

from agent import __version__
from agent.config import AgentConfig
from agent.state_store import AgentStateStore

logger = logging.getLogger("agent.client")


def get_host_identity() -> Dict[str, str]:
    hostname = socket.gethostname()
    ip_addr = ""
    try:
        ip_addr = socket.gethostbyname(hostname)
    except Exception:
        ip_addr = "127.0.0.1"
    node = uuid.getnode()
    mac = ":".join(f"{(node >> ele) & 0xff:02x}" for ele in range(40, -1, -8))
    return {
        "hostname": hostname,
        "os_name": platform.system(),
        "os_version": platform.version(),
        "architecture": platform.machine(),
        "ip_address": ip_addr,
        "mac_address": mac,
        "agent_version": __version__,
    }


class DeviceRevokedError(RuntimeError):
    """Raised when the central backend has revoked this device's access."""


class MonitoringBackendClient:
    def __init__(self, config: AgentConfig, state_store: AgentStateStore):
        self.config = config
        self.state_store = state_store
        self.session = requests.Session()
        if config.ca_cert_path:
            self.session.verify = config.ca_cert_path
        else:
            self.session.verify = config.verify_tls

    def _headers(self) -> Dict[str, str]:
        dev_id, token = self.state_store.get_credentials()
        return {
            "Authorization": f"Bearer {token}",
            "X-Device-ID": dev_id or self.config.device_id,
            "Content-Type": "application/json",
        }

    def ensure_enrolled(self) -> Dict[str, Any]:
        dev_id, token = self.state_store.get_credentials()
        if dev_id == self.config.device_id and token:
            try:
                resp = self.session.get(
                    f"{self.config.backend_url}/api/v1/devices/{self.config.device_id}/config",
                    headers=self._headers(),
                    timeout=self.config.request_timeout_sec,
                )
                if resp.status_code == 200:
                    return resp.json().get("config", {})
                if resp.status_code == 403:
                    raise DeviceRevokedError(resp.text)
                if resp.status_code == 401:
                    self.state_store.clear_token()
            except DeviceRevokedError:
                raise
            except Exception as e:
                logger.warning("Could not verify existing token against backend yet: %s", e)
                return {}

        if not self.config.enrollment_token:
            raise RuntimeError(
                "Device is not enrolled and no enrollment_token is configured. "
                "Generate an enrollment token in the Admin Dashboard and set it in agent_config.json or MONITOR_ENROLLMENT_TOKEN."
            )

        if not self.config.consent_accepted:
            raise RuntimeError(
                "Monitoring consent has not been accepted. Set consent_accepted=true or pass --accept-consent after reviewing monitored data scope."
            )

        identity = get_host_identity()
        payload = {
            "device_id": self.config.device_id,
            "enrollment_token": self.config.enrollment_token,
            "client_org": self.config.client_org or "Default",
            "tags": self.config.tags or [],
            "consent_confirmed": True,
            **identity,
        }
        resp = self.session.post(
            f"{self.config.backend_url}/api/v1/devices/register",
            json=payload,
            timeout=self.config.request_timeout_sec,
        )
        if resp.status_code == 403:
            raise DeviceRevokedError(resp.text)
        resp.raise_for_status()
        data = resp.json()
        self.state_store.set_credentials(data["device_id"], data["device_token"])
        logger.info("Successfully enrolled device %s (%s, org=%s)", data["device_id"], identity["hostname"], payload["client_org"])
        return data.get("config", {})

    def send_heartbeat(self, uptime_seconds: float) -> Optional[Dict[str, Any]]:
        identity = get_host_identity()
        resp = self.session.post(
            f"{self.config.backend_url}/api/v1/devices/{self.config.device_id}/heartbeat",
            headers=self._headers(),
            json={
                "agent_version": identity["agent_version"],
                "ip_address": identity["ip_address"],
                "uptime_seconds": uptime_seconds,
            },
            timeout=self.config.request_timeout_sec,
        )
        if resp.status_code == 403:
            raise DeviceRevokedError(resp.text)
        resp.raise_for_status()
        return resp.json().get("config")

    def send_telemetry(self, telemetry: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.post(
            f"{self.config.backend_url}/api/v1/ingest/telemetry",
            headers=self._headers(),
            json=telemetry,
            timeout=self.config.request_timeout_sec,
        )
        if resp.status_code == 403:
            raise DeviceRevokedError(resp.text)
        resp.raise_for_status()
        return resp.json()

    def send_logs(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        resp = self.session.post(
            f"{self.config.backend_url}/api/v1/ingest/logs",
            headers=self._headers(),
            json={"events": events},
            timeout=self.config.request_timeout_sec,
        )
        if resp.status_code == 403:
            raise DeviceRevokedError(resp.text)
        resp.raise_for_status()
        return resp.json()
