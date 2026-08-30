# AIRAC

OpenDispatch implements a first-class versioned AIRAC system. Every navigation
entity belongs to a cycle, and every flight plan permanently records the cycle
it was calculated against.

## Cycle numbering

The cycle identifier is `YYNN` where `YY` is the two-digit year of the
effective date and `NN` is the cycle number within that year (01..13 in a
non-leap year). Example: cycle **2608** is the 8th AIRAC effective date of
2026, effective 2026-08-06 through 2026-09-03.

`app/services/airac.py` computes the current cycle deterministically from a
known anchor (ICAO-published 2023-01-26 = cycle 2301). Every subsequent cycle
falls on a strict 28-day cadence. The function
`current_airac_cycle(today=None)` returns the cycle effective on the given
date (defaults to today, UTC) together with its effective window.

```python
from datetime import date
from app.services.airac import current_airac_cycle
current_airac_cycle(date(2026, 8, 30))
# AiracCycleInfo(cycle='2608', effective_from=2026-08-06, effective_to=2026-09-03, ...)
```

The seed uses this calculator, so `make seed` (or `docker compose run --rm
api python -m app.scripts.seed`) always activates the current real-world cycle
and deactivates any older cycle. No manual cycle management is required; the
system follows the ICAO schedule automatically.

## Schema

```sql
airac_cycles (
  id           UUID PRIMARY KEY,
  cycle        VARCHAR(8) UNIQUE,         -- e.g. "2608"
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

`is_active` is the only flag the rest of the application looks at. The seed
enforces a single active cycle (deactivates any prior active row before
activating the current one). UI and pipeline both call `get_active_cycle()`
which returns the row with `is_active = true`.

## Flight plan context

When a plan is created without an explicit cycle, the active cycle is used.
After that, the cycle is **frozen on the plan** — even if the active cycle
is later rotated, the plan continues to read against its original cycle.

`flight_plans.calculation_engine_version`, `aircraft_performance_version`, and
the weather snapshot reference complete the reproducibility context.

## Importing a new cycle

1. The seed creates the current cycle on every run and loads the bundled
   test navigation dataset under it. For production, replace the test
   dataset with a real ARINC 424 importer.
2. Stream the data in. Use bulk inserts and `session.merge` for upserts. The
   `airac_cycles.id` is referenced by every imported row.
3. Update the cycle to `import_status='COMPLETE'` and set `is_active=true`.
4. The seed automatically deactivates the previous active cycle.

A reference implementation is in `apps/api/app/scripts/seed.py`. Adapt it
to your data source (ARINC 424, XPlane, …).

## Future: cycle rollover & NOTAMs

The schema and `flight_plans.airac_cycle_id` already support rolling forward
to a new cycle. The planning UI should warn when a plan is being calculated
against a cycle that is about to expire.

NOTAMs are not yet modelled but the warnings pipeline is generic enough to
add a `NotamProvider` and emit them as `WARNING`-severity entries without
schema changes.
