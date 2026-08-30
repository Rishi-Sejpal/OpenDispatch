# Architecture

OpenDispatch is a monorepo flight planning and dispatch platform.

```
opendispatch/
├── apps/
│   ├── api/            FastAPI backend (Python 3.11)
│   └── web/            Vite + React + TS frontend
├── services/           Domain services (planning, weather, fuel, performance, etc.)
├── packages/           Shared libraries
│   ├── aviation-units/  Unit conversions (NM, ft, kg, kt, ISA, Mach↔TAS)
│   ├── aviation-geometry/ Great-circle, bearing, interpolation
│   └── shared-types/    Cross-language type definitions (reserved)
├── data/
│   ├── aircraft/        Aircraft type fixtures
│   └── test-navigation/ Test AIRAC fixture (Indian subcontinent subset)
├── tests/
│   ├── integration/     Cross-service tests
│   └── e2e/             Playwright UI tests
├── docs/                Markdown documentation
├── docker/              Dockerfiles
├── docker-compose.yml
└── .github/workflows/   CI
```

## High-level diagram

```
┌─────────────────┐    ┌──────────────────────────────────────────────────┐
│   Web (React)   │    │              API (FastAPI)                        │
│  ┌───────────┐  │    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────┐  │
│  │ MapLibre  │  │    │  │  Auth   │  │ Flight  │  │Document │  │ ... │  │
│  │ RHF/Zod   │  │ HTTPS│  │         │  │  Plans  │  │ Render  │  │     │  │
│  │ TanStack  │  ├────►│  │         │  │  API    │  │  (PDF)  │  │     │  │
│  └───────────┘  │    │  └─────────┘  └────┬────┘  └────┬────┘  └─────┘  │
│                 │    │                     │            │             │
└─────────────────┘    │                     ▼            ▼             │
                       │              ┌──────────────────────────────┐  │
                       │              │    Domain services (apps/api/app/services)  │  │
                       │              │  • route_parser   • flight_planner           │  │
                       │              │  • aircraft_perf  • fuel                       │  │
                       │              │  • weather        • pdf_renderer                │  │
                       │              │  • storage                                     │  │
                       │              └──────────┬────────────────────┘              │
                       │                         │                                    │
                       │                         ▼                                    │
                       │              ┌────────────────────────────┐                │
                       │              │   Postgres + PostGIS       │                │
                       │              │   (10 domain models, all  │                │
                       │              │    with FK + index)         │                │
                       │              └────────────────────────────┘                │
                       │                         │                                    │
                       │                         ▼                                    │
                       │              ┌────────────────────────────┐                │
                       │              │   Redis (Celery broker +   │                │
                       │              │   weather caching)          │                │
                       │              └────────────────────────────┘                │
                       └────────────────────────────────────────────────────────────┘
```

## Service boundaries

| Concern | Where |
|---|---|
| HTTP API | `apps/api/app/main.py`, `apps/api/app/api/v1/routes/*` |
| Auth (Argon2id, JWT) | `apps/api/app/core/security.py`, `apps/api/app/services/user_service.py` |
| Database / ORM | `apps/api/app/db/session.py`, `apps/api/app/models/*` |
| Migrations | `apps/api/app/migrations/` |
| Route parsing | `apps/api/app/services/route_parser.py` |
| Route validation | `apps/api/app/services/route_validator.py` |
| Aircraft performance | `apps/api/app/services/aircraft_performance.py` |
| Fuel policy | `apps/api/app/services/fuel.py` |
| Weather | `apps/api/app/services/weather.py` |
| Flight planning pipeline | `apps/api/app/services/flight_planner.py` |
| PDF generation | `apps/api/app/services/pdf_renderer.py` + `apps/api/templates/*` |
| Storage abstraction | `apps/api/app/services/storage.py` |
| Units | `packages/aviation-units/` |
| Geometry | `packages/aviation-geometry/` |
| Frontend | `apps/web/src/` |

## Domain model (PostgreSQL + PostGIS)

`airports` and `fixes` carry a `Geography(POINT, 4326)` column with a GIST index.
Every navigation entity belongs to an AIRAC cycle. Flight plans permanently
record the AIRAC cycle, calculation-engine version, aircraft-performance version,
and weather snapshot for full reproducibility.

A flight plan lifecycle:

```
DRAFT → VALIDATED → CALCULATED → GENERATED → DISPATCHED → ARCHIVED
```

Once DISPATCHED, a plan is immutable. All outputs (calculation, legs, fuel,
weights, warnings) are snapshotted and tied to the plan by FK.

## Provider abstractions

All external systems go through an interface so the core application does not
require rewrites when providers change:

- `WeatherProvider` (ABC in `app.services.weather`) — current implementation
  `LocalWeatherProvider` returns deterministic synthetic data.
- `StorageProvider` (Protocol in `app.services.storage`) — current
  implementation `LocalFileStorage` writes to the local filesystem.
- `AircraftPerformanceProvider` — currently the simplified model in
  `app.services.aircraft_performance`; swap in certified data by
  implementing the same `calculate_climb/cruise/descent/...` interface.
- `DocumentRenderer` — currently WeasyPrint + Jinja2.
- `NavigationProvider` — `data/test-navigation/navigation.json` is the seed
  fixture. Real-world data is imported through `app/scripts/seed.py` or a
  similar importer.

## Authoritative calculations

**All flight planning math runs in the backend.** The frontend only displays
results and posts user inputs. This is enforced by:

- The pipeline lives in `services/flight_planner.py` and runs on the API.
- The frontend POSTs to `/flight-plans/{id}/calculate` and re-fetches the
  snapshot. It never computes ETA, fuel, or weights.
- Templates (OFP, NavLog) are rendered server-side from the persisted plan.
