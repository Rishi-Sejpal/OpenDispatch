"""SQLAlchemy models for OpenDispatch.

These cover the full domain: identity, organizations, navigation, aircraft,
flight plans, dispatch, documents, audit.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


def _now() -> datetime:
    return datetime.now(tz=timezone.utc)


# ------------------------------------------------------------------ enums


class UserRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    DISPATCHER = "DISPATCHER"
    PILOT = "PILOT"
    VIEWER = "VIEWER"


class FlightPlanStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    CALCULATED = "CALCULATED"
    GENERATED = "GENERATED"
    DISPATCHED = "DISPATCHED"
    ARCHIVED = "ARCHIVED"


class AiracImportStatus(str, enum.Enum):
    PENDING = "PENDING"
    IMPORTING = "IMPORTING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class ProcedureKind(str, enum.Enum):
    SID = "SID"
    STAR = "STAR"
    APPROACH = "APPROACH"


class LegType(str, enum.Enum):
    COURSE_TO_FIX = "CF"
    TRACK_TO_FIX = "TF"
    DIRECT_TO_FIX = "DF"
    FIX_TO_ALTITUDE = "FA"
    FIX_TO_MANUAL_TERMINATION = "FM"
    COURSE_TO_ALTITUDE = "CA"
    COURSE_TO_RADIAL = "CR"
    COURSE_TO_DME = "CD"
    INITIAL_FIX = "IF"
    INITIAL_APPROACH_FIX = "IAF"
    INTERMEDIATE_FIX = "IFR"
    FINAL_APPROACH_FIX = "FAF"
    MISSED_APPROACH_POINT = "MAP"
    HOLD_TO_ALTITUDE = "HA"
    HOLD_TO_FIX = "HF"
    HOLD_TO_MANUAL_TERMINATION = "HM"
    ROUTE = "ROUTE"
    AIRWAY = "AIRWAY"


class FixRole(str, enum.Enum):
    WAYPOINT = "WAYPOINT"
    VOR = "VOR"
    NDB = "NDB"
    DME = "DME"
    AIRPORT = "AIRPORT"
    RUNWAY = "RUNWAY"


# ------------------------------------------------------------------ identity


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    memberships: Mapped[list["OrganizationMember"]] = relationship(back_populates="user")
    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    refresh_jti: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    user: Mapped[User] = relationship(back_populates="sessions")


# ------------------------------------------------------------------ orgs


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    icao_code: Mapped[str | None] = mapped_column(String(8), nullable=True)
    iata_code: Mapped[str | None] = mapped_column(String(4), nullable=True)
    default_fuel_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    default_units: Mapped[str] = mapped_column(String(16), nullable=False, default="kg/NM/ft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    members: Mapped[list["OrganizationMember"]] = relationship(back_populates="organization")
    aircraft: Mapped[list["AircraftRegistration"]] = relationship(back_populates="organization")
    flight_plans: Mapped[list["FlightPlan"]] = relationship(back_populates="organization")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_user"),)

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False, default=UserRole.VIEWER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    organization: Mapped[Organization] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


# ------------------------------------------------------------------ AIRAC


class AiracCycle(Base):
    __tablename__ = "airac_cycles"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    cycle: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True)  # e.g. 2401
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False, default="manual")
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    import_status: Mapped[AiracImportStatus] = mapped_column(
        Enum(AiracImportStatus, name="airac_import_status"), nullable=False, default=AiracImportStatus.PENDING
    )
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ------------------------------------------------------------------ navigation


class Airport(Base):
    __tablename__ = "airports"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    airac_cycle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("airac_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    icao: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    iata: Mapped[str | None] = mapped_column(String(4), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    region: Mapped[str | None] = mapped_column(String(120), nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_ft: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    magnetic_variation: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="UTC")
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)
    has_procedures: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        UniqueConstraint("airac_cycle_id", "icao", name="uq_airport_cycle_icao"),
        Index("ix_airports_location", "location", postgresql_using="gist"),
    )


class Runway(Base):
    __tablename__ = "runways"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    airport_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("airports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    airac_cycle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("airac_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ident: Mapped[str] = mapped_column(String(8), nullable=False)  # e.g. "09L"
    reciprocal_ident: Mapped[str | None] = mapped_column(String(8), nullable=True)
    length_ft: Mapped[float] = mapped_column(Float, nullable=False)
    width_ft: Mapped[float] = mapped_column(Float, nullable=False)
    heading_deg: Mapped[float] = mapped_column(Float, nullable=False)
    surface: Mapped[str] = mapped_column(String(40), nullable=False, default="ASP")
    elevation_ft: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ils_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ils_category: Mapped[str | None] = mapped_column(String(4), nullable=True)  # CAT I/II/III
    lighting: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (UniqueConstraint("airport_id", "ident", name="uq_runway_airport_ident"),)


class Fix(Base):
    """Combined waypoint / navaid storage. Use `role` to differentiate."""

    __tablename__ = "fixes"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    airac_cycle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("airac_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ident: Mapped[str] = mapped_column(String(12), nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role: Mapped[FixRole] = mapped_column(Enum(FixRole, name="fix_role"), nullable=False, default=FixRole.WAYPOINT)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    elevation_ft: Mapped[float | None] = mapped_column(Float, nullable=True)
    magnetic_variation: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    frequency_khz: Mapped[float | None] = mapped_column(Float, nullable=True)  # for NDB
    frequency_mhz: Mapped[float | None] = mapped_column(Float, nullable=True)  # for VOR/DME
    region: Mapped[str | None] = mapped_column(String(80), nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    location = mapped_column(Geography(geometry_type="POINT", srid=4326), nullable=True)

    __table_args__ = (
        UniqueConstraint("airac_cycle_id", "ident", name="uq_fix_cycle_ident"),
        Index("ix_fixes_location", "location", postgresql_using="gist"),
    )


class Airway(Base):
    __tablename__ = "airways"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    airac_cycle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("airac_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ident: Mapped[str] = mapped_column(String(12), nullable=False, index=True)  # e.g. "A466"
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    type: Mapped[str] = mapped_column(String(8), nullable=False, default="U")  # U/H/A (jet/rnav/other)
    direction: Mapped[str | None] = mapped_column(String(8), nullable=True)  # N/S/E/W or null=both

    __table_args__ = (UniqueConstraint("airac_cycle_id", "ident", name="uq_airway_cycle_ident"),)


class AirwaySegment(Base):
    __tablename__ = "airway_segments"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    airway_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("airways.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    from_fix_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("fixes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    to_fix_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("fixes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    distance_nm: Mapped[float] = mapped_column(Float, nullable=False)
    magnetic_course: Mapped[float] = mapped_column(Float, nullable=False)
    minimum_altitude_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    maximum_altitude_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (UniqueConstraint("airway_id", "sequence", name="uq_airway_segment_seq"),)


class Procedure(Base):
    __tablename__ = "procedures"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    airac_cycle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("airac_cycles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    airport_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("airports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)  # e.g. "ARRIB"
    kind: Mapped[ProcedureKind] = mapped_column(Enum(ProcedureKind, name="procedure_kind"), nullable=False)
    runway_ident: Mapped[str | None] = mapped_column(String(8), nullable=True, index=True)
    reference_fix_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("fixes.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (UniqueConstraint("airac_cycle_id", "airport_id", "name", "kind", "runway_ident", name="uq_proc"),)


class ProcedureTransition(Base):
    __tablename__ = "procedure_transitions"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    procedure_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("procedures.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)  # transition name or "ALL"
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)


class ProcedureLeg(Base):
    __tablename__ = "procedure_legs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    procedure_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("procedures.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transition_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("procedure_transitions.id", ondelete="CASCADE"), nullable=True, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    leg_type: Mapped[LegType] = mapped_column(Enum(LegType, name="leg_type"), nullable=False)
    fix_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("fixes.id", ondelete="SET NULL"), nullable=True
    )
    course_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_nm: Mapped[float | None] = mapped_column(Float, nullable=True)
    altitude_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    speed_kts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fly_over: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)


# ------------------------------------------------------------------ aircraft


class AircraftType(Base):
    __tablename__ = "aircraft_types"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    icao_type: Mapped[str] = mapped_column(String(8), unique=True, nullable=False, index=True)  # e.g. A320
    manufacturer: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    variant: Mapped[str | None] = mapped_column(String(40), nullable=True)
    wake_category: Mapped[str] = mapped_column(String(4), nullable=False, default="M")
    engine_type: Mapped[str] = mapped_column(String(40), nullable=False, default="JET")
    engines: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    mtow_kg: Mapped[float] = mapped_column(Float, nullable=False)
    mlw_kg: Mapped[float] = mapped_column(Float, nullable=False)
    mzfw_kg: Mapped[float] = mapped_column(Float, nullable=False)
    oew_kg: Mapped[float] = mapped_column(Float, nullable=False)
    fuel_capacity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    passenger_capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cargo_capacity_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_altitude_ft: Mapped[int] = mapped_column(Integer, nullable=False, default=41000)
    cruise_mach: Mapped[float] = mapped_column(Float, nullable=False, default=0.78)
    cruise_tas_kts: Mapped[int] = mapped_column(Integer, nullable=False, default=450)
    approach_speed_kts: Mapped[int] = mapped_column(Integer, nullable=False, default=140)
    initial_climb_alt_ft: Mapped[int] = mapped_column(Integer, nullable=False, default=5000)
    initial_cruise_alt_ft: Mapped[int] = mapped_column(Integer, nullable=False, default=35000)
    climb_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    cruise_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    descent_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    fuel_burn_model: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )


class AircraftRegistration(Base):
    __tablename__ = "aircraft_registrations"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    aircraft_type_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("aircraft_types.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    registration: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    nickname: Mapped[str | None] = mapped_column(String(120), nullable=True)
    fuel_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    aircraft_type = relationship("AircraftType")
    organization: Mapped[Organization] = relationship(back_populates="aircraft")


# ------------------------------------------------------------------ weather


class WeatherReport(Base):
    __tablename__ = "weather_reports"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    airport_icao: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="local")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metar_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    taf_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    parsed: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


class WindsAloftReport(Base):
    __tablename__ = "winds_aloft_reports"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_to: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="local")
    data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)


# ------------------------------------------------------------------ flight plans


class FlightPlan(Base):
    __tablename__ = "flight_plans"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    airac_cycle_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("airac_cycles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[FlightPlanStatus] = mapped_column(
        Enum(FlightPlanStatus, name="flight_plan_status"), nullable=False, default=FlightPlanStatus.DRAFT
    )
    callsign: Mapped[str | None] = mapped_column(String(16), nullable=True)
    flight_number: Mapped[str | None] = mapped_column(String(16), nullable=True)

    departure_icao: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    arrival_icao: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    alternate_icaos: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    aircraft_type_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("aircraft_types.id", ondelete="SET NULL"), nullable=True
    )
    aircraft_registration_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("aircraft_registrations.id", ondelete="SET NULL"), nullable=True
    )

    passengers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cargo_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payload_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    route_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sid_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("procedures.id", ondelete="SET NULL"), nullable=True
    )
    star_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("procedures.id", ondelete="SET NULL"), nullable=True
    )
    approach_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("procedures.id", ondelete="SET NULL"), nullable=True
    )
    departure_runway_ident: Mapped[str | None] = mapped_column(String(8), nullable=True)
    arrival_runway_ident: Mapped[str | None] = mapped_column(String(8), nullable=True)

    cruise_altitude_ft: Mapped[int] = mapped_column(Integer, nullable=False, default=35000)
    cost_index: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    cruise_tas_kts: Mapped[int | None] = mapped_column(Integer, nullable=True)

    fuel_policy: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    scheduled_off_block: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_takeoff: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_landing: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    calculation_engine_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    aircraft_performance_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    weather_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("weather_reports.id", ondelete="SET NULL"), nullable=True
    )

    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dispatched_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    organization: Mapped[Organization] = relationship(back_populates="flight_plans")
    legs: Mapped[list["FlightPlanLeg"]] = relationship(
        back_populates="flight_plan", cascade="all, delete-orphan", order_by="FlightPlanLeg.sequence"
    )
    calculations: Mapped["FlightPlanCalculation | None"] = relationship(
        back_populates="flight_plan", cascade="all, delete-orphan", uselist=False
    )
    weights: Mapped["FlightPlanWeight | None"] = relationship(
        back_populates="flight_plan", cascade="all, delete-orphan", uselist=False
    )
    fuel: Mapped["FlightPlanFuel | None"] = relationship(
        back_populates="flight_plan", cascade="all, delete-orphan", uselist=False
    )
    documents: Mapped[list["GeneratedDocument"]] = relationship(
        back_populates="flight_plan", cascade="all, delete-orphan"
    )
    warnings: Mapped[list["FlightPlanWarning"]] = relationship(
        back_populates="flight_plan", cascade="all, delete-orphan"
    )


class FlightPlanLeg(Base):
    __tablename__ = "flight_plan_legs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    flight_plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("flight_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    ident: Mapped[str] = mapped_column(String(16), nullable=False)
    leg_type: Mapped[str] = mapped_column(String(20), nullable=False, default="ENROUTE")
    procedure_leg_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("procedure_legs.id", ondelete="SET NULL"), nullable=True
    )
    airway_ident: Mapped[str | None] = mapped_column(String(16), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    course_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_nm: Mapped[float | None] = mapped_column(Float, nullable=True)
    cumulative_distance_nm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    altitude_ft: Mapped[int | None] = mapped_column(Integer, nullable=True)
    speed_kts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wind_direction_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_kts: Mapped[float | None] = mapped_column(Float, nullable=True)
    air_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    true_air_speed_kts: Mapped[float | None] = mapped_column(Float, nullable=True)
    ground_speed_kts: Mapped[float | None] = mapped_column(Float, nullable=True)
    eta_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fuel_used_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    fuel_remaining_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)

    flight_plan: Mapped[FlightPlan] = relationship(back_populates="legs")


class FlightPlanCalculation(Base):
    __tablename__ = "flight_plan_calculations"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    flight_plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("flight_plans.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    total_distance_nm: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    estimated_time_enroute_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_ground_speed_kts: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cruise_ground_speed_kts: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    climb_fuel_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cruise_fuel_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    descent_fuel_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    approach_fuel_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    extra_fuel_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    outputs: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    formulas: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    flight_plan: Mapped[FlightPlan] = relationship(back_populates="calculations")


class FlightPlanWeight(Base):
    __tablename__ = "flight_plan_weights"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    flight_plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("flight_plans.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    oew_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    payload_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    zfw_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    takeoff_fuel_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    tow_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    landing_fuel_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    lw_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    flight_plan: Mapped[FlightPlan] = relationship(back_populates="weights")


class FlightPlanFuel(Base):
    __tablename__ = "flight_plan_fuel"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    flight_plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("flight_plans.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    taxi_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    trip_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    contingency_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    alternate_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    final_reserve_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    additional_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    extra_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    block_kg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    policy_used: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    flight_plan: Mapped[FlightPlan] = relationship(back_populates="fuel")


class FlightPlanWarning(Base):
    __tablename__ = "flight_plan_warnings"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    flight_plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("flight_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="INFO")
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    flight_plan: Mapped[FlightPlan] = relationship(back_populates="warnings")


# ------------------------------------------------------------------ documents


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    flight_plan_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("flight_plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doc_type: Mapped[str] = mapped_column(String(40), nullable=False)  # OFP / NAV_LOG / FUEL / WEIGHT
    template_version: Mapped[str] = mapped_column(String(16), nullable=False, default="1")
    storage_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(200), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(80), nullable=False, default="application/pdf")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    flight_plan: Mapped[FlightPlan] = relationship(back_populates="documents")


# ------------------------------------------------------------------ audit


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=_uuid)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
