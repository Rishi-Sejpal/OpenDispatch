"""Tests for fuel service."""

from __future__ import annotations

from app.services.fuel import (
    DEFAULT_POLICY,
    calculate_alternate_fuel,
    calculate_block_fuel,
    calculate_final_reserve,
)


def test_final_reserve_default() -> None:
    # 30 min at 2600 kg/hr = 1300 kg
    assert abs(calculate_final_reserve(DEFAULT_POLICY, 2600.0) - 1300.0) < 1e-6


def test_final_reserve_zero_distance() -> None:
    assert calculate_final_reserve({"final_reserve_minutes": 15}, 1000.0) == 250.0


def test_alternate_fuel_basic() -> None:
    # 100 NM at 200 kt = 0.5 hr * 2600 = 1300 kg
    assert abs(calculate_alternate_fuel(DEFAULT_POLICY, 100.0, 200.0, 2600.0) - 1300.0) < 1e-6


def test_alternate_fuel_zero_distance() -> None:
    assert calculate_alternate_fuel(DEFAULT_POLICY, 0, 200, 2600) == 0


def test_block_fuel_sum() -> None:
    result = calculate_block_fuel(
        policy=DEFAULT_POLICY,
        trip_kg=5000.0,
        alternate_kg=1000.0,
        final_reserve_kg=1300.0,
        extra_kg=0.0,
        additional_kg=0.0,
    )
    # taxi (200) + trip (5000) + contingency (5% of 5000 = 250) + alt (1000) + reserve (1300) = 7750
    assert abs(result.taxi_kg - 200.0) < 1e-6
    assert abs(result.contingency_kg - 250.0) < 1e-6
    assert abs(result.block_kg - 7750.0) < 1e-6
