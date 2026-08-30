# Security

OpenDispatch is designed for self-hosted use. By default, the system is
intended to run inside a trusted network or behind a reverse proxy that
terminates TLS.

## Authentication

Authentication is delegated to [Supabase Auth](https://supabase.com/docs/guides/auth).

- The frontend uses `supabase-js` to sign up, sign in, and refresh tokens.
- The backend verifies Supabase-issued HS256 access tokens with
  `SUPABASE_JWT_SECRET` on every protected endpoint.
- No passwords are ever stored in the OpenDispatch database. Supabase
  handles credential storage (argon2id by default) and refresh tokens.
- The first time a Supabase user calls the API the backend auto-provisions
  a `public.users` row by reading `email`, `user_metadata.full_name`, and
  `app_metadata.is_superuser` from the JWT.
- `POST /auth/logout` is recorded in the audit log; the actual sign-out
  happens client-side via `supabase.auth.signOut()`.

The `JWT_SECRET` legacy variable is retained for backwards compatibility
with any locally-issued tokens but is no longer used by the application.
Supabase's own `SUPABASE_JWT_SECRET` is the secret you must protect and
rotate. Rotating it invalidates every active session.

## Authorization

- Organization-scoped role checks: `OWNER`, `ADMIN`, `DISPATCHER`, `PILOT`,
  `VIEWER`.
- Plan visibility is scoped to the caller's organizations.
- `is_superuser` (read from the JWT's `app_metadata.is_superuser`) bypasses
  role checks. The seed user is the only superuser.
- Admin endpoints (e.g. AIRAC import) require `ADMIN` or higher.

The role hierarchy is:

```
VIEWER  <  PILOT  <  DISPATCHER  <  ADMIN  <  OWNER
```

## Headers

The API sets:

- `X-Request-ID` on every response (echoed from request or generated).
- `Access-Control-Allow-Origin` from the `CORS_ORIGINS` env (comma-separated).
- `Access-Control-Allow-Credentials: true` if the request includes
  credentials.
- No `Server` header is added by the application; the reverse proxy
  should add one if you want to advertise it.

## Input validation

- Pydantic v2 models validate all incoming JSON bodies.
- SQLAlchemy parameterizes all queries (no string concatenation).
- Geometry columns are populated only via `geoalchemy2` with explicit
  SRID 4326.

## Rate limiting

Not enabled by default. Add a reverse-proxy rate limiter (nginx, Caddy,
Traefik) or wire `slowapi` to FastAPI in front of the routers.

## Audit log

`audit_logs` records:

- actor user id
- organization id
- action (`flight_plan.dispatched`, `user.registered`, …)
- target type and id
- IP, user agent
- payload (JSONB)
- timestamp

The web UI does not yet expose an audit log viewer; query the table
directly for now.

## Secrets

- Never commit `.env` to the repository (`.gitignore` excludes it).
- The `SUPABASE_SERVICE_ROLE_KEY` and `SUPABASE_JWT_SECRET` are
  server-only secrets. The `SUPABASE_ANON_KEY` is safe to expose to the
  browser (it is embedded in the web bundle).
- The seed user's password is **only** for local development. Change
  immediately for any non-development deployment.
- The compose file does not pass through Docker secrets; for production,
  use Docker secrets or a secret manager (HashiCorp Vault, AWS Secrets
  Manager, etc.) and read them into the container's environment.

## Data classification

- Navigation data is **not** secret. Open data may be safely stored and
  shared.
- User accounts, organizations, flight plans and documents **are**
  sensitive. Restrict access to the database and storage.
- The system does not store payment information, government IDs, or
  anything similar.

## Vulnerability reporting

OpenDispatch is provided as-is. For security issues, open a private
issue or contact the maintainers directly. Do not include exploit
details in public bug reports.

## Compliance

OpenDispatch is not a certified dispatch system. It must not be used as
the system of record for any flight whose dispatch is legally required to
be performed by a certified operational control system.

## Dependency scanning

CI runs `ruff` and `mypy` but does not (yet) scan for known vulnerabilities
in third-party packages. Add `pip-audit` or `safety` to the CI pipeline
before exposing the deployment publicly.
