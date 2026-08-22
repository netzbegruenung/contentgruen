# 🚀 Deployment Guide – Gut gesagt

This guide helps you deploy Gut gesagt in a test or production environment using Docker and `docker-compose`.
Prod Server is managed by Saltstack.

We aim for a **clean, reproducible setup** with minimal manual steps.

---

## 📦 What's in the box?

| Component              | Tech              | Purpose                                          |
|-----------------------|-------------------|--------------------------------------------------|
| Frontend              | Angular           | UI served via Nginx                              |
| BFF                   | .NET + YARP       | API Gateway (PROD: with Keycloak authentication) |
| Semantic Search       | Python + FastAPI  | NLP-based semantic search backend                |
| Qdrant                | Vector DB         | Vector embeddings for semantic search            |
| PostgreSQL            | SQL Database      | Application metadata (usage tracking, etc.)      |
| Reverse Proxy         | Nginx             | TLS termination & routing (PROD: via SaltStack)  |

---

## ⚡ Quick Deploy (Local Development)

If you're running locally for development, use Docker Compose:

```bash
cd mvp
docker compose -f docker-compose.dev.yml build
docker compose -f docker-compose.dev.yml up -d
```

Then access:

* Frontend: [http://localhost:80](http://localhost:80)
* BFF: [http://localhost:5054](http://localhost:5054)
* Semantic Search: [http://localhost:8000/docs](http://localhost:8000/docs)
* PostgreSQL: `localhost:5433` (for debugging; container listens on 5432)

> All containers run isolated and talk via Docker network.

---

## 🧪 Test System

> **In transition.** The test environment is moving to SaltStack management. The manually
> managed system described below is being **discontinued**.

### Current (SaltStack-managed)

- 🔗 Frontend: https://contentgruen-test.netzbegruenung.de
- **Management:** SaltStack, alongside production
- **Images:** floating `:main` tag, pulled automatically by a Watchtower sidecar, so every
  merge to `main` reaches this environment without a Salt run
- **Backups:** disabled (`enable_backup: false` in the Salt pillar)

### Legacy (manual, being discontinued)

- 🔗 Frontend: [https://test.contentgruen.de](https://test.contentgruen.de)
- 🔗 BFF API: [https://bff.test.contentgruen.de](https://bff.test.contentgruen.de)
- 🔗 API Docs: [https://bff.test.contentgruen.de/docs](https://bff.test.contentgruen.de/docs)

### Server Details (legacy system)

- **Host:** Hetzner VPS — hostname and credentials are not published here.
  Ask in the project channel if you need access.
- **OS:** Ubuntu 24.04 LTS
- **Access:** SSH with key authentication
- **Management:** Manual (not in SaltStack)

### Deployment Process (legacy system)

1. **SSH to the test server** (host and user from the project channel):
   ```bash
   ssh <user>@<test-host>
   ```

2. **Update the compose file:**
   ```bash
   cd <deployment-dir>
   nano docker-compose.yml  # Use mvp/docker-compose.tst.yml from this repo
   ```

3. **Deploy:**
   ```bash
   docker compose pull
   docker compose up -d
   docker compose logs -f  # Check for errors
   ```

### Service Configuration (legacy system)

Services are configured to only listen on localhost and are proxied via Nginx:
- Frontend: `127.0.0.1:3000` → nginx → `https://test.contentgruen.de`
- BFF: `127.0.0.1:3001` → nginx → `https://bff.test.contentgruen.de`
- Semantic Search: Internal only (accessed via BFF)
- PostgreSQL: Internal only

### Nginx Configuration (legacy system)

Located in `/etc/nginx/sites-available/`:
- `test.contentgruen.de.conf` - Frontend proxy
- `bff.test.contentgruen.de.conf` - BFF proxy

TLS certificates are managed by Certbot with automatic renewal.

---

## 🌻 Production System

### 🖥 Server

- **Host:** `contentgruen.netzbegruenung.verdigado.net`
- **Access:** SSH via Netzbegruenung SaltStack managed users
- **Management:** Fully automated via SaltStack

### 🌐 Domains & Routing

In production, Gut gesagt is accessed via subdomains routed by an external Nginx reverse proxy:

| Domain/Subdomain                                | Target Service          |
| ----------------------------------------------- | ----------------------- |
| `contentgruen.netzbegruenung.de`                | Angular Frontend (:3000)|
| `contentgruen.netzbegruenung.verdigado.net`     | Angular Frontend (:3000)|
| `bff.contentgruen.netzbegruenung.de`            | .NET API Gateway (:3001)|

The two frontend hostnames share one nginx server block. Port 80 is a blanket redirect to
HTTPS.

`contentgruen.de` redirects to `contentgruen.netzbegruenung.de`. That redirect is **not** part
of the SaltStack state — it is handled upstream (registrar/DNS level).

Server and Nginx are managed via the Netzbegruenung/Verdigado SaltStack:
> https://git.verdigado.com/verdigado-Privileged/Salt/src/branch/master/states/contentgruen

TLS is managed automatically using Let's Encrypt certificates.
Renewal is handled via certbot by the default nginx-reverse-proxy from the SaltStack setup.

### 📂 Data & Persistence

Compose runs with a working directory of `/opt/contentgruen`, so Docker prefixes the declared
volume names with `contentgruen_`:

| Service          | Docker volume                            | Note                                    |
| ---------------- | ---------------------------------------- | --------------------------------------- |
| Qdrant           | `contentgruen_qdrant_storage`            | Content and vector embeddings           |
| PostgreSQL       | `contentgruen_pgdata_app`                | Application data (votes, usage, reports)|
| Semantic Search  | `contentgruen_semantic_search_metadata`  | Index metadata                          |
| TLS certs        | `/etc/letsencrypt/`                      | Managed outside containers              |

The production database is `contentgruen_app`, user `app_user`; the password comes from a
Passbolt-backed Salt pillar.

### 🚧 Updating Production

CI runs on GitHub Actions:
- `.github/workflows/build.yml` — builds on every push to `main` and on pull requests,
  publishing `:main` and `:sha-<short>` tags. The SaltStack-managed test environment tracks
  `:main` via Watchtower.
- `.github/workflows/release.yml` — runs on `v*` tags, publishing `:vX.Y.Z`, `:X.Y` and
  `:latest` for all four images.

Both run the same test suites first, defined once in `.github/workflows/tests-backend.yml`
and `tests-frontend.yml` and called by each; images are pushed only if they pass.

`:latest` is produced by `docker/metadata-action`'s `latest=auto` flavor: it moves for normal
release tags but is skipped for prereleases (`v1.2.3-rc.1`), so release candidates can be
tagged without moving production.

Images are pushed into the Netzbegruenung/Verdigado registry:
> https://git.verdigado.com/netzbegruenung-images/-/packages

**How production actually updates:** the Salt compose file pins each image by digest
(`:latest@sha256:…`). A Renovate bot raises the digest bumps; production changes only when
that compose file is rewritten and Salt re-runs `docker compose pull` + `down`/`up`. There is
no Watchtower in production.

> Because production pins `:latest`, the `latest=auto` flavor in `release.yml` is load-bearing.
> Disabling it, or moving the tag rules away from `type=semver`, would stop `:latest` moving
> and silently freeze production updates with no failing build to signal it.

**Deployment Schedule:**
- Automatic: Weekly by the Netzbegruenung/Verdigado admin team
- Manual: Ask in the project channel for urgent deployments

---

## 🔧 Maintenance Tasks

### Cleanup Docker Resources (Test Server)

```bash
# Check disk usage
df -h
docker system df

# Remove unused images (careful!)
docker image prune -a --filter "until=24h" -f

# Remove all unused resources
docker system prune -a --volumes -f
```

### Backup and Restore System

Gut gesagt uses an automated backup system that backs up both Qdrant vector data and PostgreSQL metadata.

**First-time setup:**

No setup script is required — `backup.sh` creates `/opt/contentgruen-backups/{daily,weekly}/`
on first run. In production the cron schedule is provisioned by SaltStack.

**Create backup:**
```bash
cd /opt/contentgruen/mvp/scripts/backup
./backup.sh
```

**Restore from backup:**

Paths are resolved relative to `/opt/contentgruen-backups/`:
```bash
cd /opt/contentgruen/mvp/scripts/backup
./restore.sh daily/latest                    # Latest daily backup
./restore.sh weekly/latest                   # Latest weekly backup
./restore.sh daily/backup_YYYYMMDD_HHMMSS    # A specific backup
```

**Test backup/restore:**
```bash
cd /opt/contentgruen/mvp/scripts/backup
./test-backup-restore.sh
```

**What gets backed up:**
- ✅ Qdrant vector database (content embeddings)
- ✅ PostgreSQL application database (usage tracking, metadata)
- ✅ Backup metadata with checksums for integrity verification

**Storage location:**
- Backups are stored in `/opt/contentgruen-backups/{daily,weekly}/` on the host
- Runs on Sunday additionally produce a weekly backup
- Automatic rotation keeps the last 7 daily and 4 weekly backups
  (`KEEP_DAILY` / `KEEP_WEEKLY` at the top of `backup.sh`)
- Each backup includes: `qdrant_snapshot.tar`, `postgresql.sql`, `metadata.json`

**Important notes:**
- Restore is a destructive operation - always confirm before running
- For remote admin access: Qdrant dashboard at `http://localhost:6333/dashboard` (localhost-only for security)
- See `mvp/scripts/backup/README.md` for detailed documentation

### View Logs

```bash
# All services
docker compose logs -f --tail=100

# Specific service
docker compose logs contentgruen-bff -f --tail=50
```

---

## 🧯 Troubleshooting

### Nothing loads?

```bash
# Check container status
docker compose ps

# Check logs for errors
docker compose logs -f

# Test internal connectivity
docker exec contentgruen-bff curl http://contentgruen-semantic-search:8000/health
```

### Nginx issues?

```bash
# Check Nginx status
systemctl status nginx

# Test Nginx config
nginx -t

# View error logs
tail -f /var/log/nginx/error.log
```

### TLS certificate expired?

```bash
# Manual renewal
sudo certbot renew

# Force renewal
sudo certbot renew --force-renewal
```

### PostgreSQL connection issues?

```bash
# Check if PostgreSQL is running
docker exec contentgruen-app-postgres pg_isready

# Connect to database
docker exec -it contentgruen-app-postgres psql -U app_user -d contentgruen_app
```

---

## 🔮 What's next?

* Monitoring setup (Uptime Robot, Prometheus + Grafana)
* Unified test/prod deployment via GitOps
* Migration to Kubernetes (long-term)

---

## 🤝 Need help?

Talk to us in the Chatbegrünung channel:
- 📢 `#ProjektContentGrün`
- 🔗 [chatbegruenung.de](https://chatbegruenung.de/channel/ProjektContentGruen)

Ask in the channel for test-system or production access — the maintainers are reachable there.

---

## 💚 Thanks

This system is built to support digital democracy and collaborative communication.
Thanks for helping make it more stable and useful!

---

*Last updated: 2026-07-25*
