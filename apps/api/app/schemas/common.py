"""Common schema utilities."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    db: bool
    redis: bool
    version: str


class PageMeta(BaseModel):
    total: int
    page: int
    page_size: int
