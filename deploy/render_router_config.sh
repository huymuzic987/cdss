#!/usr/bin/env bash
# Renders the stable nginx router configuration for one release. Keeping this
# pure makes the write-lock rules testable without touching Docker or production.
set -euo pipefail

RELEASE_VERSION="${1:?usage: render_router_config.sh <version> <frontend-alias> <write-lock-enabled>}"
FRONTEND_ALIAS="${2:?usage: render_router_config.sh <version> <frontend-alias> <write-lock-enabled>}"
WRITE_LOCK_ENABLED="${3:?usage: render_router_config.sh <version> <frontend-alias> <write-lock-enabled>}"

case "$WRITE_LOCK_ENABLED" in
    true)
        LOCK_RULES="$(cat <<'EOF'
    ~^(PUT|PATCH|DELETE):/trees/[^/]+/layout$ 1;
    ~^POST:/fhir/import$ 1;
    ~^POST:/dashboard/seed$ 1;
    ~^POST:/__deployment/write-lock-probe$ 1;
EOF
)"
        ;;
    false)
        LOCK_RULES=""
        ;;
    *)
        echo "ERROR: write-lock-enabled must be true or false." >&2
        exit 2
        ;;
esac

cat <<EOF
map "\$request_method:\$uri" \$cdss_write_blocked {
    default 0;
${LOCK_RULES}
}

server {
    listen 80;
    server_name _;
    add_header X-CDSS-Release "${RELEASE_VERSION}" always;

    if (\$cdss_write_blocked = 1) {
        return 418;
    }

    error_page 418 = @deployment_write_maintenance;
    location @deployment_write_maintenance {
        default_type application/json;
        add_header Retry-After "60" always;
        add_header Cache-Control "no-store" always;
        return 503 '{"detail":"Deployment maintenance is in progress; retry this write shortly."}';
    }

    # Docker's embedded DNS is queried repeatedly, so a frontend container
    # restart does not leave nginx pinned to its former IP address.
    resolver 127.0.0.11 ipv6=off valid=10s;
    set \$release_upstream http://${FRONTEND_ALIAS};

    location / {
        proxy_pass \$release_upstream;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
