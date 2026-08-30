# Development

## Prerequisites

- Docker + Docker Compose v2
- GNU Make
- ~4 GB free RAM (PostGIS image is ~1.2 GB)

No host-side Python or Node needed; everything runs in containers.

## First-time setup

```bash
git clone https://github.com/Rishi-Sejpal/OpenDispatch.git
cd OpenDispatch
cp .env.example .env
docker compose up -d --build
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m app.scripts.seed
open http://localhost:5173
```

Default credentials:

- email: `dispatch@opendispatch.example.com`
- password: `dispatch123!`

## Daily workflow

```bash
make up              # start all services
make logs            # tail logs
make api             # shell into the API container
make api-test        # run backend tests
make lint            # ruff + mypy
make format          # auto-format
make migrate         # apply DB migrations
make seed            # reload test data
make down            # stop everything
make clean           # nuke volumes and caches
```

## Code layout

- **Backend** — `apps/api/app/`
  - `core/` config, logging, errors, security, packages_path
  - `db/` SQLAlchemy engine + session
  - `models/` ORM models (all in one `__init__.py`)
  - `schemas/` Pydantic request/response models
  - `api/v1/routes/` FastAPI routers
  - `services/` domain services (planning, weather, fuel, performance, …)
  - `migrations/` Alembic
  - `worker.py` Celery bootstrap
  - `scripts/seed.py` seed CLI
  - `templates/` Jinja2 PDF templates
  - `tests/` pytest

- **Frontend** — `apps/web/src/`
  - `App.tsx` shell + routes
  - `pages/` Login, Register, Dashboard, FlightPlans, NewFlightPlan, FlightPlanDetail, Airports, Routes, Aircraft, Documents, Settings
  - `components/` LiveSummary, RouteEditor, FlightMap
  - `lib/` api, auth, queries, types, format, theme
  - `hooks/useDebounce.ts`

- **Packages** — `packages/`
  - `aviation-units/` pure-Python unit conversions
  - `aviation-geometry/` great-circle, bearing, interpolation

## Coding style

Backend:
- Python 3.11 type hints throughout
- `ruff check` for linting
- `mypy --strict-compatible` for type checking
- All public functions have docstrings
- Errors are raised through the `OpenDispatchError` hierarchy in `app.core.errors`
  and produce `{"error": {"code", "message", "details"}}` JSON bodies
- No `print`; use `structlog` logger

Frontend:
- TypeScript strict
- React 18 functional components
- TanStack Query for all server state
- Zod for runtime validation
- Tailwind utility classes (no inline styles except for dynamic map elements)

## Testing

```bash
# Backend unit + integration tests
make api-test

# Frontend type check
make typecheck
```

Tests are co-located with the code:

- `apps/api/tests/test_units.py` — units
- `apps/api/tests/test_geometry.py` — geometry
- `apps/api/tests/test_route_parser.py` — route parser
- `apps/api/tests/test_fuel.py` — fuel
- `apps/api/tests/test_performance.py` — performance
- `apps/api/tests/test_planner_integration.py` — full pipeline

Integration tests use a real Postgres via the `db` service. Each test creates
fresh fixtures and cleans up in teardown so re-runs are safe.

## Debugging

API logs go to stdout in JSON format (configurable via `LOG_JSON=false` for
console output). The middleware adds a request ID to every request; include it
in bug reports.

```bash
# follow API logs
make logs

# single request
curl -s http://localhost:8000/api/v1/health | jq

# log into the API container
make api

# run a one-off Python command
docker compose run --rm api python -c "from app.main import app; print(app.title)"
```

## Adding a new feature

1. Update the database schema in `apps/api/app/models/__init__.py` and write a
   new Alembic migration in `apps/api/app/migrations/versions/`.
2. Add Pydantic schemas in `apps/api/app/schemas/`.
3. Add a service in `apps/api/app/services/` (or extend an existing one).
4. Wire a router in `apps/api/app/api/v1/routes/` and add it to the v1
   `__init__.py`.
5. Update the frontend queries (`apps/web/src/lib/queries.ts`) and pages.
6. Write tests (unit + integration).
7. Run `make lint` and `make api-test`.
8. Commit and push.

## API conventions

- All endpoints under `/api/v1/`.
- Auth via `Authorization: Bearer <access_token>`.
- JSON error shape: `{"error": {"code": "...", "message": "...", "details": {}}}`.
- UUIDs everywhere for IDs.
- Timestamps are RFC 3339 UTC with `Z` suffix.
- Status codes: 200 OK, 201 Created, 204 No Content, 400/422 Validation,
  401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 500 Internal.
