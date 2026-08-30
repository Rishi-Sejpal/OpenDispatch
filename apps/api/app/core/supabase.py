"""Supabase client and helpers.

Authentication is delegated to Supabase Auth. The backend uses two clients:

- ``supabase_admin``: a service-role client that can read and write any row
  in the database and call admin endpoints (used by the seed to create the
  default superuser).
- ``verify_supabase_jwt``: a stateless JWT verifier that the FastAPI
  dependency layer uses to authenticate the bearer token in
  ``Authorization: Bearer ...`` headers.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from jose import JWTError, jwt
from supabase import Client, create_client

from app.core.config import get_settings
from app.core.errors import UnauthorizedError


@lru_cache
def get_supabase_admin() -> Client:
    """Return a Supabase client authenticated with the service-role key.

    Use sparingly: this client bypasses Row Level Security and has full
    administrative power over the project.
    """
    s = get_settings()
    return create_client(s.supabase_url, s.supabase_service_role_key)


def verify_supabase_jwt(token: str) -> dict[str, Any]:
    """Verify a Supabase-issued access token (HS256) and return its claims.

    Raises ``UnauthorizedError`` if the token is invalid, expired, or was not
    issued for an authenticated user.
    """
    s = get_settings()
    if s.supabase_jwt_secret.startswith("[YOUR-"):
        raise UnauthorizedError("Supabase JWT secret is not configured.")
    try:
        claims = jwt.decode(
            token,
            s.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as exc:
        raise UnauthorizedError(
            "Invalid or expired token.", details={"reason": str(exc)}
        ) from exc
    if claims.get("role") != "authenticated":
        raise UnauthorizedError("Token role is not authenticated.")
    return claims
