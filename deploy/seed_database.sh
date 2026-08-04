#!/usr/bin/env bash
# Streams seed.sql into psql. For a cloned production database, the complete
# TREE LAYOUTS section is omitted and the existing rows are restored at the
# end of the seed transaction. The restore also protects operator-edited
# layouts from graph-normalization statements later in seed.sql.
set -euo pipefail

MODE="${1:?usage: seed_database.sh <all|preserve-layouts>}"
SEED_FILE="${2:-backups/seed.sql}"
LAYOUT_START='^-- 5\. TREE LAYOUTS '
LAYOUT_END='^-- 6\. MEDICINES REFERENCE CATALOG '

if [ ! -s "$SEED_FILE" ]; then
    echo "ERROR: seed file is missing or empty: $SEED_FILE" >&2
    exit 1
fi
if [ "$(grep -c '^BEGIN;$' "$SEED_FILE" || true)" -ne 1 ] \
    || [ "$(grep -c '^COMMIT;$' "$SEED_FILE" || true)" -ne 1 ]; then
    echo "ERROR: seed file must contain exactly one BEGIN and one COMMIT." >&2
    exit 1
fi

case "$MODE" in
    all)
        cat "$SEED_FILE"
        ;;
    preserve-layouts)
        start_count="$(grep -c "$LAYOUT_START" "$SEED_FILE" || true)"
        end_count="$(grep -c "$LAYOUT_END" "$SEED_FILE" || true)"
        start_line="$(grep -n "$LAYOUT_START" "$SEED_FILE" | cut -d: -f1 || true)"
        end_line="$(grep -n "$LAYOUT_END" "$SEED_FILE" | cut -d: -f1 || true)"
        if [ "$start_count" -ne 1 ] || [ "$end_count" -ne 1 ] \
            || [ -z "$start_line" ] || [ -z "$end_line" ] \
            || [ "$start_line" -ge "$end_line" ]; then
            echo "ERROR: seed layout section markers are missing, duplicated, or out of order." >&2
            exit 1
        fi
        awk '
            /^BEGIN;$/ {
                print
                print "CREATE TEMP TABLE cdss_preserved_tree_layouts ON COMMIT DROP AS TABLE public.tree_layouts;"
                next
            }
            /^-- 5\. TREE LAYOUTS / { skipping = 1; next }
            /^-- 6\. MEDICINES REFERENCE CATALOG / { skipping = 0 }
            /^COMMIT;$/ {
                print "DELETE FROM public.tree_layouts;"
                print "INSERT INTO public.tree_layouts SELECT * FROM cdss_preserved_tree_layouts;"
                print
                next
            }
            !skipping { print }
        ' "$SEED_FILE"
        ;;
    *)
        echo "ERROR: mode must be all or preserve-layouts" >&2
        exit 2
        ;;
esac
