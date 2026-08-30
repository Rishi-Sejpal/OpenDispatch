# Aviation calculations

This document describes the simplified, open-source performance and planning
models used by OpenDispatch. They are intended for **planning, training, and
simulation only**. They are **NOT** certified operational data and must not be
used to dispatch a real aircraft without cross-checking against approved
aircraft performance manuals.

## Units

All internal calculations use:

- distance: **NM** (nautical miles)
- altitude: **ft** (feet)
- speed: **kt** (knots)
- mass/fuel: **kg**
- temperature: **°C**
- pressure: **hPa**
- angles: **degrees**
- time: **seconds**

Conversions to and from kg/lb, NM/km, ft/m, kt/km/h, gal/L are explicit; the
runtime never silently mixes units.

## Geometry

`packages/aviation-geometry` provides:

- `great_circle_distance(LatLon, LatLon) -> float` (NM) — haversine on a sphere
  with `EARTH_RADIUS_NM = 3440.065`.
- `initial_bearing(LatLon, LatLon) -> float` (degrees true, 0–360).
- `final_bearing(...)`, `interpolate_position(...)` (slerp), `destination_point(...)`.
- `cross_track_distance(point, line_start, line_end) -> float` (NM).
- `along_track_distance(point, line_start, line_end) -> float` (NM, signed).
- `magnetic_heading(true, variation) -> float` (Magnetic = True − variation;
  variation is positive east, negative west).
- `rhumb_line_distance(...)`.

All functions are pure and tested in `apps/api/tests/test_geometry.py`.

## Wind

Wind direction is **meteorological FROM** (the direction the wind is blowing
*from*). Ground speed is:

```
headwind = -wind_spd * cos(wind_dir_rad - course_rad)
GS       = TAS - headwind
```

A pure headwind (wind from opposite to course) reduces GS; a pure tailwind
increases it. Wind correction angle is currently ignored (assumes the aircraft
flies the rhumb track).

## Aircraft performance

`apps/api/app/services/aircraft_performance.py` exposes:

```
PerformanceContext(aircraft, initial_weight_kg, altitude_ft,
                   temperature_c, wind_direction_deg, wind_speed_kts,
                   cost_index)
```

with:

- `calculate_climb(context, target_altitude_ft, course_deg=0)`
  - ROC: 1500 ft/min × weight factor (1.0 at OEW, 0.6 at MTOW)
  - TAS: 0.8 × cruise Mach TAS at average altitude
  - Fuel flow: 3000 kg/hr × (weight/MTOW)^0.8
- `calculate_cruise(context, distance_nm, course_deg=0)`
  - TAS: Mach 0.78 (or configured) at altitude
  - Fuel flow: 2600 kg/hr × (weight/MTOW)^0.85 × cost_index_factor
- `calculate_descent(context, target_altitude_ft, course_deg=0)`
  - ROD: 1500 ft/min
  - TAS: 0.7 × cruise Mach TAS
  - Fuel flow: 600 kg/hr (idle)
- `calculate_fuel_burn(...)` returns climb/cruise/descent fuel & time.
- `calculate_max_altitude(aircraft, weight_kg)` linear between ceiling at OEW
  and ceiling−8000 ft at MTOW.

Mach→TAS uses the speed of sound `a = sqrt(1.4 * 287.0528 * T_K)` for
`T_K` from ISA temperature at altitude.

## Fuel

```
block_fuel = taxi + trip + contingency + alternate + final_reserve
             + additional + extra
contingency = trip × contingency_percent     (default 5%)
final_reserve = final_reserve_minutes × cruise_fuel_flow   (default 30 min)
```

The default policy is in `app.services.fuel.DEFAULT_POLICY`. Operators and
organizations can override; per-aircraft and per-flight overrides are also
supported via the `fuel_policy` JSON field on the plan.

## Weight & balance

```
ZFW = OEW + payload
TOW = ZFW + block_fuel
LW  = TOW - taxi - trip - alternate
```

Limits:

- `ZFW ≤ MZFW`
- `TOW ≤ MTOW`
- `LW ≤ MLW`
- `block_fuel ≤ fuel_capacity_kg`

Any violation produces a CRITICAL warning that blocks dispatch.

## Warnings

Each plan emits a list of `Warning(severity, code, message, details)`:

- INFO — informational, does not block
- WARNING — operator should review
- ERROR — indicates a planning problem, blocks dispatch if it can't be
  reconciled
- CRITICAL — limits violated or safety-relevant. Dispatch is blocked while
  any CRITICAL warning is present.

The dispatch endpoint refuses to flip the plan to DISPATCHED while any
CRITICAL warning is present.

## Disclaimer

The disclaimer is rendered on the OFP and the landing page of the web UI:

> This is a planning estimate produced by OpenDispatch and is not a substitute
> for certified aircraft performance data, official navigation data, ATC
> clearance, or legally required dispatch systems. Always cross-check against
> approved sources before flight.
