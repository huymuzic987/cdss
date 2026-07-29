# API Guide

The API is divided by responsibility. Start with the page for the capability
you are integrating instead of reading every endpoint in one document.

## Endpoint groups

| Capability | Endpoints | Guide |
| --- | --- | --- |
| Clinical evaluation | `POST /evaluate`, `POST /evaluate/follow-up` | [Evaluation](evaluation.md) |
| Tree visualization and layout | `/trees`, graph and layout endpoints | [Trees and layouts](trees-and-layouts.md) |
| Knowledge and clinical-data exchange | `/fhir/*` | [FHIR and dashboard](fhir-and-dashboard.md) |
| Clinical statistics | `/dashboard/*` | [FHIR and dashboard](fhir-and-dashboard.md) |
| Liveness | `GET /health` | This page |

For exhaustive request and response examples, see the
[complete API reference](complete-reference.md). The running application also exposes
interactive documentation at `/docs` and raw OpenAPI at `/openapi.json`.

## Shared behavior

- JSON is used for request and response bodies.
- Evaluation accepts a FHIR R4 `Bundle`, not the engine's flat input object.
- Domain failures use a shared error envelope with a stable `code`, readable
  `message`, structured `details`, and partial traversal state when available.
- An unresolved cross-tree link returns HTTP 424.
- Tree evaluation is read-only. FHIR import, dashboard seeding, and saved canvas
  layouts are separate persistence features.

## Health check

`GET /health` reports whether the API process is alive. It is suitable for
container health checks, not for clinical evaluation or deep database
diagnostics.

## When changing the API

Update the backend schema, route behavior, affected frontend type and client,
focused documentation page, and contract or integration tests together.
