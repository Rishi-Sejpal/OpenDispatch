"""Route parsing and validation schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RouteParseRequest(BaseModel):
    route: str = Field(..., min_length=1, max_length=2000)
    airac_cycle: str | None = None
    departure: str | None = None
    arrival: str | None = None


class RouteLeg(BaseModel):
    sequence: int
    ident: str
    leg_type: str  # AIRWAY or DCT
    airway: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    cumulative_distance_nm: float = 0.0
    segment_distance_nm: float = 0.0
    course_deg: float | None = None
    valid: bool = True
    error: str | None = None


class RouteParseResponse(BaseModel):
    legs: list[RouteLeg]
    total_distance_nm: float
    errors: list[str] = Field(default_factory=list)


class RouteValidationResponse(BaseModel):
    valid: bool
    errors: list[dict] = Field(default_factory=list)
    warnings: list[dict] = Field(default_factory=list)
