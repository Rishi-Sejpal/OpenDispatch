# Aircraft performance

OpenDispatch ships with a simplified, open-source aircraft performance model.
It is **not** certified and must not be used for real dispatch without
cross-checking against approved aircraft performance manuals (AFM, FCOM, etc.).

## Aircraft type model

`aircraft_types` carries:

- Identification: `icao_type`, `manufacturer`, `model`, `variant`,
  `wake_category`, `engine_type`, `engines`.
- Mass limits: `mtow_kg`, `mlw_kg`, `mzfw_kg`, `oew_kg`, `fuel_capacity_kg`,
  `passenger_capacity`, `cargo_capacity_kg`.
- Performance: `max_altitude_ft`, `cruise_mach`, `cruise_tas_kts`,
  `approach_speed_kts`, `initial_climb_alt_ft`, `initial_cruise_alt_ft`.
- Profiles (JSONB): `climb_profile`, `cruise_profile`, `descent_profile`,
  `fuel_burn_model`.

Profiles are kept as JSONB to allow per-aircraft overrides and future
extension without schema changes. The current simplified engine reads the
flat fields (`cruise_mach`, `cruise_tas_kts`, `mtow_kg`, `oew_kg`, …) and
ignores the profile blobs. They are persisted for forward-compatibility.

## Simplified model

```
climb:
  ROC  = 1500 ft/min × weight_factor
  time = delta_alt / ROC
  TAS  = 0.8 × TAS_at_cruise_mach(avg_alt)
  fuel = 3000 kg/hr × (weight/MTOW)^0.8 × time/3600

cruise:
  TAS  = cruise_mach × speed_of_sound(altitude)
  fuel = 2600 kg/hr × (weight/MTOW)^0.85 × CI_factor × time/3600
  CI_factor = 1 + clamp((cost_index - 30) / 200, -0.15, 0.15)

descent:
  ROD  = 1500 ft/min
  TAS  = 0.7 × TAS_at_cruise_mach(avg_alt)
  fuel = 600 kg/hr × time/3600   (idle)
```

`max_altitude(weight) = ceiling - 8000 × (weight - OEW) / (MTOW - OEW)`.

These are **documented approximations**, not certified.

## Versioning

`flight_plans.aircraft_performance_version` is set when the plan is
calculated. The current engine writes `"1.0.0"`. To upgrade the model:

1. Bump the version constant in
   `apps/api/app/services/flight_planner.calculate_flight_plan`.
2. Old plans retain their old `aircraft_performance_version` and will not
   be re-calculated against the new model unless the user clicks
   "Recalculate".
3. New plans are tagged with the new version. The frontend can show a
   badge or a warning if a plan is on an old version.

## Replacing the model with certified data

Implement the same interface in a new service module:

```python
def calculate_climb(context, target_altitude_ft, course_deg=0.0) -> ClimbResult: ...
def calculate_cruise(context, distance_nm, course_deg=0.0) -> CruiseResult: ...
def calculate_descent(context, target_altitude_ft, course_deg=0.0) -> DescentResult: ...
def calculate_fuel_burn(context, distance_nm, course_deg=0.0) -> dict: ...
def calculate_ground_speed(tas_kts, course_deg, wind_dir, wind_spd) -> float: ...
def calculate_time(distance_nm, ground_speed_kts) -> float: ...
def calculate_max_altitude(aircraft, weight_kg) -> int: ...
```

Read inputs from `AircraftType.fuel_burn_model` (JSONB) and the runtime
context. The planner will pick it up automatically because everything
goes through `app.services.aircraft_performance`.
