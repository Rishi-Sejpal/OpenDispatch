# Test suite status

All checks were run against the live stack (`db`/`redis`/`api`/`worker`/`web` up, seed applied).
Run them yourself with `make test`, `make lint`, `make typecheck`, `make e2e`.

## Status: ALL PASS

| Suite | Command | Result |
| --- | --- | --- |
| Backend unit/integration | `pytest tests/` | 70 passed (60 + 10 AIRAC) |
| Backend linter | `ruff check .` | All checks passed |
| Backend types | `mypy app` | no issues in 55 source files |
| DB migrations | `alembic upgrade head` | head = 0002_supabase_auth |
| Active AIRAC cycle | resolved by seed | **2608** (2026-08-06 → 2026-09-03) |
| Web linter | `npm run lint` (eslint) | 0 problems |
| Web formatter | `npm run format:check` (prettier) | All files compliant |
| Web unit tests | `npm run test` (vitest + Testing Library) | 8 passed |
| Web types | `npm run typecheck` | clean |
| Web build | `npm run build` (vite) | success, per-route chunks |
| End-to-end | `npx playwright test` | requires real Supabase (see below) |

## Supabase

Authentication and the database have moved to [Supabase](https://supabase.com).
See `docs/SUPABASE.md` for the full provisioning walk-through. The relevant
changes:

- The backend no longer stores passwords or refresh tokens. It verifies
  Supabase-issued HS256 JWTs with `SUPABASE_JWT_SECRET` and auto-provisions
  a row in `public.users` on first contact.
- The frontend uses `supabase-js` for sign-up, sign-in, sign-out, and
  refresh. The axios client attaches the Supabase access token to every
  request.
- `make seed` creates the default superuser either via `auth.admin.create_user`
  (when `SEED_USE_SUPABASE_AUTH=true` and a real Supabase project is
  configured) or as a local stub row (CI and local dev without Supabase).
- The `users.password_hash` and `user_sessions` columns were dropped in
  Alembic migration `0002_supabase_auth`.

The `make up` / `make test` defaults still bring up a local postgis so
the repo is usable offline; the production / target database is Supabase.
Set `DATABASE_URL` and the `SUPABASE_*` variables in `.env` to point at
your project (see `docs/SUPABASE.md`).

## AIRAC

Cycle numbering is computed deterministically from a known ICAO anchor
(cycle 2301 effective 2023-01-26). The active cycle is always the one
effective today — `2608` as of writing — and the seed loads the test
navigation dataset (now global: EGLL, EHAM, LFPG, KJFK, RJTT, OMDB, …)
under it. See `docs/AIRAC.md` and `apps/api/app/services/airac.py`.

## Frontend defaults

`NewFlightPlan` no longer pre-fills VABB/VIDP or a sample route. The
schema marks departure, arrival, route, cruise altitude, passengers, and
cargo as required; the E2E and users type every field.

## CI

`.github/workflows/ci.yml` backend job runs lint + typecheck + migrate +
seed + pytest against a `postgis/postgis:15-3.4` service container
(SEED_USE_SUPABASE_AUTH=false so the seed takes the local-stub path).
Frontend job runs eslint, vitest, typecheck, and build.