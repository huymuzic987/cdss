# Authoring a New Decision Tree

This is a practical walkthrough for adding a brand-new tree (or extending an
existing one) to the database. It assumes you have already read
[docs/cdss/json-dialect.md](json-dialect.md) (the condition/patch grammar) and
[docs/cdss/traversal-engine-contract.md](traversal-engine-contract.md) (the
node-type semantics). This document is about the mechanics of building rows
that satisfy those rules - it does not repeat the grammar itself.

Remember the core idea from [docs/architecture.md](../architecture.md): a tree
is data, not code. Authoring a tree means writing rows into
`decision_trees`, `decision_nodes`, `decision_edges`, and (optionally)
`node_source_references`. Nothing in `src/cdss` changes.

## 1. Decide the shape on paper first

Before touching the database, sketch:

- The tree's `tree_key` (a short, kebab-case, globally unique string - this is
  what callers pass as `start_tree_key` to `POST /evaluate`, and what other
  trees' `LINK` nodes will reference as `link_target_tree_key`).
- Every node: its `node_key` (unique within the tree), its `NodeType`
  (`START`, `CONDITION`, `INFERENCE`, `ACTION`, `END`, `LINK`, or `GLOBAL`),
  and bilingual display text (`text_en`, `text_vi`).
- Every edge between nodes, with a `traversal_order` at each node that has
  more than one outgoing edge - this is priority, not visual layout. The
  engine evaluates outgoing candidates in ascending `traversal_order` and
  enters the first one whose condition passes (or that is unconditional).
- Which `input.*` fields the tree needs from callers, and which
  `context.*` paths it reads from or writes for other trees. If you are
  adding a cross-tree read or write, update
  [docs/cdss/context-contract.md](context-contract.md) **before** seeding the
  tree - that document is the single source of truth for what any other tree
  is allowed to assume is present in `context`.

## 2. The structural rules you must satisfy

These are enforced by `validate_tree_graph()` in
`src/cdss/domain/decision_tree/validator.py`, which runs once per tree at the
start of every traversal (and again the first time a `LINK` loads a new
tree). Get these wrong and every evaluation of your tree will fail with a
typed `InvalidTreeStructure` or `InvalidStartNode` error, not a clinical
result:

- **Exactly one `START` node.** No more, no less.
- **No cycles.** The engine does its own cycle detection at runtime by node
  identity, but the validator also rejects a graph containing a cycle
  statically, using DFS over the internal edges.
- **Every executable node must be reachable from `START`.** "Executable"
  excludes `GLOBAL` nodes - they are metadata, never traversed.
- **`START`, `CONDITION`, and `INFERENCE` nodes must have at least one
  outgoing edge.**
- **`END` and `LINK` nodes must have zero outgoing edges.** (An `ACTION`
  node may have zero or more - zero makes it a terminal action, non-zero
  makes it a pass-through step, as documented in the traversal contract.)
- **Every `CONDITION` node must have a non-null, well-formed
  `condition_definition`.** A non-`CONDITION` node's `condition_definition`
  is optional; if present it still must be well-formed (this is what lets a
  `LINK` or `ACTION` node be one of several conditional outgoing candidates).
- **Every `LINK` node must have a non-empty `link_target_tree_key`.**
  `link_target_node_key` is optional - leave it null to enter the target
  tree's `START`, or set it to jump straight to a specific node in the target
  tree.
- **No edge may cross trees, and no edge may touch a `GLOBAL` node.** Edges
  are purely internal wiring for one tree's executable nodes.
- **No duplicate `(from_node, to_node)` pair and no duplicate
  `traversal_order` at the same source node.** `decision_edges` also enforces
  both as database-level unique constraints, so this fails at insert time,
  not just at validation time.
- **Every `condition_definition` and `context_patch` must parse under the
  frozen dialect.** See [json-dialect.md](json-dialect.md) for the exact
  grammar; a malformed document (unknown operator, wrong operand shape,
  invalid path root) is rejected the same way whether it comes from your new
  tree or an existing one.

None of this is soft guidance - it is the same code path that validates the
14 already-seeded trees. There is no "draft" or "unvalidated" state for a
tree once it is in the database; every request that reaches it re-validates
it.

## 3. Writing the rows

There is no tracked seed-authoring CLI or ORM factory for trees in this
repository - trees are written as SQL (directly, or accumulated into
`backups/seed.sql`) or via whatever the tree editor UI produces through the
API's read-only endpoints in the future. Today, the mechanical steps are:

1. Insert one row into `decision_trees` (`id`: generate a UUID; `tree_key`,
   `name_en`, `name_vi`). `tree_key`, `name_en`, and `name_vi` are all
   `UNIQUE` at the database level.
2. Insert one row per node into `decision_nodes`, all sharing that tree's
   `id` as `tree_id`. Set `condition_definition` / `context_patch` /
   `action_payload` / `global_config` (all nullable `JSONB`) only where that
   node type calls for them - see the traversal contract's node-type table
   for which fields each type actually uses. `(tree_id, node_key)` is
   `UNIQUE`, so node keys only need to be unique within their own tree.
3. Insert one row per edge into `decision_edges`
   (`from_node_id`, `to_node_id`, `traversal_order`). Both endpoints must be
   nodes you just inserted in the same tree.
