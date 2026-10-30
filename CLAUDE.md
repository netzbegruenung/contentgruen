# CLAUDE.md - Project Guide for AI Assistants

This file helps AI assistants (like Claude) understand the Gut gesagt project structure and development workflow.

## IMPORTANT: Git Guidelines
- **NO EMOJIS** in commit messages
- Keep commit messages professional and focused on the changes; Conventional Commits.
- Agent commits carry a `Co-Authored-By:` trailer naming the agent/model. No other AI
  references (no "Generated with …" lines) in commit messages.
- **Primary repository: Forgejo** — `git.verdigado.com/Netzbegruenung/gutgesagt`, which is
  what `origin` points at. Branches, pull requests, reviews and issues live there.
- **GitHub is a read-only mirror** — `github.com/netzbegruenung/contentgruen` (remote
  `github`). Forgejo pushes every change there automatically (push mirror); GitHub Actions
  build and release the container images from the mirrored pushes and tags. Never push to
  GitHub directly and do not open PRs or issues there.
- **`main` is protected on Forgejo**: nobody pushes to it directly, only listed maintainers
  merge. Work on a branch (agents: `sb/` prefix), push it, open a PR.
- **Opening PRs and comments**: via the Forgejo API (`https://git.verdigado.com/api/v1/`),
  not `tea` and not `gh` (`gh` is not authenticated on the dev VM). Note that
  `/issues` also returns PRs; filter with `type=issues`.
- `.github/workflows/` changes reach GitHub CI directly through the mirror; flag them
  explicitly in the PR.

## Dev-VM (Agenten-Sandbox)

Wegwerf-Sandbox, kein Mensch entwickelt hier interaktiv: alles läuft in Docker Compose
(`mvp/docker-compose.dev.yml`, Projekt `gutgesagt-dev`) und darf jederzeit gelöscht und
neu aufgebaut werden. Dev-Loop über `mvp/run-local.sh` — aus jedem Verzeichnis aufrufbar,
nichts im Vordergrund, Exit != 0 bei Fehler:

    up | status | reset | wipe | seed | test | logs <dienst> | down

- `reset` (~30s, Volumes bleiben) = Default nach Code-Änderungen.
- `wipe` (~2 min, `down -v` + Rebuild + Seeding) nur bei Schema-/Seed-Problemen.
- `status` ist maschinenlesbar und schlägt auch bei leerer `content_collection` fehl.
- Ports: Frontend 8080, BFF 5054, Semantic 8000, Qdrant 6333/6334, PostgreSQL 5433.
  Rootless Docker kann keine Ports < 1024 binden — daher 8080 statt 80.
- VM-Voraussetzung (nicht im Repo): `docker buildx` >= 0.17 in `~/.docker/cli-plugins/`;
  das Debian-Paket 0.13 ist zu alt für Compose 2.40 und lässt jeden Build scheitern.

### Remote access

Die Sandbox begrenzt Rechenzeit und Dateisystem, nicht Identität. Ein Push lässt sich nicht
dadurch zurücknehmen, dass man die VM neu aufsetzt. Deshalb kann das Credential auf der VM
nur wenig:

- Git spricht HTTPS mit `git.verdigado.com` über einen repo-lokalen Credential-Helper. Der
  liest einen Forgejo-Token des Bot-Accounts, der **nur für dieses Repo** gilt
  (Schreibrecht, kein Admin). Den Token nie ausgeben, loggen oder in Dateien schreiben.
- Was der Token nicht kann, erzwingt der Server: kein Push und kein Merge auf `main`
  (Branch-Schutz), keine Repo-Einstellungen, kein Spiegel-Setup.
- Kein SSH-Key, kein `gh`-Token und kein GitHub-Zugang auf der VM. Nichts davon
  nachrüsten, um eine Einschränkung zu umgehen.
- Konsequenz für Agenten: Branches pushen und PRs öffnen geht ohne Rückfrage; mergen,
  Releases/Tags und alles an der Infrastruktur bleibt beim Maintainer.

## Quick Start Commands

### Start Development Environment

**Dev-Stack in Docker (Linux, siehe Dev-VM oben):**
```bash
mvp/run-local.sh up
# Access: http://localhost:8080
```

**Local Mode (Windows, Dienste ausserhalb von Docker):**
```bash
cd mvp
run-local.bat   # (or scripts/dev/run-local.bat)
# Access: http://localhost:4200
```

