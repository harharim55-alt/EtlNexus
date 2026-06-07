#!/usr/bin/env bash
# Export all Docker images needed for closed-network deployment.
# Usage:
#   ./scripts/export-images.sh prod [output-dir]   # db + backend + frontend only
#   ./scripts/export-images.sh dev  [output-dir]   # full stack (Airflow, Keycloak, Iceberg, etc.)
set -euo pipefail

MODE=${1:-prod}
OUT_DIR=${2:-./etlnexus-images}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

mkdir -p "$OUT_DIR"

echo "=== Building images ==="
docker compose build

# Generate offline compose file (strip build/develop sections)
if [ "$MODE" = "prod" ]; then
  echo "=== Exporting PROD images ==="
  IMAGES=(
    "postgres:16-alpine"
    "etlnexus-backend"
    "etlnexus-frontend"
  )
  python3 "$SCRIPT_DIR/strip_compose_build.py" docker-compose.prod.yml "$OUT_DIR/docker-compose.yml"
else
  echo "=== Exporting DEV images (full stack) ==="
  IMAGES=(
    "postgres:16-alpine"
    "etlnexus-backend"
    "etlnexus-frontend"
    "etlnexus-airflow-webserver"
    "etlnexus-airflow-scheduler"
    "etlnexus-airflow-init"
    "etlnexus-iceberg-data-seed"
    "tabulario/iceberg-rest:latest"
    "quay.io/keycloak/keycloak:26.2"
    "python:3.12-slim"
    "alpine:latest"
  )
  python3 "$SCRIPT_DIR/strip_compose_build.py" docker-compose.yml "$OUT_DIR/docker-compose.yml"

  # Bundle runtime files needed by volume mounts (DAGs, seeds, Keycloak realm)
  echo "=== Bundling dev runtime files ==="
  mkdir -p "$OUT_DIR/dev"
  cp -r dev/dags "$OUT_DIR/dev/dags"
  cp -r dev/seeds "$OUT_DIR/dev/seeds"
  cp -r dev/keycloak "$OUT_DIR/dev/keycloak"
fi

# Save all images in a single tarball (deduplicates shared layers)
echo "  Saving ${#IMAGES[@]} images -> images.tar"
docker save "${IMAGES[@]}" -o "$OUT_DIR/images.tar"
echo "  Size: $(du -h "$OUT_DIR/images.tar" | cut -f1)"

cp .env.example "$OUT_DIR/.env.example"
cp "$SCRIPT_DIR/import-images.sh" "$OUT_DIR/import-images.sh"

echo ""
echo "=== Export complete ==="
echo "Output directory: $OUT_DIR"
echo "Files:"
ls -lh "$OUT_DIR"
echo ""
echo "Transfer the '$OUT_DIR' directory to the closed network and run:"
echo "  ./import-images.sh"
echo "  cp .env.example .env && vi .env  # configure for your environment"
echo "  docker compose up -d"
