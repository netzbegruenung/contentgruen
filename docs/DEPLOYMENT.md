# 🚀 Deployment Guide – Gut gesagt

This guide helps you deploy Gut gesagt with Docker and `docker compose`.
The test and production environments run on verdigado's internal infrastructure; how they
are operated is documented internally, not in this repository.

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
| Reverse Proxy         | Nginx             | TLS termination & routing (PROD: external proxy) |

---

## ⚡ Quick Deploy (Local Development)

If you're running locally for development, use Docker Compose:

```bash
cd mvp
docker compose -f docker-compose.dev.yml build
docker compose -f docker-compose.dev.yml up -d
```

Then access:

* Frontend: [http://localhost:8080](http://localhost:8080)
* BFF: [http://localhost:5054](http://localhost:5054)
* Semantic Search: [http://localhost:8000/docs](http://localhost:8000/docs)
* PostgreSQL: `localhost:5433` (for debugging; container listens on 5432)

> All containers run isolated and talk via Docker network.

---

## 🧪 Test System

- 🔗 Frontend: https://gutgesagt-test.netzbegruenung.de
- **Operation:** runs on verdigado's internal infrastructure, like production. Hosts, access
  and the deployment procedure are documented internally, not in this repository.
- **Images:** floating `:main` tag, rolled out **manually** by the operators. A merge to `main`
  does not reach this environment by itself. Database migrations need no manual step: the
  semantic search service applies them on startup, see "Database migrations" below.
  Changes to existing data in Qdrant ship as scripts in `mvp/scripts/manual/` and usually run
  right after the new image goes live; each script's README section gives the order.

---

## 🌻 Production System

### 🌐 Public domains

| Domain                            | Serves                  |
| --------------------------------- | ----------------------- |
| `gutgesagt.netzbegruenung.de`     | Angular Frontend        |
| `bff.gutgesagt.netzbegruenung.de` | .NET API Gateway (BFF)  |

`contentgruen.de` redirects to `gutgesagt.netzbegruenung.de`.

### 🖥 Operation

Production runs on verdigado's internal infrastructure: an external nginx reverse proxy
terminates TLS (Let's Encrypt) and routes the public domains to the frontend and BFF
containers. Server, reverse proxy, compose file, secrets and backup schedule are managed
there; the details are documented internally. `mvp/docker-compose.prd.yml` in this repository
is only a placeholder.

Memory: since #358 the semantic service also loads spaCy (`de_core_news_sm`) and CharSplit
for the Gegenlesen, about 0.5 GB more RAM than before (measured on the dev VM: ~180 MB for the
model, ~350 MB for CharSplit's n-gram table), loaded in the background about two seconds after
start. If the container has a memory limit, raise it accordingly.

Visitor counting (#446): the semantic service recognises visitors by a daily pseudonym built
from the client address and the User-Agent (`utils/besucher_pseudonym.py`). Two preconditions:

- **`X-Real-IP` reaches the semantic service.** nginx sets it, YARP in the BFF passes it on
  (`IdentityHeaderTransformTests` checks that it is not stripped). Without it the service only
  sees its peer, and all visitors with the same User-Agent count as one person. The header is
  only trustworthy while the BFF and the semantic service are reachable through nginx alone;
  a client that reaches them directly can choose its own address and inflate the person
  counts (the report rate limit relies on the same header).
- **One uvicorn worker.** The daily key lives in the memory of the process. With several
  workers a visitor would count once per worker; a restart counts visitors again on that day.

### 🚧 Updating Production

Pull requests are checked on Forgejo by Woodpecker (`.woodpecker/ci.yaml`, required status
for `main`, see [CI.md](CI.md)). After the merge, GitHub Actions on the mirror build the images:
- `.github/workflows/build.yml` — builds on every push to `main`, publishing `:main` and
  `:sha-<short>` tags. The test environment runs `:main`, rolled out manually (see above).
- `.github/workflows/release.yml` — runs on `v*` tags, publishing `:X.Y.Z` (the tag without
  its `v`), `:X.Y` and `:latest` for all four images.

Both run the same test suites first, defined once in `.github/workflows/tests-backend.yml`,
`tests-frontend.yml` and `tests-bff.yml` and called by each; images are pushed only if they pass.

`:latest` is produced by `docker/metadata-action`'s `latest=auto` flavor: it moves for normal
release tags but is skipped for prereleases (`v1.2.3-rc.1`). A prerelease tag therefore never
reaches production.

Images are pushed into the Netzbegruenung/Verdigado registry:
> https://git.verdigado.com/netzbegruenung-images/-/packages

**How production updates:** production pins `:latest` by digest. Renovate raises the digest
bumps; production changes only once the operators roll a bump out. A release tag does not
deploy anything by itself.

> Because production pins `:latest`, the `latest=auto` flavor in `release.yml` is
> load-bearing. Disabling it, or moving the tag rules away from `type=semver`, would stop
> `:latest` moving and silently freeze production updates with no failing build to signal it.

#### Releases

1. **Only the maintainer sets tags.** Agents and contributors propose, they do not tag.
2. **Version scheme:** `v0.x` releases until the launch (`v0.9.0` first), `v1.0.0` at the
   launch, [SemVer](https://semver.org/) after that. No release candidates (`-rc`): they do
   not move `:latest` (see above), and production only follows `:latest`.
3. **Version in the footer:** the footer shows the `version` from
   `mvp/frontend/gutgesagt-frontend/package.json`. Before tagging, a pull request sets it to
   `X.Y.Z` (without the `v`); otherwise the new images show the old number.
   `npm version X.Y.Z --no-git-tag-version` in that directory also updates `package-lock.json`.
4. **Tag on Forgejo:** set the tag on a commit of `main` on Forgejo. The push mirror carries it
   to GitHub, where `release.yml` tests and builds the images. Check that the run is green
   and `:latest` moved before announcing the release.
5. **Change list:** the change list of a release is the Forgejo release to its tag (Releases on
   the Forgejo repository). Draft it with
   ```bash
   git fetch origin --tags
   scripts/changelog.sh vX.Y.Z > changelog.md   # since the previous v* tag
   scripts/changelog.sh vX.Y.Z <commit>         # first release, or a different start
   ```
   The script lists the merged pull requests on `main` (linked, grouped by their Conventional
   Commits prefix into Breaking Changes, Neu, Behoben, Sonstiges), the new migrations and the new
   scripts in `mvp/scripts/manual/`. It recognises a breaking change only by the `!` in the PR
   title (`feat!:`), not by a `BREAKING CHANGE:` footer, and links any commit on `main` whose
   subject ends in `(#N)` as pull request N. Review the draft, add operational steps it cannot
   know (for example a rename that needs action per environment), and publish it as the release.

For urgent deployments, ask in the project channel (see below).

---

## 🗄 Database migrations

The SQL migrations in `mvp/backend/postgres-app/migrations/` are part of the semantic search
image (`/migrations`). On every start, after creating missing tables and before accepting
requests, the service applies each migration that is not yet recorded in the table
`migrationsprotokoll`, ordered by file name without `.sql`. Each migration and its record are
committed in one transaction, so a migration recorded there never runs again.

What this means for a rollout:

- **Nothing to apply by hand.** Rolling out a new image is enough, in test and production alike.
  The service starts serving only after its migrations are in.
- **A failing migration stops the start.** It is rolled back and recorded as `fehlgeschlagen`;
  later migrations do not run. A migration waits at most 30 s for a lock, or less if it sets
  its own `lock_timeout`. The container exits; with a restart policy (the dev stack uses
  `restart: unless-stopped`) Docker starts it again, which retries the migration. Without one,
  start it again by hand. A migration that failed on a lock succeeds on a later attempt once
  the lock is free. If it keeps failing, the service log names the migration and the first
  line of the error. The failed migration leaves no trace in the database; migrations committed
  before it in the same start stay in. Before rolling back to the previous image, check that it
  works with them.
- **`VACUUM FULL` after the `COMMIT`** of three older migrations runs separately and waits at
  most 30 s for its lock. If it fails, the migration stays committed (`nachlauf_offen`), the
  service starts anyway and retries only the `VACUUM FULL` on its next start.
- **First start with this mechanism on an existing database:** migrations applied by hand
  before are not in the table yet. The repeatable ones run once more (seconds, brief table
  locks), the three non-repeatable ones are recognised by their effect and recorded as `erkannt`
  without running.
- **A new migration needs a new semantic search image.** The files are baked into it. A
  migration merged without other changes to the service only reaches `:main` once that image
  is rebuilt (see the path filter in `.github/workflows/build.yml`); release tags build all images.
- **After restoring a backup** the table holds the state of the backup. `restore.sh` restarts
  the semantic search service, which then applies the migrations added since; after a restore
  by other means, restart it yourself.

Check the state with
`SELECT name, status, zeitpunkt, fehler FROM migrationsprotokoll ORDER BY name;`.
Details, the manual fallback and the convention for new migrations:
[`mvp/backend/postgres-app/migrations/README.md`](../mvp/backend/postgres-app/migrations/README.md).

---

## 🔧 Maintenance Tasks

### Cleanup Docker Resources

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

No setup script is required — `backup.sh` creates `/opt/gutgesagt-backups/{daily,weekly}/`
(override with `BACKUP_ROOT`) on first run. Schedule it with cron; in the test and production
environments the schedule is part of verdigado's internal infrastructure.

**Create backup:**
```bash
cd mvp/scripts/backup
./backup.sh
```

**Restore from backup:**

Paths are resolved relative to `BACKUP_ROOT` (default `/opt/gutgesagt-backups/`):
```bash
cd mvp/scripts/backup
./restore.sh daily/latest                    # Latest daily backup
./restore.sh weekly/latest                   # Latest weekly backup
./restore.sh daily/backup_YYYYMMDD_HHMMSS    # A specific backup
```

**Test backup/restore:**
```bash
cd mvp/scripts/backup
./test-backup-restore.sh
```

**What gets backed up:**
- ✅ Qdrant vector database (content embeddings)
- ✅ PostgreSQL application database (usage tracking, metadata)
- ✅ Backup metadata with checksums for integrity verification

**Storage location:**
- Backups are stored in `/opt/gutgesagt-backups/{daily,weekly}/` on the host
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
docker compose logs gutgesagt-bff -f --tail=50
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
docker exec gutgesagt-bff curl http://gutgesagt-semantic-search:8000/api/v1/health
```

### Reverse proxy or TLS issues?

In the test and production environments the reverse proxy and the TLS certificates are part
of verdigado's internal infrastructure. Report problems there in the project channel (see
below).

### PostgreSQL connection issues?

```bash
# Check if PostgreSQL is running
docker exec gutgesagt-app-postgres pg_isready

# Connect to database
docker exec -it gutgesagt-app-postgres psql -U app_user -d gutgesagt_app
```

---

## 📈 Monitoring

What the application provides so that test and production can be monitored. Scraping,
alert rules and alert routing are run by the operators, outside this repository.

| What | Where | Healthy when |
|---|---|---|
| Frontend reachable | `GET /` on the frontend (nginx) | 200 |
| BFF reachable | `GET /api/check-session` on the BFF; answered by the BFF itself, without a backend call | 200 or 401 |
| Semantic search reachable | `GET /api/v1/health` on the semantic search service, checked directly on the internal network | `status` in the JSON is `healthy` (`degraded`: disk or memory above 90 %; `unhealthy`: PostgreSQL or Qdrant unreachable, or one of the checks failed; above 80 % is only a `warning` in the check and leaves `status` at `healthy`). The endpoint always answers 200, so read the field |
| Error rate (5xx) | `GET /metrics`, counter `gutgesagt_http_requests_total{status="5xx"}` | low share of all requests |
| Search response time | `GET /metrics`, histogram `gutgesagt_search_duration_seconds` | quantiles from the buckets |

`/metrics` on the semantic search service uses the Prometheus text format:

- `gutgesagt_http_requests_total{method, route, status}`: requests per HTTP method, route
  template (`/api/v1/usage/content/{content_id}/usage`, never the path with the ID in it;
  `unmatched` for paths without a route and for requests the rate limit rejects before
  routing) and status class (`2xx` ... `5xx`).
- `gutgesagt_search_duration_seconds`: duration of `POST /api/v1/search/searchByText`.
- **No personal data:** no Kennung (account ID), no search text, no session. The labels are the
  method, the route template and the status class, nothing taken from headers or bodies.
  `tests/unit/api/test_betriebskennzahlen_suche.py` checks this after a search by a
  signed-in test person through the real router and middleware.
- The values live in the memory of the process (the service runs with one worker) and
  start at zero after a restart; alert on rates, not on absolute values.
- **Not reachable from outside:** the BFF forwards every path to the semantic search
  service, `/metrics` is therefore listed in `EndpointPolicy.Blocked` and answers 404 there,
  signed in or not. Scrape the service directly on the internal network.

Disk, RAM and container restarts of the hosts come from host monitoring, not from the
application. `/api/v1/health` also reports disk and memory, but only as seen from the
semantic search container.

---

## 🔮 What's next?

* Unified test/prod deployment via GitOps
* Migration to Kubernetes (long-term)

---

## 🤝 Need help?

Talk to us in the Chatbegrünung channel:
- 📢 `#GutGesagt`
- 🔗 [chatbegruenung.de](https://chatbegruenung.de/channel/GutGesagt)

Ask in the channel for test-system or production access — the maintainers are reachable there.

---

## 💚 Thanks

This system is built to support digital democracy and collaborative communication.
Thanks for helping make it more stable and useful!

---

*Last updated: 2026-10-29*
