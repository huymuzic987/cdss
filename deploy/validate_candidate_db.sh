#!/usr/bin/env bash
# Emits fail-closed SQL checks for the migrated and seeded candidate database.
set -euo pipefail

EXPECTED_HEAD="${1:-}"
SEED_MODE="${2:-}"
EXPECTED_LAYOUT_FINGERPRINT="${3:-}"

[ -n "$EXPECTED_HEAD" ] && [ -n "$SEED_MODE" ] || {
    echo "ERROR: usage: validate_candidate_db.sh <alembic-head> <all|preserve-layouts> [layout-fingerprint]" >&2
    exit 2
}
[[ "$EXPECTED_HEAD" =~ ^[0-9a-f]+$ ]] || {
    echo "ERROR: invalid Alembic head: $EXPECTED_HEAD" >&2
    exit 1
}
case "$SEED_MODE" in
    all)
        [ -z "$EXPECTED_LAYOUT_FINGERPRINT" ] || {
            echo "ERROR: first-deploy validation must not receive a layout fingerprint." >&2
            exit 1
        }
        ;;
    preserve-layouts)
        [[ "$EXPECTED_LAYOUT_FINGERPRINT" =~ ^[0-9]+:[0-9a-f]{32}$ ]] || {
            echo "ERROR: invalid preserved-layout fingerprint." >&2
            exit 1
        }
        ;;
    *)
        echo "ERROR: seed mode must be all or preserve-layouts." >&2
        exit 2
        ;;
esac

cat <<SQL
SET statement_timeout = '30s';
SET lock_timeout = '5s';
DO \$validation\$
DECLARE
    unresolved_links integer;
    invalid_start_counts integer;
    actual_layout_fingerprint text;
    actual_tree_count integer;
    actual_node_count integer;
    actual_edge_count integer;
    actual_medicine_count integer;
    actual_symptom_count integer;
BEGIN
    IF (SELECT count(*) FROM alembic_version) <> 1
        OR (SELECT version_num FROM alembic_version LIMIT 1) <> '$EXPECTED_HEAD' THEN
        RAISE EXCEPTION 'candidate Alembic revision does not match $EXPECTED_HEAD';
    END IF;
    SELECT count(*) INTO actual_tree_count FROM decision_trees;
    SELECT count(*) INTO actual_node_count FROM decision_nodes;
    SELECT count(*) INTO actual_edge_count FROM decision_edges;
    SELECT count(*) INTO actual_medicine_count FROM medicines;
    SELECT count(*) INTO actual_symptom_count FROM symptoms;
    -- These are materialized row counts after seed cleanup and graph
    -- normalization, not counts of INSERT statements in seed.sql.
    IF actual_tree_count < 14
        OR actual_node_count < 387
        OR actual_edge_count < 428
        OR actual_medicine_count < 66
        OR actual_symptom_count < 86 THEN
        RAISE EXCEPTION 'candidate seed row counts are below the authoritative minimum (trees %, nodes %, edges %, medicines %, symptoms %)',
            actual_tree_count, actual_node_count, actual_edge_count,
            actual_medicine_count, actual_symptom_count;
    END IF;

    SELECT count(*) INTO invalid_start_counts
    FROM (
        SELECT t.id
        FROM decision_trees t
        LEFT JOIN decision_nodes n ON n.tree_id = t.id
        GROUP BY t.id
        HAVING count(*) FILTER (WHERE n.node_type = 'START') <> 1
    ) invalid_trees;
    IF invalid_start_counts <> 0 THEN
        RAISE EXCEPTION 'candidate contains % tree(s) without exactly one START node',
            invalid_start_counts;
    END IF;

    SELECT count(*) INTO unresolved_links
    FROM decision_nodes source
    LEFT JOIN decision_trees target_tree
        ON target_tree.tree_key = source.link_target_tree_key
    LEFT JOIN decision_nodes target_node
        ON target_node.tree_id = target_tree.id
        AND target_node.node_key = source.link_target_node_key
    WHERE source.node_type = 'LINK'
      AND (
          target_tree.id IS NULL
          OR (
              source.link_target_node_key IS NOT NULL
              AND target_node.id IS NULL
          )
      );
    IF unresolved_links <> 0 THEN
        RAISE EXCEPTION 'candidate contains % unresolved LINK node(s)', unresolved_links;
    END IF;

    IF '$SEED_MODE' = 'all' AND (SELECT count(*) FROM tree_layouts) < 3 THEN
        RAISE EXCEPTION 'first-deploy seed did not create the expected layouts';
    END IF;
    IF '$SEED_MODE' = 'preserve-layouts' THEN
        SELECT count(*)::text || ':' ||
            md5(COALESCE(string_agg(
                id::text || ':' || node_positions::text || ':' || edge_layouts::text,
                '|' ORDER BY id
            ), ''))
        INTO actual_layout_fingerprint
        FROM tree_layouts;
        IF actual_layout_fingerprint <> '$EXPECTED_LAYOUT_FINGERPRINT' THEN
            RAISE EXCEPTION 'tree layouts changed during preserve-layouts seed';
        END IF;
    END IF;
END
\$validation\$;
SQL
