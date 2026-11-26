"""
Central FastAPI Backend Server for Enterprise Autonomous AI Infrastructure Monitoring System.
Supports multi-computer Windows agent registration, authentication, heartbeats, live log & telemetry
ingestion, persistent SQLite storage, live AI/FAISS detection, webhook alerting, audit logs,
data retention pruning, and authenticated WebSocket + SSE streaming.
"""
import asyncio
import json
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.ai_pipeline import (
    LiveAIProcessor,
    PersistentLiveVectorStore,
    compute_hardware_trend_forecast,
)
from backend.alerts_dispatcher import alert_dispatcher
from backend.auth import (
    check_admin_credentials,
    ensure_default_admin_user,
    ensure_default_enrollment_token,
    generate_token,
    get_or_init_admin_key,
    hash_token,
    issue_operator_jwt,
    require_admin,
    require_device_auth,
    verify_enrollment_secret,
    verify_password,
)
from backend.database import (
    append_audit_log,
    create_enrollment_token,
    deactivate_enrollment_token,
    get_device,
    get_events,
    get_fleet_summary,
    get_latest_telemetry,
    get_telemetry_history,
    get_user,
    init_monitoring_db,
    insert_events_deduplicated,
    insert_telemetry_snapshot,
    is_postgres,
    list_audit_logs,
    list_devices,
    list_enrollment_tokens,
    list_incidents,
    mark_stale_devices_offline,
    prune_old_records,
    record_heartbeat,
    revoke_device,
    update_device_config,
    update_incident_status,
    upsert_device_registration,
)
from backend.models import (
    AdminLoginRequest,
    AlertSettingsRequest,
    AssistantQueryRequest,
    CreateEnrollmentTokenRequest,
    DeviceConfigModel,
    DeviceRegisterRequest,
    HeartbeatRequest,
    IncidentStatusRequest,
    LogBatchRequest,
    RevokeDeviceRequest,
    SemanticSearchRequest,
    TelemetryRequest,
)
from backend.ws_manager import LiveStreamManager

OFFLINE_TIMEOUT_SECONDS = int(os.environ.get("DEVICE_OFFLINE_SECONDS", "30"))
EVENT_RETENTION_DAYS = int(os.environ.get("EVENT_RETENTION_DAYS", "30"))
TELEMETRY_RETENTION_DAYS = int(os.environ.get("TELEMETRY_RETENTION_DAYS", "14"))

stream_manager = LiveStreamManager()
live_vector_store = PersistentLiveVectorStore()
ai_processor = LiveAIProcessor(vector_store=live_vector_store)


async def heartbeat_watchdog_loop() -> None:
    """Marks stale devices OFFLINE, dispatches alerts, and runs periodic retention pruning."""
    prune_tick = 0
    while True:
        try:
            timeout_sec = int(os.environ.get("DEVICE_OFFLINE_SECONDS", str(OFFLINE_TIMEOUT_SECONDS)))
            went_offline = mark_stale_devices_offline(timeout_seconds=timeout_sec)
            for dev in went_offline:
                append_audit_log("watchdog", "DEVICE_OFFLINE", dev["device_id"], f"{dev['hostname']} missed heartbeat > {timeout_sec}s")
                await stream_manager.broadcast("DEVICE_OFFLINE", {
                    "device": dev,
                    "summary": get_fleet_summary(),
                })
                cfg = alert_dispatcher.get_settings()
                if cfg.get("notify_on_device_offline"):
                    await asyncio.to_thread(
                        alert_dispatcher.dispatch_webhook,
                        "DEVICE_OFFLINE",
                        f"Host {dev['hostname']} ({dev.get('client_org', 'Default')}) went OFFLINE",
                        f"Device {dev['device_id']} last seen at {dev.get('last_seen')}",
                        {"device_id": dev["device_id"], "hostname": dev["hostname"]},
                    )

            prune_tick += 1
            if prune_tick >= 720:  # ~1 hour at 5s intervals
                prune_tick = 0
                await asyncio.to_thread(prune_old_records, EVENT_RETENTION_DAYS, TELEMETRY_RETENTION_DAYS)
        except Exception as e:
            print(f"[Watchdog Error] {e}")
        await asyncio.sleep(5)


