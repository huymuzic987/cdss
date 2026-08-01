#!/usr/bin/env bash
# Shared helper for deploy/*.sh scripts. Figures out which Docker Compose
# CLI is available on this host and sets $COMPOSE accordingly - not every
# host has the newer `docker compose` plugin; some only have the legacy
# standalone docker-compose binary.
#
# Pass a compose project name (e.g. "cdss-42") to get an isolated stack --
# its own containers, network, and volume -- side by side with any other
# project. Omit it for the default (unnamed) project, e.g. for one-off local
# use. See provision_stack.sh/promote_stack.sh/prune_old_stacks.sh for how
# the blue/green deploy flow uses this.
resolve_compose() {
    local project="${1:-}"
    local project_flag=""
    if [ -n "$project" ]; then
        project_flag="-p $project"
    fi
    if docker compose version > /dev/null 2>&1; then
        COMPOSE="docker compose $project_flag -f docker-compose.prod.yml"
    elif command -v docker-compose > /dev/null 2>&1; then
        COMPOSE="docker-compose $project_flag -f docker-compose.prod.yml"
    else
        echo "ERROR: neither the docker compose plugin nor the standalone docker-compose is installed on this host" >&2
        exit 1
    fi
}
