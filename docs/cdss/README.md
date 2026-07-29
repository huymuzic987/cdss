# Decision-Tree Engine Guides

The CDSS engine executes database-defined clinical workflows. Use this page to
choose the right level of detail.

## First read

[Engine overview](engine-overview.md) explains the runtime model, component
boundaries, and node lifecycle without specifying every edge case.

## By task

| Task | Read |
| --- | --- |
| Create or connect a tree | [Authoring a tree](authoring-a-tree.md) |
| Write conditions, patches, or actions | [JSON dialect](json-dialect.md) |
| Change fields shared across trees | [Context contract](context-contract.md) |
| Debug exact runtime behavior | [Traversal contract](traversal-engine-contract.md) |
| Select integration scenarios | [Mock-patient test matrix](mock-patient-test-matrix.md) |

## Stable concepts

- A tree is an immutable runtime graph loaded from PostgreSQL.
- Traversal carries a mutable run state, not a mutable graph.
- Conditions choose transitions; patches derive shared context; actions record
  clinical output.
- `LINK` transfers execution into another tree without returning automatically.
- Cross-tree context paths are interfaces and require compatibility discipline.

The detailed contracts are intentionally more exhaustive than the overview
because they define behavior that stored clinical knowledge depends on.
