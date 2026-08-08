#!/usr/bin/env bash
# Renders the stable nginx router configuration for one release. Keeping this
# pure makes the write-lock rules testable without touching Docker or production.
set -euo pipefail

RELEASE_VERSION="${1:?usage: render_router_config.sh <version> <frontend-alias> <write-lock-enabled> [upstream|legacy]}"
FRONTEND_ALIAS="${2:?usage: render_router_config.sh <version> <frontend-alias> <write-lock-enabled> [upstream|legacy]}"
WRITE_LOCK_ENABLED="${3:?usage: render_router_config.sh <version> <frontend-alias> <write-lock-enabled> [upstream|legacy]}"
ROUTER_MODE="${4:-upstream}"

case "$ROUTER_MODE" in
    upstream|legacy) ;;
    *)
        echo "ERROR: router mode must be upstream or legacy." >&2
        exit 2
        ;;
esac

case "$WRITE_LOCK_ENABLED" in
    true)
        LOCK_RULES="$(cat <<'EOF'
    ~^(PUT|PATCH|DELETE):/trees/[^/]+/layout$ 1;
    ~^POST:/fhir/import$ 1;
    ~^POST:/dashboard/seed$ 1;
    ~^POST:/regimen-decisions$ 1;
EOF
)"
        LOCK_PROBE_LOCATION="$(cat <<'EOF'
    location = /__deployment/write-lock-probe {
        default_type application/json;
        add_header Retry-After "60" always;
        add_header Cache-Control "no-store" always;
        return 503 '{"detail":"Deployment maintenance is in progress; retry this write shortly."}';
    }
EOF
)"
        ;;
    false)
        LOCK_RULES=""
        LOCK_PROBE_LOCATION=""
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
EOF

if [ "$ROUTER_MODE" = "legacy" ]; then
    cat <<EOF
server {
    listen 80;
    server_name _;
    add_header X-CDSS-Release "${RELEASE_VERSION}" always;

${LOCK_PROBE_LOCATION}

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

    root /usr/share/nginx/html;
    index index.html;
    gzip on;

    location = /health {
        proxy_pass http://backend:8000/health;
    }

    location /trees {
        proxy_pass http://backend:8000/trees;
    }

    location /evaluate {
        proxy_pass http://backend:8000/evaluate;
    }

    location /fhir/ {
        proxy_pass http://backend:8000/fhir/;
    }

    location /medicines/ {
        proxy_pass http://backend:8000/medicines/;
    }

    location = /regimen-decisions {
        proxy_pass http://backend:8000/regimen-decisions;
    }

    location = /dashboard {
        try_files \$uri \$uri/ /index.html;
    }

    location = /dashboard/ {
        try_files \$uri \$uri/ /index.html;
    }

    location /dashboard/ {
        proxy_pass http://backend:8000/dashboard/;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF
else
    cat <<EOF
server {
    listen 80;
    server_name _;
    add_header X-CDSS-Release "${RELEASE_VERSION}" always;

${LOCK_PROBE_LOCATION}

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
fi
