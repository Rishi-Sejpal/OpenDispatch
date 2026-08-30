"""Organization endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_membership
from app.core.errors import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models import Organization, OrganizationMember, User, UserRole
from app.schemas import UserResponse

router = APIRouter()


@router.get("")
def list_my_organizations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    orgs = db.execute(
        select(Organization, OrganizationMember.role)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .where(OrganizationMember.user_id == user.id)
    ).all()
    return [
        {
            "id": str(org.id),
            "name": org.name,
            "slug": org.slug,
            "role": role.value,
            "icao_code": org.icao_code,
            "iata_code": org.iata_code,
        }
        for org, role in orgs
    ]


@router.get("/{organization_id}/members")
def list_members(
    organization_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    membership = get_membership(db, user, organization_id)
    if membership.role not in {UserRole.OWNER, UserRole.ADMIN, UserRole.DISPATCHER}:
        raise ForbiddenError("Requires dispatcher role or higher.")
    members = db.execute(
        select(User, OrganizationMember.role)
        .join(OrganizationMember, OrganizationMember.user_id == User.id)
        .where(OrganizationMember.organization_id == organization_id)
    ).all()
    return [
        {"id": str(u.id), "email": u.email, "full_name": u.full_name, "role": role.value}
        for u, role in members
    ]
