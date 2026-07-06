# 🚀 Deployment Guide – ContentGrün

This guide helps you deploy ContentGrün in a test or production environment using Docker and `docker-compose`.
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
* PostgreSQL: `localhost:5432` (for debugging)

> All containers run isolated and talk via Docker network.

---

## 🧪 Test System

We run a public test system at:

- 🔗 Frontend: [https://test.contentgruen.de](https://test.contentgruen.de)
- 🔗 BFF API: [https://bff.test.contentgruen.de](https://bff.test.contentgruen.de)
- 🔗 API Docs: [https://bff.test.contentgruen.de/docs](https://bff.test.contentgruen.de/docs)

### Server Details

- **Host:** `188.245.188.134` (Hetzner VPS)
- **OS:** Ubuntu 24.04 LTS
- **Access:** SSH with key authentication
- **Management:** Manual (not in SaltStack)

### Deployment Process

1. **SSH to server:**
   ```bash
   ssh root@188.245.188.134
   ```

2. **Update docker-compose.yml:**
   ```bash
   cd /root
   nano docker-compose.yml  # Use docker-compose.tst.yml from repo
   ```

3. **Deploy:**
   ```bash
   docker compose pull
   docker compose up -d
   docker compose logs -f  # Check for errors
   ```

### Service Configuration

Services are configured to only listen on localhost and are proxied via Nginx:
- Frontend: `127.0.0.1:3000` → nginx → `https://test.contentgruen.de`
- BFF: `127.0.0.1:3001` → nginx → `https://bff.test.contentgruen.de`
- Semantic Search: Internal only (accessed via BFF)
- PostgreSQL: Internal only

### Nginx Configuration

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

In production, ContentGrün is accessed via subdomains routed by an external Nginx reverse proxy:

| Domain/Subdomain        | Target Service     |
| ----------------------- | ------------------ |
| `contentgruen.de`       | Angular Frontend   |
| `bff.contentgruen.de`   | .NET API Gateway   |

Server and Nginx are managed via the Netzbegruenung/Verdigado SaltStack:
> https://git.verdigado.com/verdigado-Privileged/Salt/src/branch/master/states/contentgruen

TLS is managed automatically using Let's Encrypt certificates.
Renewal is handled via certbot by the default nginx-reverse-proxy from the SaltStack setup.

### 📂 Data & Persistence

| Service          | Storage Location                           | Note                           |
| ---------------- | ------------------------------------------ | ------------------------------ |
| PostgreSQL       | Docker volume `pgdata-semantic`           | Vector embeddings & metadata   |
| Semantic Search  | Docker volume `semantic_search_metadata`  | Index metadata                 |
| TLS certs        | `/etc/letsencrypt/`                       | Managed outside containers     |

### 🚧 Updating Production

A CI pipeline is set up in the Netzbegruenung/Verdigado Woodpecker:
> https://ci.netzbegruenung.verdigado.net/repos/958

Images are automatically built from main and pushed into the Netzbegruenung/Verdigado registry:
> https://git.verdigado.com/netzbegruenung-images/-/packages

**Deployment Schedule:**
- Automatic: Every Friday by Netzbegruenung/Verdigado admin
- Manual: Contact Sven or admin team for urgent deployments

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

ContentGrün uses an automated backup system that backs up both Qdrant vector data and PostgreSQL metadata.

**First-time setup:**
```bash
cd /opt/contentgruen/mvp/scripts/backup  # Adjust path to your deployment
sudo ./setup-backup-system.sh
```

**Create backup:**
```bash
cd /opt/contentgruen/mvp/scripts/backup
./backup.sh                    # Regular backup
./backup.sh --compress         # Compressed backup
```

**Restore from backup:**
```bash
cd /opt/contentgruen/mvp/scripts/backup
./restore.sh                   # Restore latest backup
./restore.sh backup_YYYYMMDD_HHMMSS  # Restore specific backup
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
- Backups are stored in `/opt/contentgruen-backups/` on the host
- Automatic cleanup keeps last 7 backups (configurable via `KEEP_BACKUPS` env var)
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
docker exec contentgruen-postgres-semantic pg_isready

# Connect to database
docker exec -it contentgruen-postgres-semantic psql -U semantic_search
```

---

## 🔮 What's next?

* Monitoring setup (Uptime Robot, Prometheus + Grafana)
* Automated backups with rotation
* Unified test/prod deployment via GitOps
* Migration to Kubernetes (long-term)

---

## 🤝 Need help?

Talk to us in the Chatbegrünung channel:
- 📢 `#ProjektContentGrün`
- 🔗 [chatbegruenung.de](https://chatbegruenung.de/channel/ProjektContentGruen)
- 👤 Contact: Sebastian Banach (Test System), Sven (Production)

---

## 💚 Thanks

This system is built to support digital democracy and collaborative communication.
Thanks for helping make it more stable and useful!

---

*Last updated: August 9, 2025*
