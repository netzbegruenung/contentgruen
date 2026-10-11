# Gut gesagt Backup & Restore System

## Quick Start

### Create a Backup

```bash
cd mvp/scripts/backup # Or place backup script on server
./backup.sh
```

Creates timestamped backup in `/opt/contentgruen-backups/daily/` with automatic rotation:
- **Daily backups**: Last 7 days
- **Weekly backups**: Last 4 weeks (Sundays)

### Restore from Backup

```bash
cd mvp/scripts/backup # Or place restore script on server

# Paths are resolved relative to /opt/contentgruen-backups/ -- pass a relative
# path, not an absolute one.

# Restore latest daily backup
./restore.sh daily/latest

# Restore latest weekly backup
./restore.sh weekly/latest

# Restore specific backup
./restore.sh daily/backup_20250106_030000

# Without an argument: daily/latest
./restore.sh
```

### Test Backup/Restore

```bash
cd mvp/scripts/backup # Or place test script next to backup and restore scripts on server
./test-backup-restore.sh
```

The test exits non-zero if any check fails.

### Testing in the dev stack

`docker-compose.dev.yml` does not mount `/backups`, and `/opt` is usually not writable.
Point `BACKUP_ROOT` at a writable directory and mount it into the application container
for the duration of the test (the container names are the defaults):

```bash
export BACKUP_ROOT="$HOME/cg-backups-test"; mkdir -p "$BACKUP_ROOT"
cat > /tmp/backup-mount.yml <<YML
services:
  contentgruen-semantic-search:
    volumes:
      - $BACKUP_ROOT:/backups
YML
docker compose -f mvp/docker-compose.dev.yml -f /tmp/backup-mount.yml \
  up -d --no-build --no-deps contentgruen-semantic-search
mvp/scripts/backup/test-backup-restore.sh
# afterwards: drop the extra mount again
docker compose -f mvp/docker-compose.dev.yml up -d --no-build --no-deps contentgruen-semantic-search
```

The restore replaces the dev database and the Qdrant collection with the state of the
backup taken a moment earlier; anything written in between is lost.

## Production Setup

### Automated (Recommended)

**For production servers with SaltStack:**
- Backup system is automatically configured via Salt states
- Extracts `backup.sh` from Docker container on deployment
- Creates backup directories and sets permissions
- Configures daily cron job (3 AM) and logrotate

**Manual cron setup:**
```bash
# Add to root crontab
crontab -e

# Daily backup at 3 AM
0 3 * * * /opt/contentgruen/backup.sh >> /opt/contentgruen-backups/backup.log 2>&1
```

### Manual Setup

```bash
# Create backup directory
sudo mkdir -p /opt/contentgruen-backups
sudo chmod 700 /opt/contentgruen-backups

# Extract backup/restore scripts from container
cd /opt/contentgruen
docker cp contentgruen-semantic-search:/scripts/backup/backup.sh backup.sh
docker cp contentgruen-semantic-search:/scripts/backup/restore.sh restore.sh
docker cp contentgruen-semantic-search:/scripts/backup/test-backup-restore.sh test-backup-restore.sh
chmod 755 backup.sh restore.sh test-backup-restore.sh

# Run first backup to initialize subdirectories (make sure that there is data in the qdrant DB already)
./backup.sh

# Add cron job (see above)
```

## What Gets Backed Up

### Qdrant Snapshot (`qdrant_snapshot.tar`)
- Complete collection snapshot via Qdrant API
- All content data, metadata, and vector embeddings
- Fast restore without re-embedding

### PostgreSQL Dump (`postgresql.sql`)
- Usage tracking and events
- Uses `pg_dump --clean --create` for full restore

### Metadata (`metadata.json`)
- Backup version, timestamp, checksums
- Host system and container information

## Backup Structure

```
/opt/contentgruen-backups/
├── daily/
│   ├── backup_20250106_030000/
│   │   ├── qdrant_snapshot.tar
│   │   ├── postgresql.sql
│   │   └── metadata.json
│   ├── backup_20250107_030000/
│   └── latest -> backup_20250107_030000/
├── weekly/
│   ├── backup_20250105_030000/  # Sundays
│   └── latest -> backup_20250105_030000/
└── backup.log
```

