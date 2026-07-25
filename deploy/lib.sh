#!/usr/bin/env bash
# Shared helper for deploy/*.sh scripts. Figures out which Docker Compose
# CLI is available on this host and sets $COMPOSE accordingly - not every
# host has the newer `docker compose` plugin; some only have the legacy
# standalone docker-compose binary.
resolve_compose() {
    if docker compose version > /dev/null 2>&1; then
        COMPOSE="docker compose -f docker-compose.prod.yml"
    elif command -v docker-compose > /dev/null 2>&1; then
        COMPOSE="docker-compose -f docker-compose.prod.yml"
    else
        echo "ERROR: neither the docker compose plugin nor the standalone docker-compose is installed on this host" >&2
        exit 1
    fi
}
