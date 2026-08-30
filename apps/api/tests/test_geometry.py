"""Tests for aviation-geometry great-circle and wind math."""

from __future__ import annotations

import math

from aviation_geometry import (
    LatLon,
    along_track_distance,
    cross_track_distance,
    destination_point,
    final_bearing,
    great_circle_distance,
    initial_bearing,
    interpolate_position,
    magnetic_heading,
    normalize_degrees,
    normalize_latitude,
    normalize_longitude,
    rhumb_line_distance,
    true_heading_from_magnetic,
)


def test_normalize_degrees() -> None:
    assert normalize_degrees(0) == 0
    assert normalize_degrees(360) == 0
    assert normalize_degrees(-90) == 270
    assert normalize_degrees(720) == 0


def test_normalize_lat_lon() -> None:
    assert normalize_latitude(91) == 90
    assert normalize_latitude(-91) == -90
    assert math.isclose(normalize_longitude(181), -179)
    assert math.isclose(normalize_longitude(-181), 179)


def test_distance_zero() -> None:
    p = LatLon(19.0, 72.0)
    assert great_circle_distance(p, p) < 1e-6


def test_distance_mumbai_delhi() -> None:
    """Mumbai to Delhi great-circle distance should be ~600-700 NM."""
    mum = LatLon(19.0887, 72.8679)
    delh = LatLon(28.5562, 77.1000)
    d = great_circle_distance(mum, delh)
    # Acceptable range: 600-720 NM
    assert 600 < d < 720


def test_distance_symmetric() -> None:
    a = LatLon(0, 0)
    b = LatLon(10, 20)
    assert math.isclose(great_circle_distance(a, b), great_circle_distance(b, a), rel_tol=1e-9)


def test_initial_bearing_north() -> None:
    a = LatLon(0, 0)
    b = LatLon(1, 0)
    assert math.isclose(initial_bearing(a, b), 0.0, abs_tol=0.5)


def test_initial_bearing_east() -> None:
    a = LatLon(0, 0)
    b = LatLon(0, 1)
    assert math.isclose(initial_bearing(a, b), 90.0, abs_tol=0.5)


def test_initial_bearing_south() -> None:
    a = LatLon(0, 0)
    b = LatLon(-1, 0)
    assert math.isclose(initial_bearing(a, b), 180.0, abs_tol=0.5)


def test_initial_bearing_west() -> None:
    a = LatLon(0, 0)
    b = LatLon(0, -1)
    assert math.isclose(initial_bearing(a, b), 270.0, abs_tol=0.5)


def test_final_bearing_north_pole() -> None:
    a = LatLon(0, 0)
    b = LatLon(0.001, 0.001)
    # Going up to near-pole then back; just ensure it returns a valid angle
    fb = final_bearing(a, b)
    assert 0 <= fb < 360


def test_destination_point() -> None:
    a = LatLon(0, 0)
    p = destination_point(a, 0.0, 60.0)  # 60 NM north
    assert math.isclose(p.lat, 1.0, abs_tol=0.01)  # 1 deg lat ~ 60 NM
    assert math.isclose(p.lon, 0.0, abs_tol=0.01)


def test_interpolate_endpoints() -> None:
    a = LatLon(0, 0)
    b = LatLon(10, 0)
    assert math.isclose(interpolate_position(a, b, 0.0).lat, 0.0)
    assert math.isclose(interpolate_position(a, b, 1.0).lat, 10.0, abs_tol=0.001)
    mid = interpolate_position(a, b, 0.5)
    assert math.isclose(mid.lat, 5.0, abs_tol=0.5)


def test_interpolate_clamps() -> None:
    a = LatLon(0, 0)
    b = LatLon(10, 0)
    assert interpolate_position(a, b, -0.5).lat == 0
    assert math.isclose(interpolate_position(a, b, 1.5).lat, 10.0, abs_tol=0.001)


def test_cross_track_zero() -> None:
    a = LatLon(0, 0)
    b = LatLon(10, 0)
    p = LatLon(5, 0)
    assert cross_track_distance(p, a, b) < 1e-6


def test_along_track_at_endpoints() -> None:
    a = LatLon(0, 0)
    b = LatLon(10, 0)
    assert abs(along_track_distance(a, a, b)) < 1e-6
    full = great_circle_distance(a, b)
    assert math.isclose(along_track_distance(b, a, b), full, rel_tol=1e-3)


def test_magnetic_heading_conversion() -> None:
    # Magnetic variation east (positive)
    assert math.isclose(magnetic_heading(90.0, 5.0), 85.0)
    assert math.isclose(magnetic_heading(0.0, -10.0), 10.0)
    # Round trip
    assert math.isclose(true_heading_from_magnetic(magnetic_heading(123.0, -2.5), -2.5), 123.0, abs_tol=1e-6)


def test_rhumb_line_due_north() -> None:
    a = LatLon(0, 0)
    b = LatLon(10, 0)
    # 10 deg lat * 60 NM/deg = 600 NM
    assert math.isclose(rhumb_line_distance(a, b), 600.0, rel_tol=1e-6)
