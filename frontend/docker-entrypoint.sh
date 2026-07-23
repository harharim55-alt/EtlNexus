#!/bin/sh
# Runtime config injection — generates a config.js with environment-specific
# values, avoiding fragile sed replacement in compiled JS assets.
cat <<EOF > /usr/share/nginx/html/config.js
window.__RUNTIME_CONFIG__ = {
  AIRFLOW_URL: "${VITE_AIRFLOW_URL:-http://localhost:8080}"
};
EOF

# Resolve environment variables in nginx config (defaults for local dev)
export BACKEND_HOST="${BACKEND_HOST:-backend}"
# CSP connect-src: in dev, allow localhost; in prod, set to your Keycloak/API domains
export CSP_CONNECT_SRC="${CSP_CONNECT_SRC:-http://localhost:* https://localhost:* ws://localhost:*}"
# /api proxy timeouts — generous so slow AI Architect replies aren't cut (must be >=
# the SPA's AI_REQUEST_TIMEOUT_SECONDS). Use nginx time units (e.g. 300s).
export API_PROXY_READ_TIMEOUT="${API_PROXY_READ_TIMEOUT:-300s}"
export API_PROXY_SEND_TIMEOUT="${API_PROXY_SEND_TIMEOUT:-300s}"
# DNS resolver for the per-request backend lookup: first nameserver from /etc/resolv.conf,
# so it works under Docker (127.0.0.11) and Kubernetes/OpenShift (cluster DNS).
export NGINX_RESOLVER="${NGINX_RESOLVER:-$(awk '/^nameserver/ {print $2; exit}' /etc/resolv.conf)}"
export NGINX_RESOLVER="${NGINX_RESOLVER:-127.0.0.11}"
envsubst '${BACKEND_HOST} ${CSP_CONNECT_SRC} ${API_PROXY_READ_TIMEOUT} ${API_PROXY_SEND_TIMEOUT} ${NGINX_RESOLVER}' < /etc/nginx/conf.d/default.conf > /etc/nginx/conf.d/default.conf.tmp
mv /etc/nginx/conf.d/default.conf.tmp /etc/nginx/conf.d/default.conf

exec "$@"
