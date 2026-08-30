"""Weather schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WeatherSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    airport_icao: str
    observed_at: datetime
    valid_from: datetime
    valid_to: datetime
    source: str


class WeatherRead(WeatherSummary):
    metar_raw: str | None = None
    taf_raw: str | None = None
    parsed: dict[str, Any] = Field(default_factory=dict)
