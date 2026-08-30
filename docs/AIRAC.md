# AIRAC

OpenDispatch implements a first-class versioned AIRAC system. Every navigation
entity belongs to a cycle, and every flight plan permanently records the cycle
it was calculated against.

## Schema

```sql
airac_cycles (
  id           UUID PRIMARY KEY,
  cycle        VARCHAR(8) UNIQUE,         -- e.g. "2401"
  effective_from TIMESTAMP WITH TIME ZONE,
  effective_to   TIMESTAMP WITH TIME ZONE,
  source       VARCHAR(80),                -- e.g. "manual", "test-fixture", "arinc424"
  version      VARCHAR(32),
  import_status airac_import_status,       -- PENDING | IMPORTING | COMPLETE | FAILED
  checksum     VARCHAR(128),
  is_active    BOOLEAN,                    -- only one cycle active at a time
  notes        TEXT
)
```

`airports`, `runways`, `fixes`, `airways`, `airway_segments`, `procedures`,
`procedure_transitions`, and `procedure_legs` all carry an
`airac_cycle_id` foreign key.

## Multiple cycles

The system supports multiple cycles simultaneously. Switching to a new
cycle does not delete the old data — historical plans remain reproducible.

## Activation

`is_active` is the only flag the rest of the application looks at. There is
no enforcement that exactly one cycle is active; UI and pipeline both call
`get_active_cycle()` which picks `is_active=true` and falls back to the
most recent if none is.

## Flight plan context

When a plan is created without an explicit cycle, the active cycle is used.
After that, the cycle is **frozen on the plan** — even if the active cycle
is later rotated, the plan continues to read against its original cycle.

`flight_plans.calculation_engine_version`, `aircraft_performance_version`, and
the weather snapshot reference complete the reproducibility context.

## Importing a new cycle

1. Insert a new `airac_cycles` row with `import_status='PENDING'`.
2. Stream the data in. Use bulk inserts and `session.merge` for upserts. The
   `airac_cycles.id` is referenced by every imported row.
3. Update the cycle to `import_status='COMPLETE'` and (optionally)
   `is_active=true`.
4. If a different cycle was active, demote it to `is_active=false`.

A reference implementation is in `apps/api/app/scripts/seed.py`. Adapt it
to your data source (ARINC 424, XPlane, …).

## Future: cycle rollover & NOTAMs

The schema and `flight_plans.airac_cycle_id` already support rolling forward
to a new cycle. The planning UI should warn when a plan is being calculated
against a cycle that is about to expire.

NOTAMs are not yet modelled but the warnings pipeline is generic enough to
add a `NotamProvider` and emit them as `WARNING`-severity entries without
schema changes.
