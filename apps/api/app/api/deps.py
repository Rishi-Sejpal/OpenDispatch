"""FastAPI dependency functions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import new_request_id
from app.core.supabase import verify_supabase_jwt
from app.db.session import get_db
from app.models import Organization, OrganizationMember, User, UserRole


def require_request_id(request: Request) -> str:
    rid = request.headers.get("x-request-id") or new_request_id()
    request.state.request_id = rid
    return rid


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header.")
    return authorization.split(" ", 1)[1].strip()


def _upsert_user_from_claims(db: Session, claims: dict) -> User:
    """Provision (or refresh) a local ``users`` row from a verified Supabase
    JWT. The first time a Supabase user calls the API, we create a matching
    row here. Subsequent calls keep the row in sync with the most recent
    email and metadata.
    """
    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise UnauthorizedError("Invalid token subject.") from exc

    user = db.get(User, user_id)
    email = (claims.get("email") or "").strip().lower()
    metadata = claims.get("user_metadata") or {}
    app_metadata = claims.get("app_metadata") or {}
    full_name = (metadata.get("full_name") or email.split("@")[0] or "User")[:200]
    is_superuser = bool(app_metadata.get("is_superuser"))
    is_email_verified = bool(claims.get("email_verified"))

    if user is None:
        user = User(
            id=user_id,
            email=email,
            full_name=full_name,
            is_superuser=is_superuser,
            is_email_verified=is_email_verified,
        )
        db.add(user)
        db.flush()
    else:
        user.email = email or user.email
        if metadata.get("full_name"):
            user.full_name = (metadata["full_name"])[:200]
        user.is_superuser = is_superuser
        user.is_email_verified = is_email_verified
    user.last_login_at = datetime.now(tz=timezone.utc)
    db.commit()
    return user


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer(authorization)
    claims = verify_supabase_jwt(token)
    return _upsert_user_from_claims(db, claims)


def get_optional_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    if not authorization:
        return None
    try:
        return get_current_user(authorization=authorization, db=db)
    except UnauthorizedError:
        return None


def get_membership(
    db: Session, user: User, organization_id: uuid.UUID
) -> OrganizationMember:
    member = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user.id,
            OrganizationMember.organization_id == organization_id,
        )
    )
    if member is None:
        raise ForbiddenError("Not a member of this organization.")
    return member


def require_role(min_role: UserRole):
    """Dependency factory that requires a minimum role level."""

    role_rank = {
        UserRole.VIEWER: 1,
        UserRole.PILOT: 2,
        UserRole.DISPATCHER: 3,
        UserRole.ADMIN: 4,
        UserRole.OWNER: 5,
    }

    def _checker(
        user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if user.is_superuser:
            return user
        # require admin or owner globally (no org context here)
        member = db.scalar(
            select(OrganizationMember).where(OrganizationMember.user_id == user.id)
        )
        if member is None or role_rank.get(member.role, 0) < role_rank[min_role]:
            raise ForbiddenError(f"Requires role >= {min_role.value}.")
        return user

    return _checker


def current_user_context(
    user: User = Depends(get_current_user),
) -> User:
    return user
