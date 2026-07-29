# Tree Graph and Layout API

These endpoints support the decision-tree visualizer. Tree structure is
clinical knowledge; layout is mutable presentation state. They are stored and
cached separately.

## Tree structure

- `GET /trees` returns summary metadata for navigation without loading every
  graph.
- `GET /trees/{tree_key}/graph` returns nodes, edges, references, and metadata
  in a rendering-oriented shape.

A graph describes what can be traversed. An `/evaluate` result describes what
was traversed for one request.

## Saved layout

| Endpoint | Purpose |
| --- | --- |
| `GET /trees/{tree_key}/layout` | Load node positions and edge presentation |
| `PUT /trees/{tree_key}/layout` | Create or replace a saved layout |
| `DELETE /trees/{tree_key}/layout` | Remove it and use automatic layout |

Layouts must not change conditions, actions, links, or other clinical
behavior. A frontend may combine saved positions with automatically generated
positions for nodes added after the layout was saved.

## Component boundaries

- The graph repository loads immutable clinical structure.
- The layout repository reads and writes mutable canvas state.
- Resetting layout deletes presentation state only; it does not delete a tree.

See the [complete API reference](complete-reference.md#2-tree-graph-visualizer-data) for
exact fields and [Database](../database.md#editor-canvas-state) for storage.
