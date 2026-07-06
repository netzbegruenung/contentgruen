# CLAUDE.md - Project Guide for AI Assistants

This file helps AI assistants (like Claude) understand the ContentGrün project structure and development workflow.

## IMPORTANT: Git Guidelines
- **NO EMOJIS** in commit messages
- **NO CLAUDE REFERENCES** in commit messages (no "Generated with Claude", no "Co-Authored-By: Claude")
- Keep commit messages professional and focused on the changes
- **Forgejo/Gitea repository, NOT GitHub** — host is `git.verdigado.com`. Do not use `gh`.
- **Create PRs via AGit push over SSH:**
  - `git pr [target-branch]` → opens/updates a PR (pushes `HEAD:refs/for/<target,default main>` with `-o topic=<branch>`)
  - `git pr-update [target-branch]` → same with `-o force-push=true` to update an existing PR
- **Every git-over-SSH op (fetch/push) requires a physical YubiKey touch** — when a push/fetch "hangs", the key is waiting; touch it when it blinks (~90s window).
- **PR comments/reviews can be posted via the Forgejo HTTP API** using a stored, repo-scoped fine-grained PAT (read + issue-comment only; no code write). The token lives only in the agent sandbox at `~/.config/forgejo/token` (perms 600) and is **not** committed to the repo. Push/pull stay touch-gated SSH; only API read/comment uses the PAT. If no token is present, fall back to delivering the review in chat for manual pasting.

## Quick Start Commands

### Start Development Environment

**Local Mode (Recommended for Development):**
```bash
cd mvp
run-local.bat   # Windows (or scripts/dev/run-local.bat)
./run-local.sh  # Linux/Mac (or scripts/dev/run-local.sh)
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

ContentGrün is a semantic content platform for green political activism, helping users find and share relevant political content through AI-powered search.

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
- **API**: `SEMANTIC_SEARCH_PGVECTOR_URL` for database
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
- `review pr` - Review open PR and post comment (→ see Review Pull Request)
- `check logs` - Show recent logs from all services (→ see View Logs)
- `clean restart` - Clean and restart all services (→ see Clean Restart)
- `view api docs` - Open API documentation links (→ see View API Documentation)
- `deploy test` - Deploy to test environment (→ see Test Environment)
- `check ports` - Check for port conflicts using test-setup.bat
- `reset db` - Reset database to clean state
- `backup data` - Create backup of Qdrant and PostgreSQL
- `restore data` - Restore from backup
- `test backup` - Test backup/restore functionality

## Common Tasks

### Start Development Environment
When user requests "start local" or "start":
```bash
cd mvp
run-local.bat   # Windows
./run-local.sh  # Linux/Mac
# Access: http://localhost:4200
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
cd mvp/backend/semantic-search-service
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
2. Gather the diff from **local refs** (no fetch, no YubiKey touch needed):
   - `git log origin/main..HEAD` and `git diff origin/main...HEAD`
   - For a large diff, dump it to a file and read it in sections rather than truncating.
   - Note: this reviews against the *local* `origin/main`. If `main` may have moved, a `git fetch` (touch-gated) is needed first — tell the user.
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
6. **Post the review** as a PR comment via the Forgejo API when the stored PAT (`~/.config/forgejo/token`) is present:
   - Resolve the PR number: AGit PRs have head ref `refs/pull/<N>/head` (NOT the local branch name), so match by title or ask the user for the number rather than by `head.ref`.
   - `POST https://git.verdigado.com/api/v1/repos/Netzbegruenung/contentgruen/issues/<N>/comments` with body `{"body": "<review markdown>"}` and header `Authorization: token <PAT>`.
   - Load the token from the file; never echo it or pass it through chat/shell history.
   - If no token is present, fall back to delivering the review in chat for the user to paste manually.

### View API Documentation
When user requests "view api docs":
- Semantic Search: http://localhost:8000/docs
- BFF: http://localhost:5054/swagger

### Database Access
```bash
docker exec -it semantic-search-postgres psql -U semantic_search
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
test-setup.bat  # Windows
netstat -tuln | grep -E '(4200|5054|8000|5432)'  # Linux/Mac
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
./restore.sh /opt/contentgruen-backups/daily/latest   # Restore latest daily
./restore.sh /opt/contentgruen-backups/weekly/latest  # Restore latest weekly
./restore.sh /opt/contentgruen-backups/daily/backup_YYYYMMDD_HHMMSS  # Restore specific
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
# Python tests
cd mvp/backend/semantic-search-service
pytest

# Angular tests
cd mvp/frontend/contentgruen-frontend
ng test

# .NET tests
cd mvp/backend/BFF
dotnet test
```

## Deployment

### Test Environment
- URL: https://test.contentgruen.de
- Deployment: Manual via docker-compose.tst.yml

### Production Environment
- URL: https://contentgruen.netzbegruenung.de
- Deployment: Automated via SaltStack
- Config: External SaltStack repository

## Troubleshooting

### Port Conflicts
Check with: `test-setup.bat` or `netstat -tuln | grep [port]`

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
As of the rung-1 content-model refactor, a new type is **a spec + a model (+ a FE fragment)** — no per-type service/repository clone and no new search branch (see `docs/CONTENT_MODEL.md`, `docs/RUNG_1_PLAN.md`).
1. Create the model in `domain/models/` (`<Type>DbEntry(BaseContentDbEntry)`, `<Type>SearchResult`) and add the `ContentType` enum member.
2. Register a `ContentTypeSpec` entry in `domain/content_registry.py` (reuse `create_registry_repository` — the generic `RegistryQdrantRepository`; no new repository subclass).
3. Add a `get_<type>_service` dependency in `dependencies.py` that builds the generic service from the spec, and add an `api/v1/<type>.py` router (ingestion/input is the only type-specific seam) wired in `main.py`.
4. Add the type to the `/searchByText` spec list and the `SearchResponse` DTO — the `SearchOrchestrator` handles it generically.
5. Frontend: one entry in `shared/content-type-registry.ts` + a `<Type>ResultItem` fragment.
6. Tests-first against live Qdrant in `tests/integration/` (round-trip + orchestrator parity), plus a headless-Chrome FE render/vote test.

Legacy types (`commentary`, `generic_text`, `statement`) still have hand-written service/repository classes; do not copy that pattern for new types — prefer the registry path above.

### Testing Requirements
- Always run tests before committing (`pytest` / `make test-dev`)
- Mock repository interfaces in service tests; use `TestEmbeddingsManager`, not ad-hoc mocks
- Test positive and negative cases; naming: `test_method_name_scenario`
- See `mvp/backend/semantic-search-service/app/tests/TESTING_GUIDE.md` for details

### Pre-commit Hooks
The project uses pre-commit hooks that auto-format code (Black/Prettier) and run tests.
They may reformat files and fail on the first commit attempt, then pass on the second — this is
intentional. Don't bypass with `--no-verify` except in emergencies. The `safe-commit.sh`/`.bat`
helpers automate the retry.
