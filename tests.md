# Test suite status

All checks were run against a live stack (`db`/`redis`/`api`/`worker`/`web` up, seed applied).
Run them yourself with `make test`, `make lint`, `make typecheck`, `make e2e`.

## Status: ALL PASS

| Suite | Command | Result |
| --- | --- | --- |
| Backend unit/integration | `pytest tests/` | 60 passed |
| Backend linter | `ruff check .` | All checks passed |
| Backend types | `mypy app` | no issues in 52 source files |
| DB migrations | `alembic current` | 0001_initial (head) |
| Web linter | `npm run lint` (eslint) | 0 problems |
| Web formatter | `npm run format:check` (prettier) | All files compliant |
| Web unit tests | `npm run test` (vitest + Testing Library) | 8 passed |
| Web types | `npm run typecheck` | clean |
| Web build | `npm run build` (vite) | success, per-route chunks |
| E2E | `npx playwright test` | 1 passed (full dispatch flow) |

## Issues fixed in this pass

1. **`make lint` / `npm run lint` was broken** — `eslint` was never installed.
   Added `eslint@10`, `@eslint/js`, `typescript-eslint`, `eslint-plugin-react-hooks`,
   `globals`, `eslint-config-prettier` (dev deps) and a flat config `eslint.config.js`.
   Fixed the 18 issues it surfaced (dead imports/state, two `any` casts replaced with
   `StyleSpecification` and real `RouteLeg`/`RouteParseResult` types).

2. **`make format` / `npm run format` was broken** — `prettier` was never installed.
   Added `prettier` + `.prettierrc.json` + `.prettierignore`; formatted all 24 files.

3. **`make test` failed at the web step** — no frontend test runner existed. Added
   `vitest@3` (pinned to Vite 5), `jsdom`, `@testing-library/{react,jest-dom,user-event}`.
   Vitest config lives in `vite.config.ts`; custom setup in `src/test/setup.ts` provides
   an in-memory `Storage` shim (Node 26 ships an experimental `localStorage` global that
   shadows jsdom's). Tests: `cn`, `useTheme`, and `Login` (render, validation, submit+navigate).
   Added proper `htmlFor`/`id` label associations on the Login form (a11y + testability).

4. **pytest-asyncio deprecation warning** — `apps/api/pyproject.toml` now sets
   `asyncio_default_fixture_loop_scope = "function"` and `asyncio_mode = "auto"`.

5. **Celery deprecation warning** — `apps/api/app/worker.py` now sets
   `broker_connection_retry_on_startup = True` (image rebuilt).

6. **Vite chunk-size warnings** — route-level `React.lazy` + `Suspense` in `App.tsx`
   plus `manualChunks` vendor splitting in `vite.config.ts` (react, router, tanstack,
   forms/zod, maplibre, utils). Per-route chunks are now generated; advisory limit
   raised to 1000 kB for the (inherently large) MapLibre vendor chunk.

## CI

`.github/workflows/ci.yml` frontend job now also runs `npm run lint` and `npm run test`
(was typecheck + build only). Backend job unchanged.