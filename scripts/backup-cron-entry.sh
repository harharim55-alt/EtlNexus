#!/usr/bin/env bash
# Entrypoint for the db-backup container.
# Sets up a cron job to run backups and starts crond in foreground.
set -euo pipefail

BACKUP_SCHEDULE="${BACKUP_SCHEDULE:-0 2 * * *}"

# Write environment to a file so cron jobs inherit it
printenv | grep -E '^(PG|BACKUP_|RETENTION_)' > /etc/backup.env

# Create cron job
echo "${BACKUP_SCHEDULE} . /etc/backup.env && /scripts/backup-db.sh >> /var/log/backup.log 2>&1" | crontab -

echo "[$(date -Iseconds)] Backup cron scheduled: ${BACKUP_SCHEDULE}"

# Run an initial backup on startup
/scripts/backup-db.sh

# Start cron in foreground
exec crond -f -l 2
