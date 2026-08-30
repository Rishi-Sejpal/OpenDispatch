"""Aircraft performance model.

Uses a documented simplified fuel/performance model. Inputs and outputs are
fully exposed. This is NOT certified performance data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.models import AircraftType
from aviation_units import isa_temp_at_altitude, mach_to_tas_kts


@dataclass
class ClimbResult:
    fuel_kg: float
    time_seconds: float
    distance_nm: float
    profile: list[dict]


@dataclass
class CruiseResult:
    fuel_kg: float
    time_seconds: float
    distance_nm: float
    average_ground_speed_kts: float
    tas_kts: float


@dataclass
class DescentResult:
    fuel_kg: float
    time_seconds: float
    distance_nm: float


@dataclass
class PerformanceContext:
    aircraft: AircraftType
    initial_weight_kg: float
    altitude_ft: int
    temperature_c: float
    wind_direction_deg: float
    wind_speed_kts: float
    cost_index: int = 30


def _isa_delta(context: PerformanceContext) -> float:
    return context.temperature_c - isa_temp_at_altitude(context.altitude_ft)


def _tas_for_mach(aircraft: AircraftType, altitude_ft: int) -> float:
    return mach_to_tas_kts(aircraft.cruise_mach, altitude_ft)


def _ground_speed(tas_kts: float, course_deg: float, wind_dir: float, wind_speed: float) -> float:
    # Wind direction = direction wind is coming from
    course_rad = math.radians(course_deg)
    wind_rad = math.radians(wind_dir)
    wca = 0.0  # ignoring wind correction angle for simplicity
    head = -wind_speed * math.cos(wind_rad - course_rad)
    cross = wind_speed * math.sin(wind_rad - course_rad)
    # Headwind component positive when against course direction
    gs = tas_kts - (-head)  # if head>0 (against), gs = tas - head
    # Simpler: gs = tas - headwind
    headwind = wind_speed * math.cos(wind_rad - course_rad)
    gs_simple = tas_kts - headwind
    return max(50.0, gs_simple)


def calculate_climb(
    context: PerformanceContext, target_altitude_ft: int, course_deg: float = 0.0
) -> ClimbResult:
    """Simplified climb: average ROC and fuel flow.

    For a jet, typical climb rate is ~1500-2500 ft/min, fuel flow ~3000-5000 kg/hr at medium weight.
    This is a documented simplification.
    """
    ac = context.aircraft
    delta_alt = max(0, target_altitude_ft - context.altitude_ft)
    # Climb rate: 1800 ft/min, higher near MTOW, lower near ceiling
    weight_factor = max(0.6, min(1.0, context.initial_weight_kg / ac.mtow_kg))
    roc_fpm = 1500 * weight_factor
    time_min = delta_alt / roc_fpm
    time_seconds = time_min * 60
    # Average ground speed during climb
    avg_alt = (context.altitude_ft + target_altitude_ft) / 2
    tas = _tas_for_mach(ac, avg_alt) * 0.8  # lower during climb
    gs = _ground_speed(tas, course_deg, context.wind_direction_deg, context.wind_speed_kts)
    distance_nm = (gs * time_min) / 60
    # Fuel flow: 3500 kg/hr at 250 KGS climb, weight-dependent
    base_ff_kg_hr = 3000 * (context.initial_weight_kg / ac.mtow_kg) ** 0.8
    fuel_kg = base_ff_kg_hr * (time_min / 60)
    profile = [
        {
            "altitude_ft": target_altitude_ft,
            "time_seconds": time_seconds,
            "distance_nm": distance_nm,
            "fuel_kg": fuel_kg,
            "ground_speed_kts": gs,
        }
    ]
    return ClimbResult(
        fuel_kg=fuel_kg,
        time_seconds=time_seconds,
        distance_nm=distance_nm,
        profile=profile,
    )


def calculate_cruise(
    context: PerformanceContext, distance_nm: float, course_deg: float = 0.0
) -> CruiseResult:
    """Simplified cruise: linear fuel burn vs distance, adjusted for weight."""
    ac = context.aircraft
    tas = _tas_for_mach(ac, context.altitude_ft)
    gs = _ground_speed(tas, course_deg, context.wind_direction_deg, context.wind_speed_kts)
    time_hr = distance_nm / gs
    time_seconds = time_hr * 3600
    # Fuel flow: 2400-2800 kg/hr for A320-class at FL350
    # Cost index scales a little - higher CI = faster but more fuel
    ci_factor = 1.0 + max(-0.15, min(0.15, (context.cost_index - 30) / 200.0))
    base_ff_kg_hr = 2600 * (context.initial_weight_kg / ac.mtow_kg) ** 0.85 * ci_factor
    fuel_kg = base_ff_kg_hr * time_hr
    return CruiseResult(
        fuel_kg=fuel_kg,
        time_seconds=time_seconds,
        distance_nm=distance_nm,
        average_ground_speed_kts=gs,
        tas_kts=tas,
    )


def calculate_descent(
    context: PerformanceContext, target_altitude_ft: int, course_deg: float = 0.0
) -> DescentResult:
    """Simplified descent. Idle descent, ~1800 fpm, low fuel burn."""
    delta_alt = max(0, context.altitude_ft - target_altitude_ft)
    roc_fpm = 1500  # rate of descent, fpm
    time_min = delta_alt / roc_fpm
    time_seconds = time_min * 60
    avg_alt = (context.altitude_ft + target_altitude_ft) / 2
    tas = _tas_for_mach(context.aircraft, avg_alt) * 0.7
    gs = _ground_speed(tas, course_deg, context.wind_direction_deg, context.wind_speed_kts)
    distance_nm = (gs * time_min) / 60
    # Idle fuel: ~600 kg/hr
    fuel_kg = 600 * (time_min / 60)
    return DescentResult(
        fuel_kg=fuel_kg,
        time_seconds=time_seconds,
        distance_nm=distance_nm,
    )


def calculate_fuel_burn(
    context: PerformanceContext, distance_nm: float, course_deg: float = 0.0
) -> dict:
    """Return a full fuel/time breakdown for climb + cruise + descent to a target altitude.

    Default target altitude for descent is 5000 ft (approach).
    """
    climb = calculate_climb(context, context.altitude_ft, course_deg)  # already at cruise
    # we want to actually start from initial cruise and descend
    cruise = calculate_cruise(context, max(0.0, distance_nm - 0.0), course_deg)
    descent = calculate_descent(context, 5000, course_deg)
    return {
        "climb_fuel_kg": climb.fuel_kg,
        "cruise_fuel_kg": cruise.fuel_kg,
        "descent_fuel_kg": descent.fuel_kg,
        "climb_time_seconds": climb.time_seconds,
        "cruise_time_seconds": cruise.time_seconds,
        "descent_time_seconds": descent.time_seconds,
        "climb_distance_nm": climb.distance_nm,
        "descent_distance_nm": descent.distance_nm,
        "ground_speed_kts": cruise.average_ground_speed_kts,
        "tas_kts": cruise.tas_kts,
    }


def calculate_ground_speed(tas_kts: float, course_deg: float, wind_dir: float, wind_spd: float) -> float:
    return _ground_speed(tas_kts, course_deg, wind_dir, wind_spd)


def calculate_time(distance_nm: float, ground_speed_kts: float) -> float:
    if ground_speed_kts <= 0:
        return 0.0
    return (distance_nm / ground_speed_kts) * 3600.0


def calculate_max_altitude(aircraft: AircraftType, weight_kg: float) -> int:
    """Linear approximation: max alt drops with weight from ceiling at OEW to (ceiling - 8000) at MTOW."""
    fraction = max(0.0, min(1.0, (weight_kg - aircraft.oew_kg) / max(1.0, aircraft.mtow_kg - aircraft.oew_kg)))
    return int(aircraft.max_altitude_ft - fraction * 8000.0)
