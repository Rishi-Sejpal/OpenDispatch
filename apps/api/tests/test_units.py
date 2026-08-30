"""Tests for aviation-units conversions."""

from __future__ import annotations

import math

from aviation_units import (
    EARTH_RADIUS_NM,
    ISA_SEA_LEVEL_TEMP_C,
    ISA_TROPOPAUSE_FT,
    altitude_to_flight_level,
    c_to_f,
    f_to_c,
    flight_level_to_altitude_ft,
    format_ft,
    format_kg,
    format_lb,
    format_nm,
    ft_to_m,
    gal_to_l,
    hpa_to_inhg,
    inhg_to_hpa,
    isa_temp_at_altitude,
    kg_to_lb,
    kmh_to_kt,
    km_to_nm,
    kt_to_kmh,
    l_to_gal,
    lb_to_kg,
    m_to_ft,
    mach_to_tas_kts,
    nm_to_km,
    tas_to_mach,
)


def test_nm_km_roundtrip() -> None:
    assert math.isclose(nm_to_km(1.0), 1.852, rel_tol=1e-6)
    assert math.isclose(km_to_nm(1.852), 1.0, rel_tol=1e-6)


def test_ft_m_roundtrip() -> None:
    assert math.isclose(ft_to_m(1.0), 0.3048, rel_tol=1e-4)
    assert math.isclose(m_to_ft(1.0), 3.280839895, rel_tol=1e-6)


def test_kg_lb_roundtrip() -> None:
    assert math.isclose(kg_to_lb(1.0), 2.20462262185, rel_tol=1e-8)
    assert math.isclose(lb_to_kg(1.0), 0.45359237, rel_tol=1e-6)


def test_temperature_conversion() -> None:
    assert math.isclose(c_to_f(0.0), 32.0)
    assert math.isclose(c_to_f(100.0), 212.0)
    assert math.isclose(f_to_c(32.0), 0.0, abs_tol=1e-6)


def test_kt_kmh_conversion() -> None:
    assert math.isclose(kt_to_kmh(100.0), 185.2, rel_tol=1e-3)
    assert math.isclose(kmh_to_kt(185.2), 100.0, rel_tol=1e-3)


def test_gal_l_conversion() -> None:
    assert math.isclose(gal_to_l(1.0), 3.785411784, rel_tol=1e-6)
    assert math.isclose(l_to_gal(3.785411784), 1.0, rel_tol=1e-6)


def test_hpa_inhg_conversion() -> None:
    assert math.isclose(hpa_to_inhg(1013.25), 29.92, abs_tol=0.01)
    assert math.isclose(inhg_to_hpa(29.92), 1013.21, abs_tol=0.5)


def test_isa_temp_sea_level() -> None:
    assert isa_temp_at_altitude(0) == ISA_SEA_LEVEL_TEMP_C


def test_isa_temp_at_tropopause() -> None:
    assert math.isclose(isa_temp_at_altitude(ISA_TROPOPAUSE_FT), -56.5, abs_tol=0.5)


def test_isa_temp_above_tropopause_is_constant() -> None:
    assert isa_temp_at_altitude(40000) == isa_temp_at_altitude(50000)


def test_mach_to_tas_sea_level() -> None:
    # At sea level ISA, speed of sound ~340 m/s ~ 661 kt; M0.78 -> ~515 kt
    tas = mach_to_tas_kts(0.78, 0)
    assert 500 < tas < 530


def test_mach_to_tas_at_cruise() -> None:
    # At FL350 ISA, speed of sound ~573 kt; M0.78 -> ~447 kt
    tas = mach_to_tas_kts(0.78, 35000)
    assert 430 < tas < 470


def test_tas_to_mach_roundtrip() -> None:
    mach = 0.82
    tas = mach_to_tas_kts(mach, 37000)
    recovered = tas_to_mach(tas, 37000)
    assert math.isclose(recovered, mach, rel_tol=1e-6)


def test_flight_level_helpers() -> None:
    assert flight_level_to_altitude_ft(350) == 35000
    assert altitude_to_flight_level(35000) == 350


def test_earth_radius() -> None:
    assert math.isclose(EARTH_RADIUS_NM, 3440.065, rel_tol=1e-4)


def test_formatters() -> None:
    assert "1.0 NM" in format_nm(1.0)
    assert "kg" in format_kg(1.0)
    assert "lb" in format_lb(1.0)
    assert "ft" in format_ft(1.0)
