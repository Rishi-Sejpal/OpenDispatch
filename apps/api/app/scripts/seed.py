"""Seed the database with default AIRAC cycle, test navigation data, and a default user.

This script is idempotent. Run with `python -m app.scripts.seed`.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, update

from app.core.config import get_settings
from app.core.packages_path import ensure_packages_on_path
from app.core.supabase import get_supabase_admin

ensure_packages_on_path()

from app.db.session import session_scope  # noqa: E402
from app.models import (  # noqa: E402
    AircraftRegistration,
    AircraftType,
    AiracCycle,
    AiracImportStatus,
    Airport,
    AuditLog,
    Airway,
    AirwaySegment,
    Fix,
    FixRole,
    FlightPlan,
    Organization,
    OrganizationMember,
    Procedure,
    ProcedureKind,
    ProcedureLeg,
    ProcedureTransition,
    Runway,
    User,
    UserRole,
)
from app.services import audit  # noqa: E402
from app.services.airac import current_airac_cycle  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[4]
TEST_NAV_PATH = REPO_ROOT / "data" / "test-navigation"


def upsert_airac_cycle(db) -> AiracCycle:
    """Ensure the current real-world AIRAC cycle exists and is the active one.

    The active cycle is resolved deterministically from today's date so the
    system always uses the currently effective AIRAC schedule. Older cycles
    present in the database are deactivated but their navigation data is
    retained for historical flight plans.
    """
    info = current_airac_cycle()
    cycle_id_str = info.cycle

    # Deactivate any other active cycle so this one is the unique active.
    db.execute(update(AiracCycle).where(AiracCycle.is_active.is_(True)).values(is_active=False))

    existing = db.scalar(select(AiracCycle).where(AiracCycle.cycle == cycle_id_str))
    if existing is not None:
        existing.effective_from = datetime.combine(
            info.effective_from, datetime.min.time(), tzinfo=timezone.utc
        )
        existing.effective_to = datetime.combine(
            info.effective_to, datetime.min.time(), tzinfo=timezone.utc
        )
        existing.is_active = True
        existing.import_status = AiracImportStatus.COMPLETE
        existing.notes = (
            f"Current AIRAC cycle, effective {info.effective_from.isoformat()} "
            f"through {info.effective_to.isoformat()} (computed deterministically)."
        )
        db.flush()
        return existing

    cycle = AiracCycle(
        cycle=cycle_id_str,
        effective_from=datetime.combine(
            info.effective_from, datetime.min.time(), tzinfo=timezone.utc
        ),
        effective_to=datetime.combine(
            info.effective_to, datetime.min.time(), tzinfo=timezone.utc
        ),
        source="test-fixture",
        version="1",
        import_status=AiracImportStatus.COMPLETE,
        checksum="local-test-data",
        is_active=True,
        notes=(
            f"Current AIRAC cycle, effective {info.effective_from.isoformat()} "
            f"through {info.effective_to.isoformat()} (computed deterministically)."
        ),
    )
    db.add(cycle)
    db.flush()
    return cycle


def upsert_user(db) -> User:
    """Ensure the default superuser exists.

    In production (SEED_USE_SUPABASE_AUTH=true) the user is created and managed
    in Supabase Auth and mirrored into the local ``users`` table. The
    ``app_metadata.is_superuser`` flag is the source of truth that
    ``get_current_user`` reads back when provisioning the local row.

    In CI and local dev without Supabase, a local stub row is created so
    downstream code that references the seed user (e.g. the default
    organization) keeps working.
    """
    settings = get_settings()
    email = settings.seed_user_email

    if settings.seed_use_supabase_auth and settings.supabase_configured:
        admin = get_supabase_admin()
        listed = admin.auth.admin.list_users(page=1, per_page=200)
        auth_user = next(
            (u for u in listed if (u.email or "").lower() == email.lower()),
            None,
        )
        if auth_user is None:
            created = admin.auth.admin.create_user(
                {
                    "email": email,
                    "password": settings.seed_user_password,
                    "email_confirm": True,
                    "user_metadata": {"full_name": settings.seed_user_name},
                    "app_metadata": {"is_superuser": True, "provider": "openai-seed"},
                }
            )
            auth_user = created.user
        if not (auth_user.app_metadata or {}).get("is_superuser"):
            admin.auth.admin.update_user_by_id(
                auth_user.id,
                {"app_metadata": {"is_superuser": True, "provider": "openai-seed"}},
            )
        user = db.get(User, auth_user.id)
        if user is None:
            # A local row may exist from a previous local-only seed (a
            # different uuid) but with the same email. Reconcile by
            # rewriting the local row's id to the Supabase auth user id
            # and migrating every foreign key so the two stay in sync
            # going forward.
            existing = db.scalar(select(User).where(User.email == email))
            if existing is not None:
                existing_id = existing.id
                if existing_id != auth_user.id:
                    db.execute(
                        update(OrganizationMember)
                        .where(OrganizationMember.user_id == existing_id)
                        .values(user_id=auth_user.id)
                    )
                    db.execute(
                        update(FlightPlan)
                        .where(FlightPlan.created_by_id == existing_id)
                        .values(created_by_id=auth_user.id)
                    )
                    db.execute(
                        update(FlightPlan)
                        .where(FlightPlan.dispatched_by_id == existing_id)
                        .values(dispatched_by_id=auth_user.id)
                    )
                    db.execute(
                        update(AuditLog)
                        .where(AuditLog.actor_user_id == existing_id)
                        .values(actor_user_id=auth_user.id)
                    )
                    existing.id = auth_user.id
                existing.email = email
                existing.full_name = settings.seed_user_name
                existing.is_superuser = True
                existing.is_email_verified = True
                db.flush()
                return existing
            user = User(
                id=auth_user.id,
                email=email,
                full_name=settings.seed_user_name,
                is_superuser=True,
                is_email_verified=True,
            )
            db.add(user)
            db.flush()
        return user

    # Local stub (CI / dev without Supabase). Upsert by email so the seed
    # works whether or not a row from a previous (password-based) run
    # already exists in the database.
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        existing.is_superuser = True
        existing.is_email_verified = True
        if not existing.full_name:
            existing.full_name = settings.seed_user_name
        return existing
    import uuid as _uuid

    stable_id = _uuid.uuid5(_uuid.NAMESPACE_DNS, f"opendispatch-seed:{email}")
    user = User(
        id=stable_id,
        email=email,
        full_name=settings.seed_user_name,
        is_superuser=True,
        is_email_verified=True,
    )
    db.add(user)
    db.flush()
    return user


def upsert_organization(db, user: User) -> Organization:
    member = db.scalar(
        select(OrganizationMember).where(OrganizationMember.user_id == user.id)
    )
    if member is not None:
        return member.organization
    org = Organization(
        name="OpenDispatch Dispatch",
        slug="opendispatch-default",
        icao_code="OPD",
        iata_code="OD",
        default_fuel_policy={
            "taxi_kg": 200,
            "contingency_percent": 0.05,
            "final_reserve_minutes": 30,
            "extra_kg": 0,
            "additional_kg": 0,
        },
    )
    db.add(org)
    db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=UserRole.OWNER))
    db.flush()
    return org


AIRCRAFT_FIXTURE_PATH = REPO_ROOT / "data" / "aircraft" / "aircraft.json"


def upsert_aircraft(db) -> AircraftType:
    a320 = _upsert_single_aircraft(db, {
        "icao_type": "A320",
        "manufacturer": "Airbus",
        "model": "A320-200",
        "variant": "CFM56-5B",
        "wake_category": "M",
        "engine_type": "JET",
        "engines": 2,
        "mtow_kg": 78000,
        "mlw_kg": 66000,
        "mzfw_kg": 62500,
        "oew_kg": 42500,
        "fuel_capacity_kg": 18728,
        "passenger_capacity": 180,
        "cargo_capacity_kg": 9000,
        "max_altitude_ft": 39800,
        "cruise_mach": 0.78,
        "cruise_tas_kts": 450,
        "approach_speed_kts": 140,
        "initial_climb_alt_ft": 5000,
        "initial_cruise_alt_ft": 35000,
        "climb_profile": {"model": "simplified", "rate_fpm": 1800, "ias_kt": 250},
        "cruise_profile": {"model": "simplified", "mach": 0.78, "isa": 0},
        "descent_profile": {"model": "simplified", "rate_fpm": 1500, "mach": 0.78},
        "fuel_burn_model": {"model": "simplified", "ff_cruise_kg_hr": 2600, "ff_climb_kg_hr": 3500},
        "notes": (
            "Simplified open-source performance model. NOT certified operational data. "
            "Use only for planning, training, and simulation. Cross-check against approved "
            "aircraft performance manuals before any real flight."
        ),
    })
    if AIRCRAFT_FIXTURE_PATH.exists():
        with open(AIRCRAFT_FIXTURE_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        for entry in data.get("aircraft_types", []):
            _upsert_single_aircraft(db, entry)
    return a320


def _upsert_single_aircraft(db, entry: dict) -> AircraftType:
    icao = entry["icao_type"]
    existing = db.scalar(select(AircraftType).where(AircraftType.icao_type == icao))
    if existing is not None:
        return existing
    ac = AircraftType(**entry)
    db.add(ac)
    db.flush()
    return ac


def upsert_registration(db, org: Organization, ac: AircraftType) -> AircraftRegistration:
    existing = db.scalar(
        select(AircraftRegistration).where(AircraftRegistration.registration == "VT-OD1")
    )
    if existing is not None:
        return existing
    reg = AircraftRegistration(
        aircraft_type_id=ac.id,
        organization_id=org.id,
        registration="VT-OD1",
        nickname="OpenDispatch 1",
        fuel_policy={
            "taxi_kg": 200,
            "contingency_percent": 0.05,
            "final_reserve_minutes": 30,
        },
    )
    db.add(reg)
    db.flush()
    return reg


def load_test_navigation(db, cycle: AiracCycle) -> None:
    """Load airports, runways, fixes, airways, procedures from the test fixture directory."""
    settings_path = TEST_NAV_PATH / "navigation.json"
    if not settings_path.exists():
        raise FileNotFoundError(f"Test navigation data not found at {settings_path}")

    with open(settings_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Airports
    airports_by_icao: dict[str, Airport] = {}
    for ad in data.get("airports", []):
        existing = db.scalar(
            select(Airport).where(Airport.airac_cycle_id == cycle.id, Airport.icao == ad["icao"])
        )
        if existing is not None:
            airports_by_icao[ad["icao"]] = existing
            continue
        ap = Airport(
            airac_cycle_id=cycle.id,
            icao=ad["icao"],
            iata=ad.get("iata"),
            name=ad["name"],
            city=ad.get("city"),
            country=ad.get("country"),
            region=ad.get("region"),
            latitude=ad["latitude"],
            longitude=ad["longitude"],
            elevation_ft=ad.get("elevation_ft", 0.0),
            magnetic_variation=ad.get("magnetic_variation", 0.0),
            timezone=ad.get("timezone", "UTC"),
            has_procedures=True,
        )
        # Use raw WKT for location
        ap.location = f"SRID=4326;POINT({ad['longitude']} {ad['latitude']})"
        db.add(ap)
        db.flush()
        airports_by_icao[ad["icao"]] = ap

    # Runways
    for ad in data.get("airports", []):
        ap = airports_by_icao[ad["icao"]]
        for r in ad.get("runways", []):
            existing = db.scalar(
                select(Runway).where(Runway.airport_id == ap.id, Runway.ident == r["ident"])
            )
            if existing is not None:
                continue
            db.add(
                Runway(
                    airport_id=ap.id,
                    airac_cycle_id=cycle.id,
                    ident=r["ident"],
                    reciprocal_ident=r.get("reciprocal_ident"),
                    length_ft=r["length_ft"],
                    width_ft=r.get("width_ft", 150.0),
                    heading_deg=r["heading_deg"],
                    surface=r.get("surface", "ASP"),
                    elevation_ft=r.get("elevation_ft", ap.elevation_ft),
                    ils_available=r.get("ils_available", False),
                    ils_category=r.get("ils_category"),
                    lighting=r.get("lighting", True),
                )
            )
    db.flush()

    # Fixes
    fixes_by_ident: dict[str, Fix] = {}
    for fd in data.get("fixes", []):
        existing = db.scalar(
            select(Fix).where(Fix.airac_cycle_id == cycle.id, Fix.ident == fd["ident"])
        )
        if existing is not None:
            fixes_by_ident[fd["ident"]] = existing
            continue
        role = FixRole(fd.get("role", "WAYPOINT").upper())
        fix = Fix(
            airac_cycle_id=cycle.id,
            ident=fd["ident"],
            name=fd.get("name"),
            role=role,
            latitude=fd["latitude"],
            longitude=fd["longitude"],
            elevation_ft=fd.get("elevation_ft"),
            magnetic_variation=fd.get("magnetic_variation", 0.0),
            region=fd.get("region"),
        )
        fix.location = f"SRID=4326;POINT({fd['longitude']} {fd['latitude']})"
        db.add(fix)
        db.flush()
        fixes_by_ident[fd["ident"]] = fix

    # Airways + segments
    for ad in data.get("airways", []):
        existing = db.scalar(
            select(Airway).where(Airway.airac_cycle_id == cycle.id, Airway.ident == ad["ident"])
        )
        if existing is None:
            airway = Airway(
                airac_cycle_id=cycle.id,
                ident=ad["ident"],
                name=ad.get("name"),
                type=ad.get("type", "U"),
                direction=ad.get("direction"),
            )
            db.add(airway)
            db.flush()
        else:
            airway = existing
        # Segments
        for i, seg in enumerate(ad.get("segments", []), start=1):
            f_from = fixes_by_ident.get(seg["from"])
            f_to = fixes_by_ident.get(seg["to"])
            if f_from is None or f_to is None:
                continue
            existing_seg = db.scalar(
                select(AirwaySegment).where(
                    AirwaySegment.airway_id == airway.id,
                    AirwaySegment.sequence == i,
                )
            )
            if existing_seg is not None:
                continue
            from aviation_geometry import LatLon, great_circle_distance, initial_bearing

            dist = seg.get("distance_nm") or great_circle_distance(
                LatLon(f_from.latitude, f_from.longitude), LatLon(f_to.latitude, f_to.longitude)
            )
            crs = seg.get("magnetic_course") or initial_bearing(
                LatLon(f_from.latitude, f_from.longitude), LatLon(f_to.latitude, f_to.longitude)
            )
            db.add(
                AirwaySegment(
                    airway_id=airway.id,
                    sequence=i,
                    from_fix_id=f_from.id,
                    to_fix_id=f_to.id,
                    distance_nm=dist,
                    magnetic_course=crs,
                    minimum_altitude_ft=seg.get("min_alt"),
                    maximum_altitude_ft=seg.get("max_alt"),
                )
            )
    db.flush()

    # Procedures
    for pd in data.get("procedures", []):
        proc_ap = airports_by_icao.get(pd["airport"])
        if proc_ap is None:
            continue
        existing = db.scalar(
            select(Procedure).where(
                Procedure.airac_cycle_id == cycle.id,
                Procedure.airport_id == proc_ap.id,
                Procedure.name == pd["name"],
                Procedure.kind == ProcedureKind(pd["kind"]),
                Procedure.runway_ident == pd.get("runway"),
            )
        )
        if existing is not None:
            continue
        ref_fix = fixes_by_ident.get(pd["reference_fix"]) if pd.get("reference_fix") else None
        proc = Procedure(
            airac_cycle_id=cycle.id,
            airport_id=proc_ap.id,
            name=pd["name"],
            kind=ProcedureKind(pd["kind"]),
            runway_ident=pd.get("runway"),
            reference_fix_id=ref_fix.id if ref_fix else None,
        )
        db.add(proc)
        db.flush()

        # Transitions
        for i, tname in enumerate(pd.get("transitions", []), start=1):
            db.add(
                ProcedureTransition(
                    procedure_id=proc.id,
                    name=tname,
                    sequence=i,
                )
            )
        # Legs
        for i, ld in enumerate(pd.get("legs", []), start=1):
            leg_fix = fixes_by_ident.get(ld["fix"]) if ld.get("fix") else None
            db.add(
                ProcedureLeg(
                    procedure_id=proc.id,
                    sequence=i,
                    leg_type=ld["leg_type"],
                    fix_id=leg_fix.id if leg_fix else None,
                    course_deg=ld.get("course_deg"),
                    distance_nm=ld.get("distance_nm"),
                    altitude_ft=ld.get("altitude_ft"),
                    speed_kts=ld.get("speed_kts"),
                    fly_over=ld.get("fly_over", False),
                    remarks=ld.get("remarks"),
                )
            )
    db.flush()


def main() -> None:
    print("Seeding OpenDispatch database...")
    with session_scope() as db:
        cycle = upsert_airac_cycle(db)
        user = upsert_user(db)
        org = upsert_organization(db, user)
        ac = upsert_aircraft(db)
        upsert_registration(db, org, ac)
        load_test_navigation(db, cycle)
        audit.log_event(db, action="seed.completed", actor_user_id=user.id)
    print("Done.")


if __name__ == "__main__":
    main()
