"""Aviation geometry package.

Re-exports the public API for ergonomic `from aviation_geometry import ...` use.
"""

from aviation_geometry.geometry import (
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

__all__ = [
    "LatLon",
    "along_track_distance",
    "cross_track_distance",
    "destination_point",
    "final_bearing",
    "great_circle_distance",
    "initial_bearing",
    "interpolate_position",
    "magnetic_heading",
    "normalize_degrees",
    "normalize_latitude",
    "normalize_longitude",
    "rhumb_line_distance",
    "true_heading_from_magnetic",
]
