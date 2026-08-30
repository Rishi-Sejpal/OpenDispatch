"""Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas import HealthResponse
from app.services.health import check_db, check_redis

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        db=check_db(),
        redis=check_redis(),
        version=get_settings().calculation_engine_version,
    )


@router.get("/ready", response_model=HealthResponse)
async def ready() -> HealthResponse:
    db_ok = check_db()
    redis_ok = check_redis()
    if not db_ok or not redis_ok:
        return HealthResponse(
            status="degraded",
            db=db_ok,
            redis=redis_ok,
            version=get_settings().calculation_engine_version,
        )
    return HealthResponse(
        status="ok",
        db=db_ok,
        redis=redis_ok,
        version=get_settings().calculation_engine_version,
    )