## Monitoring

```bash
# View backup log
tail -f /opt/contentgruen-backups/backup.log

# List backups
ls -lh /opt/contentgruen-backups/daily/
ls -lh /opt/contentgruen-backups/weekly/

# Check disk usage
du -sh /opt/contentgruen-backups/
```

## Docker Compose Configuration

Required volume mount for the backup system:

```yaml
services:
  contentgruen-semantic-search:
    volumes:
      - /opt/contentgruen-backups:/backups
```

The Qdrant snapshot is written by `backup_qdrant.py` inside the application container
to `/backups/...`; only this mount makes it appear in `/opt/contentgruen-backups` on the
host. Without it `backup.sh` aborts, because the snapshot is missing on the host. The host
side of the mount must match `BACKUP_ROOT` in the scripts. PostgreSQL needs no mount:
`pg_dump` streams to the host via stdout.

## Production Notes

### Port Exposure (Security)
- Qdrant and PostgreSQL exposed to **localhost only** (`127.0.0.1:6333`, `127.0.0.1:5432`)
- Allows backup scripts to access databases securely
- Admin access: SSH to server, then use localhost ports

### Qdrant Admin Dashboard
```bash
# Access via SSH tunnel
ssh -L 6333:localhost:6333 user@server
# Open http://localhost:6333/dashboard in local browser
```

## Disaster Recovery

### Complete System Recovery

1. **Fresh server with Docker/Docker Compose**
2. **Copy backup files to** `/opt/contentgruen-backups/`
3. **Start containers:** `docker-compose up -d`
4. **Extract restore script:** `docker cp contentgruen-semantic-search:/scripts/backup/restore.sh /opt/contentgruen/restore.sh && chmod 755 /opt/contentgruen/restore.sh`
5. **Restore data:** `/opt/contentgruen/restore.sh daily/latest`

### Partial Recovery

```bash
# Restore only Qdrant
docker exec contentgruen-semantic-search python /app/scripts/restore_qdrant.py \
  --input /backups/daily/latest/qdrant_snapshot.tar

# Restore only PostgreSQL (the dump drops and recreates the database itself,
# so connect to "postgres", not to contentgruen_app)
docker exec -i contentgruen-app-postgres psql -U app_user -d postgres -v ON_ERROR_STOP=1 \
  < /opt/contentgruen-backups/daily/latest/postgresql.sql
```

## Verification After Restore

```bash
# Check Qdrant collection
curl http://localhost:6333/collections/content_collection

# Check PostgreSQL data
docker exec contentgruen-app-postgres psql -U app_user -d contentgruen_app \
  -c "SELECT COUNT(*) FROM usage_tracking;"

# Check application health
curl http://localhost:8000/api/v1/health
```

## Troubleshooting

### Container Name Mismatch

Dev, test and production use the same container names; the scripts default to them and
accept overrides from the environment (no need to edit the scripts):

| Variable | Default |
|---|---|
| `POSTGRES_CONTAINER` | `contentgruen-app-postgres` |
| `APP_CONTAINER` | `contentgruen-semantic-search` |
| `QDRANT_CONTAINER` | `contentgruen-qdrant` |

```bash
POSTGRES_CONTAINER=other-name ./backup.sh
```

A container counts as running only if `docker ps --format '{{.Names}}'` lists exactly
that name.

### Permission Issues

```bash
sudo chown -R root:root /opt/contentgruen-backups
sudo chmod 700 /opt/contentgruen-backups
```

### Disk Space

Estimated storage (with ~66MB data):
- 7 daily backups: ~462 MB
- 4 weekly backups: ~264 MB
- **Total: ~1 GB**

Adjust retention in backup.sh if needed:
```bash
KEEP_DAILY=5  # Reduce from 7
KEEP_WEEKLY=2 # Reduce from 4
```
