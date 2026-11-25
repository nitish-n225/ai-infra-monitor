"""Pydantic request/response schemas for the Central Monitoring Backend."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class DeviceConfigModel(BaseModel):
    heartbeat_interval_sec: int = Field(default=10, ge=3, le=300)
    telemetry_interval_sec: int = Field(default=10, ge=3, le=300)
    log_poll_interval_sec: int = Field(default=5, ge=2, le=300)
    event_channels: List[str] = Field(default_factory=lambda: ["System", "Application"])
    include_security_events: bool = False
    watched_log_paths: List[str] = Field(default_factory=list)
    cpu_alert_threshold: float = Field(default=90.0, ge=10.0, le=100.0)
    ram_alert_threshold: float = Field(default=90.0, ge=10.0, le=100.0)
    disk_alert_threshold: float = Field(default=90.0, ge=10.0, le=100.0)


class DeviceRegisterRequest(BaseModel):
    device_id: str = Field(..., min_length=4, max_length=128)
    hostname: str = Field(..., min_length=1, max_length=128)
    client_org: str = Field(default="Default", max_length=120)
    tags: List[str] = Field(default_factory=list)
    os_name: str = Field(default="Windows")
    os_version: str = Field(default="")
    architecture: str = Field(default="")
    ip_address: str = Field(default="")
    mac_address: str = Field(default="")
    agent_version: str = Field(default="2.0.0")
    enrollment_token: str = Field(..., min_length=4)
    consent_confirmed: bool = Field(...)


class HeartbeatRequest(BaseModel):
    agent_version: Optional[str] = None
    ip_address: Optional[str] = None
    uptime_seconds: Optional[float] = None


class LogEventItem(BaseModel):
    event_uid: Optional[str] = None
    timestamp: str
    source_type: str = Field(default="WINDOWS_EVENT_LOG")
    channel: str = Field(default="System")
    event_id: Optional[int] = None
    record_number: Optional[int] = None
    level: str = Field(default="INFO")
    service: str = Field(default="system")
    message: str
    raw_line: Optional[str] = None


class LogBatchRequest(BaseModel):
    events: List[LogEventItem] = Field(..., min_length=1, max_length=500)


class TelemetryRequest(BaseModel):
    timestamp: str
    cpu_percent: float = Field(..., ge=0.0, le=100.0)
    cpu_cores: int = Field(default=1, ge=1)
    ram_percent: float = Field(..., ge=0.0, le=100.0)
    ram_used_gb: float = Field(default=0.0, ge=0.0)
    ram_total_gb: float = Field(default=0.0, ge=0.0)
    disk_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    disk_used_gb: float = Field(default=0.0, ge=0.0)
    disk_total_gb: float = Field(default=0.0, ge=0.0)
    disk_volumes: List[Dict[str, Any]] = Field(default_factory=list)
    net_bytes_sent: int = Field(default=0, ge=0)
    net_bytes_recv: int = Field(default=0, ge=0)
    net_sent_kbps: float = Field(default=0.0, ge=0.0)
    net_recv_kbps: float = Field(default=0.0, ge=0.0)
    process_count: int = Field(default=0, ge=0)
    top_processes: List[Dict[str, Any]] = Field(default_factory=list)
    services: List[Dict[str, Any]] = Field(default_factory=list)
    uptime_seconds: float = Field(default=0.0, ge=0.0)


class CreateEnrollmentTokenRequest(BaseModel):
    label: str = Field(default="Windows Endpoint Enrollment", max_length=120)
    client_org: str = Field(default="Default", max_length=120)
    max_uses: int = Field(default=25, ge=1, le=1000)
    expires_hours: Optional[int] = Field(default=168, ge=1, le=8760)


class RevokeDeviceRequest(BaseModel):
    reason: str = Field(default="Revoked by administrator", max_length=256)


class IncidentStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(OPEN|ACKNOWLEDGED|RESOLVED)$")


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    device_id: Optional[str] = None


class AssistantQueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    device_id: Optional[str] = None


class AdminLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=256)


class AlertSettingsRequest(BaseModel):
    webhook_url: str = Field(default="", max_length=512)
    notify_on_critical_incident: bool = True
    notify_on_device_offline: bool = True
    cooldown_seconds: int = Field(default=300, ge=30, le=86400)