**Docker Mode:**
```bash
cd mvp
run-docker.bat   # Windows (or scripts/dev/run-docker.bat)
./run-docker.sh  # Linux/Mac (or scripts/dev/run-docker.sh)
# Access: http://localhost:8080 (docker-compose.dev.yml publishes the frontend on host port 8080)
```

**Run Tests:**
```bash
cd mvp
run-tests.bat   # Windows (or scripts/test/run-all-tests.bat)
./run-tests.sh  # Linux/Mac (or scripts/test/run-all-tests.sh)
```

**Default Login:** `test.user@example.com` / `Liebe>Hass!` (from `mvp/config/managed-users.example.json`)

## Project Overview

Gut gesagt is a semantic content platform for green political activism, helping users find and share relevant political content through AI-powered search.

### Tech Stack
- **Frontend**: Angular 20+ with Material Design
- **BFF**: .NET 9.0 with YARP proxy
- **API**: Python FastAPI with Qdrant vector database
- **Databases**: Qdrant (vectors), PostgreSQL (metadata)
- **Infrastructure**: Docker, nginx; test and prod run on verdigado's internal infrastructure

## Architecture Summary

```
Frontend (Angular) → BFF (.NET) → Semantic Search (Python) → Qdrant + PostgreSQL
        ↓                ↓                    ↓                    ↓
  [Port 4200/8080]  [Port 5054]        [Port 8000]         [Ports 6333, 5433]
```

Host ports shown. PostgreSQL is published on host 5433 (container port 5432).

## Key Directories

- `mvp/frontend/gutgesagt-frontend/` - Angular frontend
- `mvp/backend/BFF/` - .NET Backend-for-Frontend
- `mvp/backend/semantic-search-service/` - Python semantic search
- `docs/` - Documentation
- `mvp/data/` - Seed data

## Development Workflow

### Making Changes
1. Use `run-local.sh/bat` for development
2. Make changes (hot-reload enabled)
3. Test locally
4. Run tests: `scripts/check.sh --geaendert` while working (only the steps and frontend specs your
   changes reach), `pytest` (Python), `scripts/check.sh --schritt frontend` (Angular; single specs: `--include <pfad>`)
5. Commit changes (pre-commit hooks will format code)

### Testing in Docker
1. Use `run-docker.sh/bat`
2. Access at http://localhost:8080
3. Check logs: `docker-compose logs -f [service]`

## Environment Configuration

### Frontend Environments
- `environment.ts` - Current active config
- `environment.local.ts` - Local development
- `environment.docker.ts` - Docker mode
- `environment.prod.ts` - Production

### Service Configuration
- **BFF**: `USE_KEYCLOAK=false` for local/test
- **API**: `SEMANTIC_SEARCH_APP_DATABASE_URL` (PostgreSQL), `SEMANTIC_SEARCH_QDRANT_URL` (Qdrant)
- **Frontend**: `baseUrl` empty for Docker, `http://localhost:5054` for local

> **Datenschutz-Warnung — `OPENAI_API_KEY` / `SEMANTIC_SEARCH_OPENAI_API_KEY`.**
> Ein gesetzter Key aktiviert einen **Transfer von Bild-URLs an OpenAI in den USA**,
> sobald jemand im Bild-Formular einen Unterschrift-Vorschlag anfordert
> (`POST /api/v1/image/suggestCaption`). Einen Hintergrunddienst, der ungefragt Bilder
> beschreibt, gibt es seit #281 nicht mehr. Der Key ist die einzige Weiche
> (`get_caption_suggestion_service` in `dependencies.py`).
> **Die Datenschutzerklärung geht davon aus, dass dieser Transfer nicht stattfindet.**
> Bevor der Key irgendwo gesetzt wird, muss sie um einen Abschnitt zum Drittlandtransfer
> (Art. 44 ff. DSGVO) erweitert werden; zusätzlich sind ein AV-Vertrag und Garantien nach
> Art. 46 DSGVO nötig. Siehe auch den Hinweis an der Stelle selbst in `core/config.py`.

## Authentication Modes

### Dummy Auth (Development)
- E-Mail: `test.user@example.com` (login is by e-mail, not by user name)
- Password: `Liebe>Hass!`
- Used in local and test environments

### Keycloak (Production)
- SSO integration with Netzbegrünung
- Own realm „Gut gesagt“ prepared in #429 (sign-in switches over only after the Kennungen are migrated); template, order and setup in `docs/KEYCLOAK_REALM.md`, the realm itself is configured outside this repository

## Claude Custom Commands

