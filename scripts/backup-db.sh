#!/usr/bin/env bash
# Database backup script for EtlNexus PostgreSQL
# Runs pg_dump with gzip compression and manages retention.
#
# Environment variables:
#   PGHOST       - PostgreSQL host (default: db)
#   PGPORT       - PostgreSQL port (default: 5432)
#   PGUSER       - PostgreSQL user (default: etlnexus)
#   PGDATABASE   - Database name (default: etlnexus)
#   PGPASSWORD   - PostgreSQL password (required)
#   BACKUP_DIR   - Backup output directory (default: /backups)
#   RETENTION_DAYS - Number of days to keep backups (default: 30)

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/etlnexus_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -Iseconds)] Starting database backup..."

pg_dump \
  -h "${PGHOST:-db}" \
  -p "${PGPORT:-5432}" \
  -U "${PGUSER:-etlnexus}" \
  -d "${PGDATABASE:-etlnexus}" \
  --no-owner \
  --no-privileges \
  | gzip > "${BACKUP_FILE}"

FILESIZE=$(stat -f%z "${BACKUP_FILE}" 2>/dev/null || stat -c%s "${BACKUP_FILE}" 2>/dev/null || echo "unknown")
echo "[$(date -Iseconds)] Backup completed: ${BACKUP_FILE} (${FILESIZE} bytes)"

# Clean up old backups
if [ "${RETENTION_DAYS}" -gt 0 ]; then
  DELETED=$(find "${BACKUP_DIR}" -name "etlnexus_*.sql.gz" -type f -mtime +"${RETENTION_DAYS}" -delete -print | wc -l)
  if [ "${DELETED}" -gt 0 ]; then
    echo "[$(date -Iseconds)] Cleaned up ${DELETED} backup(s) older than ${RETENTION_DAYS} days"
  fi
fi

echo "[$(date -Iseconds)] Backup complete"
