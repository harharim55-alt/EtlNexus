#!/bin/sh
# Runtime config injection — generates a config.js with environment-specific
# values, avoiding fragile sed replacement in compiled JS assets.
cat <<EOF > /usr/share/nginx/html/config.js
window.__RUNTIME_CONFIG__ = {};
EOF

# Resolve environment variables in nginx config (defaults for local dev)
export BACKEND_HOST="${BACKEND_HOST:-backend}"
# CSP connect-src: in dev, allow localhost; in prod, set to your Keycloak/API domains
export CSP_CONNECT_SRC="${CSP_CONNECT_SRC:-http://localhost:* https://localhost:* ws://localhost:*}"
envsubst '${BACKEND_HOST} ${CSP_CONNECT_SRC}' < /etc/nginx/conf.d/default.conf > /etc/nginx/conf.d/default.conf.tmp
mv /etc/nginx/conf.d/default.conf.tmp /etc/nginx/conf.d/default.conf

exec "$@"
