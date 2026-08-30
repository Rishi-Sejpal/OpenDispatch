"""Pydantic schemas (request/response models) for the API."""

from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.schemas.common import HealthResponse, PageMeta
from app.schemas.flight_plan import (
    FlightPlanCreate,
    FlightPlanRead,
    FlightPlanSummary,
    FlightPlanUpdate,
    FlightPlanCalculateRequest,
    FlightPlanDispatchRequest,
    WarningRead,
)
from app.schemas.navigation import (
    AirportRead,
    AirportSummary,
    ProcedureRead,
    ProcedureSummary,
    RunwayRead,
    AiracCycleRead,
)
from app.schemas.aircraft import (
    AircraftTypeRead,
    AircraftTypeSummary,
    AircraftRegistrationRead,
)
from app.schemas.route import RouteParseRequest, RouteParseResponse, RouteLeg, RouteValidationResponse
from app.schemas.weather import WeatherRead, WeatherSummary

__all__ = [
    "LoginRequest",
    "RegisterRequest",
    "TokenResponse",
    "UserResponse",
    "HealthResponse",
    "PageMeta",
    "FlightPlanCreate",
    "FlightPlanRead",
    "FlightPlanSummary",
    "FlightPlanUpdate",
    "FlightPlanCalculateRequest",
    "FlightPlanDispatchRequest",
    "WarningRead",
    "AirportRead",
    "AirportSummary",
    "ProcedureRead",
    "ProcedureSummary",
    "RunwayRead",
    "AiracCycleRead",
    "AircraftTypeRead",
    "AircraftTypeSummary",
    "AircraftRegistrationRead",
    "RouteParseRequest",
    "RouteParseResponse",
    "RouteLeg",
    "RouteValidationResponse",
    "WeatherRead",
    "WeatherSummary",
]
