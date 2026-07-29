# Backend Package

The backend is a modular monolith. This page describes stable package
boundaries; use the linked guides for runtime details.

## Package boundaries

| Package | Responsibility |
| --- | --- |
| domain | Traversal, graph contracts, clinical orchestration, and typed errors |
| infrastructure | SQLAlchemy repositories and other persistence concerns |
| api | FastAPI routes, schemas, dependency wiring, and error serialization |
| core | Process configuration and database session setup |
| testing | Reusable application test support |

Dependency direction matters: domain code must not import FastAPI, SQLAlchemy,
or API schemas. Infrastructure implements interfaces owned by the domain, and
the API composes those implementations into request use cases.

## Where to read next

- [Backend components](../../docs/components/backend.md)
- [Architecture and evaluation flow](../../docs/architecture.md)
- [Decision-tree engine overview](../../docs/cdss/engine-overview.md)
- [API guide](../../docs/api/README.md)
- [Database](../../docs/database.md)

## Changing clinical logic

Clinical thresholds and branches belong in database-defined trees, not Python
conditionals. Follow [Authoring a tree](../../docs/cdss/authoring-a-tree.md)
and verify changes against the JSON dialect, context contract, and traversal
contract.

Avoid documenting every private helper in this file. File-level inventories
become stale during refactors; public responsibilities and contracts are the
maintained documentation boundary.
