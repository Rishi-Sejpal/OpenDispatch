"""PDF rendering for OpenDispatch documents using WeasyPrint."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AircraftRegistration,
    AircraftType,
    AiracCycle,
    Airport,
    FlightPlan,
    FlightPlanCalculation,
    FlightPlanFuel,
    FlightPlanWeight,
)

TEMPLATE_VERSION = "1"


def _env() -> Environment:
    base = Path(__file__).resolve().parents[2] / "templates"
    base.mkdir(parents=True, exist_ok=True)
    return Environment(loader=FileSystemLoader(str(base)), autoescape=select_autoescape(["html", "xml"]))


def _fmt_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0h00m"
    h, rem = divmod(seconds, 3600)
    m = rem // 60
    return f"{int(h)}h{int(m):02d}m"


def _format_iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%MZ")


def _flight_plan_context(db: Session, plan: FlightPlan) -> dict[str, Any]:
    cycle = db.get(AiracCycle, plan.airac_cycle_id)
    departure = db.scalar(
        select(Airport).where(
            Airport.airac_cycle_id == plan.airac_cycle_id, Airport.icao == plan.departure_icao
        )
    )
    arrival = db.scalar(
        select(Airport).where(
            Airport.airac_cycle_id == plan.airac_cycle_id, Airport.icao == plan.arrival_icao
        )
    )
    alternates = []
    for icao in plan.alternate_icaos:
        ap = db.scalar(
            select(Airport).where(Airport.airac_cycle_id == plan.airac_cycle_id, Airport.icao == icao)
        )
        if ap is not None:
            alternates.append(ap)
    ac_type = None
    if plan.aircraft_type_id:
        ac_type = db.get(AircraftType, plan.aircraft_type_id)
    if ac_type is None and plan.aircraft_registration_id:
        reg = db.get(AircraftRegistration, plan.aircraft_registration_id)
        if reg is not None:
            ac_type = db.get(AircraftType, reg.aircraft_type_id)
    registration = None
    if plan.aircraft_registration_id:
        registration = db.get(AircraftRegistration, plan.aircraft_registration_id)
    return {
        "plan": plan,
        "cycle": cycle,
        "departure": departure,
        "arrival": arrival,
        "alternates": alternates,
        "aircraft_type": ac_type,
        "registration": registration,
        "calculation": plan.calculations,
        "fuel": plan.fuel,
        "weights": plan.weights,
        "legs": plan.legs,
        "warnings": plan.warnings,
        "documents": plan.documents,
        "generated_at": datetime.now(tz=timezone.utc),
        "fmt_duration": _fmt_duration,
        "format_iso": _format_iso,
        "template_version": TEMPLATE_VERSION,
    }


def render_document(
    db: Session, plan: FlightPlan, doc_type: str
) -> tuple[str, int, str, str] | None:
    """Render a PDF and return (file_path, size_bytes, mime_type, file_name)."""
    base = Path(__file__).resolve().parents[2] / "templates"
    base.mkdir(parents=True, exist_ok=True)
    out_dir = Path("/tmp/opendispatch-pdf")
    out_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{plan.callsign or 'OFP'}-{plan.departure_icao}-{plan.arrival_icao}-{doc_type}.pdf"
    file_path = out_dir / f"{plan.id}-{doc_type}.pdf"

    env = _env()
    context = _flight_plan_context(db, plan)
    if doc_type == "OFP":
        template = env.get_template("ofp.html")
    elif doc_type == "NAV_LOG":
        template = env.get_template("nav_log.html")
    elif doc_type == "FUEL":
        template = env.get_template("fuel.html")
    elif doc_type == "WEIGHT":
        template = env.get_template("weight.html")
    else:
        return None
    html = template.render(**context)
    html_path = out_dir / f"{plan.id}-{doc_type}.html"
    html_path.write_text(html, encoding="utf-8")
    try:
        from weasyprint import HTML
        HTML(string=html, base_url=str(base)).write_pdf(target=str(file_path))
    except Exception:
        # If WeasyPrint system dependencies are missing, still return a placeholder
        placeholder = (
            "OpenDispatch - PDF rendering unavailable. "
            "Ensure WeasyPrint system dependencies are installed (libpango, libcairo, libgdk-pixbuf).\n\n"
            + html
        )
        file_path.write_text(placeholder, encoding="utf-8")
    size = file_path.stat().st_size
    return str(file_path), size, "application/pdf", file_name
