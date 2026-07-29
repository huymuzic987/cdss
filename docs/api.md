# API

Use the focused guide for the capability you are working with:

| Capability | Guide |
| --- | --- |
| Endpoint map and shared behavior | [API guide](api/README.md) |
| Clinical evaluation and FHIR input | [Evaluation](api/evaluation.md) |
| Tree graphs and saved layouts | [Trees and layouts](api/trees-and-layouts.md) |
| FHIR export, clinical import, and statistics | [FHIR and dashboard](api/fhir-and-dashboard.md) |

For every request field, response field, and extended example, use the
[complete API reference](api/complete-reference.md). The running application
also exposes interactive documentation at /docs and raw OpenAPI at
/openapi.json.

## Important boundaries

- Evaluation is stateless and does not persist patients.
- Evaluation input is an HL7 FHIR R4 collection Bundle.
- FHIR clinical import and dashboard seeding are state-changing operations.
- Saved tree layouts affect presentation only, not clinical behavior.
- Typed domain failures use stable error codes and may include partial
  traversal state.
