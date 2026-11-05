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
start. If the container has a memory limit, raise it accordingly. The Kürzungsvorschlag (#403)
uses the same spaCy model and needs no further memory. Since #405 Lingua adds about 45 MB for
the Sprachhinweis (11 languages, measured in the service image), also preloaded at start. Its
models make the image about 300 MB larger on disk (the wheel ships all languages). Since #387
the NLI-Stufe loads an NLI model (mDeBERTa-v3-base-xnli, fp32) in the background at start
(`SEMANTIC_SEARCH_DIESELBE_AUSSAGE_NLI`, default `schatten`): about 1.2 GB more RAM in use and
up to about 2 GB at the peak while loading (measured on the dev VM, `python -m
tests.regression.nli_messen --zeit`), and the image grows by about 0.55 GB. If the container has
a memory limit, raise it accordingly; `SEMANTIC_SEARCH_DIESELBE_AUSSAGE_NLI=aus` skips the model
and restores the rule before #387.

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

### 🔑 Login (Keycloak)

#429 prepares an own realm „Gut gesagt“; the BFF takes the realm from `Keycloak__Authority`,
and the semantic service creates accounts from Einladungen through the Keycloak admin API.
Until the switch, sign-in stays on the Netzbegrünung realm.

**Do not switch `Keycloak__Authority` to the new realm before the Kennungen are migrated:**
every member gets a new `sub` there, and their contributions, votes, admin rights and the
deletion list still hold the old one. Switch the BFF and enable redemption
(`SEMANTIC_SEARCH_KEYCLOAK_*`) together, after the privacy policy covers self-registration.
Order, realm template, variables and setup steps: `docs/KEYCLOAK_REALM.md`.

Beta-Zugänge (`managed-users.json`, Direktanmeldung) move into the realm in the same run as
the Kennungen (`--beta-zugaenge`, #488). Together with the BFF switch, remove the file and its
mount from test and production and set `ENABLE_MANAGED_AUTH=false`; the Direktanmeldung stays
for the dev stack only. Steps: `docs/KEYCLOAK_REALM.md`, „Beta-Zugänge umziehen“.

### ✉️ Mail (Meldungen)

#493: Who gives an e-mail address when reporting a Beitrag gets two mails from the semantic
service (Art. 16 (4) and (5) DSA): the Eingangsbestätigung right away, and the decision with the
available remedies once an admin sperrt the Beitrag, dismisses the Meldung or removes the
Beitrag. Texts: `services/meldung_mitteilen.py`; sending: `infrastructure/mail/versand.py`
(SMTP with STARTTLS or TLS only, one connection per mail, 10 s per step; a request waits at most 15 s for its mails, then answers while the sending finishes in the background). The mails carry no text from the Meldung
itself, only the title of a visible Beitrag.

| Variable | Default | Meaning |
|---|---|---|
| `SEMANTIC_SEARCH_SMTP_HOST` | unset | SMTP server. Unset: no mail goes out, admins inform by hand (mailto link in the moderation) |
| `SEMANTIC_SEARCH_SMTP_PORT` | `587` | |
| `SEMANTIC_SEARCH_SMTP_VERSCHLUESSELUNG` | `starttls` | `starttls` or `ssl` (port 465). Nothing else: the service refuses to start with any other value and never sends in plain text; the certificate must match the host name |
| `SEMANTIC_SEARCH_SMTP_BENUTZER` / `_PASSWORT` | unset | SMTP login; without a user no login. The password is a secret |
| `SEMANTIC_SEARCH_MAIL_ABSENDER` | unset | `From` address; required, without it no mail goes out |
| `SEMANTIC_SEARCH_MAIL_ANTWORT_AN` | unset | `Reply-To`; unset, replies go to the sender. The decision mail names a reply as the way to challenge the decision (Art. 20 DSA): set this to the contact address of the legal notice whenever the sender accepts no mail |

The sender domain needs SPF/DKIM for the SMTP server, otherwise the mails land in spam. A failed
mail never undoes a Meldung or decision; the log says `SMTP delivery failed (<error type>)`
without the address. Check after setting the variables: report a Beitrag on the test system with
your own address, then dismiss the Meldung in the moderation; both mails must arrive.

### 🚧 Updating Production

Pull requests are checked on Forgejo by Woodpecker (`.woodpecker/ci.yaml`, required status
for `main`, see [CI.md](CI.md)). After the merge the images are built. Until the switch
described in [CI.md, "Images and releases"](CI.md#images-and-releases) two CIs build them:

- **GitHub Actions on the mirror** (`.github/workflows/build.yml` and `release.yml`) publish
  the tags the environments use, after running their test suites
  (`tests-backend.yml`, `tests-frontend.yml`, `tests-bff.yml`).
- **Woodpecker** (`.woodpecker/build.yaml` and `release.yaml`, after a green `ci` run) builds
  the same images with the same tags, each with the prefix `woodpecker-` (`:woodpecker-main`,
  `:woodpecker-0.9.0`), so the two CIs never overwrite each other's tags. After the switch
  the prefix is gone and the GitHub workflows are removed.

Tags, the same in both CIs (`scripts/image_tags.py`):

- **Push to `main`:** `:main` and `:sha-<short>` for the images whose files changed. The test
  environment runs `:main`, rolled out manually (see above).
- **Tag `vX.Y.Z`:** `:X.Y.Z` (the tag without its `v`), `:X.Y` and `:latest` for all four
  images. A prerelease (`v1.2.3-rc.1`) only gets `:1.2.3-rc.1`.

Images are pushed into the Netzbegruenung/Verdigado registry:
> https://git.verdigado.com/netzbegruenung-images/-/packages

**How production updates:** production pins a release version (`:X.Y.Z`, by digest), not
`:latest`. Renovate proposes the next release version; production changes only once the
operators roll it out. A release tag does not deploy anything by itself. `:latest` is still
published for whoever wants the newest release, but nothing in production follows it.

#### Releases

1. **Only the maintainer sets tags.** Agents and contributors propose, they do not tag.
2. **Version scheme:** `v0.x` releases until the public launch: `v0.8.0` first, for the move
   of production, `v0.9.0` at the internal launch, `v1.0.0` at the public launch,
   [SemVer](https://semver.org/) after that. No release candidates (`-rc`): production only
   takes release versions.
3. **Release pull request:** before tagging, one pull request prepares the release.
   - **Version in the footer:** Woodpecker's release build passes the tag to the frontend
     image (build argument `APP_VERSION`), and the footer shows it; no version change is
     needed for those images. **Until the switch** ([CI.md](CI.md#images-and-releases)) the
     deployed images still come from GitHub's `release.yml`, which does not pass the tag: set
     `version` in `mvp/frontend/gutgesagt-frontend/package.json` to `X.Y.Z` (without the `v`)
     as before, `npm version X.Y.Z --no-git-tag-version` in that directory. This sub-step
     goes with the switch. Woodpecker's builds of `main` show „main · <commit>“
     instead of a version; local builds show the `package.json` version.
   - **Change list:** draft the text of the Forgejo release and show it in the description of
     the release pull request, so it is reviewed with it. The change list lives only in the
     Forgejo release, not in a file in the repository. Draft it with
     ```bash
     git fetch origin --tags
     scripts/changelog.sh origin/main             # since the previous v* tag
     scripts/changelog.sh origin/main <commit>    # first release, or a different start
     ```
     The script lists the merged pull requests on `main` (linked, grouped by their Conventional
     Commits prefix into Breaking Changes, Neu, Behoben, Sonstiges), the new migrations and the
     new scripts in `mvp/scripts/manual/`. It recognises a breaking change only by the `!` in the
     PR title (`feat!:`), not by a `BREAKING CHANGE:` footer, and links any commit on `main`
     whose subject ends in `(#N)` as pull request N. Review the draft and add, in a section
     „Ablauf beim Ausrollen“ above the generated list, the operational steps it cannot know: which
     scripts in `mvp/scripts/manual/` must run and in which order, renames that need action per
     environment, new settings, more memory.
   If `main` moves while the pull request is open, merge it in and draft the list again, so
   that it covers everything up to the tag except the release pull request itself.
4. **Tag on Forgejo:** set the tag on the merge commit of the release pull request on `main`
   on Forgejo, not on a later commit: later pull requests belong to the next release. The push
   mirror carries the tag to GitHub, where `release.yml` tests and builds the images; on
   Forgejo, Woodpecker runs `ci` and then `release` for the same tag. Check that the run is
   green and the `:X.Y.Z` tags exist in the registry before announcing the release.
5. **Forgejo release:** create the release to the tag on Forgejo (Releases on the Forgejo
   repository) and paste the reviewed draft from the release pull request. `scripts/changelog.sh
   vX.Y.Z` shows the tagged range for a last comparison; for the first release give the start
   as well (`scripts/changelog.sh v0.8.0 fae44b4b`, the commit of the former `v1.1.0`).

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
  the lock is free. If it keeps failing, the service log names the migration and the type
  of the error (not its message, which can carry values, #422); the first line of the
  message is in `migrationsprotokoll.fehler`. The failed migration leaves no trace in the
  database; migrations committed before it in the same start stay in. Before rolling back
  to the previous image, check that it works with them.
- **`VACUUM FULL` after the `COMMIT`** of three older migrations runs separately and waits at
  most 30 s for its lock. If it fails, the migration stays committed (`nachlauf_offen`), the
  service starts anyway and retries only the `VACUUM FULL` on its next start.
- **First start with this mechanism on an existing database:** migrations applied by hand
  before are not in the table yet. The repeatable ones run once more (seconds, brief table
  locks), the three non-repeatable ones are recognised by their effect and recorded as `erkannt`
  without running.
- **A new migration needs a new semantic search image.** The files are baked into it. A
  migration merged without other changes to the service only reaches `:main` once that image
  is rebuilt (path filters in `.woodpecker/build.yaml` and `.github/workflows/build.yml`;
  Woodpecker also rebuilds it for a new migration alone); release tags build all images.
- **After restoring a backup** the table holds the state of the backup. `restore.sh` restarts
  the semantic search service, which then applies the migrations added since; after a restore
  by other means, restart it yourself.

Check the state with
`SELECT name, status, zeitpunkt, fehler FROM migrationsprotokoll ORDER BY name;`.
Details, the manual fallback and the convention for new migrations:
[`mvp/backend/postgres-app/migrations/README.md`](../mvp/backend/postgres-app/migrations/README.md).

### Qdrant: named vector (#395)

Since #395 the service keeps its embedding as the named vector `e5_base`, so that another
model can get its own vector next to it later. A new collection is created that way; an
existing one from before keeps its unnamed vector until the script below changes it.
Until then the service searches the old collection as before (it logs a warning on start).
Qdrant cannot rename a vector: the script copies all points with their vectors (no new
embeddings) into `<collection>_e5_base` and turns the old name into an alias for it.
Backups, restores and the other scripts keep using the old name.

Once per environment:

1. Take a backup (`mvp/scripts/backup/backup.sh`, includes the Qdrant snapshot).
2. Roll out the image with #395.
3. Run `mvp/scripts/manual/vektor_benennen.py` without `--ausfuehren`; it only counts.
4. Run it with `--ausfuehren`, at a quiet time: what is written to Qdrant while the copy runs
   can get lost (a changed number of points aborts the run without changes).
5. Restart the semantic search service right after the script has finished
   (`docker restart gutgesagt-semantic-search`). Until then it uses no vector name, so every
   search and every new or changed Beitrag fails. Not during the run: a service that starts
   while the old name is gone creates an empty collection under it. If the run aborts, run it
   again; it replaces a half copy or sets only the missing alias.

Commands are in [`mvp/scripts/manual/README.md`](../mvp/scripts/manual/README.md). Way back:
restore the backup from step 1 and restart the service. The restore goes through the alias into
`<collection>_e5_base` (checked against Qdrant 1.18.2), and the image with #395 works with
both vector layouts. To change it again after that, run the script again: it copies into
`<collection>_e5_base_2`, moves the alias in one step and only then deletes the restored
collection.

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

Questions about deployment and requests for test-system or production access go in an issue on
[Forgejo](https://git.verdigado.com/Netzbegruenung/gutgesagt/issues); without Forgejo access,
see [CONTRIBUTING.md](../CONTRIBUTING.md#repository). Security vulnerabilities: see
[SECURITY.md](../SECURITY.md).

---

## 💚 Thanks

This system is built to support digital democracy and collaborative communication.
Thanks for helping make it more stable and useful!

---

*Last updated: 2026-10-29*
