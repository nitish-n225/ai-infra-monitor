"""
Real Alert Notification Dispatcher (Webhook / Slack / Microsoft Teams / Generic JSON).
Includes cooldown deduplication so repeated alerts don't spam operators.
"""
import logging
import os
import threading
import time
from typing import Dict, Any, Optional

import requests

from backend.database import get_setting, set_setting

logger = logging.getLogger("backend.alerts")

DEFAULT_ALERT_SETTINGS: Dict[str, Any] = {
    "webhook_url": os.environ.get("ALERT_WEBHOOK_URL", "").strip(),
    "notify_on_critical_incident": True,
    "notify_on_device_offline": True,
    "cooldown_seconds": 300,
}


class AlertDispatcher:
    def __init__(self):
        self._lock = threading.Lock()
        self._last_sent: Dict[str, float] = {}

    def get_settings(self) -> Dict[str, Any]:
        stored = get_setting("alert_settings")
        if isinstance(stored, dict):
            merged = {**DEFAULT_ALERT_SETTINGS, **stored}
        else:
            merged = dict(DEFAULT_ALERT_SETTINGS)
        env_url = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
        if not merged.get("webhook_url") and env_url:
            merged["webhook_url"] = env_url
        return merged

    def update_settings(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        merged = {**self.get_settings(), **new_settings}
        set_setting("alert_settings", merged)
        return merged

    def _should_send(self, dedup_key: str, cooldown_seconds: int) -> bool:
        now = time.monotonic()
        with self._lock:
            last = self._last_sent.get(dedup_key)
            if last is not None and (now - last) < cooldown_seconds:
                return False
            self._last_sent[dedup_key] = now
            return True

    def dispatch_webhook(self, event_type: str, title: str, message: str, metadata: Optional[Dict[str, Any]] = None, bypass_cooldown: bool = False) -> Dict[str, Any]:
        cfg = self.get_settings()
        webhook_url = (cfg.get("webhook_url") or "").strip()
        if not webhook_url:
            return {"sent": False, "reason": "No webhook_url configured"}

        dedup_key = f"{event_type}:{title}"
        if not bypass_cooldown and not self._should_send(dedup_key, int(cfg.get("cooldown_seconds", 300))):
            return {"sent": False, "reason": "Cooldown active"}

        payload = {
            "event_type": event_type,
            "title": title,
            "text": f"[{event_type}] {title}\n{message}",
            "message": message,
            "metadata": metadata or {},
        }
        try:
            resp = requests.post(webhook_url, json=payload, timeout=5)
            return {"sent": 200 <= resp.status_code < 300, "status_code": resp.status_code}
        except Exception as e:
            logger.warning("Alert webhook delivery failed: %s", e)
            return {"sent": False, "error": str(e)}


alert_dispatcher = AlertDispatcher()

