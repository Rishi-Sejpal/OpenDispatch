# OpenDispatch — Build Status (Saved 2024-01-01)

## What Is Working

The OpenDispatch monorepo is scaffolded and most of the backend is implemented end-to-end on disk. **None of it has been runtime-verified yet** because Docker build/run was interrupted during initial bring-up.

## Completed (Code On Disk)

### Repository + Infrastructure
- Root: `docker-compose.yml`, `.env.example`, `Makefile`, `.gitignore`, `LICENSE`, `README.md`
- API image: `docker/api.Dockerfile` (Python 3.11, system libs for WeasyPrint/GeoAlchemy, all deps pinned)
- Web: Vite+React+TS scaffolded but **not yet written** (see M11 below)
- CI: `.github/workflows/` directory created but **no workflow files yet**

### Packages
- `packages/aviation-units/aviation_units/{__init__,conversions,units}.py` — full unit conversion lib (NM/km, ft/m, kg/lb, kt/kmh, ISA, Mach↔TAS, etc.)
- `packages/aviation-geometry/aviation_geometry/{__init__,geometry}.py` — great-circle distance, initial/final bearing, slerp interpolation, destination_point, cross_track_distance, along_track_distance, magnetic/true heading, rhumb line

### API — Core
- `apps/api/app/main.py` — FastAPI app factory with CORS, request-id middleware, structured logging, exception handlers, lifespan
- `apps/api/app/core/config.py` — pydantic-settings config (DB URL, Redis, JWT, storage, etc.)
- `apps/api/app/core/logging.py` — structlog JSON/console config
- `apps/api/app/core/errors.py` — `OpenDispatchError` hierarchy + handlers, payload shape `{"error":{"code","message","details"}}`
- `apps/api/app/core/security.py` — Argon2id password hashing, JWT access+refresh, request-id helpers
- `apps/api/app/core/packages_path.py` — adds `packages/*` to sys.path
- `apps/api/app/db/session.py` — SQLAlchemy 2.0 engine + `get_db` dep + `session_scope` ctx mgr
- `apps/api/app/db/base.py` — declarative Base

### API — Models (`apps/api/app/models/__init__.py`)
Full SQLAlchemy models for: User, UserSession, Organization, OrganizationMember, AiracCycle, Airport (with PostGIS Geography), Runway, Fix, Airway, AirwaySegment, Procedure, ProcedureTransition, ProcedureLeg, AircraftType, AircraftRegistration, WeatherReport, WindsAloftReport, FlightPlan, FlightPlanLeg, FlightPlanCalculation, FlightPlanWeight, FlightPlanFuel, FlightPlanWarning, GeneratedDocument, AuditLog. UUIDs everywhere, JSONB for extensible blobs, GIST index on `location`, proper enums.

### API — Alembic
- `apps/api/alembic.ini`
- `apps/api/app/migrations/env.py` wired to `app.db.base.Base` + all models
- `apps/api/app/migrations/versions/0001_initial.py` — hand-written migration: creates PostGIS+uuid-ossp extensions, all enums, all tables, all indexes, GIST indexes, all FKs. **Has NOT been run yet.**

### API — Services
- `app/services/user_service.py` — register, authenticate, issue/refresh tokens, create default org
- `app/services/audit.py` — audit log helper
- `app/services/route_parser.py` — ICAO route parser, `parse_route()` returns `ParseResult` with `ParsedLeg`s
- `app/services/route_validator.py` — checks fix existence, airway segments, departure/arrival match
- `app/services/weather.py` — `WeatherProvider` ABC + `LocalWeatherProvider` (deterministic synthetic), `persist_weather_snapshot`, `persist_winds`
- `app/services/aircraft_performance.py` — `PerformanceContext`, climb/cruise/descent/max-alt/ground-speed — documented simplified model, NOT certified
- `app/services/fuel.py` — `DEFAULT_POLICY`, `calculate_final_reserve`, `calculate_alternate_fuel`, `calculate_block_fuel`
- `app/services/flight_planner.py` — full pipeline: load AIRAC, airports, aircraft, validate procedures, parse route, build geometry, weather snapshot, climb/cruise/descent fuel, alternate fuel, weights, warnings, persist all outputs
- `app/services/storage.py` — `LocalFileStorage` implementing `StorageProvider` Protocol
- `app/services/pdf_renderer.py` — Jinja2 + WeasyPrint renderer for OFP/NAV_LOG/FUEL/WEIGHT; falls back to HTML on WeasyPrint failure

### API — Routes
All v1 routes wired in `apps/api/app/api/v1/routes/`:
- `health.py` — `/health`, `/ready`
- `auth.py` — register, login, refresh, logout, me
- `users.py` — me
- `organizations.py` — list mine, list members
- `airports.py` — search, detail
- `navigation.py` — fixes search, procedures list/detail
- `airac.py` — list cycles, get active
- `aircraft.py` — list types, get type, list registrations
- `route.py` — parse, validate, geometry
- `weather.py` — get METAR/TAF, list reports
- `flight_plans.py` — list, create, get, patch, calculate, dispatch, archive, delete, documents, download

### API — Schemas
All Pydantic v2 request/response schemas in `apps/api/app/schemas/`.

### API — Templates (Jinja2)
- `apps/api/templates/ofp.html`
- `apps/api/templates/nav_log.html`
- `apps/api/templates/fuel.html`
- `apps/api/templates/weight.html`

### Data
- `data/test-navigation/navigation.json` — VABB, VIDP, VOMM, VABO, VABP, VABV, VOML, VOPB + runways + 14 fixes + airways A466, A791, L301 + SID/STAR/approach procedures
- `data/aircraft/aircraft.json` — A320, B738, AT76 performance specs

