"""Background tasks (Celery)."""

from __future__ import annotations

from app.worker import celery_app


@celery_app.task(name="opendispatch.healthcheck")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
