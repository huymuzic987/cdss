# Backend Components

The backend is one deployable FastAPI service organized into boundaries that
keep the traversal engine independent of HTTP and PostgreSQL.

## Domain

The domain owns decision-tree graph structures, traversal, conditions,
patches, actions, validation, and typed errors. It depends on repository
interfaces instead of SQLAlchemy implementations.

The follow-up classifier is also domain logic, but it is specific clinical
orchestration rather than part of the generic graph interpreter.

**Inputs:** normalized clinical values and immutable tree graphs.

**Outputs:** traversal results or typed domain errors.

**Must not depend on:** FastAPI routes, HTTP status codes, ORM sessions, or
database models.

## Infrastructure

Infrastructure implements domain repositories with PostgreSQL and SQLAlchemy.
It also owns persistence that is outside traversal: saved layouts, clinical
imports, and dashboard reporting queries.

**Inputs:** repository calls and transaction/session boundaries.

**Outputs:** domain graphs, medicine data, layouts, imported records, and
reporting projections.

**Important constraint:** mutable editor layouts must not share the immutable
clinical-graph cache.

## API

The API validates HTTP input, maps FHIR Bundles to normalized engine values,
wires repositories into the domain, serializes results, and maps typed errors
to stable HTTP responses.

Routes should coordinate use cases. They should not implement condition
evaluation, clinical thresholds, or direct persistence queries.

## Dependency direction

```text
API  ------>  Domain interfaces  <------  Infrastructure implementations
 |                                           ^
 +------------- composition/wiring ----------+
```

The domain does not point back to either outer layer. This permits fast tests
with in-memory repositories and no web server or database.

## Request boundary

Evaluation and dashboard reporting share an application process but not a
data path:

- Evaluation loads knowledge and returns a transient result.
- Clinical import persists patient and visit data.
- Dashboard queries read imported clinical data.
- Traversal never reads dashboard patient records.

See [Architecture](../architecture.md) for the complete request flow and
[Decision-tree engine overview](../cdss/engine-overview.md) for runtime logic.
