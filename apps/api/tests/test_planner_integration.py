"""Integration tests for the full flight planning pipeline.

Requires the db service to be running. Uses the dev database (since the docker
stack has a single Postgres). Tests are designed to be safe to re-run and use
unique navigation/cycle data so they don't conflict with the seed.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.session import session_scope
from app.models import (
    AircraftRegistration,
    AircraftType,
    AiracCycle,
    AiracImportStatus,
    Airport,
    Fix,
    FlightPlan,
    FlightPlanStatus,
    Organization,
    OrganizationMember,
    Runway,
    User,
    UserRole,
)
from app.services.flight_planner import calculate_flight_plan

settings = get_settings()


@pytest.fixture
def fresh_cycle(db_session):
    """Create a clean AIRAC cycle for this test."""
    cycle_id = f"T{uuid.uuid4().hex[:6]}"  # 7 chars max in VARCHAR(8)
    cycle = AiracCycle(
        cycle=cycle_id,
        effective_from=None,
        effective_to=None,
        source="integration-test",
        version="1",
        import_status=AiracImportStatus.COMPLETE,
        is_active=False,
    )
    # Need datetimes
    from datetime import datetime, timedelta, timezone

    cycle.effective_from = datetime.now(tz=timezone.utc) - timedelta(days=1)
    cycle.effective_to = datetime.now(tz=timezone.utc) + timedelta(days=1)
    db_session.add(cycle)
    db_session.flush()
    return cycle


@pytest.fixture
def fresh_org(db_session, fresh_user):
    org = Organization(name=f"Test Org {uuid.uuid4().hex[:6]}", slug=f"test-{uuid.uuid4().hex[:6]}")
    db_session.add(org)
    db_session.flush()
    db_session.add(OrganizationMember(organization_id=org.id, user_id=fresh_user.id, role=UserRole.OWNER))
    db_session.flush()
    return org


@pytest.fixture
def fresh_user(db_session):
    email = f"test-{uuid.uuid4().hex[:6]}@example.com"
    user = User(
        id=uuid.uuid4(),
        email=email,
        full_name="Test User",
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def fresh_aircraft(db_session):
    ac = AircraftType(
        icao_type=f"TEST{uuid.uuid4().hex[:4].upper()}",
        manufacturer="Test",
        model="Test",
        mtow_kg=78000,
        mlw_kg=66000,
        mzfw_kg=62500,
        oew_kg=42500,
        fuel_capacity_kg=18728,
        cruise_mach=0.78,
        cruise_tas_kts=450,
        max_altitude_ft=39800,
    )
    db_session.add(ac)
    db_session.flush()
    return ac


@pytest.fixture
def fresh_registration(db_session, fresh_org, fresh_aircraft):
    reg = AircraftRegistration(
        aircraft_type_id=fresh_aircraft.id,
        organization_id=fresh_org.id,
        registration=f"TEST-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(reg)
    db_session.flush()
    return reg


@pytest.fixture
def nav_data(db_session, fresh_cycle):
    """Create two airports, fixes, and a route between them."""
    dep = Airport(
        airac_cycle_id=fresh_cycle.id,
        icao="TST1",
        name="Test Departure",
        latitude=19.0,
        longitude=72.0,
        elevation_ft=0,
        magnetic_variation=0,
        timezone="UTC",
    )
    arr = Airport(
        airac_cycle_id=fresh_cycle.id,
        icao="TST2",
        name="Test Arrival",
        latitude=28.0,
        longitude=77.0,
        elevation_ft=0,
        magnetic_variation=0,
        timezone="UTC",
    )
    db_session.add_all([dep, arr])
    db_session.flush()
    # Runways
    for ap in (dep, arr):
        db_session.add(
            Runway(
                airport_id=ap.id,
                airac_cycle_id=fresh_cycle.id,
                ident="09",
                reciprocal_ident="27",
                length_ft=10000,
                width_ft=150,
                heading_deg=90,
                surface="ASP",
                elevation_ft=0,
            )
        )
    # Fixes
    fix1 = Fix(airac_cycle_id=fresh_cycle.id, ident="TFIX1", latitude=22.0, longitude=73.5)
    fix2 = Fix(airac_cycle_id=fresh_cycle.id, ident="TFIX2", latitude=25.0, longitude=75.5)
    db_session.add_all([fix1, fix2])
    db_session.flush()
    return {"dep": dep, "arr": arr, "fix1": fix1, "fix2": fix2}


@pytest.fixture
def db_session():
    """Yield a session and clean up test data after."""
    with session_scope() as db:
        yield db
    # Cleanup: delete test data
    with session_scope() as db:
        from app.models import AircraftRegistration, AiracCycle, OrganizationMember

        test_cycles = db.scalars(select(AiracCycle).where(AiracCycle.source == "integration-test")).all()
        for c in test_cycles:
            # Delete all flight plans under this cycle first
            db.execute(delete(FlightPlan).where(FlightPlan.airac_cycle_id == c.id))
            # Then nav entities (which depend on the cycle)
            db.execute(delete(Airport).where(Airport.airac_cycle_id == c.id))
            db.execute(delete(Fix).where(Fix.airac_cycle_id == c.id))
            db.delete(c)
        # Test orgs/registrations/users (independent of cycles)
        test_orgs = db.execute(
            select(Organization).where(Organization.name.like("Test Org %"))
        ).scalars().all()
        for o in test_orgs:
            db.execute(delete(OrganizationMember).where(OrganizationMember.organization_id == o.id))
            db.execute(delete(AircraftRegistration).where(AircraftRegistration.organization_id == o.id))
            db.delete(o)
        test_users = db.execute(
            select(User).where(User.email.like("test-%@example.com"))
        ).scalars().all()
        for u in test_users:
            db.delete(u)
        # Test aircraft
        db.execute(delete(AircraftType).where(AircraftType.icao_type.like("T%")))


def test_full_planning_pipeline(db_session, fresh_user, fresh_org, fresh_registration, fresh_cycle, nav_data):
    plan = FlightPlan(
        organization_id=fresh_org.id,
        created_by_id=fresh_user.id,
        airac_cycle_id=fresh_cycle.id,
        status=FlightPlanStatus.DRAFT,
        departure_icao="TST1",
        arrival_icao="TST2",
        alternate_icaos=[],
        aircraft_type_id=fresh_registration.aircraft_type_id,
        aircraft_registration_id=fresh_registration.id,
        passengers=100,
        cargo_kg=500,
        payload_kg=100 * 84.0 + 500,
        route_text="TST1 TFIX1 TFIX2 TST2",
        cruise_altitude_ft=35000,
        cost_index=30,
        fuel_policy={},
    )
    db_session.add(plan)
    db_session.flush()

    result = calculate_flight_plan(db_session, plan)
    assert plan.status == FlightPlanStatus.CALCULATED
    assert result["total_distance_nm"] > 500
    assert result["estimated_time_enroute_seconds"] > 0
    assert result["block_fuel_kg"] > 0
    # legs persisted
    assert len(plan.legs) > 0
    # calculation persisted
    assert plan.calculations is not None
    assert plan.calculations.total_distance_nm > 0
    # fuel persisted
    assert plan.fuel is not None
    assert plan.fuel.block_kg > 0
    # weights persisted
    assert plan.weights is not None
    assert plan.weights.tow_kg > 0
    assert plan.weights.lw_kg > 0
    # No critical warnings for a reasonable flight
    critical = [w for w in plan.warnings if w.severity == "CRITICAL"]
    assert not critical


def test_pipeline_detects_critical_tow_exceedance(db_session, fresh_user, fresh_org, fresh_cycle, nav_data):
    """Force an impossible payload that should trip TOW > MTOW."""
    small_ac = AircraftType(
        icao_type=f"TINY{uuid.uuid4().hex[:4].upper()}",
        manufacturer="Test",
        model="Tiny",
        mtow_kg=10000,  # very low
        mlw_kg=9000,
        mzfw_kg=8000,
        oew_kg=5000,
        fuel_capacity_kg=2000,
        cruise_mach=0.5,
        cruise_tas_kts=250,
        max_altitude_ft=25000,
    )
    db_session.add(small_ac)
    db_session.flush()
    reg = AircraftRegistration(
        aircraft_type_id=small_ac.id,
        organization_id=fresh_org.id,
        registration=f"TINY-{uuid.uuid4().hex[:6]}",
    )
    db_session.add(reg)
    db_session.flush()
    plan = FlightPlan(
        organization_id=fresh_org.id,
        created_by_id=fresh_user.id,
        airac_cycle_id=fresh_cycle.id,
        status=FlightPlanStatus.DRAFT,
        departure_icao="TST1",
        arrival_icao="TST2",
        alternate_icaos=[],
        aircraft_type_id=small_ac.id,
        aircraft_registration_id=reg.id,
        passengers=200,
        cargo_kg=5000,
        payload_kg=200 * 84.0 + 5000,
        route_text="TST1 TFIX1 TFIX2 TST2",
        cruise_altitude_ft=20000,
        cost_index=30,
        fuel_policy={},
    )
    db_session.add(plan)
    db_session.flush()
    calculate_flight_plan(db_session, plan)
    codes = {w.code for w in plan.warnings}
    assert "TOW_EXCEEDS_MTOW" in codes
    critical = [w for w in plan.warnings if w.severity == "CRITICAL"]
    assert critical, "Expected at least one CRITICAL warning for an overweight plan"


def test_pipeline_unknown_fix_emits_warning(db_session, fresh_user, fresh_org, fresh_registration, fresh_cycle, nav_data):
    plan = FlightPlan(
        organization_id=fresh_org.id,
        created_by_id=fresh_user.id,
        airac_cycle_id=fresh_cycle.id,
        status=FlightPlanStatus.DRAFT,
        departure_icao="TST1",
        arrival_icao="TST2",
        alternate_icaos=[],
        aircraft_type_id=fresh_registration.aircraft_type_id,
        aircraft_registration_id=fresh_registration.id,
        passengers=10,
        cargo_kg=100,
        payload_kg=10 * 84.0 + 100,
        route_text="TST1 DCT NOEXIST DCT TST2",
        cruise_altitude_ft=20000,
        cost_index=30,
        fuel_policy={},
    )
    db_session.add(plan)
    db_session.flush()
    calculate_flight_plan(db_session, plan)
    codes = {w.code for w in plan.warnings}
    # Either ROUTE_VALIDATION (with the missing fix message) or UNKNOWN_FIX
    assert any("ROUTE" in c or "UNKNOWN" in c for c in codes)