### Quick Commands Reference
- `start local` - Start local development environment (→ see Start Development Environment)
- `start docker` - Start Docker development environment
- `run tests` - Execute full test suite (→ see Run All Tests)
- `test backend` - Run Python backend tests only
- `test frontend` - Run Angular frontend tests only
- `review pr` - Review open PR, deliver the review in chat (→ see Review Pull Request)
- `check logs` - Show recent logs from all services (→ see View Logs)
- `clean restart` - Clean and restart all services (→ see Clean Restart)
- `view api docs` - Open API documentation links (→ see View API Documentation)
- `deploy test` - Deploy to test environment (→ see Test Environment)
- `check ports` - Check for port conflicts (→ see Check Ports)
- `reset db` - Reset database to clean state
- `backup data` - Create backup of Qdrant and PostgreSQL
- `restore data` - Restore from backup
- `test backup` - Test backup/restore functionality

## Common Tasks

### Start Development Environment
When user requests "start local" or "start":
```bash
mvp/run-local.sh up        # Linux/Mac: Docker dev stack -> http://localhost:8080
cd mvp && run-local.bat    # Windows: services outside Docker -> http://localhost:4200
```

When user requests "start docker":
```bash
cd mvp
run-docker.bat   # Windows
./run-docker.sh  # Linux/Mac
# Access: http://localhost:8080
```

### Run All Tests
When user requests "run tests" or "test":
```bash
cd mvp
run-tests.bat   # Windows
./run-tests.sh  # Linux/Mac
```

When user requests "test backend":
```bash
cd mvp/backend/semantic-search-service/app
pytest
```

When user requests "test frontend":
```bash
scripts/check.sh --schritt frontend    # finds the Playwright Chromium; --include <pfad> for single specs
```

### Review Pull Request
When user requests "Review PR" or "review pr":
1. Review the current branch against `main`.
2. Gather the diff:
   - `git fetch origin main`, then `git log origin/main..HEAD` and `git diff origin/main...HEAD`
   - For a large diff, dump it to a file and read it in sections rather than truncating.
3. Analyze all changed files thoroughly
4. Perform comprehensive code review covering:
   - Architecture compliance
   - Clean code practices
   - Logging best practices
   - Security concerns
   - Performance implications
   - Test coverage
   - Bug fixes validation
5. Provide structured review summary with:
   - Strengths
   - Areas to consider
   - Risk assessment
   - Recommendation (Approve/Request Changes)
6. **Deliver the review in chat.** Posting it on the PR (Forgejo API,
   `/pulls/{nr}/reviews`) only after the maintainer has seen and approved the draft.
   - Write the review to a file as well, so it can be pasted without re-reading the chat.
   - Note which PR it belongs to (`/pulls?state=open` via the API lists them).

### View API Documentation
When user requests "view api docs":
- Semantic Search: http://localhost:8000/docs
- BFF: http://localhost:5054/swagger

### Database Access
```bash
docker exec -it gutgesagt-app-postgres psql -U app_user -d gutgesagt_app
```
Container names are the same in dev, test and production: `gutgesagt-app-postgres`,
`gutgesagt-semantic-search`, `gutgesagt-qdrant`.

### View Logs
When user requests "check logs" or "view logs":
```bash
# Docker mode
docker-compose logs -f [gutgesagt-frontend|gutgesagt-bff|gutgesagt-semantic-search]

# Local mode - check terminal windows
```

### Clean Restart
When user requests "clean restart":
```bash
docker-compose -f docker-compose.dev.yml down -v
rm -rf mvp/backend/semantic-search-service/metadata/
docker-compose -f docker-compose.dev.yml up -d
```

### Check Ports
When user requests "check ports":
```bash
mvp/scripts/setup/check-environment.bat  # Windows
bash mvp/scripts/setup/check-environment.sh  # Linux/Mac
netstat -tuln | grep -E '(4200|5054|8000|5433|6333)'  # Linux/Mac
```

### Reset Database
When user requests "reset db" or "reset database":
```bash
docker-compose -f docker-compose.local-dbs.yml down -v
docker-compose -f docker-compose.local-dbs.yml up -d
# Re-run seeding if needed
```

### Backup and Restore

When user requests "backup data" or "create backup":
```bash
cd mvp/scripts/backup
./backup.sh
# Creates backup in /opt/gutgesagt-backups/daily/
# On Sundays: Also creates weekly backup
# Auto-rotates: Keeps last 7 daily + 4 weekly backups
```

When user requests "restore data" or "restore backup":
```bash
cd mvp/scripts/backup
# Paths are resolved relative to /opt/gutgesagt-backups/ -- pass a relative path
./restore.sh daily/latest                    # Restore latest daily
./restore.sh weekly/latest                   # Restore latest weekly
./restore.sh daily/backup_YYYYMMDD_HHMMSS    # Restore specific
```

