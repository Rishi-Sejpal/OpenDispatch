"""Security utilities.

Password hashing and refresh-token management have been removed: credentials
are owned by Supabase Auth and the backend only verifies Supabase-issued
JWTs (see ``app.core.supabase``). The legacy JWT helper functions are kept
for backwards compatibility but are no longer used by the application.
"""

from __future__ import annotations

import contextvars
import hashlib
import secrets
import uuid

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


def new_request_id() -> str:
    rid = str(uuid.uuid4())
    _request_id_var.set(rid)
    return rid


def get_request_id() -> str:
    return _request_id_var.get()


def short_hash(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
