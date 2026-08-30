"""Flight plan endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.errors import BusinessRuleViolation, NotFoundError
from app.db.session import get_db
from app.models import (
    AircraftRegistration,
    AircraftType,
    AiracCycle,
    Airport,
    FlightPlan,
    FlightPlanStatus,
    Organization,
    OrganizationMember,
    User,
    UserRole,
)
from app.schemas import (
    FlightPlanCalculateRequest,
    FlightPlanCreate,
    FlightPlanDispatchRequest,
    FlightPlanRead,
    FlightPlanSummary,
    FlightPlanUpdate,
)
from app.services import audit, flight_planner, pdf_renderer
from app.services import storage

router = APIRouter()


def _get_membership(db: Session, user: User, org_id: uuid.UUID) -> OrganizationMember:
    member = db.scalar(
        select(OrganizationMember).where(
            OrganizationMember.user_id == user.id, OrganizationMember.organization_id == org_id
        )
    )
    if member is None:
        raise NotFoundError("Organization not found.")
    return member


def _plan_for_user(db: Session, plan_id: uuid.UUID, user: User) -> FlightPlan:
    plan = db.get(FlightPlan, plan_id)
    if plan is None:
        raise NotFoundError("Flight plan not found.")
    _get_membership(db, user, plan.organization_id)
    return plan


def _resolve_organization(db: Session, user: User, organization_id: uuid.UUID | None) -> uuid.UUID:
    if organization_id is not None:
        _get_membership(db, user, organization_id)
        return organization_id
    # Use first organization
    member = db.scalar(
        select(OrganizationMember)
        .where(OrganizationMember.user_id == user.id)
        .order_by(OrganizationMember.created_at)
    )
    if member is None:
        raise BusinessRuleViolation("User is not a member of any organization.")
    return member.organization_id


@router.get("", response_model=list[FlightPlanSummary])
def list_plans(
    organization_id: uuid.UUID | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[FlightPlanSummary]:
    org_id = _resolve_organization(db, user, organization_id)
    stmt = (
        select(FlightPlan)
        .where(FlightPlan.organization_id == org_id)
        .order_by(FlightPlan.updated_at.desc())
        .limit(limit)
    )
    if status:
        try:
            fs = FlightPlanStatus(status.upper())
        except ValueError as exc:
            raise NotFoundError(f"Unknown status: {status}") from exc
        stmt = stmt.where(FlightPlan.status == fs)
    plans = list(db.scalars(stmt).all())
    summaries: list[FlightPlanSummary] = []
    for p in plans:
        ac_icao = None
        reg = None
        if p.aircraft_registration_id is not None:
            r = db.get(AircraftRegistration, p.aircraft_registration_id)
            if r is not None:
                reg = r.registration
                at = db.get(AircraftType, r.aircraft_type_id)
                if at is not None:
                    ac_icao = at.icao_type
        elif p.aircraft_type_id is not None:
            at = db.get(AircraftType, p.aircraft_type_id)
            if at is not None:
                ac_icao = at.icao_type
        summaries.append(
            FlightPlanSummary(
                id=p.id,
                status=p.status.value,
                departure_icao=p.departure_icao,
                arrival_icao=p.arrival_icao,
                alternate_icaos=p.alternate_icaos,
                aircraft_registration=reg,
                aircraft_type_icao=ac_icao,
                callsign=p.callsign,
                scheduled_off_block=p.scheduled_off_block,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
        )
    return summaries


@router.post("", response_model=FlightPlanRead, status_code=201)
def create_plan(
    payload: FlightPlanCreate,
    organization_id: uuid.UUID | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlightPlanRead:
    org_id = _resolve_organization(db, user, organization_id)
    cycle = db.scalar(select(AiracCycle).where(AiracCycle.is_active.is_(True)))
    if cycle is None:
        # fall back to most recent
        cycle = db.scalar(select(AiracCycle).order_by(AiracCycle.effective_from.desc()))
    if cycle is None:
        raise BusinessRuleViolation("No AIRAC cycle available. Load navigation data first.")
    plan = FlightPlan(
        organization_id=org_id,
        created_by_id=user.id,
        airac_cycle_id=cycle.id,
        status=FlightPlanStatus.DRAFT,
        departure_icao=payload.departure_icao.upper(),
        arrival_icao=payload.arrival_icao.upper(),
        alternate_icaos=[s.upper() for s in payload.alternate_icaos],
        aircraft_type_id=payload.aircraft_type_id,
        aircraft_registration_id=payload.aircraft_registration_id,
        passengers=payload.passengers,
        cargo_kg=payload.cargo_kg,
        payload_kg=payload.passengers * 84.0 + payload.cargo_kg,
        route_text=payload.route_text,
        departure_runway_ident=payload.departure_runway_ident,
        arrival_runway_ident=payload.arrival_runway_ident,
        sid_id=payload.sid_id,
        star_id=payload.star_id,
        approach_id=payload.approach_id,
        cruise_altitude_ft=payload.cruise_altitude_ft,
        cost_index=payload.cost_index,
        fuel_policy=payload.fuel_policy,
        scheduled_off_block=payload.scheduled_off_block,
        callsign=payload.callsign,
        flight_number=payload.flight_number,
    )
    db.add(plan)
    db.flush()
    audit.log_event(
        db,
        action="flight_plan.created",
        actor_user_id=user.id,
        organization_id=org_id,
        target_type="flight_plan",
        target_id=str(plan.id),
    )
    db.commit()
    db.refresh(plan)
    return _to_read(db, plan)


@router.get("/{plan_id}", response_model=FlightPlanRead)
def get_plan(
    plan_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlightPlanRead:
    plan = _plan_for_user(db, plan_id, user)
    return _to_read(db, plan)


@router.patch("/{plan_id}", response_model=FlightPlanRead)
def update_plan(
    plan_id: uuid.UUID,
    payload: FlightPlanUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlightPlanRead:
    plan = _plan_for_user(db, plan_id, user)
    if plan.status in {FlightPlanStatus.DISPATCHED, FlightPlanStatus.ARCHIVED}:
        raise BusinessRuleViolation("Cannot modify a dispatched or archived plan.")
    data = payload.model_dump(exclude_unset=True)
    if "departure_icao" in data:
        data["departure_icao"] = data["departure_icao"].upper()
    if "arrival_icao" in data:
        data["arrival_icao"] = data["arrival_icao"].upper()
    if "alternate_icaos" in data:
        data["alternate_icaos"] = [s.upper() for s in data["alternate_icaos"]]
    if "passengers" in data or "cargo_kg" in data:
        pax = data.get("passengers", plan.passengers)
        cargo = data.get("cargo_kg", plan.cargo_kg)
        data["payload_kg"] = pax * 84.0 + cargo
    for k, v in data.items():
        setattr(plan, k, v)
    plan.status = FlightPlanStatus.DRAFT
    audit.log_event(
        db,
        action="flight_plan.updated",
        actor_user_id=user.id,
        organization_id=plan.organization_id,
        target_type="flight_plan",
        target_id=str(plan.id),
    )
    db.commit()
    db.refresh(plan)
    return _to_read(db, plan)


@router.post("/{plan_id}/calculate", response_model=FlightPlanRead)
def calculate_plan(
    plan_id: uuid.UUID,
    _payload: FlightPlanCalculateRequest | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlightPlanRead:
    plan = _plan_for_user(db, plan_id, user)
    if plan.status == FlightPlanStatus.DISPATCHED:
        raise BusinessRuleViolation("Cannot recalculate a dispatched plan.")
    flight_planner.calculate_flight_plan(db, plan)
    audit.log_event(
        db,
        action="flight_plan.calculated",
        actor_user_id=user.id,
        organization_id=plan.organization_id,
        target_type="flight_plan",
        target_id=str(plan.id),
    )
    db.commit()
    db.refresh(plan)
    return _to_read(db, plan)


@router.post("/{plan_id}/dispatch", response_model=FlightPlanRead)
def dispatch_plan(
    plan_id: uuid.UUID,
    _payload: FlightPlanDispatchRequest | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlightPlanRead:
    plan = _plan_for_user(db, plan_id, user)
    if plan.status == FlightPlanStatus.DISPATCHED:
        raise BusinessRuleViolation("Plan already dispatched.")
    if plan.status not in {FlightPlanStatus.CALCULATED, FlightPlanStatus.GENERATED, FlightPlanStatus.VALIDATED}:
        # allow auto-calc
        flight_planner.calculate_flight_plan(db, plan)
    # check critical warnings
    from app.models import FlightPlanWarning

    critical = list(
        db.scalars(
            select(FlightPlanWarning).where(
                FlightPlanWarning.flight_plan_id == plan.id,
                FlightPlanWarning.severity == "CRITICAL",
            )
        ).all()
    )
    if critical:
        codes = [w.code for w in critical]
        raise BusinessRuleViolation(
            "Cannot dispatch with critical warnings.",
            details={"warnings": codes},
        )
    plan.status = FlightPlanStatus.DISPATCHED
    plan.dispatched_at = datetime.now(tz=timezone.utc)
    plan.dispatched_by_id = user.id
    audit.log_event(
        db,
        action="flight_plan.dispatched",
        actor_user_id=user.id,
        organization_id=plan.organization_id,
        target_type="flight_plan",
        target_id=str(plan.id),
    )
    db.commit()
    db.refresh(plan)
    return _to_read(db, plan)


@router.delete("/{plan_id}", status_code=204, response_class=Response)
def delete_plan(
    plan_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    plan = _plan_for_user(db, plan_id, user)
    if plan.status == FlightPlanStatus.DISPATCHED:
        raise BusinessRuleViolation("Cannot delete a dispatched plan; archive it instead.")
    db.delete(plan)
    db.commit()
    return Response(status_code=204)


@router.post("/{plan_id}/archive", response_model=FlightPlanRead)
def archive_plan(
    plan_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FlightPlanRead:
    plan = _plan_for_user(db, plan_id, user)
    plan.status = FlightPlanStatus.ARCHIVED
    db.commit()
    db.refresh(plan)
    return _to_read(db, plan)


@router.get("/{plan_id}/documents")
def list_documents(
    plan_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    plan = _plan_for_user(db, plan_id, user)
    return [
        {
            "id": str(d.id),
            "doc_type": d.doc_type,
            "file_name": d.file_name,
            "size_bytes": d.size_bytes,
            "created_at": d.created_at.isoformat(),
            "template_version": d.template_version,
        }
        for d in plan.documents
    ]


@router.post("/{plan_id}/documents", status_code=201)
def generate_documents(
    plan_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    plan = _plan_for_user(db, plan_id, user)
    # Recalculate if not calculated
    if plan.status not in {FlightPlanStatus.CALCULATED, FlightPlanStatus.GENERATED, FlightPlanStatus.DISPATCHED}:
        flight_planner.calculate_flight_plan(db, plan)
    settings = get_settings()
    fs = storage.get_default_storage()
    generated = []
    for doc_type in ["OFP", "NAV_LOG", "FUEL", "WEIGHT"]:
        result = pdf_renderer.render_document(db, plan, doc_type)
        if result is None:
            continue
        path, size, mime, filename = result
        with open(path, "rb") as fh:
            data = fh.read()
        uri = fs.put(name=filename, content=data, mime=mime)
        from app.models import GeneratedDocument

        doc = GeneratedDocument(
            flight_plan_id=plan.id,
            doc_type=doc_type,
            storage_uri=uri,
            file_name=filename,
            mime_type=mime,
            size_bytes=size,
            template_version=pdf_renderer.TEMPLATE_VERSION,
        )
        db.add(doc)
        generated.append(
            {
                "id": str(doc.id),
                "doc_type": doc_type,
                "file_name": filename,
                "size_bytes": size,
            }
        )
    plan.status = FlightPlanStatus.GENERATED
    db.commit()
    return {"documents": generated}


@router.get("/{plan_id}/documents/{doc_id}/download")
def download_document(
    plan_id: uuid.UUID,
    doc_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    plan = _plan_for_user(db, plan_id, user)
    doc = next((d for d in plan.documents if d.id == doc_id), None)
    if doc is None:
        raise NotFoundError("Document not found.")
    fs = storage.get_default_storage()
    data = fs.get(doc.storage_uri)
    tmp_path = f"/tmp/opendispatch-{doc.id}.pdf"
    with open(tmp_path, "wb") as fh:
        fh.write(data)
    return FileResponse(tmp_path, media_type=doc.mime_type, filename=doc.file_name)


def _to_read(db: Session, plan: FlightPlan) -> FlightPlanRead:
    cycle = db.get(AiracCycle, plan.airac_cycle_id)
    ac_icao = None
    reg = None
    if plan.aircraft_registration_id is not None:
        r = db.get(AircraftRegistration, plan.aircraft_registration_id)
        if r is not None:
            reg = r.registration
            at = db.get(AircraftType, r.aircraft_type_id)
            if at is not None:
                ac_icao = at.icao_type
    elif plan.aircraft_type_id is not None:
        at = db.get(AircraftType, plan.aircraft_type_id)
        if at is not None:
            ac_icao = at.icao_type
    legs = [
        {
            "id": str(l.id),
            "sequence": l.sequence,
            "ident": l.ident,
            "leg_type": l.leg_type,
            "airway": l.airway_ident,
            "latitude": l.latitude,
            "longitude": l.longitude,
            "course_deg": l.course_deg,
            "distance_nm": l.distance_nm,
            "cumulative_distance_nm": l.cumulative_distance_nm,
            "altitude_ft": l.altitude_ft,
            "speed_kts": l.speed_kts,
            "wind_direction_deg": l.wind_direction_deg,
            "wind_speed_kts": l.wind_speed_kts,
            "true_air_speed_kts": l.true_air_speed_kts,
            "ground_speed_kts": l.ground_speed_kts,
            "eta_seconds": l.eta_seconds,
            "fuel_used_kg": l.fuel_used_kg,
            "fuel_remaining_kg": l.fuel_remaining_kg,
        }
        for l in plan.legs
    ]
    calc = plan.calculations
    fuel = plan.fuel
    weights = plan.weights
    documents = [
        {
            "id": str(d.id),
            "doc_type": d.doc_type,
            "file_name": d.file_name,
            "size_bytes": d.size_bytes,
            "created_at": d.created_at.isoformat(),
        }
        for d in plan.documents
    ]
    warnings = [
        {
            "severity": w.severity,
            "code": w.code,
            "message": w.message,
            "details": w.details,
        }
        for w in plan.warnings
    ]
    return FlightPlanRead(
        id=plan.id,
        status=plan.status.value,
        departure_icao=plan.departure_icao,
        arrival_icao=plan.arrival_icao,
        alternate_icaos=plan.alternate_icaos,
        aircraft_registration=reg,
        aircraft_type_icao=ac_icao,
        callsign=plan.callsign,
        scheduled_off_block=plan.scheduled_off_block,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        route_text=plan.route_text,
        departure_runway_ident=plan.departure_runway_ident,
        arrival_runway_ident=plan.arrival_runway_ident,
        sid_id=plan.sid_id,
        star_id=plan.star_id,
        approach_id=plan.approach_id,
        passengers=plan.passengers,
        cargo_kg=plan.cargo_kg,
        payload_kg=plan.payload_kg,
        cruise_altitude_ft=plan.cruise_altitude_ft,
        cost_index=plan.cost_index,
        fuel_policy=plan.fuel_policy,
        airac_cycle=cycle.cycle if cycle else "?",
        calculation_engine_version=plan.calculation_engine_version,
        aircraft_performance_version=plan.aircraft_performance_version,
        dispatched_at=plan.dispatched_at,
        legs=legs,
        calculation={
            "total_distance_nm": calc.total_distance_nm if calc else 0.0,
            "estimated_time_enroute_seconds": calc.estimated_time_enroute_seconds if calc else 0,
            "average_ground_speed_kts": calc.average_ground_speed_kts if calc else 0.0,
            "cruise_ground_speed_kts": calc.cruise_ground_speed_kts if calc else 0.0,
            "climb_fuel_kg": calc.climb_fuel_kg if calc else 0.0,
            "cruise_fuel_kg": calc.cruise_fuel_kg if calc else 0.0,
            "descent_fuel_kg": calc.descent_fuel_kg if calc else 0.0,
        } if calc else None,
        fuel={
            "taxi_kg": fuel.taxi_kg,
            "trip_kg": fuel.trip_kg,
            "contingency_kg": fuel.contingency_kg,
            "alternate_kg": fuel.alternate_kg,
            "final_reserve_kg": fuel.final_reserve_kg,
            "additional_kg": fuel.additional_kg,
            "extra_kg": fuel.extra_kg,
            "block_kg": fuel.block_kg,
        } if fuel else None,
        weights={
            "oew_kg": weights.oew_kg,
            "payload_kg": weights.payload_kg,
            "zfw_kg": weights.zfw_kg,
            "takeoff_fuel_kg": weights.takeoff_fuel_kg,
            "tow_kg": weights.tow_kg,
            "landing_fuel_kg": weights.landing_fuel_kg,
            "lw_kg": weights.lw_kg,
        } if weights else None,
        warnings=warnings,
        documents=documents,
    )
