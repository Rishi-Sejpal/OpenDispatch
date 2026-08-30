"""Database session and engine configuration."""

from __future__ import annotations

import socket
from collections.abc import Generator
from contextlib import contextmanager
from urllib.parse import unquote, urlsplit, urlunsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base."""


def _resolve_database_url(raw_url: str) -> str:
    """Return a copy of ``raw_url`` whose host is replaced with an IPv4
    literal when one is available, so the connection works from networks
    that only see an IPv6 AAAA record for the database host (e.g. Docker
    bridge networks reaching Supabase's direct connection hostname).

    If no IPv4 address can be resolved the original URL is returned
    unchanged.
    """
    parts = urlsplit(raw_url)
    host = parts.hostname
    port = parts.port
    if not host or host.startswith("[") or _is_ip_literal(host):
        return raw_url
    try:
        infos = socket.getaddrinfo(host, port or 5432, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return raw_url
    ipv4 = next(
        (info[4] for info in infos if info[0] == socket.AF_INET),
        None,
    )
    if ipv4 is None:
        return raw_url
    target_host = ipv4[0]
    userinfo = ""
    if parts.username:
        userinfo = unquote(parts.username)
        if parts.password:
            userinfo += f":{unquote(parts.password)}"
        userinfo += "@"
    new_netloc = f"{userinfo}{target_host}:{port or 5432}"
    return urlunsplit(
        (parts.scheme, new_netloc, parts.path, parts.query, parts.fragment)
    )


def _is_ip_literal(host: str) -> bool:
    try:
        socket.inet_pton(socket.AF_INET, host)
        return True
    except OSError:
        try:
            socket.inet_pton(socket.AF_INET6, host)
            return True
        except OSError:
            return False


_settings = get_settings()
_database_url = _resolve_database_url(_settings.database_url)

engine = create_engine(
    _database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a session and commits/rollbacks at the end."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager variant for use outside FastAPI request lifecycle."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
