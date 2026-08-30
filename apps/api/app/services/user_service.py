"""User service.

Passwords and refresh tokens are managed by Supabase. This module only
contains the application-level helpers we still need: looking up a user by
id, creating the first organization for a new user, and listing the
organizations a user belongs to.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models import Organization, OrganizationMember, User, UserRole
from app.services import audit


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower()))


def create_default_organization(
    db: Session, user: User, organization_name: str
) -> Organization:
    slug = (organization_name.lower().replace(" ", "-") or f"org-{user.id.hex[:8]}")[:80]
    base = slug
    counter = 1
    while db.scalar(select(Organization).where(Organization.slug == slug)):
        slug = f"{base}-{counter}"
        counter += 1
    org = Organization(name=organization_name, slug=slug)
    db.add(org)
    db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=UserRole.OWNER))
    db.flush()
    audit.log_event(
        db,
        action="organization.created",
        actor_user_id=user.id,
        organization_id=org.id,
        target_type="organization",
        target_id=str(org.id),
    )
    return org


def list_user_organizations(db: Session, user: User) -> list[Organization]:
    return list(
        db.scalars(
            select(Organization)
            .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
            .where(OrganizationMember.user_id == user.id)
        ).all()
    )
