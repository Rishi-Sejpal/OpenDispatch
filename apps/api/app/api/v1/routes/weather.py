"""Weather endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User, WeatherReport
from app.schemas import WeatherRead, WeatherSummary
from app.services import weather as weather_svc

router = APIRouter()


@router.get("/{icao}/metar", response_model=WeatherRead)
def get_metar(
    icao: str,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeatherRead:
    provider = weather_svc.get_default_provider()
    m = provider.get_metar(icao.upper())
    t = provider.get_taf(icao.upper())
    return WeatherRead(
        id=__import__("uuid").uuid4(),
        airport_icao=m.icao,
        observed_at=m.observed_at,
        valid_from=t.valid_from,
        valid_to=t.valid_to,
        source=provider.name,
        metar_raw=m.raw,
        taf_raw=t.raw,
        parsed={"metar": m.to_dict(), "taf": t.to_dict()},
    )


@router.get("/reports", response_model=list[WeatherSummary])
def list_reports(
    airport: str | None = None,
    limit: int = 20,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WeatherSummary]:
    stmt = select(WeatherReport).order_by(WeatherReport.observed_at.desc()).limit(limit)
    if airport:
        stmt = stmt.where(WeatherReport.airport_icao == airport.upper())
    return [WeatherSummary.model_validate(r) for r in db.scalars(stmt).all()]
