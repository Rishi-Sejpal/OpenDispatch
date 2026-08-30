"""Flight planning pipeline.

This is the heart of OpenDispatch. Given a draft flight plan, it:

1. Loads AIRAC cycle, airports, aircraft, procedures, route.
2. Validates the route.
3. Computes geometry.
4. Loads weather.
5. Computes aircraft performance.
6. Computes trip / alternate / reserve fuel.
7. Computes weight & balance.
8. Generates navigation log legs.
9. Validates limits and emits warnings.
10. Persists calculation outputs.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models import (
    AircraftRegistration,
    AircraftType,
    AiracCycle,
    Airport,
    Fix,
    FlightPlan,
    FlightPlanCalculation,
    FlightPlanFuel,
    FlightPlanLeg,
    FlightPlanStatus,
    FlightPlanWarning,
    Procedure,
    ProcedureKind,
    Runway,
    WeatherReport,
)
from app.services import aircraft_performance as perf
from app.services import fuel as fuel_svc
from app.services import weather as weather_svc
from app.services.route_parser import parse_route
from aviation_geometry import LatLon, great_circle_distance, initial_bearing
from aviation_units import isa_temp_at_altitude


@dataclass
class PlanInputs:
    flight_plan: FlightPlan
    cycle: AiracCycle
    departure: Airport
    arrival: Airport
    alternates: list[Airport] = field(default_factory=list)
    aircraft_type: AircraftType | None = None
    registration: AircraftRegistration | None = None


def _aircraft_type_for_plan(db: Session, plan: FlightPlan) -> AircraftType | None:
    if plan.aircraft_type_id is not None:
        return db.get(AircraftType, plan.aircraft_type_id)
    if plan.aircraft_registration_id is not None:
        reg = db.get(AircraftRegistration, plan.aircraft_registration_id)
        if reg is not None:
            return db.get(AircraftType, reg.aircraft_type_id)
    return None


def _airport(db: Session, cycle_id: uuid.UUID, icao: str) -> Airport:
    ap = db.scalar(select(Airport).where(Airport.airac_cycle_id == cycle_id, Airport.icao == icao.upper()))
    if ap is None:
        raise NotFoundError(f"Airport {icao} not found in cycle.")
    return ap


def _resolve_alternates(
    db: Session, cycle_id: uuid.UUID, primary: Airport, requested: list[str]
) -> list[Airport]:
    out: list[Airport] = []
    for icao in requested:
        ap = db.scalar(
            select(Airport).where(Airport.airac_cycle_id == cycle_id, Airport.icao == icao.upper())
        )
        if ap is not None:
            out.append(ap)
    # Automatic fallback: pick the closest airport with a runway >= 6000ft
    if not out:
        candidates = list(
            db.scalars(
                select(Airport).where(Airport.airac_cycle_id == cycle_id, Airport.icao != primary.icao)
            ).all()
        )
        scored: list[tuple[float, Airport]] = []
        for c in candidates:
            d = great_circle_distance(
                LatLon(primary.latitude, primary.longitude), LatLon(c.latitude, c.longitude)
            )
            scored.append((d, c))
        scored.sort(key=lambda x: x[0])
        for d, c in scored:
            runways = list(
                db.scalars(select(Runway).where(Runway.airport_id == c.id)).all()
            )
            if any(r.length_ft >= 6000 for r in runways):
                out.append(c)
                if len(out) >= 1:
                    break
    return out


def _effective_policy(plan: FlightPlan) -> dict[str, Any]:
    base = dict(fuel_svc.DEFAULT_POLICY)
    if plan.fuel_policy:
        base.update(plan.fuel_policy)
    return base


def calculate_flight_plan(db: Session, plan: FlightPlan) -> dict[str, Any]:
    """Run the full planning pipeline and persist outputs to the DB."""

    # 1. Validate plan state
    if plan.status not in {FlightPlanStatus.DRAFT, FlightPlanStatus.VALIDATED, FlightPlanStatus.CALCULATED}:
        # Allow re-calculation but not after dispatch
        if plan.status == FlightPlanStatus.DISPATCHED:
            raise NotFoundError("Cannot recalculate a dispatched flight plan.")

    # 2. Load AIRAC
    cycle = db.get(AiracCycle, plan.airac_cycle_id)
    if cycle is None:
        raise NotFoundError("AIRAC cycle not found for flight plan.")

    # 3. Load airports
    departure = _airport(db, cycle.id, plan.departure_icao)
    arrival = _airport(db, cycle.id, plan.arrival_icao)
    alternates = _resolve_alternates(db, cycle.id, arrival, plan.alternate_icaos)

    # 4. Load aircraft
    ac_type = _aircraft_type_for_plan(db, plan)
    if ac_type is None:
        # emit a warning and use placeholder performance
        ac_type = AircraftType(
            icao_type="GENERIC",
            manufacturer="Generic",
            model="Generic",
            mtow_kg=79000,
            mlw_kg=66000,
            mzfw_kg=62000,
            oew_kg=42000,
            fuel_capacity_kg=18000,
            cruise_mach=0.78,
            cruise_tas_kts=450,
            max_altitude_ft=41000,
        )

    registration = (
        db.get(AircraftRegistration, plan.aircraft_registration_id)
        if plan.aircraft_registration_id
        else None
    )

    # 5. Validate procedures
    sid_proc = db.get(Procedure, plan.sid_id) if plan.sid_id else None
    star_proc = db.get(Procedure, plan.star_id) if plan.star_id else None
    approach_proc = db.get(Procedure, plan.approach_id) if plan.approach_id else None

    sid_warnings = _validate_procedure(sid_proc, plan.departure_runway_ident, ProcedureKind.SID, departure)
    star_warnings = _validate_procedure(star_proc, None, ProcedureKind.STAR, arrival)
    approach_warnings = _validate_procedure(approach_proc, plan.arrival_runway_ident, ProcedureKind.APPROACH, arrival)

    # 6. Parse + validate route
    parsed = parse_route(plan.route_text or "")
    route_errors = list(parsed.errors)

    # 7. Build geometry
    legs_data: list[dict[str, Any]] = []
    cumulative = 0.0
    prev_pos: tuple[float, float] | None = (
        (departure.latitude, departure.longitude) if not sid_proc else None
    )
    # If SID is selected, start at departure, then begin geometry with first route leg
    if sid_proc is not None and not parsed.legs:
        # No enroute legs after SID — that's fine for short hops
        pass

    # Weather provider
    provider = weather_svc.get_default_provider()
    valid_at = plan.scheduled_off_block or datetime.now(tz=timezone.utc)

    # Snapshot weather for the relevant airports
    weather_reports: list[WeatherReport] = weather_svc.persist_weather_snapshot(
        db, provider, [plan.departure_icao, plan.arrival_icao] + [a.icao for a in alternates], valid_at
    )
    if weather_reports:
        plan.weather_snapshot_id = weather_reports[0].id

    dep_metar = provider.get_metar(plan.departure_icao)
    arr_metar = provider.get_metar(plan.arrival_icao)

    # Build legs from parsed route
    route_total_nm = 0.0
    for leg in parsed.legs:
        fix = db.scalar(
            select(Fix).where(Fix.airac_cycle_id == cycle.id, Fix.ident == leg.ident)
        )
        ap = None
        if fix is None:
            ap = db.scalar(
                select(Airport).where(
                    Airport.airac_cycle_id == cycle.id, Airport.icao == leg.ident
                )
            )
        if fix is not None:
            pos = (fix.latitude, fix.longitude)
        elif ap is not None:
            pos = (ap.latitude, ap.longitude)
        else:
            route_errors.append(f"Unknown fix '{leg.ident}'.")
            continue

        seg_dist = 0.0
        course = None
        if prev_pos is not None:
            seg_dist = great_circle_distance(LatLon(*prev_pos), LatLon(*pos))
            course = initial_bearing(LatLon(*prev_pos), LatLon(*pos))
            cumulative += seg_dist
        legs_data.append(
            {
                "ident": leg.ident,
                "leg_type": leg.leg_type,
                "airway": leg.airway,
                "latitude": pos[0],
                "longitude": pos[1],
                "cumulative_distance_nm": round(cumulative, 2),
                "segment_distance_nm": round(seg_dist, 2),
                "course_deg": round(course, 1) if course is not None else None,
            }
        )
        prev_pos = pos

    # Add arrival airport as a final leg if not already present
    if not legs_data or legs_data[-1]["ident"] != arrival.icao:
        last_pos = prev_pos
        pos = (arrival.latitude, arrival.longitude)
        if last_pos is not None:
            seg_dist = great_circle_distance(LatLon(*last_pos), LatLon(*pos))
            course = initial_bearing(LatLon(*last_pos), LatLon(*pos))
            cumulative += seg_dist
        legs_data.append(
            {
                "ident": arrival.icao,
                "leg_type": "ARRIVAL",
                "airway": None,
                "latitude": pos[0],
                "longitude": pos[1],
                "cumulative_distance_nm": round(cumulative, 2),
                "segment_distance_nm": round(seg_dist, 2) if last_pos is not None else 0.0,
                "course_deg": round(course, 1) if last_pos is not None and course is not None else None,
            }
        )

    route_total_nm = cumulative

    # 8. Aircraft performance
    initial_weight_kg = ac_type.oew_kg + plan.payload_kg
    # Use average wind/temp at cruise altitude over midpoint
    midpoint = LatLon(
        (departure.latitude + arrival.latitude) / 2.0,
        (departure.longitude + arrival.longitude) / 2.0,
    )
    cruise_alt = min(plan.cruise_altitude_ft, perf.calculate_max_altitude(ac_type, initial_weight_kg))
    wind_dir, wind_spd, temp_c = provider.get_wind_at(
        midpoint.lat, midpoint.lon, cruise_alt, valid_at
    )
    ctx = perf.PerformanceContext(
        aircraft=ac_type,
        initial_weight_kg=initial_weight_kg,
        altitude_ft=cruise_alt,
        temperature_c=temp_c,
        wind_direction_deg=wind_dir,
        wind_speed_kts=wind_spd,
        cost_index=plan.cost_index,
    )
    climb = perf.calculate_climb(ctx, cruise_alt)
    descent = perf.calculate_descent(ctx, 5000)
    cruise_distance = max(0.0, route_total_nm - descent.distance_nm)
    cruise = perf.calculate_cruise(ctx, cruise_distance)
    # Alternate: distance + descent
    alt_distance_nm = 0.0
    if alternates:
        alt = alternates[0]
        alt_distance_nm = great_circle_distance(
            LatLon(arrival.latitude, arrival.longitude), LatLon(alt.latitude, alt.longitude)
        )

    total_distance = route_total_nm
    total_time = climb.time_seconds + cruise.time_seconds + descent.time_seconds
    avg_gs = (total_distance / (total_time / 3600.0)) if total_time > 0 else 0.0

    # 9. Fuel policy
    policy = _effective_policy(plan)
    trip_kg = climb.fuel_kg + cruise.fuel_kg + descent.fuel_kg
    final_reserve_kg = fuel_svc.calculate_final_reserve(policy, 2600.0)
    alternate_kg = 0.0
    if alternates and alt_distance_nm > 0:
        # Build a separate performance context for the alternate leg at the destination
        alt_ctx = perf.PerformanceContext(
            aircraft=ac_type,
            initial_weight_kg=initial_weight_kg,
            altitude_ft=5000,
            temperature_c=provider.get_wind_at(arrival.latitude, arrival.longitude, 5000, valid_at)[2],
            wind_direction_deg=provider.get_wind_at(arrival.latitude, arrival.longitude, 5000, valid_at)[0],
            wind_speed_kts=provider.get_wind_at(arrival.latitude, arrival.longitude, 5000, valid_at)[1],
            cost_index=plan.cost_index,
        )
        alt_cruise = perf.calculate_cruise(alt_ctx, alt_distance_nm)
        alt_descent = perf.calculate_descent(alt_ctx, 1500)
        alternate_kg = alt_cruise.fuel_kg + alt_descent.fuel_kg

    fuel_result = fuel_svc.calculate_block_fuel(
        policy=policy,
        trip_kg=trip_kg,
        alternate_kg=alternate_kg,
        final_reserve_kg=final_reserve_kg,
        extra_kg=float(policy.get("extra_kg", 0.0)),
        additional_kg=float(policy.get("additional_kg", 0.0)),
    )

    # 10. Weights
    zfw_kg = ac_type.oew_kg + plan.payload_kg
    tow_kg = zfw_kg + fuel_result.block_kg
    landing_fuel_kg = max(0.0, fuel_result.block_kg - fuel_result.taxi_kg - trip_kg - fuel_result.alternate_kg - fuel_result.contingency_kg)
    lw_kg = max(0.0, tow_kg - (fuel_result.taxi_kg + trip_kg + fuel_result.alternate_kg))

    # 11. Warnings
    warnings: list[FlightPlanWarning] = []
    if not alternates:
        warnings.append(_warn(plan, "NO_ALTERNATE", "WARNING", "No alternate airport selected."))
    if tow_kg > ac_type.mtow_kg:
        warnings.append(
            _warn(plan, "TOW_EXCEEDS_MTOW", "CRITICAL", f"Takeoff weight {tow_kg:.0f} kg exceeds MTOW {ac_type.mtow_kg:.0f} kg.",
                  {"tow_kg": tow_kg, "mtow_kg": ac_type.mtow_kg})
        )
    if zfw_kg > ac_type.mzfw_kg:
        warnings.append(
            _warn(plan, "ZFW_EXCEEDS_MZFW", "CRITICAL", f"ZFW {zfw_kg:.0f} kg exceeds MZFW {ac_type.mzfw_kg:.0f} kg.")
        )
    if lw_kg > ac_type.mlw_kg:
        warnings.append(
            _warn(plan, "LW_EXCEEDS_MLW", "CRITICAL", f"Landing weight {lw_kg:.0f} kg exceeds MLW {ac_type.mlw_kg:.0f} kg.")
        )
    if fuel_result.block_kg > ac_type.fuel_capacity_kg:
        warnings.append(
            _warn(plan, "BLOCK_FUEL_EXCEEDS_CAPACITY", "CRITICAL",
                  f"Block fuel {fuel_result.block_kg:.0f} kg exceeds capacity {ac_type.fuel_capacity_kg:.0f} kg.")
        )
    if lw_kg > 0.95 * ac_type.mlw_kg:
        warnings.append(
            _warn(plan, "LW_NEAR_MLW", "WARNING", f"Landing weight {lw_kg:.0f} kg is within 5% of MLW {ac_type.mlw_kg:.0f} kg.")
        )
    if plan.payload_kg > 0 and plan.passengers <= 0:
        warnings.append(
            _warn(plan, "PAYLOAD_WITHOUT_PASSENGERS", "INFO", "Payload set without passengers; verify seat allocation.")
        )
    for w in sid_warnings + star_warnings + approach_warnings:
        warnings.append(_warn(plan, w["code"], w["severity"], w["message"], w.get("details")))
    for err in route_errors:
        warnings.append(_warn(plan, "ROUTE_VALIDATION", "ERROR", err))
    if not plan.route_text and not sid_proc and not star_proc:
        warnings.append(
            _warn(plan, "NO_ROUTE", "WARNING", "No route string and no procedures selected; using direct track only.")
        )

    # 12. Persist
    _persist_legs(db, plan, legs_data, ctx, total_time, fuel_result)
    _persist_calculation(
        db,
        plan,
        total_distance,
        total_time,
        avg_gs,
        climb.fuel_kg,
        cruise.fuel_kg,
        descent.fuel_kg,
        0.0,
        extras={"cruise_ground_speed_kts": cruise.average_ground_speed_kts},
    )
    _persist_fuel(db, plan, fuel_result, policy)
    _persist_weights(db, plan, zfw_kg, tow_kg, landing_fuel_kg, lw_kg)
    _persist_warnings(db, plan, warnings)

    plan.status = FlightPlanStatus.CALCULATED
    plan.aircraft_performance_version = "1.0.0"
    plan.calculation_engine_version = get_settings().calculation_engine_version
    db.flush()
    return {
        "total_distance_nm": total_distance,
        "estimated_time_enroute_seconds": total_time,
        "block_fuel_kg": fuel_result.block_kg,
    }


def _warn(plan: FlightPlan, code: str, severity: str, message: str, details: dict | None = None) -> FlightPlanWarning:
    return FlightPlanWarning(
        flight_plan_id=plan.id,
        severity=severity,
        code=code,
        message=message,
        details=details or {},
    )


def _validate_procedure(
    proc: Procedure | None, runway_ident: str | None, expected: ProcedureKind, airport: Airport
) -> list[dict]:
    issues: list[dict] = []
    if proc is None:
        return issues
    if proc.kind != expected:
        issues.append({
            "code": "PROCEDURE_KIND_MISMATCH",
            "severity": "ERROR",
            "message": f"Procedure {proc.name} is {proc.kind.value} but expected {expected.value}.",
        })
    if proc.airport_id != airport.id:
        issues.append({
            "code": "PROCEDURE_AIRPORT_MISMATCH",
            "severity": "ERROR",
            "message": f"Procedure {proc.name} is for a different airport.",
        })
    if expected in {ProcedureKind.SID, ProcedureKind.APPROACH} and runway_ident is not None and proc.runway_ident not in {None, "ALL", runway_ident}:
        issues.append({
            "code": "INVALID_PROCEDURE_TRANSITION",
            "severity": "ERROR",
            "message": f"Procedure {proc.name} is not for runway {runway_ident}.",
        })
    return issues


def _persist_legs(
    db: Session,
    plan: FlightPlan,
    legs_data: list[dict],
    ctx: perf.PerformanceContext,
    total_time: float,
    fuel: fuel_svc.FuelResult,
) -> None:
    # Remove old legs
    existing = list(
        db.scalars(select(FlightPlanLeg).where(FlightPlanLeg.flight_plan_id == plan.id)).all()
    )
    for leg in existing:
        db.delete(leg)
    db.flush()

    fuel_remaining = fuel.block_kg - fuel.taxi_kg
    if not legs_data:
        return
    seg_time = total_time / max(1, len(legs_data))
    seg_fuel = (fuel.trip_kg) / max(1, len(legs_data))
    cumulative_time = 0.0
    cumulative_fuel = fuel_remaining
    for i, ld in enumerate(legs_data, start=1):
        cumulative_time += seg_time
        cumulative_fuel = max(0.0, cumulative_fuel - seg_fuel)
        wind_dir, wind_spd, temp_c = ctx.wind_direction_deg, ctx.wind_speed_kts, ctx.temperature_c
        leg = FlightPlanLeg(
            flight_plan_id=plan.id,
            sequence=i,
            ident=ld["ident"],
            leg_type=ld.get("leg_type", "ENROUTE"),
            airway_ident=ld.get("airway"),
            latitude=ld.get("latitude"),
            longitude=ld.get("longitude"),
            course_deg=ld.get("course_deg"),
            distance_nm=ld.get("segment_distance_nm"),
            cumulative_distance_nm=ld.get("cumulative_distance_nm", 0.0),
            altitude_ft=ctx.altitude_ft,
            speed_kts=int(ctx.aircraft.cruise_tas_kts),
            wind_direction_deg=wind_dir,
            wind_speed_kts=wind_spd,
            air_temp_c=temp_c,
            true_air_speed_kts=ctx.aircraft.cruise_tas_kts,
            ground_speed_kts=ctx.aircraft.cruise_tas_kts - wind_spd * 0.5,
            eta_seconds=int(cumulative_time),
            fuel_used_kg=seg_fuel,
            fuel_remaining_kg=cumulative_fuel,
        )
        db.add(leg)


def _persist_calculation(
    db: Session,
    plan: FlightPlan,
    total_distance: float,
    total_time: float,
    avg_gs: float,
    climb_fuel: float,
    cruise_fuel: float,
    descent_fuel: float,
    approach_fuel: float,
    extras: dict[str, Any] | None = None,
) -> None:
    calc = db.scalar(
        select(FlightPlanCalculation).where(FlightPlanCalculation.flight_plan_id == plan.id)
    )
    if calc is None:
        calc = FlightPlanCalculation(flight_plan_id=plan.id)
        db.add(calc)
    calc.total_distance_nm = total_distance
    calc.estimated_time_enroute_seconds = int(total_time)
    calc.average_ground_speed_kts = avg_gs
    calc.cruise_ground_speed_kts = (extras or {}).get("cruise_ground_speed_kts", avg_gs)
    calc.climb_fuel_kg = climb_fuel
    calc.cruise_fuel_kg = cruise_fuel
    calc.descent_fuel_kg = descent_fuel
    calc.approach_fuel_kg = approach_fuel
    calc.inputs = {
        "cruise_altitude_ft": plan.cruise_altitude_ft,
        "cost_index": plan.cost_index,
    }
    calc.outputs = {
        "total_distance_nm": total_distance,
        "ete_seconds": int(total_time),
        "avg_ground_speed_kts": avg_gs,
    }
    calc.formulas = {
        "block_fuel": "taxi + trip + contingency + alternate + final_reserve + additional + extra",
        "contingency": "trip_fuel * contingency_percent",
        "final_reserve": "hold_minutes * cruise_fuel_flow_kg_per_hr",
    }
    calc.computed_at = datetime.now(tz=timezone.utc)
    db.flush()


def _persist_fuel(
    db: Session,
    plan: FlightPlan,
    fuel: fuel_svc.FuelResult,
    policy: dict[str, Any],
) -> None:
    f = db.scalar(select(FlightPlanFuel).where(FlightPlanFuel.flight_plan_id == plan.id))
    if f is None:
        f = FlightPlanFuel(flight_plan_id=plan.id)
        db.add(f)
    f.taxi_kg = fuel.taxi_kg
    f.trip_kg = fuel.trip_kg
    f.contingency_kg = fuel.contingency_kg
    f.alternate_kg = fuel.alternate_kg
    f.final_reserve_kg = fuel.final_reserve_kg
    f.additional_kg = fuel.additional_kg
    f.extra_kg = fuel.extra_kg
    f.block_kg = fuel.block_kg
    f.policy_used = policy
    db.flush()


def _persist_weights(
    db: Session,
    plan: FlightPlan,
    zfw_kg: float,
    tow_kg: float,
    landing_fuel_kg: float,
    lw_kg: float,
) -> None:
    w = db.scalar(select(FlightPlanWeight).where(FlightPlanWeight.flight_plan_id == plan.id))
    if w is None:
        w = FlightPlanWeight(flight_plan_id=plan.id)
        db.add(w)
    w.oew_kg = 0.0
    w.payload_kg = plan.payload_kg
    w.zfw_kg = zfw_kg
    w.takeoff_fuel_kg = 0.0
    w.tow_kg = tow_kg
    w.landing_fuel_kg = landing_fuel_kg
    w.lw_kg = lw_kg
    db.flush()


def _persist_warnings(
    db: Session,
    plan: FlightPlan,
    warnings: list[FlightPlanWarning],
) -> None:
    existing = list(
        db.scalars(select(FlightPlanWarning).where(FlightPlanWarning.flight_plan_id == plan.id)).all()
    )
    for w in existing:
        db.delete(w)
    db.flush()
    for w in warnings:
        db.add(w)
    db.flush()
