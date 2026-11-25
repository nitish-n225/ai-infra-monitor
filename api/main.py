import os
import asyncio
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from storage.database import (
    init_db, get_stats, get_recent_logs, get_recent_alerts,
    resolve_alert, clear_database
)
from detection.pipeline import SecurityPipeline
from ingestion.log_generator import LogGenerator

# Initialize DB tables on startup
init_db()

app = FastAPI(
    title="Intelligent Log Anomaly & Threat Detection System",
    description="SIEM & Log Security Monitoring powered by Rule-Based Signatures and Machine Learning.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pipeline = SecurityPipeline()

# Connection Manager for WebSockets
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# Background stream control
background_streaming = True

async def background_log_worker():
    """Generates continuous background web traffic for live demonstration."""
    while True:
        try:
            if background_streaming and manager.active_connections:
                # Generate a normal log event
                normal_event = LogGenerator.generate_normal_log()
                result = pipeline.process(normal_event)
                await manager.broadcast({
                    "type": "NEW_LOG",
                    "data": result,
                    "stats": get_stats()
                })
        except Exception as e:
            print(f"Error in background worker: {e}")
        await asyncio.sleep(2.0)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(background_log_worker())

# ----------------- REST API Endpoints -----------------

@app.get("/api/stats")
def fetch_stats():
    return get_stats()

@app.get("/api/logs")
def fetch_logs(limit: int = 50, threats_only: bool = False):
    return get_recent_logs(limit=limit, filter_threats_only=threats_only)

@app.get("/api/alerts")
def fetch_alerts(limit: int = 30):
    return get_recent_alerts(limit=limit)

@app.post("/api/alerts/{alert_id}/resolve")
def mark_alert_resolved(alert_id: int):
    resolve_alert(alert_id)
    return {"status": "success", "message": f"Alert {alert_id} resolved"}

@app.post("/api/ingest")
async def ingest_log(payload: Dict[str, Any]):
    """Ingest custom raw log line or JSON event from external clients."""
    raw_log = payload.get("log") or payload
    result = pipeline.process(raw_log)
    await manager.broadcast({
        "type": "NEW_LOG",
        "data": result,
        "stats": get_stats()
    })
    return {"status": "processed", "result": result}

@app.post("/api/simulate/{attack_type}")
async def simulate_attack(attack_type: str):
    """Triggers simulated attacks for live project demonstration."""
    attack_type = attack_type.lower()
    processed_events = []

    if attack_type == "sqli":
        event = LogGenerator.generate_sqli_attack()
        result = pipeline.process(event)
        processed_events.append(result)

    elif attack_type == "xss":
        event = LogGenerator.generate_xss_attack()
        result = pipeline.process(event)
        processed_events.append(result)

    elif attack_type == "path_traversal":
        event = LogGenerator.generate_path_traversal()
        result = pipeline.process(event)
        processed_events.append(result)

    elif attack_type == "recon":
        event = LogGenerator.generate_recon_probe()
        result = pipeline.process(event)
        processed_events.append(result)

    elif attack_type == "brute_force":
        events = LogGenerator.generate_brute_force_batch()
        for ev in events:
            res = pipeline.process(ev)
            processed_events.append(res)
            await asyncio.sleep(0.05)

    elif attack_type == "dos":
        events = LogGenerator.generate_dos_batch()
        for ev in events:
            res = pipeline.process(ev)
            processed_events.append(res)
            await asyncio.sleep(0.02)

    elif attack_type == "normal":
        event = LogGenerator.generate_normal_log()
        result = pipeline.process(event)
        processed_events.append(result)

    else:
        raise HTTPException(status_code=400, detail=f"Unknown attack type: {attack_type}")

    # Broadcast updates to WebSocket clients
    stats = get_stats()
    for ev in processed_events:
        await manager.broadcast({
            "type": "NEW_LOG",
            "data": ev,
            "stats": stats
        })

    return {
        "status": "success",
        "attack_type": attack_type,
        "events_generated": len(processed_events)
    }

@app.post("/api/clear")
async def reset_data():
    clear_database()
    stats = get_stats()
    await manager.broadcast({"type": "RESET", "stats": stats})
    return {"status": "cleared"}

@app.post("/api/stream/toggle")
def toggle_stream():
    global background_streaming
    background_streaming = not background_streaming
    return {"background_streaming": background_streaming}

# ----------------- WebSocket Endpoint -----------------

@app.websocket("/ws/logs")
async def websocket_logs_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Send initial snapshot of stats
    await websocket.send_text(json.dumps({
        "type": "INIT",
        "stats": get_stats()
    }))
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ----------------- Static Web Files -----------------
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
if os.path.exists(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

@app.get("/")
def serve_dashboard():
    index_file = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Web dashboard files are being prepared."}
