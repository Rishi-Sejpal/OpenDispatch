# Deploying OpenDispatch against Supabase

OpenDispatch uses Supabase for both the database and authentication. This
document explains how to provision a Supabase project, point the application
at it, and run the migrations and seed.

## 1. Create a Supabase project

1. Sign in to <https://supabase.com> and create a new project.
2. Note the project reference (the slug in the URL) — for example
   `ythiuyltgzerhsnkrsbt`.
3. Go to **Project Settings → API** and copy:
   - **Project URL** (e.g. `https://ythiuyltgzerhsnkrsbt.supabase.co`)
   - **anon public** key
   - **service_role** key (server-only secret)
   - **JWT Secret** (under JWT Settings)
4. Go to **Project Settings → Database → Connection string → Direct** and
   copy the Postgres connection string. The password is the one you set
   when you created the project; if you do not remember it, reset it
   under **Database password**.

## 2. Fill `.env`

Copy `.env.example` to `.env` and replace the placeholders:

```ini
DATABASE_URL=postgresql+psycopg://postgres:<your-password>@db.<project-ref>.supabase.co:5432/postgres
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_ANON_KEY=<anon key>
SUPABASE_SERVICE_ROLE_KEY=<service_role key>
SUPABASE_JWT_SECRET=<JWT secret>
SEED_USE_SUPABASE_AUTH=true
```

The `SEED_USE_SUPABASE_AUTH=true` flag tells `make seed` to create the
default superuser through `auth.admin.create_user`. Without it the seed
falls back to a local stub row (used by CI).

## 3. Disable email confirmation (dev / test only)

In the Supabase dashboard go to **Authentication → Providers → Email** and
turn **Confirm email** off. The Playwright E2E expects to be able to
sign up and immediately start dispatching without a confirmation email.
Turn this back on for production.

## 4. Bring the stack up

```bash
make up       # builds and starts redis/api/worker/web
make migrate  # alembic upgrade head against Supabase
make seed     # creates AIRAC 2608 + global nav + dispatch superuser
```

`make seed` will:

- Resolve the current AIRAC cycle (`2608` as of writing) deterministically
  and activate it.
- Load the test navigation dataset (VABB, VIDP, EGLL, KJFK, …) into the
  active cycle.
- Create the user `dispatch@opendispatch.example.com` (password
  `dispatch123!`) in Supabase Auth with `app_metadata.is_superuser = true`.
- Create a default organization and add the user as owner.

Open <http://localhost:5173> and sign in.

## 5. Local development without Supabase

The CI test suite runs against a plain `postgis/postgis:15-3.4` service
container (see `.github/workflows/ci.yml`). It exercises the planner,
fuel, geometry, and AIRAC modules without ever calling Supabase. To
reproduce locally:

```bash
docker run -d --name od-postgis -p 55432:5432 \
  -e POSTGRES_USER=opendispatch -e POSTGRES_PASSWORD=opendispatch \
  -e POSTGRES_DB=opendispatch postgis/postgis:15-3.4
DATABASE_URL=postgresql+psycopg://opendispatch:opendispatch@localhost:55432/opendispatch \
SUPABASE_URL=https://test.supabase.co SUPABASE_ANON_KEY=test SUPABASE_SERVICE_ROLE_KEY=test \
SUPABASE_JWT_SECRET=test-jwt \
SEED_USE_SUPABASE_AUTH=false \
docker compose run --rm api alembic -c alembic.ini upgrade head
SEED_USE_SUPABASE_AUTH=false \
docker compose run --rm api python -m app.scripts.seed
docker compose run --rm api pytest tests/
```

`SEED_USE_SUPABASE_AUTH=false` makes the seed create a local stub user
row instead of contacting Supabase.

## Architecture summary

- **Database**: Supabase Postgres. The application uses SQLAlchemy +
  Alembic and is otherwise unaware of the hosting; `DATABASE_URL` is the
  only switch.
- **Authentication**: Supabase Auth issues access tokens (HS256 JWTs).
  The backend verifies them with `SUPABASE_JWT_SECRET` and
  auto-provisions a row in `public.users` on first contact, mirroring
  `email`, `full_name`, and `is_superuser` from the token's
  `user_metadata` and `app_metadata`.
- **Refresh tokens**: managed by `supabase-js` on the client. The
  backend does not see them and there is no `user_sessions` table.
- **Password storage**: never. Supabase Auth handles credentials
  (argon2 by default).
- **Seed bootstrap**: `auth.admin.create_user` + `app_metadata.is_superuser`.
