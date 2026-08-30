"""Auth-related schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class BootstrapOrganizationRequest(BaseModel):
    """Create the caller's first organization and add them as owner.

    Called once by the frontend after the user signs up via Supabase Auth,
    so the rest of the API has an organization to attach flight plans to.
    """

    organization_name: str = Field(..., min_length=1, max_length=200)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    is_active: bool
    is_superuser: bool
    is_email_verified: bool
    created_at: datetime
    last_login_at: datetime | None = None
