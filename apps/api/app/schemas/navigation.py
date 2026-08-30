"""Navigation schemas (airports, runways, procedures, AIRAC)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AiracCycleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    cycle: str
    effective_from: datetime
    effective_to: datetime
    source: str
    version: str
    import_status: str
    is_active: bool
    notes: str | None = None


class RunwayRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    ident: str
    reciprocal_ident: str | None = None
    length_ft: float
    width_ft: float
    heading_deg: float
    surface: str
    elevation_ft: float
    ils_available: bool
    ils_category: str | None = None
    lighting: bool


class AirportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    icao: str
    iata: str | None = None
    name: str
    city: str | None = None
    country: str | None = None
    region: str | None = None
    latitude: float
    longitude: float
    elevation_ft: float
    has_procedures: bool


class AirportRead(AirportSummary):
    magnetic_variation: float
    timezone: str
    runways: list[RunwayRead] = Field(default_factory=list)


class ProcedureSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    airport_icao: str | None = None
    name: str
    kind: str
    runway_ident: str | None = None


class ProcedureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    airport_icao: str
    name: str
    kind: str
    runway_ident: str | None = None
    legs: list[dict] = Field(default_factory=list)
    transitions: list[str] = Field(default_factory=list)
