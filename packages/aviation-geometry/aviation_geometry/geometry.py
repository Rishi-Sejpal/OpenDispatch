"""Great-circle geometry and aviation-specific navigational math.

All angles in degrees unless suffixed `_rad`. All distances in NM.
Uses mean Earth radius from aviation-units.
"""

from __future__ import annotations

import math
from typing import NamedTuple

from aviation_units import EARTH_RADIUS_NM


def _to_rad(deg: float) -> float:
    return deg * math.pi / 180.0


def _to_deg(rad: float) -> float:
    return rad * 180.0 / math.pi


def normalize_degrees(deg: float) -> float:
    return deg % 360.0


def normalize_latitude(deg: float) -> float:
    return max(-90.0, min(90.0, deg))


def normalize_longitude(deg: float) -> float:
    return ((deg + 180.0) % 360.0) - 180.0


class LatLon(NamedTuple):
    lat: float
    lon: float


def great_circle_distance(p1: LatLon, p2: LatLon) -> float:
    """Great-circle distance in nautical miles using the haversine formula."""
    lat1 = _to_rad(p1.lat)
    lat2 = _to_rad(p2.lat)
    dlat = _to_rad(p2.lat - p1.lat)
    dlon = _to_rad(p2.lon - p1.lon)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(min(1.0, math.sqrt(a)))
    return EARTH_RADIUS_NM * c


def initial_bearing(p1: LatLon, p2: LatLon) -> float:
    """Initial true bearing from p1 to p2 (degrees, 0-360)."""
    lat1 = _to_rad(p1.lat)
    lat2 = _to_rad(p2.lat)
    dlon = _to_rad(p2.lon - p1.lon)
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = _to_deg(math.atan2(y, x))
    return normalize_degrees(bearing)


def final_bearing(p1: LatLon, p2: LatLon) -> float:
    """Final true bearing into p2 along the great circle from p1."""
    return normalize_degrees(initial_bearing(p2, p1) + 180.0)


def interpolate_position(p1: LatLon, p2: LatLon, fraction: float) -> LatLon:
    """Slerp-style interpolation along the great circle. fraction in [0, 1]."""
    if fraction <= 0.0:
        return LatLon(p1.lat, p1.lon)
    if fraction >= 1.0:
        return LatLon(p2.lat, p2.lon)
    lat1 = _to_rad(p1.lat)
    lon1 = _to_rad(p1.lon)
    lat2 = _to_rad(p2.lat)
    lon2 = _to_rad(p2.lon)
    d = 2 * math.asin(
        math.sqrt(
            math.sin((lat2 - lat1) / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
        )
    )
    if d == 0:
        return LatLon(p1.lat, p1.lon)
    a = math.sin((1 - fraction) * d) / math.sin(d)
    b = math.sin(fraction * d) / math.sin(d)
    x = a * math.cos(lat1) * math.cos(lon1) + b * math.cos(lat2) * math.cos(lon2)
    y = a * math.cos(lat1) * math.sin(lon1) + b * math.cos(lat2) * math.sin(lon2)
    z = a * math.sin(lat1) + b * math.sin(lat2)
    lat = math.atan2(z, math.sqrt(x * x + y * y))
    lon = math.atan2(y, x)
    return LatLon(_to_deg(lat), _to_deg(lon))


def destination_point(start: LatLon, bearing_deg: float, distance_nm: float) -> LatLon:
    """Project a point from `start` along the given true bearing for distance_nm NM."""
    lat1 = _to_rad(start.lat)
    lon1 = _to_rad(start.lon)
    brg = _to_rad(bearing_deg)
    d = distance_nm / EARTH_RADIUS_NM
    lat2 = math.asin(math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(brg))
    lon2 = lon1 + math.atan2(
        math.sin(brg) * math.sin(d) * math.cos(lat1),
        math.cos(d) - math.sin(lat1) * math.sin(lat2),
    )
    return LatLon(_to_deg(lat2), _to_deg(lon2))


def cross_track_distance(p: LatLon, line_start: LatLon, line_end: LatLon) -> float:
    """Unsigned cross-track distance in NM from point p to the great circle line_start -> line_end.

    Uses Vincenty's formula on a sphere.
    """
    d13 = great_circle_distance(line_start, p) / EARTH_RADIUS_NM
    theta13 = _to_rad(initial_bearing(line_start, p))
    theta12 = _to_rad(initial_bearing(line_start, line_end))
    xt = math.asin(math.sin(d13) * math.sin(theta13 - theta12))
    return abs(xt) * EARTH_RADIUS_NM


def along_track_distance(p: LatLon, line_start: LatLon, line_end: LatLon) -> float:
    """Along-track distance in NM (signed) from line_start to the perpendicular foot of p."""
    d13 = great_circle_distance(line_start, p) / EARTH_RADIUS_NM
    theta12 = _to_rad(initial_bearing(line_start, line_end))
    theta13 = _to_rad(initial_bearing(line_start, p))
    cos_xt = math.cos(d13) * math.cos(theta13 - theta12)
    if abs(cos_xt) < 1e-12:
        return 0.0
    dat = math.acos(max(-1.0, min(1.0, cos_xt)))
    if math.sin(theta13 - theta12) < 0:
        dat = -dat
    return dat * EARTH_RADIUS_NM


def magnetic_heading(true_heading_deg: float, magnetic_variation_deg: float) -> float:
    """Convert true heading to magnetic heading.

    magnetic_variation is positive for east, negative for west.
    Magnetic = True - Variation
    """
    return normalize_degrees(true_heading_deg - magnetic_variation_deg)


def true_heading_from_magnetic(magnetic_heading_deg: float, magnetic_variation_deg: float) -> float:
    return normalize_degrees(magnetic_heading_deg + magnetic_variation_deg)


def rhumb_line_distance(p1: LatLon, p2: LatLon) -> float:
    """Distance in NM along a rhumb line (constant true bearing)."""
    if abs(p2.lat - p1.lat) < 1e-9:
        return abs(p2.lon - p1.lon) * math.cos(_to_rad(p1.lat)) * 60
    dlat = p2.lat - p1.lat
    dlon = p2.lon - p1.lon
    psi = math.log(
        math.tan(math.pi / 4 + _to_rad(p2.lat) / 2)
        / math.tan(math.pi / 4 + _to_rad(p1.lat) / 2)
    )
    q = dlat / psi if abs(psi) > 1e-12 else math.cos(_to_rad(p1.lat))
    delta_psi = math.sqrt(dlat * dlat + q * q * dlon * dlon)
    return delta_psi * 60
