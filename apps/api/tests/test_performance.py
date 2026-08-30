"""Tests for aircraft performance service."""

from __future__ import annotations

from app.models import AircraftType
from app.services.aircraft_performance import (
    PerformanceContext,
    _ground_speed,
    calculate_climb,
    calculate_cruise,
    calculate_descent,
    calculate_fuel_burn,
    calculate_max_altitude,
)


def _a320() -> AircraftType:
    return AircraftType(
        icao_type="A320",
        manufacturer="Airbus",
        model="A320-200",
        mtow_kg=78000,
        mlw_kg=66000,
        mzfw_kg=62500,
        oew_kg=42500,
        fuel_capacity_kg=18728,
        cruise_mach=0.78,
        cruise_tas_kts=450,
        max_altitude_ft=39800,
    )


def test_ground_speed_calm_wind() -> None:
    # Calm wind: GS = TAS
    assert abs(_ground_speed(450.0, 90.0, 0.0, 0.0) - 450.0) < 1e-6


def test_ground_speed_headwind() -> None:
    # Wind from 270 blowing east; course 090 (east) -> pure headwind
    # headwind = -wind * cos(270-90) = -50*cos(180) = -50*(-1) = 50
    # GS = TAS - 50 = 400
    assert abs(_ground_speed(450.0, 90.0, 270.0, 50.0) - 400.0) < 1e-6


def test_ground_speed_tailwind() -> None:
    # Wind from 90 blowing west; course 090 -> pure tailwind
    # headwind = -50 * cos(90-90) = -50 -> GS = 450 - (-50) = 500
    assert abs(_ground_speed(450.0, 90.0, 90.0, 50.0) - 500.0) < 1e-6


def test_ground_speed_crosswind() -> None:
    # Wind from 0 blowing south; course 090 -> pure crosswind
    # headwind = -50 * cos(0-90) = -50 * 0 = 0 -> GS = 450
    assert abs(_ground_speed(450.0, 90.0, 0.0, 50.0) - 450.0) < 1e-6


def test_climb_fuel_positive() -> None:
    ac = _a320()
    ctx = PerformanceContext(
        aircraft=ac,
        initial_weight_kg=60000.0,
        altitude_ft=0,
        temperature_c=15.0,
        wind_direction_deg=0.0,
        wind_speed_kts=0.0,
    )
    result = calculate_climb(ctx, 35000)
    assert result.fuel_kg > 0
    assert result.time_seconds > 0
    assert result.distance_nm >= 0


def test_climb_zero_delta_is_zero() -> None:
    """Climbing from current altitude to the same altitude is a no-op."""
    ac = _a320()
    ctx = PerformanceContext(
        aircraft=ac,
        initial_weight_kg=60000.0,
        altitude_ft=35000,
        temperature_c=-54.5,
        wind_direction_deg=0.0,
        wind_speed_kts=0.0,
    )
    result = calculate_climb(ctx, 35000)
    assert result.fuel_kg == 0
    assert result.time_seconds == 0


def test_cruise_distance_proportional() -> None:
    ac = _a320()
    ctx = PerformanceContext(
        aircraft=ac,
        initial_weight_kg=60000.0,
        altitude_ft=35000,
        temperature_c=-54.5,
        wind_direction_deg=0.0,
        wind_speed_kts=0.0,
    )
    short = calculate_cruise(ctx, 100.0)
    long = calculate_cruise(ctx, 500.0)
    assert long.fuel_kg > short.fuel_kg
    assert long.time_seconds > short.time_seconds
    # ~5x distance -> ~5x time (rough)
    assert 4 < long.time_seconds / short.time_seconds < 6


def test_descent_fuel_less_than_cruise() -> None:
    ac = _a320()
    ctx = PerformanceContext(
        aircraft=ac,
        initial_weight_kg=60000.0,
        altitude_ft=35000,
        temperature_c=-54.5,
        wind_direction_deg=0.0,
        wind_speed_kts=0.0,
    )
    # Compare a cruise of ~100NM with a descent that covers the same altitude drop.
    cruise = calculate_cruise(ctx, 100.0)
    descent = calculate_descent(ctx, 5000)
    # Descent uses idle fuel flow; cruise uses much more
    assert descent.fuel_kg < cruise.fuel_kg


def test_fuel_burn_full() -> None:
    ac = _a320()
    ctx = PerformanceContext(
        aircraft=ac,
        initial_weight_kg=60000.0,
        altitude_ft=35000,
        temperature_c=-54.5,
        wind_direction_deg=0.0,
        wind_speed_kts=0.0,
    )
    result = calculate_fuel_burn(ctx, 500.0)
    assert "climb_fuel_kg" in result
    assert "cruise_fuel_kg" in result
    assert "descent_fuel_kg" in result
    assert result["cruise_fuel_kg"] > 0


def test_max_altitude_at_oew_higher() -> None:
    ac = _a320()
    at_oew = calculate_max_altitude(ac, ac.oew_kg)
    at_mtow = calculate_max_altitude(ac, ac.mtow_kg)
    assert at_oew > at_mtow
    assert at_oew <= ac.max_altitude_ft
