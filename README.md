# OpenDispatch

Open-source flight planning and dispatch platform.

This is a planning tool. It is **not** a substitute for certified aircraft performance data, official navigation data, ATC clearance, or legally required operational control systems. See `SECURITY.md` and `AVIATION_CALCULATIONS.md`.

## Quickstart

```bash
cp .env.example .env
docker compose up -d --build
# wait for the api container to finish booting
make seed
open http://localhost:5173
```

## Default developer account

After `make seed`:

- email: `dispatch@opendispatch.local`
- password: `dispatch123!`

## Architecture

See `docs/ARCHITECTURE.md`.

## License

Apache-2.0.
