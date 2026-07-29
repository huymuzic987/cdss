# Documentation

Use this page as the documentation entry point. Each guide owns one topic;
the root README stays intentionally short.

## I want to...

| Goal | Read |
| --- | --- |
| Run the project locally | [Getting started](getting-started.md) |
| Understand the whole system | [Architecture](architecture.md) |
| Understand backend boundaries | [Backend components](components/backend.md) |
| Call or integrate with the API | [API guide](api/README.md) |
| Understand database tables | [Database](database.md) |
| Work on the frontend | [Frontend](frontend.md) |
| Understand the decision-tree engine | [Engine guide](cdss/README.md) |
| Create a clinical decision tree | [Authoring a tree](cdss/authoring-a-tree.md) |
| Understand condition and patch JSON | [JSON dialect](cdss/json-dialect.md) |
| Understand exact traversal behavior | [Traversal contract](cdss/traversal-engine-contract.md) |
| Change cross-tree context fields | [Context contract](cdss/context-contract.md) |
| Seed, restore, or troubleshoot data | [Operations](operations.md) |
| Run database tests safely | [Testing](testing.md) |
| Deploy the application | [Deployment](deployment.md) |

## Suggested reading paths

### New contributor

1. [Getting started](getting-started.md)
2. [Architecture](architecture.md)
3. [Backend components](components/backend.md) or [Frontend](frontend.md)
4. The guide for the feature you plan to change

### Decision-tree author

1. [Authoring a tree](cdss/authoring-a-tree.md)
2. [JSON dialect](cdss/json-dialect.md)
3. [Context contract](cdss/context-contract.md)
4. [Mock-patient test matrix](cdss/mock-patient-test-matrix.md)

### API or frontend integrator

1. [API guide](api/README.md)
2. [Frontend](frontend.md)
3. [Evaluation and FHIR input](api/evaluation.md)
3. The evaluation and FHIR Bundle sections of the API reference

### Operator

1. [Operations](operations.md)
2. [Deployment](deployment.md)
3. [Testing](testing.md)

## Document levels

The documentation uses three levels so readers can stop when they have enough
information:

1. **Overview** — purpose, boundaries, and important data flow.
2. **Component guide** — responsibilities, interfaces, and failure cases.
3. **Contract/reference** — exact runtime rules, schemas, and edge cases.

Low-level implementation inventories are intentionally avoided. Filenames and
private helper functions change more often than component responsibilities and
public contracts.

## Source of truth

- Code and tests define current implementation behavior.
- Contract documents define behavior that other components may rely on.
- Alembic migrations define the database schema history.
- OpenAPI at `/openapi.json` defines generated HTTP schema details.

If a short overview conflicts with a contract, treat the contract as
authoritative and update the overview.