def _startup_warmup() -> None:
    from src.embedding_engine import LogEmbeddingEngine
    try:
        LogEmbeddingEngine.get_model()
        rebuilt = live_vector_store.rebuild_from_db_if_empty()
        if rebuilt:
            print(f"[Backend] Rebuilt {rebuilt} FAISS vectors from persisted database events.")
    except Exception as e:
        print(f"[Backend] Warmup/FAISS rebuild warning: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    init_monitoring_db()
    admin_key = get_or_init_admin_key()
    ensure_default_admin_user()
    ensure_default_enrollment_token()
    live_vector_store.load()
    if os.environ.get("LOW_MEMORY_MODE", "false").lower() in ("1", "true", "yes"):
        rebuilt = live_vector_store.rebuild_from_db_if_empty()
        if rebuilt:
            print(f"[Backend] Rebuilt {rebuilt} lightweight FAISS vectors from persisted database.")
    elif os.environ.get("LAZY_EMBEDDINGS", "false").lower() not in ("1", "true", "yes"):
        asyncio.create_task(asyncio.to_thread(_startup_warmup))
    db_mode = "PostgreSQL" if is_postgres() else "SQLite"
    print(f"[Backend] Database initialized ({db_mode}). Admin Key ready (length={len(admin_key)}). Offline timeout={OFFLINE_TIMEOUT_SECONDS}s")
    watchdog_task = asyncio.create_task(heartbeat_watchdog_loop())
    try:
        yield
    finally:
        watchdog_task.cancel()
        try:
            await watchdog_task
        except asyncio.CancelledError:
            pass


def _parse_cors_origins() -> List[str]:
    raw = os.environ.get("CORS_ALLOWED_ORIGINS", "").strip()
    if raw:
        return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    return ["http://localhost:8501", "http://127.0.0.1:8501"]


app = FastAPI(
    title="Enterprise Autonomous AI Infrastructure Monitoring Backend",
    description="Real-time multi-device Windows infrastructure monitoring, AI RCA, predictive risk, and FAISS semantic intelligence.",
    version="6.0.0",
    lifespan=lifespan,
)

cors_origins = _parse_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=(cors_origins != ["*"]),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-Key", "X-Device-ID"],
)


@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "service": "ai-infrastructure-monitoring-backend",
        "status": "online",
        "version": app.version,
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/health")
def health_check() -> Dict[str, Any]:
    return {
        "status": "ok",
        "service": "ai-infrastructure-monitoring-backend",
        "database": "postgresql" if is_postgres() else "sqlite",
        "offline_timeout_seconds": int(os.environ.get("DEVICE_OFFLINE_SECONDS", str(OFFLINE_TIMEOUT_SECONDS))),
        "faiss_vectors": live_vector_store.get_stats()["total_vectors"],
    }


# ---------------------------------------------------------------------------
# Operator Login (JWT Authentication)
# ---------------------------------------------------------------------------

@app.post("/api/v1/auth/login")
def operator_login(req: AdminLoginRequest) -> Dict[str, Any]:
    user = get_user(req.username.strip())
    if not user or not verify_password(req.password, user["password_hash"]):
        append_audit_log(req.username, "LOGIN_FAILED", "dashboard", "Invalid username or password")
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = issue_operator_jwt(user["username"], role=user["role"])
    append_audit_log(user["username"], "LOGIN_SUCCESS", "dashboard", f"Role={user['role']}")
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"],
    }


# ---------------------------------------------------------------------------
# Device Enrollment, Authentication, Heartbeat & Configuration Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/v1/devices/register")
async def register_device(req: DeviceRegisterRequest) -> Dict[str, Any]:
    if not req.consent_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Explicit user consent (consent_confirmed=true) is required before enrolling a monitoring agent.",
        )

    existing = get_device(req.device_id)
    if existing and existing.get("status") == "REVOKED":
        raise HTTPException(
            status_code=403,
            detail="DEVICE_REVOKED: This device has been revoked by an administrator and cannot re-enroll automatically.",
        )

    tok_meta = verify_enrollment_secret(req.enrollment_token)
    if not tok_meta:
        raise HTTPException(status_code=401, detail="Invalid, expired, or exhausted enrollment token.")

    device_token = generate_token("dev")
    token_hash = hash_token(device_token)
    default_cfg = (existing.get("config") if existing else None) or DeviceConfigModel().model_dump()

    reg_payload = req.model_dump()
    if reg_payload.get("client_org") in (None, "", "Default") and tok_meta.get("client_org"):
        reg_payload["client_org"] = tok_meta["client_org"]

    device = upsert_device_registration(reg_payload, token_hash=token_hash, config=default_cfg)
    append_audit_log(device["device_id"], "DEVICE_REGISTERED", device["hostname"], f"org={device.get('client_org')}")
    await stream_manager.broadcast("DEVICE_REGISTERED", {
        "device": device,
        "summary": get_fleet_summary(),
    })

    return {
        "status": "registered",
        "device_id": device["device_id"],
        "device_token": device_token,
        "config": device["config"],
        "device": device,
    }


