# Contributing

Thanks for your interest in OpenDispatch! This project aims to be a small,
focused, and well-tested open-source flight planning platform.

## Code of conduct

Be respectful, be helpful, and stay on-topic. This is a planning tool, not a
certified dispatch system; please don't misrepresent its outputs.

## How to contribute

1. Fork the repository and create a feature branch.
2. Make your changes, including tests.
3. Run `make lint` and `make api-test`. CI will run the same checks.
4. Open a pull request against `main`.

## Coding conventions

- **Python** — type hints, docstrings for public functions, errors via the
  `OpenDispatchError` hierarchy, no `print` (use `structlog`).
- **TypeScript** — strict mode, React 18 functional components, Zod for
  runtime validation, TanStack Query for server state.
- **SQL** — every migration must be reversible. Use `op.execute()` for raw
  DDL; the project uses PostGIS-specific features so plain Alembic
  autogenerate won't always work.

## Reporting bugs

Open an issue with:

- A minimal reproduction
- Expected vs actual output
- API request/response if relevant
- The full output of `/api/v1/health`

## Feature requests

Open an issue with the `enhancement` label. Briefly describe the use case,
not just the implementation. OpenDispatch is intentionally narrow in scope;
features that belong in a real dispatch system (certified performance,
ATC filing, etc.) are not appropriate for this project.

## Documentation

Doc files live in `docs/`. If you change behaviour, update the relevant
doc in the same pull request.

## Code of practice

- **Never** commit copyrighted navigation data, aircraft performance
  manuals, or proprietary weather data. OpenDispatch is open-source and
  ships only open or self-generated data.
- Do not invent or fabricate safety-critical outputs. If a calculation is
  uncertain, the system already says so via warnings — keep that path.
- Tests are required for any new behaviour that is testable.
