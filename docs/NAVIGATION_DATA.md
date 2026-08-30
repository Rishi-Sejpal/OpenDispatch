# Navigation data

OpenDispatch stores navigation data (airports, runways, navaids, waypoints,
airways, procedures) in PostgreSQL + PostGIS. Every entity belongs to an AIRAC
cycle and the cycle is recorded on every flight plan for full reproducibility.

## What ships in the repository

`data/test-navigation/navigation.json` is a small, deterministic fixture:

- 8 airports (VABB, VIDP, VOMM, VABO, VABP, VABV, VOML, VOPB) with runways
- 14 fixes (waypoints, VORs)
- 3 airways (A466, A791, L301) with segments
- 9 procedures (SIDs, STARs, approaches)

Coordinates for major airports are sourced from publicly available reference
information. Procedures, airways, and minor fixes are simplified
representations intended to exercise the planning pipeline. **Not for
operational use.**

`data/aircraft/aircraft.json` contains simplified performance profiles for
A320, B738, and AT76. They are documented in `docs/AVIATION_CALCULATIONS.md`.

## Loading the test data

```bash
make seed
```

This invokes `apps/api/app/scripts/seed.py`, which:

1. Upserts AIRAC cycle `2401` (idempotent).
2. Creates the default user (`dispatch@opendispatch.example.com` /
   `dispatch123!`) and organization.
3. Loads the A320 type and registration `VT-OD1`.
4. Loads airports, runways, fixes, airways, procedures from
   `data/test-navigation/navigation.json`.

## Importing your own data

The seed script is a **plugin-style importer**. To add a new dataset, either:

1. Convert your data to the JSON shape under `data/test-navigation/` and run
   `make seed` again (idempotent — it skips existing records).
2. Write a new importer that follows the same `upsert_*` pattern in
   `apps/api/app/scripts/seed.py`. Use `ON CONFLICT` semantics via SQLAlchemy
   `session.merge` or explicit `select + insert/update`.
3. Build a more advanced importer (e.g. CSV/ARINC 424) by extending the
   `NavigationProvider` abstraction in `app.services`.

**Important.** Do not bundle copyrighted or proprietary navigation
databases (Jeppesen, Lufthansa Systems, etc.) in the repository. They have
strict redistribution licenses. Use licensed data only via importers that
read from files you provide locally — never commit the source data.

## AIRAC

Each cycle has:

- `cycle` (e.g. `2401` — ICAO AIRAC cycle identifier)
- `effective_from` / `effective_to`
- `source` (e.g. `manual`, `test-fixture`, `arinc424-import`)
- `version`, `checksum`, `import_status`
- `is_active` — only one cycle should be active at a time

`apps/api/app/services/flight_planner.py` always reads the cycle stored on the
plan; the active cycle is only used when creating a new plan or when an
unbound query is run. See `docs/AIRAC.md` for details on the cycle
lifecycle.

## Procedures

A `Procedure` row is a SID/STAR/approach with a name, kind, optional
`runway_ident`, optional `reference_fix_id`, and a sequence of `ProcedureLeg`
rows. Transitions are first-class (`ProcedureTransition` rows) so that
procedure compatibility (e.g. STAR ↔ Approach, Approach ↔ Runway) can be
validated in the planning pipeline.

The current implementation validates:

- Procedure kind matches the slot (SID at departure, STAR/Approach at arrival).
- Procedure airport matches the airport it's attached to.
- For SID/Approach, runway is `null`, `ALL`, or the selected runway.

UI restrictions (e.g. only show STARs that are valid for the selected
runway) are not yet enforced client-side; the API returns 422 with a
structured error if the selection is invalid.

## Airways

An `Airway` row has a sequence of `AirwaySegment` rows connecting two fixes
each. The route parser emits an AIRWAY leg from join to leave; the validator
warns if the airway does not contain a matching segment in the active cycle
(airways are not always bidirectional in the real world).
