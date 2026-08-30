"""Shared test fixtures."""

from __future__ import annotations

import os

# Force settings to test-friendly values BEFORE app imports happen anywhere.
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-do-not-use-in-prod-1234567890")
os.environ.setdefault(
    "SUPABASE_JWT_SECRET", "test-supabase-jwt-secret-do-not-use-in-production"
)
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://opendispatch:opendispatch@db:5432/opendispatch")
os.environ.setdefault("REDIS_URL", "redis://redis:6379/0")
