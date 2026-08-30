"""Route parsing and validation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import AiracCycle, Airport, Fix, User
from app.schemas import RouteParseRequest, RouteParseResponse, RouteLeg, RouteValidationResponse
from app.services.route_parser import parse_route
from app.services.route_validator import validate_route
from aviation_geometry import LatLon, great_circle_distance, initial_bearing

router = APIRouter()


def _active_cycle(db: Session) -> AiracCycle | None:
    return db.scalar(select(AiracCycle).where(AiracCycle.is_active.is_(True)))


@router.post("/parse", response_model=RouteParseResponse)
def parse(payload: RouteParseRequest, _user: User = Depends(get_current_user)) -> RouteParseResponse:
    result = parse_route(payload.route)
    return RouteParseResponse(
        legs=[
            RouteLeg(
                sequence=l.sequence,
                ident=l.ident,
                leg_type=l.leg_type,
                airway=l.airway,
            )
            for l in result.legs
        ],
        total_distance_nm=0.0,
        errors=result.errors,
    )


@router.post("/validate", response_model=RouteValidationResponse)
def validate(
    payload: RouteParseRequest,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RouteValidationResponse:
    cycle = _active_cycle(db)
    departure = None
    arrival = None
    if payload.departure:
        if cycle is not None:
            departure = db.scalar(
                select(Airport).where(Airport.airac_cycle_id == cycle.id, Airport.icao == payload.departure.upper())
            )
    if payload.arrival:
        if cycle is not None:
            arrival = db.scalar(
                select(Airport).where(Airport.airac_cycle_id == cycle.id, Airport.icao == payload.arrival.upper())
            )
    result = validate_route(db, payload.route, cycle, departure, arrival)
    return RouteValidationResponse(
        valid=len(result.errors) == 0,
        errors=[{"code": e.code, "message": e.message, "details": e.details} for e in result.errors],
        warnings=[{"code": w.code, "message": w.message, "details": w.details} for w in result.warnings],
    )


@router.post("/geometry", response_model=RouteParseResponse)
def geometry(
    payload: RouteParseRequest,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RouteParseResponse:
    """Parse the route and compute geometry for each leg using the active cycle's fix database."""
    cycle = _active_cycle(db)
    parsed = parse_route(payload.route)

    legs_out: list[RouteLeg] = []
    cumulative = 0.0
    prev_position: tuple[float, float] | None = None
    errors = list(parsed.errors)

    for leg in parsed.legs:
        fix = None
        if cycle is not None:
            fix = db.scalar(select(Fix).where(Fix.airac_cycle_id == cycle.id, Fix.ident == leg.ident))
        if fix is None:
            # try treating as airport
            ap = None
            if cycle is not None:
                ap = db.scalar(
                    select(Airport).where(Airport.airac_cycle_id == cycle.id, Airport.icao == leg.ident)
                )
            if ap is not None:
                pos = (ap.latitude, ap.longitude)
            else:
                pos = None
        else:
            pos = (fix.latitude, fix.longitude)

        seg_dist = 0.0
        course = None
        if pos is not None and prev_position is not None:
            seg_dist = great_circle_distance(LatLon(*prev_position), LatLon(*pos))
            course = initial_bearing(LatLon(*prev_position), LatLon(*pos))
            cumulative += seg_dist

        legs_out.append(
            RouteLeg(
                sequence=leg.sequence,
                ident=leg.ident,
                leg_type=leg.leg_type,
                airway=leg.airway,
                latitude=pos[0] if pos else None,
                longitude=pos[1] if pos else None,
                cumulative_distance_nm=round(cumulative, 2),
                segment_distance_nm=round(seg_dist, 2),
                course_deg=round(course, 1) if course is not None else None,
                valid=pos is not None,
            )
        )
        if pos is None:
            errors.append(f"Unknown fix '{leg.ident}'.")
        if pos is not None:
            prev_position = pos

    return RouteParseResponse(
        legs=legs_out,
        total_distance_nm=round(cumulative, 2),
        errors=errors,
    )
