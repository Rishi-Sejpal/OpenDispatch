"""User and auth service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import Organization, OrganizationMember, User, UserRole, UserSession
from app.services import audit


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    is_superuser: bool = False,
) -> User:
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise ConflictError("Email is already registered.", details={"email": email})
    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        is_superuser=is_superuser,
    )
    db.add(user)
    db.flush()
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not user.is_active:
        raise UnauthorizedError("Invalid credentials.")
    if not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid credentials.")
    user.last_login_at = datetime.now(tz=timezone.utc)
    db.flush()
    return user


def issue_tokens(db: Session, user: User, *, user_agent: str | None, ip_address: str | None) -> dict[str, Any]:
    access, ttl = create_access_token(subject=str(user.id), claims={"email": user.email})
    refresh, _ = create_refresh_token(subject=str(user.id))
    refresh_payload = decode_token(refresh)
    sess = UserSession(
        user_id=user.id,
        refresh_jti=refresh_payload["jti"],
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=datetime.fromtimestamp(refresh_payload["exp"], tz=timezone.utc),
    )
    db.add(sess)
    db.flush()
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": ttl,
    }


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


def create_default_organization(db: Session, user: User, organization_name: str) -> Organization:
    slug = (organization_name.lower().replace(" ", "-") or f"org-{user.id.hex[:8]}")[:80]
    base = slug
    counter = 1
    while db.scalar(select(Organization).where(Organization.slug == slug)):
        slug = f"{base}-{counter}"
        counter += 1
    org = Organization(name=organization_name, slug=slug)
    db.add(org)
    db.flush()
    member = OrganizationMember(organization_id=org.id, user_id=user.id, role=UserRole.OWNER)
    db.add(member)
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
