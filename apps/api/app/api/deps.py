"""FastAPI dependency functions."""

from __future__ import annotations

import uuid

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ForbiddenError, UnauthorizedError
from app.core.security import decode_token, get_request_id, new_request_id
from app.db.session import get_db
from app.models import Organization, OrganizationMember, User, UserRole
from app.services import user_service


def require_request_id(request: Request) -> str:
    rid = request.headers.get("x-request-id") or new_request_id()
    request.state.request_id = rid
    return rid


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing or invalid Authorization header.")
    return authorization.split(" ", 1)[1].strip()


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer(authorization)
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise UnauthorizedError("Wrong token type.")
    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedError("Token missing subject.")
    try:
        user_id = uuid.UUID(sub)
    except (ValueError, TypeError) as exc:
        raise UnauthorizedError("Invalid token subject.") from exc
    return user_service.get_user_by_id(db, user_id)


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
