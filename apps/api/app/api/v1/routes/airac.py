"""AIRAC cycle endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AiracCycle, User
from app.schemas import AiracCycleRead

router = APIRouter()


@router.get("/cycles", response_model=list[AiracCycleRead])
def list_cycles(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AiracCycleRead]:
    cycles = list(db.scalars(select(AiracCycle).order_by(AiracCycle.effective_from.desc())).all())
    return [AiracCycleRead.model_validate(c) for c in cycles]


@router.get("/cycles/active", response_model=AiracCycleRead | None)
def get_active_cycle(
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiracCycleRead | None:
    cycle = db.scalar(select(AiracCycle).where(AiracCycle.is_active.is_(True)))
    if cycle is None:
        return None
    return AiracCycleRead.model_validate(cycle)
