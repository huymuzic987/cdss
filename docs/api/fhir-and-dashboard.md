# FHIR Export, Clinical Import, and Dashboard API

These endpoints export decision-tree knowledge and persist clinical data for
statistics. Neither capability is part of stateless `/evaluate` traversal.

## Knowledge export

| Endpoint | Result |
| --- | --- |
| `GET /fhir/PlanDefinition` | Bundle containing all exported trees |
| `GET /fhir/PlanDefinition/{tree_key}` | One tree as a PlanDefinition |
| `GET /fhir/Library/{tree_key}` | Global tree configuration as a Library |

Internal conditions are mapped into FHIR expression structures. The internal
JSON dialect remains the authoritative runtime format.

## Clinical-data import and export

| Endpoint | Purpose |
| --- | --- |
| `POST /fhir/import` | Import supported patient and visit resources |
| `GET /fhir/Patient` | Export the supported patient collection |
| `GET /fhir/Patient/{fhir_id}` | Export one supported patient |

Imported data is persisted for dashboard queries and is never read by the
decision-tree traversal engine.

## Dashboard

Dashboard endpoints under `/dashboard` provide seeding, summary metrics,
patient search, and patient detail.

```text
seed or FHIR import
    -> persisted patients and visits
    -> filtered summary/patient queries
    -> frontend charts and detail views
```

Dashboard filters define reporting cohorts. They do not alter clinical trees
or evaluation results.

## Data safety

- Treat import and seed endpoints as state-changing operations.
- Use synthetic or approved test data in development.
- Do not confuse dashboard persistence with `/evaluate` statelessness.
- Follow environment retention and backup requirements for clinical data.

See [exact FHIR shapes](complete-reference.md#4-fhir-knowledge-export-fhir),
[dashboard details](complete-reference.md#5-statistics-dashboard-dashboard),
[database schema](../database.md#clinicaldashboard-data), and
[operations](../operations.md#2-seeding-the-clinicaldashboard-data).
