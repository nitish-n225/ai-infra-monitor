"""
Agent Configuration Loader.
Loads backend URL, enrollment settings, client organization, watched log paths, and explicit user consent.
"""
import json
import os
import socket
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional

AGENT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = AGENT_DIR / "agent_config.json"
DEFAULT_STATE_PATH = AGENT_DIR / "agent_state.db"


def generate_stable_device_id() -> str:
    node = uuid.getnode()
    host = socket.gethostname().lower()
    raw = f"{host}-{node:012x}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, raw))


@dataclass
class AgentConfig:
    backend_url: str = ""
    enrollment_token: str = ""
    client_org: str = "Default"
    tags: List[str] = field(default_factory=list)
    device_id: str = field(default_factory=generate_stable_device_id)
    consent_accepted: bool = False
    heartbeat_interval_sec: int = 10
    telemetry_interval_sec: int = 10
    log_poll_interval_sec: int = 5
    event_channels: List[str] = field(default_factory=lambda: ["System", "Application"])
    include_security_events: bool = False
    security_event_ids: List[int] = field(
        default_factory=lambda: [4624, 4625, 4634, 4648, 4720, 4726, 4740, 1102]
    )
    watched_log_paths: List[str] = field(default_factory=list)
    initial_event_lookback: int = 20
    request_timeout_sec: int = 30
    verify_tls: bool = True
    ca_cert_path: str = ""
    agent_log_path: str = ""

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "AgentConfig":
        path = Path(config_path) if config_path else Path(os.environ.get("AGENT_CONFIG_PATH", str(DEFAULT_CONFIG_PATH)))
        data = {}
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))

        cfg = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

        if os.environ.get("BACKEND_URL"):
            cfg.backend_url = os.environ["BACKEND_URL"].strip()
        if os.environ.get("MONITOR_BACKEND_URL"):
            cfg.backend_url = os.environ["MONITOR_BACKEND_URL"].strip()
        if os.environ.get("MONITOR_ENROLLMENT_TOKEN"):
            cfg.enrollment_token = os.environ["MONITOR_ENROLLMENT_TOKEN"].strip()
        if os.environ.get("AGENT_CLIENT_ORG"):
            cfg.client_org = os.environ["AGENT_CLIENT_ORG"].strip()
        if os.environ.get("AGENT_DEVICE_ID"):
            cfg.device_id = os.environ["AGENT_DEVICE_ID"].strip()
        if os.environ.get("AGENT_CONSENT_ACCEPTED", "").lower() in ("1", "true", "yes"):
            cfg.consent_accepted = True
        if os.environ.get("AGENT_INCLUDE_SECURITY", "").lower() in ("1", "true", "yes"):
            cfg.include_security_events = True
        if os.environ.get("AGENT_WATCHED_LOGS"):
            cfg.watched_log_paths = [p.strip() for p in os.environ["AGENT_WATCHED_LOGS"].split(";") if p.strip()]
        if os.environ.get("AGENT_CA_CERT"):
            cfg.ca_cert_path = os.environ["AGENT_CA_CERT"].strip()

        cfg.backend_url = cfg.backend_url.rstrip("/")
        return cfg

    def save(self, config_path: Optional[Path] = None) -> None:
        path = Path(config_path) if config_path else Path(os.environ.get("AGENT_CONFIG_PATH", str(DEFAULT_CONFIG_PATH)))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
