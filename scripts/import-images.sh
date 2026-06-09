#!/usr/bin/env bash
# Load Docker images from tarballs on a closed-network machine.
# Usage:
#   ./import-images.sh [image-dir]
# Default: current directory
set -euo pipefail

IMG_DIR=${1:-.}

if ! ls "$IMG_DIR"/*.tar &>/dev/null; then
  echo "No .tar files found in $IMG_DIR"
  exit 1
fi

echo "=== Loading Docker images ==="
for tarball in "$IMG_DIR"/*.tar; do
  SIZE=$(du -h "$tarball" | cut -f1)
  echo "  Loading $(basename "$tarball") ($SIZE)..."
  docker load -i "$tarball"
done

echo ""
echo "=== All images loaded ==="
docker images --format 'table {{.Repository}}\t{{.Tag}}\t{{.Size}}' | head -20
echo ""
echo "Next steps:"
echo "  1. cp .env.example .env"
echo "  2. Edit .env with your environment settings (database, Spark Connect, SSO, etc.)"
echo "  3. docker compose up -d"
