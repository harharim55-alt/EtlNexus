#!/bin/sh
# Runtime env injection — replace the build-time Airflow URL with the
# runtime VITE_AIRFLOW_URL so exported images work on any host without
# rebuilding the frontend.
if [ -n "$VITE_AIRFLOW_URL" ]; then
  find /usr/share/nginx/html/assets -name '*.js' -exec \
    sed -i "s|http://localhost:8080|${VITE_AIRFLOW_URL}|g" {} +
fi
exec "$@"
