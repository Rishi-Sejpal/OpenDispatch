"""Security utilities: password hashing, JWT, request IDs."""

from __future__ import annotations

import contextvars
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.errors import UnauthorizedError

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

_password_hasher: PasswordHasher | None = None


def get_password_hasher() -> PasswordHasher:
    global _password_hasher
    if _password_hasher is None:
        _password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
    return _password_hasher


def hash_password(password: str) -> str:
    return get_password_hasher().hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        get_password_hasher().verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:  # noqa: BLE001
        return False
    return True


def create_access_token(*, subject: str, claims: dict[str, Any] | None = None) -> tuple[str, int]:
    s = get_settings()
    now = datetime.now(tz=timezone.utc)
    exp = now + timedelta(seconds=s.jwt_access_ttl_seconds)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "access",
        "jti": secrets.token_urlsafe(16),
    }
    if claims:
        payload.update(claims)
    token = jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)
    return token, s.jwt_access_ttl_seconds


def create_refresh_token(*, subject: str) -> tuple[str, int]:
    s = get_settings()
    now = datetime.now(tz=timezone.utc)
    exp = now + timedelta(seconds=s.jwt_refresh_ttl_seconds)
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),
    }
    token = jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)
    return token, s.jwt_refresh_ttl_seconds


def decode_token(token: str) -> dict[str, Any]:
    s = get_settings()
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
    except JWTError as exc:
        raise UnauthorizedError("Invalid or expired token.", details={"reason": str(exc)}) from exc


def new_request_id() -> str:
    rid = str(uuid.uuid4())
    _request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    return _request_id_var.get()


def short_hash(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
