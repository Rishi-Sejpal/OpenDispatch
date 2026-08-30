# API

All endpoints under `/api/v1/`. JSON in, JSON out. UUIDs for IDs.

## Authentication

Most endpoints require an access token. Get one via `/auth/login`, then send
`Authorization: Bearer <access_token>`.

### POST /auth/register
Create a new user and (optionally) a new organization.

```json
{
  "email": "user@example.com",
  "password": "string (min 8 chars)",
  "full_name": "Jane Doe",
  "organization_name": "Acme Airlines"   // optional
}
```

### POST /auth/login
```json
{ "email": "...", "password": "..." }
```
Returns `{ "access_token", "refresh_token", "token_type", "expires_in" }`.

### POST /auth/refresh
Body: `{"refresh_token": "..."}`. Returns new tokens.

### POST /auth/logout
Revokes all sessions for the current user.

### GET /auth/me
Returns the authenticated user.

## Organizations

### GET /organizations
List the organizations the current user belongs to.

### GET /organizations/{id}/members
List members (requires DISPATCHER or higher).

## AIRAC

### GET /airac/cycles
List all AIRAC cycles.

### GET /airac/cycles/active
Get the currently active cycle.

## Airports

### GET /airports?q=&limit=&airac_cycle=
Search airports. `q` matches ICAO, IATA, name, city.

### GET /airports/{icao}?airac_cycle=
Airport detail with runways.

## Navigation

### GET /navigation/fixes?q=&limit=
Search fixes (waypoints, VOR/NDB/DME).

### GET /navigation/procedures?airport=&kind=
List procedures. `kind` is `SID` | `STAR` | `APPROACH`.

### GET /navigation/procedures/{id}
Procedure detail with legs and transitions.

## Aircraft

### GET /aircraft/types
List aircraft types (A320, B738, AT76, ...).

### GET /aircraft/types/{icao}
Aircraft type detail.

### GET /aircraft/registrations?organization_id=
List aircraft registrations.

## Weather

### GET /weather/{icao}/metar
Get the latest weather report for an airport (METAR + TAF).

### GET /weather/reports?airport=&limit=
List cached weather reports.

## Routes

### POST /routes/parse
Parse a route string. Body: `{ "route": "VABB DCT BOM A466 GADIN A466 DEL DCT VIDP" }`.

### POST /routes/validate
Parse + validate against the active cycle. Body:
`{ "route": "...", "departure": "VABB", "arrival": "VIDP" }`.

### POST /routes/geometry
Parse + compute per-leg geometry (lat, lon, course, distance).

## Flight plans

### POST /flight-plans
Create a new draft plan.

```json
{
  "departure_icao": "VABB",
  "arrival_icao": "VIDP",
  "alternate_icaos": ["VABP"],
  "aircraft_registration_id": "uuid",
  "passengers": 150,
  "cargo_kg": 1200,
  "cruise_altitude_ft": 35000,
  "cost_index": 30,
  "route_text": "VABB DCT BOM A466 GADIN A466 DEL DCT VIDP",
  "departure_runway_ident": "27",
  "arrival_runway_ident": "10",
  "sid_id": "uuid",
  "star_id": "uuid",
  "approach_id": "uuid",
  "callsign": "AIC119",
  "scheduled_off_block": "2026-08-30T10:00:00Z"
}
```

### GET /flight-plans
List the caller's plans.

### GET /flight-plans/{id}
Full plan detail including legs, calculation, fuel, weights, warnings, documents.

### PATCH /flight-plans/{id}
Update mutable fields. After edit, plan returns to DRAFT.

### POST /flight-plans/{id}/calculate
Run the full planning pipeline. Persists legs, calculation, fuel, weights, warnings.

### POST /flight-plans/{id}/dispatch
Mark the plan dispatched. Critical warnings block dispatch.

### POST /flight-plans/{id}/archive
Mark archived.

### DELETE /flight-plans/{id}
Delete (not allowed for DISPATCHED plans).

### GET /flight-plans/{id}/documents
List generated documents (OFP, NAV_LOG, FUEL, WEIGHT).

### POST /flight-plans/{id}/documents
Generate all four PDFs.

### GET /flight-plans/{id}/documents/{doc_id}/download
Download a single PDF.

## Health

### GET /health
Liveness + db + redis check.

### GET /ready
Same but returns 503 if any dependency is down.

## Errors

```json
{
  "error": {
    "code": "INVALID_PROCEDURE_TRANSITION",
    "message": "The selected STAR cannot transition to the selected runway.",
    "details": {}
  }
}
```

Codes: `NOT_FOUND`, `VALIDATION_FAILED`, `CONFLICT`, `UNAUTHORIZED`, `FORBIDDEN`,
`BUSINESS_RULE_VIOLATION`, `INTERNAL_ERROR`, `DATABASE_ERROR`, plus domain-specific
codes like `TOW_EXCEEDS_MTOW`, `INVALID_PROCEDURE_TRANSITION`, `UNKNOWN_FIX`.

## Full OpenAPI

Browse `http://localhost:8000/api/docs` (Swagger UI) or
`http://localhost:8000/api/redoc`. The raw schema is at
`/api/openapi.json`.
