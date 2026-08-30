"""Health check utilities."""

from __future__ import annotations

from sqlalchemy import text

from app.db.session import engine


def check_db() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False


def check_redis() -> bool:
    try:
        from app.core.config import get_settings
        import redis

        client = redis.Redis.from_url(get_settings().redis_url, socket_connect_timeout=1, socket_timeout=1)
        return bool(client.ping())
    except Exception:  # noqa: BLE001
        return False
