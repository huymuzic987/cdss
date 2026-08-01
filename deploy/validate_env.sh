#!/usr/bin/env bash
# Validates a production dotenv credential before it replaces the live file.
set -euo pipefail
source "$(dirname "$0")/lib.sh"

ENV_FILE="${1:-.env}"
validate_dotenv_file "$ENV_FILE"

APP_ENV="$(dotenv_require "$ENV_FILE" APP_ENV)"
POSTGRES_USER="$(dotenv_require "$ENV_FILE" POSTGRES_USER)"
POSTGRES_PASSWORD="$(dotenv_require "$ENV_FILE" POSTGRES_PASSWORD)"
POSTGRES_DB="$(dotenv_require "$ENV_FILE" POSTGRES_DB)"
APP_PORT="$(dotenv_require "$ENV_FILE" APP_PORT)"
BACKUP_HOST_DIR="$(dotenv_require "$ENV_FILE" BACKUP_HOST_DIR)"
BACKUP_RETENTION="$(dotenv_require "$ENV_FILE" BACKUP_RETENTION)"
BACKUP_FILE_MODE="$(dotenv_require "$ENV_FILE" BACKUP_FILE_MODE)"

if [ "$APP_ENV" != "production" ]; then
    echo "ERROR: APP_ENV must be production." >&2
    exit 1
fi
if [ "$POSTGRES_PASSWORD" = "change-me" ]; then
    echo "ERROR: placeholder POSTGRES_PASSWORD is forbidden." >&2
    exit 1
fi
case "$APP_PORT" in
    *[!0-9]*|'')
        echo "ERROR: APP_PORT must be numeric." >&2
        exit 1
        ;;
esac
case "$BACKUP_RETENTION" in
    *[!0-9]*|'')
        echo "ERROR: BACKUP_RETENTION must be a positive integer." >&2
        exit 1
        ;;
esac
if [ "$BACKUP_RETENTION" -lt 1 ]; then
    echo "ERROR: BACKUP_RETENTION must be at least 1." >&2
    exit 1
fi
if [ "$BACKUP_FILE_MODE" != "0600" ]; then
    echo "ERROR: BACKUP_FILE_MODE must be 0600." >&2
    exit 1
fi
if [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_DB" ] || [ -z "$BACKUP_HOST_DIR" ]; then
    echo "ERROR: validated production values must not be empty." >&2
    exit 1
fi

echo "Production environment file validated."
