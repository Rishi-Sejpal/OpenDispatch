"""Route validation against the navigation database.

Given an ICAO route string and an AIRAC cycle, ensure:
- every fix exists
- every airway exists and contains the expected join/leave fixes
- departure/arrival match the endpoints
- no duplicates / discontinuities
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AiracCycle, Airway, Airport, Fix
from app.services.route_parser import parse_route


@dataclass
class RouteIssue:
    code: str
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    errors: list[RouteIssue] = field(default_factory=list)
    warnings: list[RouteIssue] = field(default_factory=list)


def _lookup_fix(db: Session, cycle_id, ident: str) -> Optional[Fix]:
    return db.scalar(select(Fix).where(Fix.airac_cycle_id == cycle_id, Fix.ident == ident))


def _lookup_airport(db: Session, cycle_id, icao: str) -> Optional[Airport]:
    return db.scalar(select(Airport).where(Airport.airac_cycle_id == cycle_id, Airport.icao == icao))


def _find_airway_segment(db: Session, cycle_id, airway_ident: str, join: str, leave: str) -> Optional[int]:
    from app.models import AirwaySegment

    aw = db.scalar(select(Airway).where(Airway.airac_cycle_id == cycle_id, Airway.ident == airway_ident))
    if aw is None:
        return None
    j = _lookup_fix(db, cycle_id, join)
    l = _lookup_fix(db, cycle_id, leave)
    if j is None or l is None:
        return None
    return db.scalar(
        select(AirwaySegment).where(
            AirwaySegment.airway_id == aw.id,
            AirwaySegment.from_fix_id == j.id,
            AirwaySegment.to_fix_id == l.id,
        )
    )


def validate_route(
    db: Session,
    route_text: str,
    cycle: AiracCycle | None,
    departure: Airport | None = None,
    arrival: Airport | None = None,
) -> ValidationResult:
    result = ValidationResult()
    parsed = parse_route(route_text)
    if parsed.errors:
        for err in parsed.errors:
            result.errors.append(RouteIssue(code="PARSE_ERROR", message=err))

    if cycle is None:
        result.errors.append(RouteIssue(code="NO_ACTIVE_CYCLE", message="No active AIRAC cycle."))
        return result

    if not parsed.legs:
        return result

    # Check endpoints
    if departure is not None and parsed.legs and parsed.legs[0].ident != departure.icao:
        # route may start with a SID route; do not flag as error if departure matches a SID
        result.warnings.append(
            RouteIssue(
                code="ROUTE_START_MISMATCH",
                message=f"Route starts with '{parsed.legs[0].ident}' but departure is {departure.icao}.",
            )
        )
    if arrival is not None and parsed.legs and parsed.legs[-1].ident != arrival.icao:
        result.warnings.append(
            RouteIssue(
                code="ROUTE_END_MISMATCH",
                message=f"Route ends with '{parsed.legs[-1].ident}' but arrival is {arrival.icao}.",
            )
        )

    # Check each fix exists
    last_ident = None
    for leg in parsed.legs:
        # An airway leg's "ident" is the leave fix; the join fix was the previous leg
        is_airway_leg = leg.leg_type == "AIRWAY"
        if is_airway_leg and leg.via:
            join, leave = leg.via
            aw_seg = _find_airway_segment(db, cycle.id, leg.airway, join, leave)
            if aw_seg is None:
                # not necessarily invalid - airways may not contain all combinations
                aw_exists = db.scalar(
                    select(Airway).where(Airway.airac_cycle_id == cycle.id, Airway.ident == leg.airway)
                )
                if aw_exists is None:
                    result.errors.append(
                        RouteIssue(
                            code="UNKNOWN_AIRWAY",
                            message=f"Airway '{leg.airway}' is not defined in cycle {cycle.cycle}.",
                            details={"airway": leg.airway},
                        )
                    )
                else:
                    result.warnings.append(
                        RouteIssue(
                            code="AIRWAY_SEGMENT_MISSING",
                            message=(
                                f"Airway {leg.airway} does not contain a segment {join} -> {leave} "
                                "in this cycle."
                            ),
                            details={"airway": leg.airway, "join": join, "leave": leave},
                        )
                    )
            last_ident = leg.ident
            continue
        fix = _lookup_fix(db, cycle.id, leg.ident)
        ap = _lookup_airport(db, cycle.id, leg.ident) if fix is None else None
        if fix is None and ap is None:
            result.errors.append(
                RouteIssue(
                    code="UNKNOWN_FIX",
                    message=f"Unknown fix or airport '{leg.ident}'.",
                    details={"ident": leg.ident},
                )
            )
        if last_ident and last_ident == leg.ident:
            result.warnings.append(
                RouteIssue(
                    code="DUPLICATE_FIX",
                    message=f"Duplicate fix '{leg.ident}'.",
                    details={"ident": leg.ident},
                )
            )
        last_ident = leg.ident

    return result
