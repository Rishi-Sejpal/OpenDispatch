"""Aircraft endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import AircraftRegistration, AircraftType, User
from app.schemas import AircraftRegistrationRead, AircraftTypeRead, AircraftTypeSummary

router = APIRouter()


@router.get("/types", response_model=list[AircraftTypeSummary])
def list_aircraft_types(
    q: str | None = None,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AircraftTypeSummary]:
    stmt = select(AircraftType).order_by(AircraftType.icao_type)
    if q:
        like = f"%{q.upper()}%"
        stmt = stmt.where(AircraftType.icao_type.ilike(like))
    types = list(db.scalars(stmt).all())
    return [AircraftTypeSummary.model_validate(t) for t in types]


@router.get("/types/{icao_type}", response_model=AircraftTypeRead)
def get_aircraft_type(
    icao_type: str,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AircraftTypeRead:
    ac = db.scalar(select(AircraftType).where(AircraftType.icao_type == icao_type.upper()))
    if ac is None:
        raise NotFoundError(f"Aircraft type {icao_type} not found.")
    return AircraftTypeRead.model_validate(ac)


@router.get("/registrations", response_model=list[AircraftRegistrationRead])
def list_registrations(
    organization_id: uuid.UUID | None = None,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AircraftRegistrationRead]:
    stmt = select(AircraftRegistration).order_by(AircraftRegistration.registration)
    if organization_id is not None:
        stmt = stmt.where(AircraftRegistration.organization_id == organization_id)
    regs = list(db.scalars(stmt).all())
    result: list[AircraftRegistrationRead] = []
    for r in regs:
        atype = db.get(AircraftType, r.aircraft_type_id)
        if atype is None:
            continue
        result.append(
            AircraftRegistrationRead(
                id=r.id,
                registration=r.registration,
                nickname=r.nickname,
                aircraft_type=AircraftTypeSummary.model_validate(atype),
                organization_id=r.organization_id,
                active=r.active,
            )
        )
    return result
