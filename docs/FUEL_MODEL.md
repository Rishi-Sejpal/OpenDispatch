# Fuel model

OpenDispatch implements a deterministic, configurable fuel policy.

## Components

- `taxi_kg` — fuel burned between pushback and takeoff (default 200 kg).
- `trip_kg` — climb + cruise + descent + approach.
- `contingency_kg` — `trip_kg × contingency_percent` (default 5%).
- `alternate_kg` — fuel to fly the alternate + approach. If the user did not
  select an alternate, the pipeline auto-selects the closest suitable
  airport from the cycle.
- `final_reserve_kg` — holding fuel. Default 30 minutes at the cruise
  fuel flow.
- `additional_kg` — operator-specified extra (e.g. minimum take-off fuel).
- `extra_kg` — discretionary.

```
block_fuel = taxi + trip + contingency + alternate + final_reserve + additional + extra
```

## Policy resolution

The effective policy is computed as a layered merge:

1. Default policy (`app.services.fuel.DEFAULT_POLICY`).
2. Organization's `default_fuel_policy` (if any).
3. Aircraft registration's `fuel_policy` (if any).
4. Flight plan's `fuel_policy` (if any) — highest priority.

Each layer overrides the previous. The merged policy is what the planner
uses; it is also persisted on `flight_plan_fuel.policy_used` for
reproducibility.

## Inputs and outputs

`calculate_fuel_burn(context, distance_nm)` returns a dict with the climb,
cruise, and descent fuel and time. `calculate_block_fuel(...)` returns a
`FuelResult` with all line items and the final `block_kg`. The planning
pipeline writes everything to `flight_plan_fuel` and returns a `Warning`
list to the UI.

## Sample policy

```json
{
  "taxi_kg": 200,
  "contingency_percent": 0.05,
  "final_reserve_minutes": 30,
  "extra_kg": 0,
  "additional_kg": 0
}
```

This is what the seed user and default organization start with.

## Future

- Per-flight-policy overrides via dropdown (e.g. "max endurance",
  "max range", "minimum take-off fuel").
- Operator-specific reserve minima (ICAO / EASA / FAA rules).
- Holding-pattern aware reserves (rather than flat minutes).
