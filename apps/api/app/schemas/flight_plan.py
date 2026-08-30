"""Flight plan schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FlightPlanCreate(BaseModel):
    departure_icao: str = Field(..., min_length=3, max_length=8)
    arrival_icao: str = Field(..., min_length=3, max_length=8)
    alternate_icaos: list[str] = Field(default_factory=list)
    aircraft_type_id: uuid.UUID | None = None
    aircraft_registration_id: uuid.UUID | None = None
    passengers: int = 0
    cargo_kg: float = 0.0
    route_text: str = ""
    departure_runway_ident: str | None = None
    arrival_runway_ident: str | None = None
    sid_id: uuid.UUID | None = None
    star_id: uuid.UUID | None = None
    approach_id: uuid.UUID | None = None
    cruise_altitude_ft: int = 35000
    cost_index: int = 30
    fuel_policy: dict[str, Any] = Field(default_factory=dict)
    scheduled_off_block: datetime | None = None
    callsign: str | None = None
    flight_number: str | None = None


class FlightPlanUpdate(BaseModel):
    departure_icao: str | None = None
    arrival_icao: str | None = None
    alternate_icaos: list[str] | None = None
    aircraft_type_id: uuid.UUID | None = None
    aircraft_registration_id: uuid.UUID | None = None
    passengers: int | None = None
    cargo_kg: float | None = None
    route_text: str | None = None
    departure_runway_ident: str | None = None
    arrival_runway_ident: str | None = None
    sid_id: uuid.UUID | None = None
    star_id: uuid.UUID | None = None
    approach_id: uuid.UUID | None = None
    cruise_altitude_ft: int | None = None
    cost_index: int | None = None
    fuel_policy: dict[str, Any] | None = None
    scheduled_off_block: datetime | None = None
    callsign: str | None = None
    flight_number: str | None = None


class FlightPlanCalculateRequest(BaseModel):
    force: bool = False


class FlightPlanDispatchRequest(BaseModel):
    confirm: bool = True


class WarningRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    severity: str
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class FlightPlanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: str
    departure_icao: str
    arrival_icao: str
    alternate_icaos: list[str]
    aircraft_registration: str | None = None
    aircraft_type_icao: str | None = None
    callsign: str | None = None
    scheduled_off_block: datetime | None = None
    created_at: datetime
    updated_at: datetime


class FlightPlanRead(FlightPlanSummary):
    route_text: str
    departure_runway_ident: str | None = None
    arrival_runway_ident: str | None = None
    sid_id: uuid.UUID | None = None
    star_id: uuid.UUID | None = None
    approach_id: uuid.UUID | None = None
    passengers: int
    cargo_kg: float
    payload_kg: float
    cruise_altitude_ft: int
    cost_index: int
    fuel_policy: dict[str, Any]
    airac_cycle: str
    calculation_engine_version: str
    aircraft_performance_version: str | None = None
    dispatched_at: datetime | None = None
    legs: list[dict[str, Any]] = Field(default_factory=list)
    calculation: dict[str, Any] | None = None
    fuel: dict[str, Any] | None = None
    weights: dict[str, Any] | None = None
    warnings: list[WarningRead] = Field(default_factory=list)
    documents: list[dict[str, Any]] = Field(default_factory=list)
