"""Auth endpoints.

Supabase owns credentials and issues access tokens. The backend only verifies
Supabase-issued JWTs and exposes a couple of convenience endpoints for the
frontend to bootstrap a workspace and fetch the current user.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import ConflictError
from app.db.session import get_db
from app.models import Organization, OrganizationMember, User, UserRole
from app.schemas import BootstrapOrganizationRequest, UserResponse
from app.services import audit

router = APIRouter()


@router.post("/bootstrap", response_model=UserResponse)
def bootstrap_organization(
    payload: BootstrapOrganizationRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Create the caller's first organization and add them as owner.

    Called by the frontend right after a successful Supabase sign-up so that
    subsequent calls (flight plans, aircraft, etc.) have an organization to
    attach to. Idempotent: if the user already belongs to an organization the
    first one is returned and no new organization is created.
    """
    existing = db.scalar(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    )
    if existing is not None:
        return user

    base_slug = (
        payload.organization_name.lower().replace(" ", "-") or f"org-{user.id.hex[:8]}"
    )[:80]
    slug = base_slug
    counter = 1
    while db.scalar(select(Organization).where(Organization.slug == slug)):
        slug = f"{base_slug}-{counter}"
        counter += 1

    org = Organization(
        name=payload.organization_name,
        slug=slug,
        default_fuel_policy={
            "taxi_kg": 200,
            "contingency_percent": 0.05,
            "final_reserve_minutes": 30,
            "extra_kg": 0,
            "additional_kg": 0,
        },
    )
    db.add(org)
    db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=UserRole.OWNER))
    audit.log_event(
        db,
        action="organization.created",
        actor_user_id=user.id,
        organization_id=org.id,
        target_type="organization",
        target_id=str(org.id),
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/logout", status_code=204, response_class=Response)
def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Record a logout event. The actual session is cleared client-side via
    ``supabase.auth.signOut()``; this endpoint is here so the audit trail
    matches the previous behavior.
    """
    audit.log_event(
        db,
        action="user.logout",
        actor_user_id=user.id,
        target_type="user",
        target_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return Response(status_code=204)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> User:
    return user
