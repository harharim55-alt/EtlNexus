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

if [ "$MODE" = "prod" ]; then
  echo "=== Exporting PROD images ==="
  IMAGES=(
    "postgres:16-alpine"
    "etlnexus-backend"
    "etlnexus-frontend"
  )
  cp docker-compose.prod.yml "$OUT_DIR/docker-compose.yml"
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
  cp docker-compose.yml "$OUT_DIR/docker-compose.yml"
fi

for img in "${IMAGES[@]}"; do
  filename=$(echo "$img" | tr '/:' '__')
  echo "  Saving $img -> ${filename}.tar"
  docker save "$img" -o "$OUT_DIR/${filename}.tar"
done

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
