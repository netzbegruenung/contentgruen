# CLAUDE.md - Project Guide for AI Assistants

This file helps AI assistants (like Claude) understand the Gut gesagt project structure and development workflow.

## IMPORTANT: Git Guidelines
- **NO EMOJIS** in commit messages
- **NO CLAUDE REFERENCES** in commit messages (no "Generated with Claude", no "Co-Authored-By: Claude")
- Keep commit messages professional and focused on the changes
- **GitHub repository** — `github.com/netzbegruenung/contentgruen`, which is what `origin` points at.
  (The project was hosted on Forgejo at `git.verdigado.com` before the public open-source release;
  that host now only serves the container registry used by CI.)
- **The `gh` CLI is not authenticated on the dev VM and will not be** — see
  [Remote access](#remote-access-ssh--yubikey) below. `gh pr create`, `gh pr view`,
  `gh pr checks`, `gh pr comment` and `gh api` all fail with a login prompt. Do not run
  `gh auth login`, and do not add a token or credential helper to work around it — that
  would reintroduce exactly the bypass this setup removes.
- **Pushing works, but every push needs a human.** `origin` is SSH only, the key is a
  FIDO2 YubiKey forwarded from the maintainer's machine, and each connection needs a
  physical touch. Prepare and push freely, but expect the command to block until someone
  presses the key — announce a push before running it rather than firing it at an
  unattended terminal.
- **Opening a PR is the maintainer's step.** Push the branch, then hand over the compare
  URL — `https://github.com/netzbegruenung/contentgruen/compare/main...<branch>?expand=1`,
  which the push output also prints — together with a suggested title and body.
- Never push directly to `main`; always branch and hand over a PR link.

## Dev-VM (Agenten-Sandbox)

Wegwerf-Sandbox, kein Mensch entwickelt hier interaktiv: alles läuft in Docker Compose
(`mvp/docker-compose.dev.yml`, Projekt `contentgruen-dev`) und darf jederzeit gelöscht und
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

### Remote access (SSH + YubiKey)

Die Sandbox begrenzt Rechenzeit und Dateisystem — nicht Identität. Ein Push lässt sich
nicht dadurch zurücknehmen, dass man die VM neu aufsetzt. Deshalb liegt hier bewusst
**kein Credential, das ohne Menschen schreiben kann**:

- Kein privater SSH-Key auf der VM, kein `gh`-Token, kein Credential-Helper, keine
  `~/.netrc`. Der einzige Weg zu `origin` ist SSH über den **weitergereichten Agent**
  des Maintainers mit einem `ED25519-SK`-Key (FIDO2). Jede Verbindung = eine Signatur =
  ein Touch. Ein Agent-Forward erlaubt das *Anfordern* einer Signatur, nicht deren
  Erteilung — die bleibt am Stick.
- Konsequenz für Agenten: Alles Lokale (Branches, Commits, Tests, Dev-Stack) läuft ohne
  Rückfrage. Alles, was die VM verlässt, blockiert bis jemand drückt.

Damit das in langlebigen tmux-Sessions funktioniert, hängt der Agent-Socket an einem
**stabilen Pfad** statt am pro Verbindung wechselnden `/tmp/ssh-XXXX/agent.NNN`:

- `~/.ssh/rc` zieht `~/.ssh/agent.sock` bei jedem SSH-Login auf den aktuellen Socket nach.
- `~/.zshenv` exportiert `SSH_AUTH_SOCK=~/.ssh/agent.sock` — `.zshenv` liest auch jede
  nicht-interaktive zsh, also greift es für die frischen Shells, die Agent-Harnesses pro
  Tool-Aufruf starten.
- `SSH_AUTH_SOCK` ist aus tmux' `update-environment` entfernt, damit tmux seine beim
  Anlegen der Session eingefrorene Kopie nicht in neue Panes injiziert.

Diese drei Dateien liegen auf der VM, nicht im Repo. Symptom, wenn eins davon fehlt:
`git push` scheitert mit `Permission denied (publickey)` **statt** den YubiKey blinken zu
lassen — der Key ist dann nicht weg, es zeigt nur etwas auf einen toten Socket. Prüfen mit
`readlink -f "$SSH_AUTH_SOCK"` und einem Abgleich gegen die lebenden `/tmp/ssh-*/agent.*`.

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
# Access: http://localhost/
```

**Run Tests:**
```bash
cd mvp
run-tests.bat   # Windows (or scripts/test/run-all-tests.bat)
./run-tests.sh  # Linux/Mac (or scripts/test/run-all-tests.sh)
```

**Default Login:** `testuser` / `Liebe>Hass!`

## Project Overview

Gut gesagt is a semantic content platform for green political activism, helping users find and share relevant political content through AI-powered search.

### Tech Stack
- **Frontend**: Angular 20+ with Material Design
- **BFF**: .NET 9.0 with YARP proxy
- **API**: Python FastAPI with Qdrant vector database
- **Databases**: Qdrant (vectors), PostgreSQL (metadata)
- **Infrastructure**: Docker, nginx, SaltStack (prod)

## Architecture Summary

```
Frontend (Angular) → BFF (.NET) → Semantic Search (Python) → Qdrant + PostgreSQL
        ↓                ↓                    ↓                    ↓
    [Port 4200/80]   [Port 5054]        [Port 8000]         [Ports 6333, 5433]
```

Host ports shown. PostgreSQL is published on host 5433 (container port 5432).

## Key Directories

- `mvp/frontend/contentgruen-frontend/` - Angular frontend
- `mvp/backend/BFF/` - .NET Backend-for-Frontend
- `mvp/backend/semantic-search-service/` - Python semantic search
- `docs/` - Documentation
- `mvp/data/` - Seed data

## Development Workflow

### Making Changes
1. Use `run-local.sh/bat` for development
2. Make changes (hot-reload enabled)
3. Test locally
4. Run tests: `pytest` (Python), `ng test` (Angular)
5. Commit changes (pre-commit hooks will format code)

### Testing in Docker
1. Use `run-docker.sh/bat`
2. Access at http://localhost/
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

## Authentication Modes

### Dummy Auth (Development)
- Username: `testuser`
- Password: `Liebe>Hass!`
- Used in local and test environments

### Keycloak (Production)
- SSO integration with Netzbegrünung
- Managed by SaltStack configuration

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
# Access: http://localhost/
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
cd mvp/frontend/contentgruen-frontend
ng test
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
6. **Deliver the review in chat.** Posting it is the maintainer's step — `gh` is not
   authenticated on the dev VM (see [Git Guidelines](#important-git-guidelines)), so
   `gh pr comment` / `gh pr review` are not available and no workaround should be added.
   - Write the review to a file as well, so it can be pasted without re-reading the chat.
   - Note which PR it belongs to. The number cannot be resolved via `gh pr list`; take it
     from the user, or name the branch and let them match it.

### View API Documentation
When user requests "view api docs":
- Semantic Search: http://localhost:8000/docs
- BFF: http://localhost:5054/swagger

### Database Access
```bash
docker exec -it contentgruen-app-postgres psql -U app_user -d contentgruen_app
```

### View Logs
When user requests "check logs" or "view logs":
```bash
# Docker mode
docker-compose logs -f [contentgruen-frontend|contentgruen-bff|contentgruen-semantic-search]

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
# Creates backup in /opt/contentgruen-backups/daily/
# On Sundays: Also creates weekly backup
# Auto-rotates: Keeps last 7 daily + 4 weekly backups
```

When user requests "restore data" or "restore backup":
```bash
cd mvp/scripts/backup
# Paths are resolved relative to /opt/contentgruen-backups/ -- pass a relative path
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
- First run: `backup.sh` auto-creates directories (`/opt/contentgruen-backups/daily/`, `/opt/contentgruen-backups/weekly/`)
- Automatic rotation: Keeps last 7 daily + 4 weekly backups
- Includes Qdrant vectors and PostgreSQL metadata
- Restore is destructive - always confirm before running
- Production: Automated via SaltStack (extracts script from container, sets up cron)
- See `mvp/scripts/backup/README.md` for detailed documentation

## Testing

### Run All Tests
```bash
# Python tests (pytest.ini lives in app/)
cd mvp/backend/semantic-search-service/app
pytest

# Angular tests
cd mvp/frontend/contentgruen-frontend
ng test

# .NET tests (test project is BFF.Tests; run from the solution directory)
cd mvp/backend
dotnet test
```

## Deployment

### Test Environment
- URL: https://contentgruen-test.netzbegruenung.de (SaltStack-managed, tracks the `:main` image tag)
- Legacy URL: https://test.contentgruen.de (manual deployment, being discontinued)
- Deployment: Manual via docker-compose.tst.yml

### Production Environment
- URL: https://contentgruen.netzbegruenung.de
- Deployment: Automated via SaltStack
- Config: External SaltStack repository

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

### Adding a New Content Type
As of the rung-1 content-model refactor, a new type is **a spec + a model (+ a FE fragment)** — no per-type service/repository clone and no new search branch (see `docs/CONTENT_MODEL.md`).
1. Create the model in `domain/models/` (`<Type>DbEntry(BaseContentDbEntry)`, `<Type>SearchResult`) and add the `ContentType` enum member.
2. Register a `ContentTypeSpec` entry in `domain/content_registry.py` (reuse `create_registry_repository` — the generic `RegistryQdrantRepository`; no new repository subclass).
3. Add a `get_<type>_service` dependency in `dependencies.py` that builds the generic service from the spec, and add an `api/v1/<type>.py` router (ingestion/input is the only type-specific seam) wired in `main.py`.
4. Add the type to the `/searchByText` spec list and the `SearchResponse` DTO — the `SearchOrchestrator` handles it generically.
5. Frontend: one entry in `shared/content-type-registry.ts` + a `<Type>ResultItem` fragment.
6. Tests-first against live Qdrant in `tests/integration/` (round-trip + orchestrator parity), plus a headless-Chrome FE render/vote test.

Legacy types (`statement`, `reference`, `commentary`, `generic_text`) still have hand-written service/repository classes; do not copy that pattern for new types — prefer the registry path above. Note that `commentary` and `generic_text` also have registry specs that nothing resolves yet.

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
