#!/usr/bin/env bash
# Runs inside the dedicated PostgreSQL backup container.
#
# "backup-now" creates one full plain-SQL dump immediately.
# "daemon" waits until local midnight, creates a dump, and repeats daily.
set -euo pipefail

BACKUP_DIR="/backups"
RETENTION="${BACKUP_RETENTION:-10}"
FILE_MODE="${BACKUP_FILE_MODE:-0600}"
VERSION="${DEPLOY_VERSION:?DEPLOY_VERSION is required}"

if ! [[ "$RETENTION" =~ ^[1-9][0-9]*$ ]]; then
    echo "ERROR: BACKUP_RETENTION must be a positive integer" >&2
    exit 1
fi

create_backup() {
    local timestamp filename temporary
    timestamp="$(date '+%Y%m%d-%H%M%S')"
    filename="${BACKUP_DIR}/cdss-db-${VERSION}-${timestamp}.sql"
    temporary="${filename}.tmp.$$"

    mkdir -p "$BACKUP_DIR"
    chmod 0700 "$BACKUP_DIR"

    echo "Creating database backup ${filename}..."
    if ! pg_dump \
        --format=plain \
        --create \
        --clean \
        --if-exists \
        --no-owner \
        --no-privileges \
        --file="$temporary"; then
        rm -f "$temporary"
        echo "ERROR: pg_dump failed" >&2
        return 1
    fi

    chmod "$FILE_MODE" "$temporary"
    mv "$temporary" "$filename"
    echo "Backup completed: ${filename}"

    mapfile -t backup_files < <(
        find "$BACKUP_DIR" -maxdepth 1 -type f -name 'cdss-db-*.sql' \
            -printf '%T@ %p\n' | sort -rn
    )

    if [ "${#backup_files[@]}" -gt "$RETENTION" ]; then
        for ((i = RETENTION; i < ${#backup_files[@]}; i++)); do
            old_file="${backup_files[$i]#* }"
            echo "Removing expired backup ${old_file}..."
            rm -f -- "$old_file"
        done
    fi
}

run_daemon() {
    while true; do
        now_epoch="$(date +%s)"
        next_midnight_epoch="$(date -d 'tomorrow 00:00:00' +%s)"
        wait_seconds=$((next_midnight_epoch - now_epoch))
        echo "Next database backup is in ${wait_seconds} seconds."
        sleep "$wait_seconds"

        until create_backup; do
            echo "Backup failed; retrying in 300 seconds." >&2
            sleep 300
        done
    done
}

case "${1:-daemon}" in
    backup-now)
        create_backup
        ;;
    daemon)
        run_daemon
        ;;
    *)
        echo "Usage: $0 {backup-now|daemon}" >&2
        exit 2
        ;;
esac