### Seed
- `apps/api/app/scripts/seed.py` — upserts AIRAC cycle 2401, default user (dispatch@opendispatch.local / dispatch123!), default org, A320, registration VT-OD1, loads test navigation. **Idempotent.** **Has NOT been run yet.**

### Celery
- `apps/api/app/worker.py` + `apps/api/app/workers/tasks.py` — Celery bootstrap, single healthcheck task

### Frontend
- `apps/web/` directory exists (created via mkdir) but **EMPTY**. No package.json, no source, nothing.

## What Is NOT Done

### Critical — must be done tomorrow
1. **Fix 204-status FastAPI errors** — already partially done (added `response_class=Response` to `delete_plan` and `logout`). Need to rebuild image and re-test, then iterate on any remaining startup errors.
2. **Run the migration** — `docker compose run --rm api alembic upgrade head` and fix any errors.
3. **Run the seed** — `docker compose run --rm api python -m app.scripts.seed`. Fix any errors.
4. **Bring up full stack** — `docker compose up -d`, verify `curl localhost:8000/api/v1/health` works.
5. **Run the E2E backend flow with curl**:
   - `POST /auth/login` → tokens
   - `GET /airac/cycles/active` → verify cycle 2401
   - `GET /airports?q=VABB` → verify Mumbai returned
   - `GET /navigation/procedures?airport=VIDP&kind=SID` → verify DELHI
   - `POST /flight-plans` → create
   - `POST /flight-plans/{id}/calculate` → check calculation, fuel, weights
   - `POST /flight-plans/{id}/documents` → generate PDFs
   - `POST /flight-plans/{id}/dispatch` → must succeed
6. **Write unit tests** — `apps/api/tests/test_*.py` for geometry, route_parser, route_validator, fuel, weight, performance. Use pytest. They live in the api container.
7. **Build the frontend** — apps/web: package.json, vite.config, Tailwind, TanStack Query, RHF, Zod, MapLibre, full UI (login, dashboard, flight plan wizard, route editor, results, documents).
8. **Add CI workflow** — `.github/workflows/ci.yml` running lint+typecheck+pytest+docker build.
9. **Write all docs** — ARCHITECTURE.md, DEVELOPMENT.md, API.md, AVIATION_CALCULATIONS.md, NAVIGATION_DATA.md, AIRAC.md, AIRCRAFT_PERFORMANCE.md, FUEL_MODEL.md, SECURITY.md, CONTRIBUTING.md.
10. **E2E test (Playwright)** — `tests/e2e/` covering the 24-step acceptance flow.

### Nice-to-have polish (later)
- Proper `apps/web` Dockerfile (currently uses node:22 + npm install at container start; slow)
- Rate limiting (slowapi)
- Background AIRAC import job
- Add `Organization` create endpoint (currently only via registration)
- Aircraft registration create endpoint
- More aircraft types and procedures
- Tests for PDF rendering
- Health/audit list endpoints for admin

## Files Modified Today (quick reference)

```
README.md, LICENSE, .env.example, .gitignore, Makefile
docker-compose.yml, docker/api.Dockerfile
apps/api/pyproject.toml, alembic.ini
apps/api/app/__init__.py, main.py
apps/api/app/core/{config,logging,errors,security,packages_path}.py
apps/api/app/db/{session,base}.py
apps/api/app/models/__init__.py
apps/api/app/migrations/{env.py, script.py.mako, versions/0001_initial.py}
apps/api/app/schemas/{__init__,common,auth,navigation,aircraft,route,flight_plan,weather}.py
apps/api/app/services/{__init__,user_service,audit,route_parser,route_validator,weather,aircraft_performance,fuel,flight_planner,storage,pdf_renderer}.py
apps/api/app/api/__init__.py
apps/api/app/api/deps.py
apps/api/app/api/v1/{__init__,routes/__init__}.py
apps/api/app/api/v1/routes/{health,auth,users,organizations,airports,navigation,airac,aircraft,route,weather,flight_plans}.py
apps/api/app/worker.py
apps/api/app/workers/{__init__,tasks}.py
apps/api/app/scripts/{__init__,seed}.py
apps/api/templates/{ofp,nav_log,fuel,weight}.html
data/test-navigation/navigation.json
data/aircraft/aircraft.json
```

## Resume Instructions

1. `cd /home/rishis/Projects/OpenDispatch`
2. `docker compose build api` (rebuild after today's fixes)
3. `docker compose up -d db redis`
4. Wait for healthy, then:
   ```
   docker compose run --rm api alembic upgrade head
   docker compose run --rm api python -m app.scripts.seed
   docker compose up -d api worker web
   curl -s http://localhost:8000/api/v1/health | jq
   ```
5. Test login:
   ```
   curl -s -X POST http://localhost:8000/api/v1/auth/login \
     -H 'Content-Type: application/json' \
     -d '{"email":"dispatch@opendispatch.local","password":"dispatch123!"}' | jq
   ```
6. Fix any errors that come up — they will likely be in service code, FastAPI route signatures, or migration order.
7. Then proceed to write frontend + tests + docs per the M11/M12 todos.

## Open Risks / Watch For

- **WeasyPrint** needs libpango + libcairo + libgdk-pixbuf in the image — already installed in `docker/api.Dockerfile`. If PDF rendering still fails, the renderer falls back to a text file with the HTML.
- **PostGIS** extension creation requires the postgis image — using `postgis/postgis:15-3.4`. Migration creates extension explicitly.
- **The web service** uses `npm install` at container start which is slow. Move to a multi-stage Dockerfile later.
- **Argon2** native binding may not be pre-built for the slim image — installed `build-essential` so pip can compile if needed. Already verified working in initial build.
- **Local port 5432 and 6379 were in use on the host** — changed compose to map to 55432 / 56379. Update the README if you change this.
