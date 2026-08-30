"""Celery worker bootstrap.

Currently we don't use Celery for the planning pipeline (it runs synchronously
in the request), but the worker is configured to handle future async jobs
such as AIRAC imports and PDF re-renders.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()
celery_app = Celery(
    "opendispatch",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    broker_connection_retry_on_startup=True,
)
