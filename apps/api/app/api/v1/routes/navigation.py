"""Navigation endpoints (procedures, fixes, airways)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import (
    AiracCycle,
    Airport,
    Fix,
    Procedure,
    ProcedureKind,
    ProcedureLeg,
    ProcedureTransition,
    User,
)
from app.schemas import ProcedureRead, ProcedureSummary

router = APIRouter()


def _active_cycle(db: Session) -> AiracCycle | None:
    return db.scalar(select(AiracCycle).where(AiracCycle.is_active.is_(True)))


@router.get("/fixes")
def list_fixes(
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    cycle = _active_cycle(db)
    if cycle is None:
        return []
    stmt = select(Fix).where(Fix.airac_cycle_id == cycle.id)
    if q:
        like = f"%{q.upper()}%"
        stmt = stmt.where(Fix.ident.ilike(like))
    stmt = stmt.order_by(Fix.ident).limit(limit)
    return [
        {
            "id": str(f.id),
            "ident": f.ident,
            "name": f.name,
            "role": f.role.value if hasattr(f.role, "value") else f.role,
            "latitude": f.latitude,
            "longitude": f.longitude,
        }
        for f in db.scalars(stmt).all()
    ]


@router.get("/procedures", response_model=list[ProcedureSummary])
def list_procedures(
    airport: str = Query(...),
    kind: str | None = Query(default=None),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProcedureSummary]:
    cycle = _active_cycle(db)
    if cycle is None:
        return []
    ap = db.scalar(select(Airport).where(Airport.airac_cycle_id == cycle.id, Airport.icao == airport.upper()))
    if ap is None:
        raise NotFoundError(f"Airport {airport} not found in active cycle.")
    stmt = select(Procedure).where(
        Procedure.airac_cycle_id == cycle.id, Procedure.airport_id == ap.id
    )
    if kind:
        try:
            kind_enum = ProcedureKind(kind.upper())
        except ValueError as exc:
            raise NotFoundError(f"Unknown procedure kind: {kind}") from exc
        stmt = stmt.where(Procedure.kind == kind_enum)
    stmt = stmt.order_by(Procedure.kind, Procedure.name, Procedure.runway_ident)
    return [ProcedureSummary.model_validate(p) for p in db.scalars(stmt).all()]


@router.get("/procedures/{procedure_id}", response_model=ProcedureRead)
def get_procedure(
    procedure_id: uuid.UUID,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProcedureRead:
    proc = db.get(Procedure, procedure_id)
    if proc is None:
        raise NotFoundError("Procedure not found.")
    ap = db.get(Airport, proc.airport_id)
    legs = db.scalars(
        select(ProcedureLeg)
        .where(ProcedureLeg.procedure_id == proc.id)
        .order_by(ProcedureLeg.sequence)
    ).all()
    transitions = list(
        db.scalars(
            select(ProcedureTransition)
            .where(ProcedureTransition.procedure_id == proc.id)
            .order_by(ProcedureTransition.sequence)
        ).all()
    )
    leg_dicts: list[dict[str, Any]] = []
    for leg in legs:
        fix = db.get(Fix, leg.fix_id) if leg.fix_id else None
        leg_dicts.append(
            {
                "sequence": leg.sequence,
                "transition_id": str(leg.transition_id) if leg.transition_id else None,
                "leg_type": leg.leg_type.value if hasattr(leg.leg_type, "value") else leg.leg_type,
                "fix_ident": fix.ident if fix else None,
                "fix_latitude": fix.latitude if fix else None,
                "fix_longitude": fix.longitude if fix else None,
                "course_deg": leg.course_deg,
                "distance_nm": leg.distance_nm,
                "altitude_ft": leg.altitude_ft,
                "speed_kts": leg.speed_kts,
                "fly_over": leg.fly_over,
                "remarks": leg.remarks,
            }
        )
    return ProcedureRead(
        id=proc.id,
        airport_icao=ap.icao if ap else "?",
        name=proc.name,
        kind=proc.kind.value if hasattr(proc.kind, "value") else proc.kind,
        runway_ident=proc.runway_ident,
        legs=leg_dicts,
        transitions=[t.name for t in transitions],
    )
