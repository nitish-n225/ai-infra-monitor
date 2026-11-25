"""
Real-Time WebSocket & Server-Sent Events (SSE) Broadcaster.
Pushes live device registrations, heartbeats, incoming logs, telemetry, and incidents to connected dashboards.
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Set
from fastapi import WebSocket


class LiveStreamManager:
    """Manages connected WebSocket and SSE clients for real-time dashboard updates."""

    def __init__(self):
        self.websocket_clients: List[WebSocket] = []
        self.sse_queues: Set[asyncio.Queue] = set()
        self._seq: int = 0

    async def connect_ws(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.websocket_clients.append(websocket)

    def disconnect_ws(self, websocket: WebSocket) -> None:
        if websocket in self.websocket_clients:
            self.websocket_clients.remove(websocket)

    def register_sse_queue(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self.sse_queues.add(q)
        return q

    def unregister_sse_queue(self, q: asyncio.Queue) -> None:
        self.sse_queues.discard(q)

    async def broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        self._seq += 1
        envelope = {
            "seq": self._seq,
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": payload,
        }
        serialized = json.dumps(envelope, default=str)

        # Broadcast to WebSocket clients
        for ws in list(self.websocket_clients):
            try:
                await ws.send_text(serialized)
            except Exception:
                self.disconnect_ws(ws)

        # Broadcast to SSE subscribers
        for q in list(self.sse_queues):
            try:
                if q.full():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(serialized)
            except Exception:
                pass