When user requests "test backup" or "test backup restore":
```bash
cd mvp/scripts/backup
./test-backup-restore.sh
```

**Important Notes:**
- First run: `backup.sh` auto-creates directories (`/opt/gutgesagt-backups/daily/`, `/opt/gutgesagt-backups/weekly/`)
- Container names default to the ones above; override with `POSTGRES_CONTAINER`,
  `APP_CONTAINER`, `QDRANT_CONTAINER` if needed. `BACKUP_ROOT` (default `/opt/gutgesagt-backups`)
  must be mounted at `/backups` in `gutgesagt-semantic-search`, otherwise `backup.sh` aborts
  because the Qdrant snapshot is missing on the host. Dev-stack test: README "Testing in the dev stack"
- Automatic rotation: Keeps last 7 daily + 4 weekly backups
- Includes Qdrant vectors and PostgreSQL metadata
- Restore is destructive - always confirm before running
- Production: scheduled on verdigado's internal infrastructure
- See `mvp/scripts/backup/README.md` for detailed documentation

## Testing

### Run All Tests
```bash
# Python tests (pytest.ini lives in app/)
cd mvp/backend/semantic-search-service/app
pytest

# Angular tests
scripts/check.sh --schritt frontend

# .NET tests (test project is BFF.Tests; run from the solution directory)
cd mvp/backend
dotnet test
```

E2E tests (Playwright, against the running dev stack, not in CI and not part of `scripts/check.sh`):
`mvp/frontend/gutgesagt-frontend/e2e/`, how to run them in its `README.md`.

## Deployment

### Test Environment
- URL: https://gutgesagt-test.netzbegruenung.de (runs the `:main` image tag)
- Deployment: Manual, by the operators. A new `:main` image is **not** rolled out
  automatically. Database migrations are applied by the semantic service on startup
  (`docs/DEPLOYMENT.md`, "Database migrations"); the convention for new ones:
  `mvp/backend/postgres-app/migrations/README.md`.

### Production Environment
- URL: https://gutgesagt.netzbegruenung.de
- Deployment: pins `:latest` by digest; a tag push alone deploys nothing. Release flow:
  `docs/DEPLOYMENT.md`, "Updating Production"
- Config: verdigado's internal infrastructure, outside this repository

## Troubleshooting

### Port Conflicts
Check with `bash mvp/scripts/setup/check-environment.sh` (or `check-environment.bat` on Windows), or `netstat -tuln | grep [port]`

### Docker Issues
```bash
docker-compose down
docker system prune -a  # Warning: removes all unused images
```

### Database Issues
```bash
docker-compose -f docker-compose.local-dbs.yml down -v  # Reset databases (Qdrant + PostgreSQL)
```

## Project Status

See [STATUS.md](./STATUS.md) for current development status and roadmap.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution guidelines.

## Architecture Details

See [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) for detailed system architecture.

## Coding Standards & Patterns

### Python Backend (Semantic Search Service)
- **Repository Pattern** for data access; **Service Layer** for business logic
- **Dependency Injection** via constructor parameters; **Factory Pattern** for repository creation
- Prefer composition over inheritance

### Naming Conventions
- Classes: `PascalCase` (e.g., `StatementService`)
- Methods: `snake_case` (e.g., `get_by_author()`)
- Private methods: `_single_underscore` prefix
- Interfaces: `I` prefix (e.g., `IBaseContentRepository`)

### Backend File Organization
- Domain models in `domain/models/`, interfaces in `domain/interfaces/`
- Services in `services/` (by concern), repositories in `repositories/` (by type)
- Tests mirror source structure
- Schema changes for existing databases: a dated SQL script in `mvp/backend/postgres-app/migrations/`,
  convention in its `README.md`

