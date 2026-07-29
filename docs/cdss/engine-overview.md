# Decision-Tree Engine Overview

The engine is a generic graph interpreter. Clinical thresholds and treatment
branches live in database rows and JSON documents rather than Python control
flow.

## Main components

| Component | Responsibility |
| --- | --- |
| Graph model | Represent immutable nodes, edges, references, and metadata |
| Repository | Load graphs without exposing ORM objects to the domain |
| Validator | Reject unsafe or ambiguous graph structure before traversal |
| Condition evaluator | Decide whether a candidate transition matches |
| Patch processor | Merge or copy derived values into shared context |
| Action collector | Record clinical recommendations and optional enrichment |
| Walker | Coordinate node entry, transitions, links, trace, and completion |

## Runtime data

One evaluation owns a run state containing:

- normalized input, which remains the request snapshot;
- mutable context shared across linked trees;
- collected actions;
- traversal trace and source references;
- metadata for every visited tree.

The engine writes none of this to the database.

## Node lifecycle

```text
load graph
  -> validate graph
  -> enter START
  -> enter node
  -> apply node effect
  -> evaluate ordered outgoing candidates
  -> enter next node or linked tree
  -> finish at END or terminal ACTION
```

## Node responsibilities

| Type | Behavior |
| --- | --- |
| `START` | Entry point; immediately chooses an outgoing transition |
| `CONDITION` | Allows entry only when its condition matches |
| `INFERENCE` | Applies a context patch, then continues |
| `ACTION` | Collects an action and may continue or terminate |
| `END` | Applies final effects and terminates successfully |
| `LINK` | Transfers execution to a target tree or target node |
| `GLOBAL` | Stores tree configuration and is never traversed |

## Transition selection

Outgoing edges are considered by `traversal_order`. The target node's
condition determines whether that candidate can be entered. No match is a
typed traversal failure rather than an implicit default.

## Cross-tree execution

A `LINK` loads and validates its target, then continues with the same run
state. There is no call stack and no automatic return to the source tree. The
target therefore depends on context paths established by earlier trees.

See the [context contract](context-contract.md) before adding or renaming such
paths.

## Failure model

Expected engine failures are typed and carry stable codes. Important classes
include missing trees, invalid graphs, missing runtime paths, unmatched
transitions, cycles, step-limit exhaustion, and unresolved links. The API maps
these errors to HTTP responses and may include partial run state.

## Where to go deeper

- [Traversal contract](traversal-engine-contract.md): exact ordering, trace,
  action, link, success, and error semantics.
- [JSON dialect](json-dialect.md): precise condition, patch, action, and global
  configuration shapes.
- [Authoring a tree](authoring-a-tree.md): practical creation workflow and
  verification checklist.
