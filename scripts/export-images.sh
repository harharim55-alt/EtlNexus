#!/usr/bin/env bash
# Export the two images (backend + frontend) for offline deployment.
#
# The stack connects to EXISTING external services (PostgreSQL, LLM endpoint, Spark
# Connect, Keycloak/OIDC) configured entirely via .env — only these two images ship.
set -euo pipefail

OUT_DIR=${1:-./etlnexus-images}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"
mkdir -p "$OUT_DIR"

echo "=== Building images ==="
docker compose build

IMAGES=(
  "etlnexus-backend"
  "etlnexus-frontend"
)

echo "=== Generating offline compose (strip build/develop) ==="
python3 "$SCRIPT_DIR/strip_compose_build.py" --strip build,develop \
  docker-compose.yml "$OUT_DIR/docker-compose.yml"

echo "  Saving ${#IMAGES[@]} images -> images.tar"
docker save "${IMAGES[@]}" -o "$OUT_DIR/images.tar"
echo "  Size: $(du -h "$OUT_DIR/images.tar" | cut -f1)"

cp .env.example "$OUT_DIR/.env.example"
cp "$SCRIPT_DIR/import-images.sh" "$OUT_DIR/import-images.sh"

echo ""
echo "=== Export complete -> $OUT_DIR ==="
ls -lh "$OUT_DIR"
echo ""
echo "On the target:"
echo "  ./import-images.sh                   # docker load images.tar"
echo "  cp .env.example .env  &&  edit .env  # point at your external DB/LLM/Spark/Keycloak"
echo "  docker compose up -d"
