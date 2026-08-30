"""Aircraft-related schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class AircraftTypeSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    icao_type: str
    manufacturer: str
    model: str
    variant: str | None = None
    wake_category: str
    engine_type: str
    engines: int
    mtow_kg: float
    passenger_capacity: int


class AircraftTypeRead(AircraftTypeSummary):
    mlw_kg: float
    mzfw_kg: float
    oew_kg: float
    fuel_capacity_kg: float
    cargo_capacity_kg: float
    max_altitude_ft: int
    cruise_mach: float
    cruise_tas_kts: int
    approach_speed_kts: int
    initial_climb_alt_ft: int
    initial_cruise_alt_ft: int
    notes: str | None = None


class AircraftRegistrationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    registration: str
    nickname: str | None = None
    aircraft_type: AircraftTypeSummary
    organization_id: uuid.UUID
    active: bool