4. Optionally insert `node_source_references` rows for any node that should
   cite a guideline section - `(node_id, reference_order)` is `UNIQUE`, and
   `section_path` is a JSON array of `{"number": ..., "title": ...}` objects
   per the audited shape in [json-dialect.md](json-dialect.md).

If you are extending `backups/seed.sql` (the tracked, pure-INSERT seed file
used by fresh local setups - see [docs/operations.md](../operations.md)),
add your tree's INSERT statements there so new checkouts get it too. If you
only insert directly into a running database, remember that a fresh
`restore.py` run replaces the whole database from a committed snapshot and
will not carry your addition forward - commit it to `seed.sql` (or produce a
new snapshot via `dump.py` against a database you trust) before you consider
the tree durable in this repository.

## 4. Wiring it into other trees (and being wired into)

- To make an existing tree hand off to your new tree, add a `LINK` node to
  the existing tree with `link_target_tree_key` set to your new `tree_key`.
  Remember: a `LINK` is a **tail transfer**, not a call - there is no return
  edge back to the calling tree. If your tree needs to hand control back,
  that must be represented explicitly as its own `LINK` back, in stored
  topology.
- If your tree reads a `context.*` path, whatever tree writes that path must
  run earlier in every execution path that reaches your tree, or your read
  must tolerate absence with an `exists` guard. This is exactly the
  "load-bearing dependency" concept in
  [context-contract.md](context-contract.md) - add your tree's reads/writes
  to that document's namespace and dependency tables.
- If your tree is meant to be reachable as a top-level entry point (called
  directly via `start_tree_key` in `POST /evaluate`), no extra wiring is
  needed - any seeded `tree_key` is a valid `start_tree_key`.
- If you deliberately want your tree's target to *not* exist yet (to test the
  `LinkTargetNotFound` failure path, the way `hypertension-older-adults` is
  used today), just point a `LINK` at a `tree_key` you have not seeded. This
  is a supported, tested pattern - see
  [mock-patient-test-matrix.md](mock-patient-test-matrix.md).

## 5. Caching gotcha

By default (`CDSS_GRAPH_CACHE_ENABLED=false`), every request reloads tree
definitions fresh from the database, so a newly seeded or edited tree is
visible immediately. If a deployment has turned graph caching **on**, a
process that already loaded the old (or absent) version of your tree will
keep serving it until the cache is cleared - that deployment owns
invalidation after any re-seed. See
[docs/architecture.md](../architecture.md#2-infrastructure-layer--cdssinfrastructuredb).

## 6. Verifying the tree

There is no dry-run validation endpoint - the same validation that runs
during a real traversal is the only validation available. Practical ways to
check a new tree before trusting it:

1. **Load its graph.** `GET /trees/{tree_key}/graph` (see
   [docs/api.md](../api.md)) returns the full node/edge/reference structure
   as loaded by the same `SqlAlchemyTreeGraphRepository` the traversal engine
   uses. If the tree is structurally broken, this call fails the same way a
   traversal would.
2. **Open it in the visualizer.** The frontend's canvas
   (`frontend/src/canvas/`, see [docs/frontend.md](../frontend.md)) renders
   whatever `GET /trees/{tree_key}/graph` returns, auto-laid-out via ELK, so
   you can visually confirm the shape matches your sketch - dead ends,
   accidental disconnected nodes, and mis-ordered edges are usually obvious
   once rendered.
3. **Walk it for real inputs.** `POST /evaluate` with `start_tree_key` set to
   your new tree and a representative FHIR `Bundle` input (see
   [docs/api.md](../api.md) for the request shape). Set `CDSS_DEBUG_OUTPUT=true`
   in your local `.env` to get the full action trail and trace instead of just
   the terminal action, which is much easier to debug against while
   authoring.
4. **Add it to the test suite.** Follow the existing pattern in
   `tests/db/test_seeded_tree_validation.py` (structural validation over every
   seeded tree) and `tests/db/test_mock_patient_scenarios.py` /
   `tests/db/test_seeded_link_execution.py` (fixture-driven end-to-end
   traversals with exact expected actions/trace/references) to lock in your
   new tree's behavior the same way the existing 14 are locked in. See
   [docs/cdss/mock-patient-test-matrix.md](mock-patient-test-matrix.md) for
   the existing fixture catalog and its conventions.

## 7. Common mistakes

- **Forgetting `CONDITION` needs a definition.** An empty/null
  `condition_definition` on a `CONDITION` node is not "always true" - it is a
  validation error. Only non-`CONDITION` candidates with a null definition
  are treated as unconditional matches.
- **Relying on read order instead of `exists` guards.** The condition
  evaluator is not short-circuiting across `all`/`any` - every child is
  always evaluated, even in a logically dead branch. A comparison against an
  unwritten `context.*` path fails the whole run with `MissingRuntimePath`,
  not just that branch. Guard optional reads with `{"op": "exists", ...}`
  first if the path is not guaranteed.
- **Writing into `input_snapshot`.** Context patches can only write to
  `context.*`. There is no operation that mutates the caller's input.
- **Assuming a `LINK` returns.** It doesn't. If two trees need to alternate,
  that has to be modeled as explicit `LINK` topology in both directions, not
  assumed control flow.
- **Skipping the context contract.** Adding a `context.*` write or read
  without updating [context-contract.md](context-contract.md) first is a
  contract violation even if your tree works fine in isolation - a later
  tree may depend on the exact key you chose.