@app.post("/api/v1/devices/{device_id}/heartbeat")
async def device_heartbeat(
    device_id: str,
    req: HeartbeatRequest,
    auth_device: Dict[str, Any] = Depends(require_device_auth),
) -> Dict[str, Any]:
    if auth_device["device_id"] != device_id:
        raise HTTPException(status_code=403, detail="Device ID mismatch")

    updated = record_heartbeat(device_id, ip_address=req.ip_address, agent_version=req.agent_version)
    if not updated:
        raise HTTPException(status_code=403, detail="DEVICE_REVOKED")

    await stream_manager.broadcast("HEARTBEAT", {
        "device_id": device_id,
        "hostname": updated["hostname"],
        "status": updated["status"],
        "last_seen": updated["last_seen"],
        "summary": get_fleet_summary(),
    })
    return {
        "status": "ok",
        "device_status": updated["status"],
        "last_seen": updated["last_seen"],
        "config": updated["config"],
    }


@app.get("/api/v1/devices/{device_id}/config")
def fetch_device_config(
    device_id: str,
    auth_device: Dict[str, Any] = Depends(require_device_auth),
) -> Dict[str, Any]:
    if auth_device["device_id"] != device_id:
        raise HTTPException(status_code=403, detail="Device ID mismatch")
    device = get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"device_id": device_id, "config": device["config"]}


# ---------------------------------------------------------------------------
# Real Log & Telemetry Ingestion Endpoints (Authenticated Agent)
# ---------------------------------------------------------------------------

async def _notify_new_critical_incidents(device: Dict[str, Any], ai_state: Optional[Dict[str, Any]]) -> None:
    if not ai_state:
        return
    cfg = alert_dispatcher.get_settings()
    if not cfg.get("notify_on_critical_incident"):
        return
    for inc in ai_state.get("newly_created_incidents", []):
        if inc.get("severity") in ("CRITICAL", "HIGH"):
            await asyncio.to_thread(
                alert_dispatcher.dispatch_webhook,
                "INCIDENT_DETECTED",
                f"[{inc['severity']}] {device['hostname']}: {inc['title']}",
                inc.get("confirmed_evidence", ""),
                {"device_id": device["device_id"], "category": inc["category"], "incident_id": inc["id"]},
            )


@app.post("/api/v1/ingest/logs")
async def ingest_logs(
    req: LogBatchRequest,
    auth_device: Dict[str, Any] = Depends(require_device_auth),
) -> Dict[str, Any]:
    device = get_device(auth_device["device_id"])
    raw_items = [ev.model_dump() for ev in req.events]
    enriched = await asyncio.to_thread(ai_processor.enrich_and_classify_events, device, raw_items)
    inserted = await asyncio.to_thread(insert_events_deduplicated, enriched)

    indexed_count = 0
    ai_state = None
    if inserted:
        latest_tel = await asyncio.to_thread(get_latest_telemetry, device["device_id"])
        ai_state = await asyncio.to_thread(ai_processor.evaluate_device_ai_state, device, latest_tel)
        await _notify_new_critical_incidents(device, ai_state)
        # Index into FAISS asynchronously so log ingestion returns immediately without HTTP timeout
        asyncio.create_task(asyncio.to_thread(ai_processor.index_new_events, inserted))
        indexed_count = len(inserted)

        await stream_manager.broadcast("NEW_LOGS", {
            "device_id": device["device_id"],
            "hostname": device["hostname"],
            "inserted_count": len(inserted),
            "events": inserted[:25],
            "ai_state": ai_state,
            "summary": get_fleet_summary(),
        })

    return {
        "status": "ok",
        "received": len(raw_items),
        "inserted": len(inserted),
        "duplicates_skipped": len(raw_items) - len(inserted),
        "faiss_indexed": indexed_count,
        "ai_state": ai_state,
    }


@app.post("/api/v1/ingest/telemetry")
async def ingest_telemetry(
    req: TelemetryRequest,
    auth_device: Dict[str, Any] = Depends(require_device_auth),
) -> Dict[str, Any]:
    device = get_device(auth_device["device_id"])
    payload = req.model_dump()
    snap_id = await asyncio.to_thread(insert_telemetry_snapshot, device["device_id"], payload)
    ai_state = await asyncio.to_thread(ai_processor.evaluate_device_ai_state, device, payload)
    await _notify_new_critical_incidents(device, ai_state)

    await stream_manager.broadcast("NEW_TELEMETRY", {
        "device_id": device["device_id"],
        "hostname": device["hostname"],
        "snapshot_id": snap_id,
        "telemetry": payload,
        "ai_state": ai_state,
        "summary": get_fleet_summary(),
    })

    return {
        "status": "ok",
        "snapshot_id": snap_id,
        "ai_state": ai_state,
    }


