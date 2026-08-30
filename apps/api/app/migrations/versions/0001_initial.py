"""Initial schema for OpenDispatch.

Revision ID: 0001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Required extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # ------------------------------------------------------------ enums
    user_role = postgresql.ENUM(
        "OWNER", "ADMIN", "DISPATCHER", "PILOT", "VIEWER", name="user_role", create_type=True
    )
    flight_plan_status = postgresql.ENUM(
        "DRAFT", "VALIDATED", "CALCULATED", "GENERATED", "DISPATCHED", "ARCHIVED",
        name="flight_plan_status", create_type=True,
    )
    airac_import_status = postgresql.ENUM(
        "PENDING", "IMPORTING", "COMPLETE", "FAILED",
        name="airac_import_status", create_type=True,
    )
    procedure_kind = postgresql.ENUM(
        "SID", "STAR", "APPROACH", name="procedure_kind", create_type=True
    )
    leg_type = postgresql.ENUM(
        "CF", "TF", "DF", "FA", "FM", "CA", "CR", "CD", "IF", "IAF", "IFR", "FAF",
        "MAP", "HA", "HF", "HM", "ROUTE", "AIRWAY",
        name="leg_type", create_type=True,
    )
    fix_role = postgresql.ENUM(
        "WAYPOINT", "VOR", "NDB", "DME", "AIRPORT", "RUNWAY",
        name="fix_role", create_type=True,
    )

    user_role.create(op.get_bind(), checkfirst=True)
    flight_plan_status.create(op.get_bind(), checkfirst=True)
    airac_import_status.create(op.get_bind(), checkfirst=True)
    procedure_kind.create(op.get_bind(), checkfirst=True)
    leg_type.create(op.get_bind(), checkfirst=True)
    fix_role.create(op.get_bind(), checkfirst=True)

    # ------------------------------------------------------------ identity
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(254), nullable=False, unique=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_superuser", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("is_email_verified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_jti", sa.String(64), nullable=False, unique=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("ix_user_sessions_refresh_jti", "user_sessions", ["refresh_jti"])

    # ------------------------------------------------------------ orgs
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("icao_code", sa.String(8), nullable=True),
        sa.Column("iata_code", sa.String(4), nullable=True),
        sa.Column("default_fuel_policy", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("default_units", sa.String(16), nullable=False, server_default="kg/NM/ft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    op.create_table(
        "organization_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", postgresql.ENUM(name="user_role", create_type=False), nullable=False, server_default="VIEWER"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )
    op.create_index("ix_organization_members_organization_id", "organization_members", ["organization_id"])
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])

    # ------------------------------------------------------------ AIRAC
    op.create_table(
        "airac_cycles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("cycle", sa.String(8), nullable=False, unique=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(80), nullable=False, server_default="manual"),
        sa.Column("version", sa.String(32), nullable=False, server_default="1"),
        sa.Column("import_status", postgresql.ENUM(name="airac_import_status", create_type=False), nullable=False, server_default="PENDING"),
        sa.Column("checksum", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_airac_cycles_cycle", "airac_cycles", ["cycle"])

    # ------------------------------------------------------------ navigation
    op.create_table(
        "airports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("airac_cycle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("airac_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("icao", sa.String(8), nullable=False),
        sa.Column("iata", sa.String(4), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("city", sa.String(120), nullable=True),
        sa.Column("country", sa.String(120), nullable=True),
        sa.Column("region", sa.String(120), nullable=True),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("elevation_ft", sa.Float, nullable=False, server_default="0"),
        sa.Column("magnetic_variation", sa.Float, nullable=False, server_default="0"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
        sa.Column("location", geoalchemy2.types.Geography(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("has_procedures", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("attributes", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.UniqueConstraint("airac_cycle_id", "icao", name="uq_airport_cycle_icao"),
    )
    op.create_index("ix_airports_icao", "airports", ["icao"])
    op.create_index("ix_airports_iata", "airports", ["iata"])
    op.create_index("ix_airports_airac_cycle_id", "airports", ["airac_cycle_id"])
    op.execute("CREATE INDEX ix_airports_location ON airports USING GIST (location)")

    op.create_table(
        "runways",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("airport_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("airports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("airac_cycle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("airac_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ident", sa.String(8), nullable=False),
        sa.Column("reciprocal_ident", sa.String(8), nullable=True),
        sa.Column("length_ft", sa.Float, nullable=False),
        sa.Column("width_ft", sa.Float, nullable=False),
        sa.Column("heading_deg", sa.Float, nullable=False),
        sa.Column("surface", sa.String(40), nullable=False, server_default="ASP"),
        sa.Column("elevation_ft", sa.Float, nullable=False, server_default="0"),
        sa.Column("ils_available", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("ils_category", sa.String(4), nullable=True),
        sa.Column("lighting", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.UniqueConstraint("airport_id", "ident", name="uq_runway_airport_ident"),
    )
    op.create_index("ix_runways_airport_id", "runways", ["airport_id"])
    op.create_index("ix_runways_airac_cycle_id", "runways", ["airac_cycle_id"])

    op.create_table(
        "fixes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("airac_cycle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("airac_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ident", sa.String(12), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("role", postgresql.ENUM(name="fix_role", create_type=False), nullable=False, server_default="WAYPOINT"),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("elevation_ft", sa.Float, nullable=True),
        sa.Column("magnetic_variation", sa.Float, nullable=False, server_default="0"),
        sa.Column("frequency_khz", sa.Float, nullable=True),
        sa.Column("frequency_mhz", sa.Float, nullable=True),
        sa.Column("region", sa.String(80), nullable=True),
        sa.Column("attributes", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("location", geoalchemy2.types.Geography(geometry_type="POINT", srid=4326), nullable=True),
        sa.UniqueConstraint("airac_cycle_id", "ident", name="uq_fix_cycle_ident"),
    )
    op.create_index("ix_fixes_ident", "fixes", ["ident"])
    op.create_index("ix_fixes_airac_cycle_id", "fixes", ["airac_cycle_id"])
    op.execute("CREATE INDEX ix_fixes_location ON fixes USING GIST (location)")

    op.create_table(
        "airways",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("airac_cycle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("airac_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ident", sa.String(12), nullable=False),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("type", sa.String(8), nullable=False, server_default="U"),
        sa.Column("direction", sa.String(8), nullable=True),
        sa.UniqueConstraint("airac_cycle_id", "ident", name="uq_airway_cycle_ident"),
    )
    op.create_index("ix_airways_ident", "airways", ["ident"])
    op.create_index("ix_airways_airac_cycle_id", "airways", ["airac_cycle_id"])

    op.create_table(
        "airway_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("airway_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("airways.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("from_fix_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fixes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("to_fix_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fixes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("distance_nm", sa.Float, nullable=False),
        sa.Column("magnetic_course", sa.Float, nullable=False),
        sa.Column("minimum_altitude_ft", sa.Integer, nullable=True),
        sa.Column("maximum_altitude_ft", sa.Integer, nullable=True),
        sa.UniqueConstraint("airway_id", "sequence", name="uq_airway_segment_seq"),
    )
    op.create_index("ix_airway_segments_airway_id", "airway_segments", ["airway_id"])
    op.create_index("ix_airway_segments_from_fix_id", "airway_segments", ["from_fix_id"])
    op.create_index("ix_airway_segments_to_fix_id", "airway_segments", ["to_fix_id"])

    op.create_table(
        "procedures",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("airac_cycle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("airac_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("airport_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("airports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("kind", postgresql.ENUM(name="procedure_kind", create_type=False), nullable=False),
        sa.Column("runway_ident", sa.String(8), nullable=True),
        sa.Column("reference_fix_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fixes.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("airac_cycle_id", "airport_id", "name", "kind", "runway_ident", name="uq_proc"),
    )
    op.create_index("ix_procedures_airac_cycle_id", "procedures", ["airac_cycle_id"])
    op.create_index("ix_procedures_airport_id", "procedures", ["airport_id"])
    op.create_index("ix_procedures_name", "procedures", ["name"])
    op.create_index("ix_procedures_runway_ident", "procedures", ["runway_ident"])

    op.create_table(
        "procedure_transitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("procedure_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("procedures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("sequence", sa.Integer, nullable=False),
    )
    op.create_index("ix_procedure_transitions_procedure_id", "procedure_transitions", ["procedure_id"])

    op.create_table(
        "procedure_legs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("procedure_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("procedures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transition_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("procedure_transitions.id", ondelete="CASCADE"), nullable=True),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("leg_type", postgresql.ENUM(name="leg_type", create_type=False), nullable=False),
        sa.Column("fix_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fixes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("course_deg", sa.Float, nullable=True),
        sa.Column("distance_nm", sa.Float, nullable=True),
        sa.Column("altitude_ft", sa.Integer, nullable=True),
        sa.Column("speed_kts", sa.Integer, nullable=True),
        sa.Column("fly_over", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("remarks", sa.String(500), nullable=True),
    )
    op.create_index("ix_procedure_legs_procedure_id", "procedure_legs", ["procedure_id"])
    op.create_index("ix_procedure_legs_transition_id", "procedure_legs", ["transition_id"])
    op.create_index("ix_procedure_legs_fix_id", "procedure_legs", ["fix_id"])

    # ------------------------------------------------------------ aircraft
    op.create_table(
        "aircraft_types",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("icao_type", sa.String(8), nullable=False, unique=True),
        sa.Column("manufacturer", sa.String(120), nullable=False),
        sa.Column("model", sa.String(120), nullable=False),
        sa.Column("variant", sa.String(40), nullable=True),
        sa.Column("wake_category", sa.String(4), nullable=False, server_default="M"),
        sa.Column("engine_type", sa.String(40), nullable=False, server_default="JET"),
        sa.Column("engines", sa.Integer, nullable=False, server_default="2"),
        sa.Column("mtow_kg", sa.Float, nullable=False),
        sa.Column("mlw_kg", sa.Float, nullable=False),
        sa.Column("mzfw_kg", sa.Float, nullable=False),
        sa.Column("oew_kg", sa.Float, nullable=False),
        sa.Column("fuel_capacity_kg", sa.Float, nullable=False),
        sa.Column("passenger_capacity", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cargo_capacity_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("max_altitude_ft", sa.Integer, nullable=False, server_default="41000"),
        sa.Column("cruise_mach", sa.Float, nullable=False, server_default="0.78"),
        sa.Column("cruise_tas_kts", sa.Integer, nullable=False, server_default="450"),
        sa.Column("approach_speed_kts", sa.Integer, nullable=False, server_default="140"),
        sa.Column("initial_climb_alt_ft", sa.Integer, nullable=False, server_default="5000"),
        sa.Column("initial_cruise_alt_ft", sa.Integer, nullable=False, server_default="35000"),
        sa.Column("climb_profile", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("cruise_profile", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("descent_profile", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("fuel_burn_model", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_aircraft_types_icao_type", "aircraft_types", ["icao_type"])

    op.create_table(
        "aircraft_registrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("aircraft_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("aircraft_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("registration", sa.String(16), nullable=False, unique=True),
        sa.Column("nickname", sa.String(120), nullable=True),
        sa.Column("fuel_policy", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_aircraft_registrations_aircraft_type_id", "aircraft_registrations", ["aircraft_type_id"])
    op.create_index("ix_aircraft_registrations_organization_id", "aircraft_registrations", ["organization_id"])
    op.create_index("ix_aircraft_registrations_registration", "aircraft_registrations", ["registration"])

    # ------------------------------------------------------------ weather
    op.create_table(
        "weather_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("airport_icao", sa.String(8), nullable=False),
        sa.Column("source", sa.String(40), nullable=False, server_default="local"),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metar_raw", sa.Text, nullable=True),
        sa.Column("taf_raw", sa.Text, nullable=True),
        sa.Column("parsed", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_weather_reports_airport_icao", "weather_reports", ["airport_icao"])

    op.create_table(
        "winds_aloft_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(40), nullable=False, server_default="local"),
        sa.Column("data", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # ------------------------------------------------------------ flight plans
    op.create_table(
        "flight_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("airac_cycle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("airac_cycles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", postgresql.ENUM(name="flight_plan_status", create_type=False), nullable=False, server_default="DRAFT"),
        sa.Column("callsign", sa.String(16), nullable=True),
        sa.Column("flight_number", sa.String(16), nullable=True),
        sa.Column("departure_icao", sa.String(8), nullable=False),
        sa.Column("arrival_icao", sa.String(8), nullable=False),
        sa.Column("alternate_icaos", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("aircraft_type_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("aircraft_types.id", ondelete="SET NULL"), nullable=True),
        sa.Column("aircraft_registration_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("aircraft_registrations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("passengers", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cargo_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("payload_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("route_text", sa.Text, nullable=False, server_default=""),
        sa.Column("sid_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("procedures.id", ondelete="SET NULL"), nullable=True),
        sa.Column("star_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("procedures.id", ondelete="SET NULL"), nullable=True),
        sa.Column("approach_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("procedures.id", ondelete="SET NULL"), nullable=True),
        sa.Column("departure_runway_ident", sa.String(8), nullable=True),
        sa.Column("arrival_runway_ident", sa.String(8), nullable=True),
        sa.Column("cruise_altitude_ft", sa.Integer, nullable=False, server_default="35000"),
        sa.Column("cost_index", sa.Integer, nullable=False, server_default="30"),
        sa.Column("cruise_tas_kts", sa.Integer, nullable=True),
        sa.Column("fuel_policy", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("scheduled_off_block", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_takeoff", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_landing", sa.DateTime(timezone=True), nullable=True),
        sa.Column("calculation_engine_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("aircraft_performance_version", sa.String(32), nullable=True),
        sa.Column("weather_snapshot_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("weather_reports.id", ondelete="SET NULL"), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dispatched_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_flight_plans_organization_id", "flight_plans", ["organization_id"])
    op.create_index("ix_flight_plans_created_by_id", "flight_plans", ["created_by_id"])
    op.create_index("ix_flight_plans_airac_cycle_id", "flight_plans", ["airac_cycle_id"])
    op.create_index("ix_flight_plans_departure_icao", "flight_plans", ["departure_icao"])
    op.create_index("ix_flight_plans_arrival_icao", "flight_plans", ["arrival_icao"])

    op.create_table(
        "flight_plan_legs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("flight_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("flight_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("ident", sa.String(16), nullable=False),
        sa.Column("leg_type", sa.String(20), nullable=False, server_default="ENROUTE"),
        sa.Column("procedure_leg_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("procedure_legs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("airway_ident", sa.String(16), nullable=True),
        sa.Column("latitude", sa.Float, nullable=True),
        sa.Column("longitude", sa.Float, nullable=True),
        sa.Column("course_deg", sa.Float, nullable=True),
        sa.Column("distance_nm", sa.Float, nullable=True),
        sa.Column("cumulative_distance_nm", sa.Float, nullable=False, server_default="0"),
        sa.Column("altitude_ft", sa.Integer, nullable=True),
        sa.Column("speed_kts", sa.Integer, nullable=True),
        sa.Column("wind_direction_deg", sa.Float, nullable=True),
        sa.Column("wind_speed_kts", sa.Float, nullable=True),
        sa.Column("air_temp_c", sa.Float, nullable=True),
        sa.Column("true_air_speed_kts", sa.Float, nullable=True),
        sa.Column("ground_speed_kts", sa.Float, nullable=True),
        sa.Column("eta_seconds", sa.Integer, nullable=True),
        sa.Column("fuel_used_kg", sa.Float, nullable=True),
        sa.Column("fuel_remaining_kg", sa.Float, nullable=True),
        sa.Column("remarks", sa.String(500), nullable=True),
    )
    op.create_index("ix_flight_plan_legs_flight_plan_id", "flight_plan_legs", ["flight_plan_id"])

    op.create_table(
        "flight_plan_calculations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("flight_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("flight_plans.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("total_distance_nm", sa.Float, nullable=False, server_default="0"),
        sa.Column("estimated_time_enroute_seconds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("average_ground_speed_kts", sa.Float, nullable=False, server_default="0"),
        sa.Column("cruise_ground_speed_kts", sa.Float, nullable=False, server_default="0"),
        sa.Column("climb_fuel_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("cruise_fuel_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("descent_fuel_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("approach_fuel_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("extra_fuel_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("inputs", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("outputs", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("formulas", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "flight_plan_weights",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("flight_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("flight_plans.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("oew_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("payload_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("zfw_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("takeoff_fuel_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("tow_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("landing_fuel_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("lw_kg", sa.Float, nullable=False, server_default="0"),
    )

    op.create_table(
        "flight_plan_fuel",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("flight_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("flight_plans.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("taxi_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("trip_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("contingency_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("alternate_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("final_reserve_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("additional_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("extra_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("block_kg", sa.Float, nullable=False, server_default="0"),
        sa.Column("policy_used", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    op.create_table(
        "flight_plan_warnings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("flight_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("flight_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="INFO"),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("details", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_flight_plan_warnings_flight_plan_id", "flight_plan_warnings", ["flight_plan_id"])

    op.create_table(
        "generated_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("flight_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("flight_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("doc_type", sa.String(40), nullable=False),
        sa.Column("template_version", sa.String(16), nullable=False, server_default="1"),
        sa.Column("storage_uri", sa.String(500), nullable=False),
        sa.Column("file_name", sa.String(200), nullable=False),
        sa.Column("mime_type", sa.String(80), nullable=False, server_default="application/pdf"),
        sa.Column("size_bytes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_generated_documents_flight_plan_id", "generated_documents", ["flight_plan_id"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("target_type", sa.String(80), nullable=True),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_target_id", "audit_logs", ["target_id"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE")
    op.execute("DROP TABLE IF EXISTS generated_documents CASCADE")
    op.execute("DROP TABLE IF EXISTS flight_plan_warnings CASCADE")
    op.execute("DROP TABLE IF EXISTS flight_plan_fuel CASCADE")
    op.execute("DROP TABLE IF EXISTS flight_plan_weights CASCADE")
    op.execute("DROP TABLE IF EXISTS flight_plan_calculations CASCADE")
    op.execute("DROP TABLE IF EXISTS flight_plan_legs CASCADE")
    op.execute("DROP TABLE IF EXISTS flight_plans CASCADE")
    op.execute("DROP TABLE IF EXISTS winds_aloft_reports CASCADE")
    op.execute("DROP TABLE IF EXISTS weather_reports CASCADE")
    op.execute("DROP TABLE IF EXISTS aircraft_registrations CASCADE")
    op.execute("DROP TABLE IF EXISTS aircraft_types CASCADE")
    op.execute("DROP TABLE IF EXISTS procedure_legs CASCADE")
    op.execute("DROP TABLE IF EXISTS procedure_transitions CASCADE")
    op.execute("DROP TABLE IF EXISTS procedures CASCADE")
    op.execute("DROP TABLE IF EXISTS airway_segments CASCADE")
    op.execute("DROP TABLE IF EXISTS airways CASCADE")
    op.execute("DROP TABLE IF EXISTS fixes CASCADE")
    op.execute("DROP TABLE IF EXISTS runways CASCADE")
    op.execute("DROP TABLE IF EXISTS airports CASCADE")
    op.execute("DROP TABLE IF EXISTS airac_cycles CASCADE")
    op.execute("DROP TABLE IF EXISTS organization_members CASCADE")
    op.execute("DROP TABLE IF EXISTS organizations CASCADE")
    op.execute("DROP TABLE IF EXISTS user_sessions CASCADE")
    op.execute("DROP TABLE IF EXISTS users CASCADE")

    bind = op.get_bind()
    sa.Enum(name="user_role").drop(bind, checkfirst=True)
    sa.Enum(name="flight_plan_status").drop(bind, checkfirst=True)
    sa.Enum(name="airac_import_status").drop(bind, checkfirst=True)
    sa.Enum(name="procedure_kind").drop(bind, checkfirst=True)
    sa.Enum(name="leg_type").drop(bind, checkfirst=True)
    sa.Enum(name="fix_role").drop(bind, checkfirst=True)
