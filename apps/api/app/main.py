"""FastAPI application entry point."""

from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import api_v1_router
from app.core.config import get_settings
from app.core.errors import install_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.packages_path import ensure_packages_on_path
from app.db.session import engine
from app.services.health import check_db, check_redis

ensure_packages_on_path()
configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    log.info("startup", service="opendispatch-api", version="0.1.0")
    yield
    log.info("shutdown", service="opendispatch-api")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="OpenDispatch API",
        version="0.1.0",
        description=(
            "OpenDispatch is an open-source flight planning and dispatch platform. "
            "This API exposes identity, navigation, flight planning, weather, "
            "and document generation endpoints. It is not a substitute for "
            "certified operational control systems."
        ),
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = rid
        structlog.contextvars.bind_contextvars(request_id=rid, method=request.method, path=request.url.path)
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("request_failed")
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["x-request-id"] = rid
        log.info(
            "request",
            status_code=response.status_code,
            duration_ms=round(elapsed_ms, 2),
        )
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )

    install_exception_handlers(app)
    app.include_router(api_v1_router, prefix="/api/v1")

    @app.get("/", include_in_schema=False)
    async def root() -> JSONResponse:
        return JSONResponse(
            {
                "service": "opendispatch-api",
                "version": "0.1.0",
                "docs": "/api/docs",
                "api_root": "/api/v1",
            }
        )

    return app


app = create_app()