# ---------------------------------------------------------------------------
# Authenticated Dashboard / Admin Query & Management Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/v1/fleet/summary")
def fleet_summary(client_org: Optional[str] = None, actor: str = Depends(require_admin)) -> Dict[str, Any]:
    return {
        **get_fleet_summary(client_org=client_org),
        "faiss_vectors": live_vector_store.get_stats()["total_vectors"],
    }


@app.get("/api/v1/devices")
def get_all_devices(client_org: Optional[str] = None, actor: str = Depends(require_admin)) -> List[Dict[str, Any]]:
    return list_devices(client_org=client_org)


@app.get("/api/v1/devices/{device_id}")
def get_single_device(device_id: str, actor: str = Depends(require_admin)) -> Dict[str, Any]:
    dev = get_device(device_id)
    if not dev:
        raise HTTPException(status_code=404, detail="Device not found")
    dev["latest_telemetry"] = get_latest_telemetry(device_id)
    return dev


@app.get("/api/v1/devices/{device_id}/telemetry")
def device_telemetry_history(
    device_id: str,
    limit: int = Query(default=60, ge=1, le=500),
    actor: str = Depends(require_admin),
) -> List[Dict[str, Any]]:
    return get_telemetry_history(device_id, limit=limit)


@app.get("/api/v1/devices/{device_id}/forecast")
def device_hardware_forecast(device_id: str, actor: str = Depends(require_admin)) -> Dict[str, Any]:
    history = get_telemetry_history(device_id, limit=30)
    return compute_hardware_trend_forecast(history)


@app.put("/api/v1/devices/{device_id}/config")
async def update_config(device_id: str, cfg: DeviceConfigModel, actor: str = Depends(require_admin)) -> Dict[str, Any]:
    updated = update_device_config(device_id, cfg.model_dump())
    if not updated:
        raise HTTPException(status_code=404, detail="Device not found")
    append_audit_log(actor, "DEVICE_CONFIG_UPDATED", device_id, json.dumps(cfg.model_dump()))
    await stream_manager.broadcast("DEVICE_CONFIG_UPDATED", {"device": updated})
    return updated


@app.post("/api/v1/devices/{device_id}/revoke")
async def revoke_device_endpoint(device_id: str, req: RevokeDeviceRequest, actor: str = Depends(require_admin)) -> Dict[str, Any]:
    revoked = revoke_device(device_id, req.reason)
    if not revoked:
        raise HTTPException(status_code=404, detail="Device not found")
    append_audit_log(actor, "DEVICE_REVOKED", device_id, req.reason)
    await stream_manager.broadcast("DEVICE_REVOKED", {
        "device": revoked,
        "summary": get_fleet_summary(),
    })
    return revoked


@app.get("/api/v1/events")
def query_events(
    device_id: Optional[str] = None,
    client_org: Optional[str] = None,
    level: Optional[str] = None,
    channel: Optional[str] = None,
    search: Optional[str] = None,
    critical_only: bool = False,
    limit: int = Query(default=200, ge=1, le=1000),
    actor: str = Depends(require_admin),
) -> List[Dict[str, Any]]:
    return get_events(
        device_id=device_id,
        client_org=client_org,
        level=level,
        channel=channel,
        search=search,
        critical_only=critical_only,
        limit=limit,
    )


@app.get("/api/v1/incidents")
def query_incidents(
    device_id: Optional[str] = None,
    client_org: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    actor: str = Depends(require_admin),
) -> List[Dict[str, Any]]:
    return list_incidents(device_id=device_id, client_org=client_org, status=status, limit=limit)


@app.patch("/api/v1/incidents/{incident_id}")
async def patch_incident_status(incident_id: int, req: IncidentStatusRequest, actor: str = Depends(require_admin)) -> Dict[str, Any]:
    updated = update_incident_status(incident_id, req.status)
    if not updated:
        raise HTTPException(status_code=404, detail="Incident not found")
    append_audit_log(actor, "INCIDENT_UPDATED", str(incident_id), f"status={req.status}")
    await stream_manager.broadcast("INCIDENT_UPDATED", {"incident": updated, "summary": get_fleet_summary()})
    return updated


