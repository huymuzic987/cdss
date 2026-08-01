#!/usr/bin/env bash
# Streams seed.sql into psql. For a cloned production database, the complete
# TREE LAYOUTS section is omitted so operator-edited node/edge positions and
# layout metadata remain byte-for-byte unchanged.
set -euo pipefail

MODE="${1:?usage: seed_database.sh <all|preserve-layouts>}"
SEED_FILE="${2:-backups/seed.sql}"

case "$MODE" in
    all)
        cat "$SEED_FILE"
        ;;
    preserve-layouts)
        awk '
            /^-- 5\. TREE LAYOUTS / { skipping = 1; next }
            /^-- 6\. MEDICINES REFERENCE CATALOG / { skipping = 0 }
            !skipping { print }
        ' "$SEED_FILE"
        ;;
    *)
        echo "ERROR: mode must be all or preserve-layouts" >&2
        exit 2
        ;;
esac
