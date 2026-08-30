"""Fuel policy + fuel calculation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DEFAULT_POLICY: dict[str, Any] = {
    "taxi_kg": 200.0,
    "contingency_percent": 0.05,  # 5% of trip fuel
    "final_reserve_minutes": 30,   # 30 min holding at 1500 ft
    "extra_kg": 0.0,
    "additional_kg": 0.0,
    "alternate_strategy": "manual",  # "manual" or "automatic"
    "hold_speed_kts": 220,
    "hold_altitude_ft": 1500,
}


@dataclass
class FuelResult:
    taxi_kg: float
    trip_kg: float
    contingency_kg: float
    alternate_kg: float
    final_reserve_kg: float
    additional_kg: float
    extra_kg: float
    block_kg: float

    def to_dict(self) -> dict[str, float]:
        return {
            "taxi_kg": self.taxi_kg,
            "trip_kg": self.trip_kg,
            "contingency_kg": self.contingency_kg,
            "alternate_kg": self.alternate_kg,
            "final_reserve_kg": self.final_reserve_kg,
            "additional_kg": self.additional_kg,
            "extra_kg": self.extra_kg,
            "block_kg": self.block_kg,
        }


def calculate_final_reserve(
    policy: dict[str, Any], aircraft_fuel_burn_kg_per_hr: float
) -> float:
    """Final reserve = hold_time * hold_fuel_flow."""
    minutes = float(policy.get("final_reserve_minutes", DEFAULT_POLICY["final_reserve_minutes"]))
    return aircraft_fuel_burn_kg_per_hr * (minutes / 60.0)


def calculate_alternate_fuel(
    policy: dict[str, Any],
    alternate_distance_nm: float,
    ground_speed_kts: float,
    fuel_burn_kg_per_hr: float,
) -> float:
    if alternate_distance_nm <= 0 or ground_speed_kts <= 0:
        return 0.0
    time_hr = alternate_distance_nm / ground_speed_kts
    return fuel_burn_kg_per_hr * time_hr


def calculate_block_fuel(
    *,
    policy: dict[str, Any],
    trip_kg: float,
    alternate_kg: float,
    final_reserve_kg: float,
    extra_kg: float = 0.0,
    additional_kg: float = 0.0,
    taxi_kg: float | None = None,
) -> FuelResult:
    taxi_kg = taxi_kg if taxi_kg is not None else float(policy.get("taxi_kg", DEFAULT_POLICY["taxi_kg"]))
    contingency_kg = trip_kg * float(policy.get("contingency_percent", DEFAULT_POLICY["contingency_percent"]))
    block_kg = (
        taxi_kg
        + trip_kg
        + contingency_kg
        + alternate_kg
        + final_reserve_kg
        + additional_kg
        + extra_kg
    )
    return FuelResult(
        taxi_kg=taxi_kg,
        trip_kg=trip_kg,
        contingency_kg=contingency_kg,
        alternate_kg=alternate_kg,
        final_reserve_kg=final_reserve_kg,
        additional_kg=additional_kg,
        extra_kg=extra_kg,
        block_kg=block_kg,
    )