### Adding a New Content Type
As of the rung-1 content-model refactor, a new type is **a spec + a model (+ a FE fragment)** — no per-type service/repository clone and no new search branch (see `docs/CONTENT_MODEL.md`).
1. Create the model in `domain/models/` (`<Type>DbEntry(BaseContentDbEntry)`, `<Type>SearchResult`) and add the `ContentType` enum member.
2. Register a `ContentTypeSpec` entry in `domain/content_registry.py` (reuse `create_registry_repository` — the generic `RegistryQdrantRepository`; no new repository subclass).
3. Add a `get_<type>_service` dependency in `dependencies.py` that builds the generic service from the spec, and add an `api/v1/<type>.py` router (ingestion/input is the only type-specific seam) wired in `main.py`.
4. Add the type to the `/searchByText` spec list and the `SearchResponse` DTO — the `SearchOrchestrator` handles it generically.
   Responses go out through a `<Type>Response(BeitragResponse)` and a `<Type>Treffer` in `dtos/beitrag.py`: an allowlist of fields, never the DbEntry, so no Kennung leaks (#333). Build them with `als_responses`/`fuer_aufrufer` (`services/beitrag_fuer_aufrufer.py`); if the type shows up in `/content/recent`, add it to `NEUESTE` in `api/v1/content.py`; `OFT_GENUTZT` in `api/v1/usage.py` maps every type to its response for "Diese Woche oft genutzt".
5. Frontend: one entry in `shared/content-type-registry.ts` (key, icon, German `label`, `resultField`, `emoji`), the type's fields in the `ausSuchergebnis` adapter (`beitragskarte/karten-daten.ts`) and, if it needs its own body, a block in `app-beitragskarte`. There is one card component for all types. The registry imports no components, so type names (`typLabel()`) stay out of the initial bundle.
6. Tests-first against live Qdrant in `tests/integration/` (round-trip + orchestrator parity), plus a headless-Chrome FE render/vote test.

Legacy types (`statement`, `reference`, `commentary`, `generic_text`) still have hand-written service/repository classes; do not copy that pattern for new types — prefer the registry path above. Note that `commentary` and `generic_text` also have registry specs that nothing resolves yet.

### Titel von Beiträgen: Behauptung, kein Thema
Der Titel eines **Kommentars** und einer **Hintergrundinfo** ist genau ein Satz, der eine
Behauptung mit Haltung aufstellt: 3–120 Zeichen. Frage und Thema gehören ins **Statement**,
auf das der Beitrag antwortet, nicht in den Titel. Im Destillier-Ablauf ist das Satz-Feld
„Was ist der Punkt? Ein Satz.“ genau dieser Titel.

- **Richtig:** „Wärmepumpe lohnt sich auch im Altbau“, „Wärmepumpen rechnen sich im Altbau,
  wenn man die Förderung mitrechnet“
- **Falsch:** Fragen („Lohnt sich Wärmepumpe im Altbau?“), Themen („Wärmepumpen im Altbau“),
  Etiketten („Faktenhammer“, „Nachbars Gewinn“)

**Limit und Kartenhöhe gehören zusammen:** Die Titelbox der Suchkarte ist fest auf diese Länge
ausgemessen. Wer das Limit ändert, misst die Karte neu. Die Regel nicht ohne
Produktentscheidung lockern. Bildtitel (≤ 200, beschreibend) und Post-Titel folgen ihr nicht.

### Testing Requirements
- Always run tests before committing (`pytest` from `app/`, or `make test-backend-fast`)
- Mock repository interfaces in service tests; use `TestEmbeddingsManager`, not ad-hoc mocks
- Test positive and negative cases; naming: `test_method_name_scenario`
- See `mvp/backend/semantic-search-service/app/tests/TESTING_GUIDE.md` for details

### Pre-commit Hooks
The project uses pre-commit hooks that auto-format Python code (Black) and run the backend unit tests.
They may reformat files and fail on the first commit attempt, then pass on the second — this is
intentional. Don't bypass with `--no-verify` except in emergencies. The `safe-commit.sh`/`.bat`
helpers automate the retry.

### Full check and review rules
- `scripts/check.sh` runs everything a PR must pass (retired words, Ruff, Black, Python unit tests and
  `scripts/tests/`, frontend tests, BFF tests in the .NET SDK container; `--integration` adds the
  integration tests, `--schritt <name>` runs one step, `--include <pfad>` only the frontend specs under
  that path, `--geaendert` only what the changes since `origin/main` reach, integration included if they reach it). For checks in between use
  `--geaendert`; run the full `--integration` check before opening a PR. Woodpecker runs
  the same steps on every PR (`docs/CI.md`); a red run gets a comment with the red steps.
- Replaced names are listed in `scripts/retired-words.txt`; the check and a pre-commit hook reject
  them in added lines.
- Reviews check the judgement rules in `CODING_STANDARDS.md`.

## Agent skills

### Issue tracker

Issues live on Forgejo (`origin`), accessed through the REST API with curl; GitHub is a read-only mirror. See `docs/agents/issue-tracker.md`.

### Triage labels

Default triage vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` at the root, decisions in `docs/adr/`, both in German and changed only through pull requests. See `docs/agents/domain.md`.
