# OpenDispatch

Open-source flight planning and dispatch platform.

This is a planning tool. It is **not** a substitute for certified aircraft performance data, official navigation data, ATC clearance, or legally required operational control systems. See `SECURITY.md` and `AVIATION_CALCULATIONS.md`.

## Quickstart

1. Create a Supabase project (Postgres + Auth) and fill in `.env`:

   ```bash
   cp .env.example .env
   # edit .env: set DATABASE_URL, SUPABASE_URL, SUPABASE_ANON_KEY,
   # SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET
   ```

   See **`docs/SUPABASE.md`** for the full provisioning walk-through.

2. Bring the stack up:

   ```bash
   docker compose up -d --build
   make migrate   # alembic upgrade head
   make seed      # loads AIRAC 2608 + global nav + the default superuser
   ```

3. Open <http://localhost:5173> and sign in.

## Default developer account

After `make seed`:

- email: `dispatch@opendispatch.example.com`
- password: `dispatch123!`

## Architecture

See `docs/ARCHITECTURE.md`.

## License

Apache-2.0.
