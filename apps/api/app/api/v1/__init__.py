"""API v1 router aggregation."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import (
    airac,
    aircraft,
    airports,
    auth,
    flight_plans,
    health,
    navigation,
    organizations,
    route,
    users,
    weather,
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router, tags=["health"])
api_v1_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(users.router, prefix="/users", tags=["users"])
api_v1_router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
api_v1_router.include_router(airports.router, prefix="/airports", tags=["airports"])
api_v1_router.include_router(navigation.router, prefix="/navigation", tags=["navigation"])
api_v1_router.include_router(airac.router, prefix="/airac", tags=["airac"])
api_v1_router.include_router(aircraft.router, prefix="/aircraft", tags=["aircraft"])
api_v1_router.include_router(weather.router, prefix="/weather", tags=["weather"])
api_v1_router.include_router(route.router, prefix="/routes", tags=["routes"])
api_v1_router.include_router(flight_plans.router, prefix="/flight-plans", tags=["flight-plans"])
