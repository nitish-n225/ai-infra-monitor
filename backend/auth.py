"""
Authentication & Role Security Helpers for the Central Backend.
Supports:
- Operator Login (PBKDF2-HMAC-SHA256 password hashing + JWT session tokens)
- Admin API Key authentication (X-Admin-Key)
- Enrollment Token verification (single/multi-use hashed tokens + org scoping)
- Device Bearer Token generation & SHA-256 verification
- WebSocket / SSE query-token or header authentication
"""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import jwt
from fastapi import Header, HTTPException, Query

from backend.database import (
    BASE_DIR,
    create_enrollment_token,
    get_device_raw,
    get_user,
    list_enrollment_tokens,
    upsert_user,
    validate_and_consume_enrollment_token,
)

ADMIN_KEY_FILE = BASE_DIR / "data" / ".admin_key"
JWT_SECRET_FILE = BASE_DIR / "data" / ".jwt_secret"


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        alg, salt, digest_hex = stored_hash.split("$", 2)
        if alg != "pbkdf2_sha256":
            return False
        candidate = hash_password(password, salt=salt)
        return hmac.compare_digest(candidate, stored_hash)
    except Exception:
        return False


def generate_token(prefix: str = "agt") -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def get_or_init_admin_key() -> str:
    env_key = os.environ.get("MONITOR_ADMIN_KEY", "").strip()
    if env_key:
        return env_key
    if ADMIN_KEY_FILE.exists():
        stored = ADMIN_KEY_FILE.read_text(encoding="utf-8").strip()
        if stored:
            return stored
    ADMIN_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    generated = f"adm_{secrets.token_urlsafe(24)}"
    ADMIN_KEY_FILE.write_text(generated, encoding="utf-8")
    return generated


def get_or_init_jwt_secret() -> str:
    env_sec = os.environ.get("MONITOR_JWT_SECRET", "").strip()
    if env_sec:
        return env_sec
    if JWT_SECRET_FILE.exists():
        stored = JWT_SECRET_FILE.read_text(encoding="utf-8").strip()
        if stored:
            return stored
    JWT_SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    generated = secrets.token_urlsafe(48)
    JWT_SECRET_FILE.write_text(generated, encoding="utf-8")
    return generated


def ensure_default_admin_user() -> None:
    """Ensures an initial admin operator user exists if configured via env or creates local bootstrap admin."""
    username = os.environ.get("MONITOR_ADMIN_USER", "admin").strip() or "admin"
    env_pw = os.environ.get("MONITOR_ADMIN_PASSWORD", "").strip()
    existing = get_user(username)
    if env_pw:
        upsert_user(username, hash_password(env_pw), role="admin")
    elif not existing:
        # Bootstrap password defaults to Admin Key if no custom password provided
        bootstrap_pw = get_or_init_admin_key()
        upsert_user(username, hash_password(bootstrap_pw), role="admin")


def issue_operator_jwt(username: str, role: str = "admin", hours: int = 24) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=hours)).timestamp()),
    }
    return jwt.encode(payload, get_or_init_jwt_secret(), algorithm="HS256")


def verify_operator_jwt(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, get_or_init_jwt_secret(), algorithms=["HS256"])
    except Exception:
        return None


def ensure_default_enrollment_token() -> Optional[str]:
    env_token = os.environ.get("MONITOR_ENROLLMENT_TOKEN", "").strip()
    if not env_token:
        return None
    token_hash = hash_token(env_token)
    existing = list_enrollment_tokens()
    if not existing:
        expires_at = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
        create_enrollment_token(
            token_id="tok_env_bootstrap",
            token_hash=token_hash,
            label="Bootstrap Enrollment Token (ENV)",
            client_org="Default",
            max_uses=500,
            expires_at=expires_at,
        )
    return env_token


def verify_enrollment_secret(raw_token: str) -> Optional[Dict[str, Any]]:
    env_token = os.environ.get("MONITOR_ENROLLMENT_TOKEN", "").strip()
    if env_token and hmac.compare_digest(raw_token, env_token):
        return {"token_id": "tok_env_bootstrap", "client_org": "Default"}
    return validate_and_consume_enrollment_token(hash_token(raw_token))


def check_admin_credentials(x_admin_key: Optional[str], authorization: Optional[str], query_token: Optional[str] = None) -> str:
    expected_key = get_or_init_admin_key()
    if x_admin_key and hmac.compare_digest(x_admin_key.strip(), expected_key):
        return "api_key_admin"
    bearer = None
    if authorization and authorization.startswith("Bearer "):
        bearer = authorization.split(" ", 1)[1].strip()
    elif query_token:
        bearer = query_token.strip()
    if bearer:
        if hmac.compare_digest(bearer, expected_key):
            return "api_key_admin"
        claims = verify_operator_jwt(bearer)
        if claims and claims.get("sub"):
            return str(claims["sub"])
    raise HTTPException(status_code=401, detail="Invalid or missing administrator credentials")


def require_admin(
    x_admin_key: Optional[str] = Header(default=None, alias="X-Admin-Key"),
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> str:
    return check_admin_credentials(x_admin_key=x_admin_key, authorization=authorization, query_token=token)


def require_device_auth(
    authorization: Optional[str] = Header(default=None),
    x_device_id: Optional[str] = Header(default=None, alias="X-Device-ID"),
) -> Dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer device token")
    if not x_device_id:
        raise HTTPException(status_code=401, detail="Missing X-Device-ID header")

    raw_token = authorization.split(" ", 1)[1].strip()
    device = get_device_raw(x_device_id.strip())
    if not device:
        raise HTTPException(status_code=401, detail="Unknown device_id; enroll first")
    if device["status"] == "REVOKED":
        raise HTTPException(status_code=403, detail="DEVICE_REVOKED: Device access has been revoked by administrator")

    provided_hash = hash_token(raw_token)
    if not hmac.compare_digest(provided_hash, device["token_hash"]):
        raise HTTPException(status_code=401, detail="Invalid device token")

    return device
