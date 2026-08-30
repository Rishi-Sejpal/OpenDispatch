"""Auth endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import ConflictError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models import User, UserSession
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.services import audit, user_service

router = APIRouter()


def _client_info(request: Request, user_agent: str | None) -> tuple[str | None, str | None]:
    return (request.client.host if request.client else None, user_agent)


@router.post("/register", response_model=UserResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    user = user_service.create_user(
        db,
        email=payload.email,
        password=payload.password,
        full_name=payload.full_name,
    )
    if payload.organization_name:
        user_service.create_default_organization(db, user, payload.organization_name)
    audit.log_event(db, action="user.registered", actor_user_id=user.id, target_type="user", target_id=str(user.id))
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    request: Request,
    user_agent: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = user_service.authenticate(db, payload.email, payload.password)
    ip, ua = _client_info(request, user_agent)
    tokens = user_service.issue_tokens(db, user, user_agent=ua, ip_address=ip)
    audit.log_event(
        db,
        action="user.login",
        actor_user_id=user.id,
        target_type="user",
        target_id=str(user.id),
        ip_address=ip,
        user_agent=ua,
    )
    db.commit()
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    refresh_token: str,
    request: Request,
    user_agent: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> TokenResponse:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise UnauthorizedError("Wrong token type.")
    jti = payload.get("jti")
    sess = db.scalar(select(UserSession).where(UserSession.refresh_jti == jti))
    if sess is None or sess.revoked_at is not None:
        raise UnauthorizedError("Refresh token revoked.")
    user = db.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")
    sess.revoked_at = __import__("datetime").datetime.now(tz=__import__("datetime").timezone.utc)
    ip, ua = _client_info(request, user_agent)
    tokens = user_service.issue_tokens(db, user, user_agent=ua, ip_address=ip)
    db.commit()
    return TokenResponse(**tokens)


@router.post("/logout", status_code=204, response_class=Response)
def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    # Revoke all sessions for this user (simple default)
    from datetime import datetime, timezone

    for sess in db.scalars(select(UserSession).where(UserSession.user_id == user.id)).all():
        sess.revoked_at = datetime.now(tz=timezone.utc)
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
