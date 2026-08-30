"""Airports endpoints."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import Airport, Runway, User
from app.schemas import AirportRead, AirportSummary

router = APIRouter()


@router.get("", response_model=list[AirportSummary])
def list_airports(
    q: str | None = Query(default=None, description="Search by ICAO/IATA/name/city"),
    airac_cycle: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AirportSummary]:
    stmt = select(Airport)
    if airac_cycle:
        from app.models import AiracCycle

        cycle = db.scalar(select(AiracCycle).where(AiracCycle.cycle == airac_cycle))
        if cycle is None:
            return []
        stmt = stmt.where(Airport.airac_cycle_id == cycle.id)
    else:
        # default to active cycle
        from app.models import AiracCycle

        active = db.scalar(select(AiracCycle).where(AiracCycle.is_active.is_(True)))
        if active is None:
            active = db.scalar(select(AiracCycle).order_by(AiracCycle.effective_from.desc()))
        if active is not None:
            stmt = stmt.where(Airport.airac_cycle_id == active.id)
    if q:
        like = f"%{q.upper()}%"
        stmt = stmt.where(
            or_(
                Airport.icao.ilike(like),
                Airport.iata.ilike(like),
                Airport.name.ilike(like),
                Airport.city.ilike(like),
            )
        )
    stmt = stmt.order_by(Airport.icao).limit(limit)
    airports = list(db.scalars(stmt).all())
    return [AirportSummary.model_validate(a) for a in airports]


@router.get("/{icao}", response_model=AirportRead)
def get_airport(
    icao: str,
    airac_cycle: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AirportRead:
    icao = icao.upper()
    stmt = select(Airport).where(Airport.icao == icao).options(selectinload(Airport.runways))
    if airac_cycle:
        from app.models import AiracCycle

        cycle = db.scalar(select(AiracCycle).where(AiracCycle.cycle == airac_cycle))
        if cycle is None:
            raise NotFoundError(f"AIRAC cycle {airac_cycle} not found.")
        stmt = stmt.where(Airport.airac_cycle_id == cycle.id)
    else:
        from app.models import AiracCycle

        active = db.scalar(select(AiracCycle).where(AiracCycle.is_active.is_(True)))
        if active is None:
            active = db.scalar(select(AiracCycle).order_by(AiracCycle.effective_from.desc()))
        if active is not None:
            stmt = stmt.where(Airport.airac_cycle_id == active.id)
    airport = db.scalar(stmt)
    if airport is None:
        raise NotFoundError(f"Airport {icao} not found.")
    return AirportRead.model_validate(airport)