@app.post("/api/v1/enrollment-tokens")
def issue_enrollment_token(req: CreateEnrollmentTokenRequest, actor: str = Depends(require_admin)) -> Dict[str, Any]:
    raw_token = f"enroll_{secrets.token_urlsafe(24)}"
    token_id = f"tok_{secrets.token_hex(6)}"
    expires_at = None
    if req.expires_hours:
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=req.expires_hours)).isoformat()
    meta = create_enrollment_token(
        token_id=token_id,
        token_hash=hash_token(raw_token),
        label=req.label,
        client_org=req.client_org,
        max_uses=req.max_uses,
        expires_at=expires_at,
    )
    append_audit_log(actor, "TOKEN_CREATED", token_id, f"label={req.label}, org={req.client_org}")
    return {"token": raw_token, "metadata": meta}


@app.get("/api/v1/enrollment-tokens")
def get_enrollment_tokens(actor: str = Depends(require_admin)) -> List[Dict[str, Any]]:
    return list_enrollment_tokens()


@app.delete("/api/v1/enrollment-tokens/{token_id}")
def revoke_enrollment_token(token_id: str, actor: str = Depends(require_admin)) -> Dict[str, Any]:
    ok = deactivate_enrollment_token(token_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Enrollment token not found")
    append_audit_log(actor, "TOKEN_REVOKED", token_id, "Deactivated by administrator")
    return {"status": "deactivated", "token_id": token_id}


@app.post("/api/v1/search/semantic")
def semantic_search(req: SemanticSearchRequest, actor: str = Depends(require_admin)) -> Dict[str, Any]:
    return live_vector_store.search(
        query=req.query,
        top_k=req.top_k,
        device_id=req.device_id,
        min_similarity=0.1,
    )


@app.post("/api/v1/assistant/query")
def assistant_query(req: AssistantQueryRequest, actor: str = Depends(require_admin)) -> Dict[str, Any]:
    return ai_processor.query_assistant(query=req.query, device_id=req.device_id)


@app.get("/api/v1/audit-logs")
def get_audit_logs(limit: int = Query(default=100, ge=1, le=500), actor: str = Depends(require_admin)) -> List[Dict[str, Any]]:
    return list_audit_logs(limit=limit)


@app.get("/api/v1/alerts/settings")
def get_alert_settings(actor: str = Depends(require_admin)) -> Dict[str, Any]:
    return alert_dispatcher.get_settings()


@app.put("/api/v1/alerts/settings")
def update_alert_settings(req: AlertSettingsRequest, actor: str = Depends(require_admin)) -> Dict[str, Any]:
    updated = alert_dispatcher.update_settings(req.model_dump())
    append_audit_log(actor, "ALERT_SETTINGS_UPDATED", "webhooks", f"enabled={bool(req.webhook_url)}")
    return updated


@app.post("/api/v1/alerts/test")
def test_alert_webhook(actor: str = Depends(require_admin)) -> Dict[str, Any]:
    res = alert_dispatcher.dispatch_webhook(
        "WEBHOOK_TEST",
        "Enterprise AI Monitor Test Alert",
        "Webhook alert delivery verified from Central Backend.",
        {"triggered_by": actor},
        bypass_cooldown=True,
    )
    append_audit_log(actor, "ALERT_TEST", "webhooks", json.dumps(res))
    return res


# ---------------------------------------------------------------------------
# Authenticated Real-Time Streaming Endpoints (WebSocket + SSE)
# ---------------------------------------------------------------------------

@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    token = websocket.query_params.get("token") or websocket.headers.get("x-admin-key")
    auth_hdr = websocket.headers.get("authorization")
    try:
        check_admin_credentials(x_admin_key=token, authorization=auth_hdr, query_token=token)
    except HTTPException:
        await websocket.close(code=1008)
        return

    await stream_manager.connect_ws(websocket)
    try:
        await websocket.send_text(json.dumps({
            "seq": 0,
            "type": "INIT",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {
                "summary": get_fleet_summary(),
                "devices": list_devices(),
            },
        }, default=str))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        stream_manager.disconnect_ws(websocket)
    except Exception:
        stream_manager.disconnect_ws(websocket)


@app.get("/api/v1/stream")
async def sse_live_stream(actor: str = Depends(require_admin)) -> StreamingResponse:
    queue = stream_manager.register_sse_queue()

    async def event_generator():
        try:
            init_payload = json.dumps({
                "seq": 0,
                "type": "INIT",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {
                    "summary": get_fleet_summary(),
                    "devices": list_devices(),
                },
            }, default=str)
            yield f"event: INIT\ndata: {init_payload}\n\n"
            while True:
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield f"event: UPDATE\ndata: {msg}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            stream_manager.unregister_sse_queue(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
