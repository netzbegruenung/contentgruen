# Gut gesagt Architecture Documentation

## Overview

Gut gesagt is a progressive content platform with semantic search capabilities for green political activism. The application runs in multiple environments with different configurations.

## Environment Overview

### 1. Local Development
- **Purpose**: Active development with hot-reload
- **Access**: http://localhost:4200 (frontend), http://localhost:5054 (BFF), http://localhost:8000 (API)
- **Infrastructure**: Services run locally, only Qdrant and PostgreSQL in Docker (`docker-compose.local-dbs.yml`)
- **Authentication**: E-mail login against `managed-users.json` (`test.user@example.com`/`Liebe>Hass!`)

### 2. Docker Development
- **Purpose**: Testing containerized deployment locally
- **Access**: http://localhost (frontend via nginx proxy)
- **Infrastructure**: All services in Docker containers
- **Authentication**: E-mail login against `managed-users.json` (`test.user@example.com`/`Liebe>Hass!`)

### 3. Test Environment
- **Purpose**: Integration testing and demos
- **Access**: https://gutgesagt-test.netzbegruenung.de
- **Infrastructure**: Docker containers on verdigado's internal infrastructure
- **Authentication**: Whatever the BFF configuration enables (`GET /api/auth/modes`): Keycloak and/or
  Direktanmeldung; the accounts are not part of this repository
- **Management**: Rolled out manually on verdigado's internal infrastructure; details are documented internally

### 4. Production Environment
- **Purpose**: Live system for Netzbegrünung members
- **Access**: https://gutgesagt.netzbegruenung.de (contentgruen.de redirects here)
- **Infrastructure**: Docker containers on verdigado's internal infrastructure
- **Authentication**: Keycloak SSO integration
- **Management**: Rolled out on verdigado's internal infrastructure; details are documented internally

## Service Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    External Nginx (Prod/Test)                   │
│                  OR Direct Access (Local/Docker)                │
└─────────────────────────────────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
┌─────────────────────┐ ┌─────────────┐ ┌──────────────────┐
│  Frontend (Angular) │ │  BFF (.NET) │ │ Semantic Search  │
│    Port: 80/4200    │ │ Port: 5054  │ │   (FastAPI)      │
│                     │ │             │ │  Port: 8000      │
│  Container nginx    │ │   YARP      │ │                  │
│  serves static      │ │   Proxy     │ │  E5 embeddings   │
└─────────────────────┘ └─────────────┘ └──────────────────┘
                                │               │
                                └───────┬───────┘
                                        ▼
                    ┌──────────────────────────────────────┐
                    │  Qdrant (Vector DB)  │  PostgreSQL     │
                    │  Port: 6333          │  (application   │
                    │                      │   data)         │
                    │                      │  Port: 5433→5432│
                    └──────────────────────────────────────┘

Host ports are shown. In Docker, PostgreSQL is published on host port 5433 and
listens on 5432 inside the container.
```

## Component Details

### Frontend (Angular)
- **Technology**: Angular 20+, Angular Material UI
- **Deployment**:
  - **Local**: Angular CLI dev server (webpack) on port 4200
  - **Docker/Test/Prod**: nginx container serving static files on port 80
- **Environment Config**:
  - `environment.ts` - Active configuration
  - `environment.local.ts` - Local development (baseUrl: empty, `ng serve` proxies to the BFF via `proxy.conf.json`)
  - `environment.docker.ts` - Docker mode (baseUrl: empty for proxy)
  - `environment.prod.ts` - Production (uses placeholders replaced at runtime)

### BFF (Backend-for-Frontend)
- **Technology**: .NET 9.0, YARP reverse proxy
- **Purpose**:
  - Authentication handling (Keycloak, Direktanmeldung, or the old dummy login)
  - API gateway/proxy to semantic search service
  - User context injection via headers
- **Configuration**:
  - `USE_KEYCLOAK` - Enable/disable Keycloak SSO
  - `BACKEND_URL` - Semantic search service URL
  - `FRONTEND_URL` - Frontend URL for redirects

### Semantic Search Service
- **Technology**: Python FastAPI, Qdrant vector database, E5 multilingual embeddings
- **Databases**:
  - Qdrant for vector embeddings and content storage
  - PostgreSQL for application metadata (usage tracking)
- **Features**:
  - Unified content storage with type filtering
  - Semantic similarity search using 768-dimensional E5 embeddings
  - Asynchronous data seeding
  - RESTful API with OpenAPI docs
- **Architecture**:
  - Repository pattern for data access
  - Service layer for business logic
  - Dependency injection for testability

### PostgreSQL
- **Purpose**: Application data — votes, usage tracking, search tracking, moderation reports,
  and per person the usage last shown in the Rückmeldung (`gesehene_nutzung`).
  Content and its vector embeddings live in Qdrant, not in PostgreSQL.
- **Image**: `postgres:16-alpine` (service `postgres-app`, container `gutgesagt-app-postgres`)
- **Access**:
  - Local/Docker: localhost:5433 (container port 5432)
  - Test/Prod: Internal Docker network

> The schema is defined by the SQLAlchemy models
> (`app/infrastructure/database/models.py`); the semantic service creates missing tables
> with `create_all` on start. `mvp/backend/postgres-app/init.sql` additionally creates
> `usage_tracking` and `usage_events` on an empty volume and must match the models
> exactly (checked by `tests/integration/test_migrationen.py`). It is baked into the
> `gutgesagt-postgres-app` image used by test and production, and bind-mounted by the
> local compose files. Existing databases get schema changes from
> `mvp/backend/postgres-app/migrations/`: the semantic service applies them on start,
> after `create_all`, and records each in the table `migrationsprotokoll`
> (`app/infrastructure/database/migrationen.py`).

## Nginx Configuration

Both frontend configurations (`nginx.conf`, `nginx.docker.conf`) share
`nginx.protokoll.conf`: the access log carries the path without query string and no
referrer, and no line for searches or the results page (#275, see
`docs/LOESCHKONZEPT.md`).

### Local Development
- **No nginx** - Direct access to services

### Docker Development
- **Frontend Container nginx** (`nginx.docker.conf`):
  - Serves Angular static files
  - Proxies `/api/*`, `/login`, `/logout` to BFF container
  - Single entry point on port 80

### Test Environment
- **Frontend Container nginx**: Serves static files
- **External nginx**: Routes traffic to containers

### Production Environment
- **Frontend Container nginx**: Serves static files
- **External nginx** (part of the operated infrastructure):
  - TLS termination
  - Routes gutgesagt.netzbegruenung.de → frontend container
  - Routes bff.gutgesagt.netzbegruenung.de → BFF container
  - Keycloak integration

## Authentication Flow

### Direktanmeldung (Beta-Zugang)
Login with e-mail address and password, for Beta-Zugang accounts. It does not depend on the
environment: it is on whenever `ENABLE_MANAGED_AUTH` is true (the default) and the BFF finds a
non-empty users file, so production can offer it next to Keycloak. Local and Docker development
log in this way.

1. User enters e-mail address and password in frontend ("Direktanmeldung")
2. Frontend POSTs to BFF `/api/auth/login/managed`
3. BFF validates against `managed-users.json` (bcrypt hashes; example users in
   `mvp/config/managed-users.example.json`, e.g. `test.user@example.com`/`Liebe>Hass!`)
4. BFF sets session cookie
5. BFF returns user info

`managed-users.json` is gitignored. `mvp/run-local.sh` creates it from the example file for
the Docker dev stack; for the local mode copy it by hand (`docs/DEV-SETUP.md`). Without the
file the Direktanmeldung is off.

With `USE_KEYCLOAK=false` the BFF also still answers the old dummy `POST /login`
(default `testuser`/`Liebe>Hass!`, overridable via `DUMMY_AUTH_USERNAME`/`DUMMY_AUTH_PASSWORD`;
user id `test-user-id-1`, which must never be an admin, see `ADMIN_USER_IDS` below). The
frontend no longer has a form for it.

### Keycloak (Production)
1. User accesses protected resource
2. BFF redirects to Keycloak login
3. User authenticates with Keycloak
4. Keycloak redirects back with token
5. BFF validates token and creates session
6. BFF injects user context in API calls

## Deployment Configurations

### Docker Compose Files
- **docker-compose.dev.yml**: Full stack for local Docker development
- **docker-compose.local-dbs.yml**: Qdrant + PostgreSQL only, for local component-based development
- **docker-compose.prd.yml**: Placeholder; the production compose file is managed outside this repository

### Container Registry
- Test/Prod images: `git.verdigado.com/netzbegruenung-images/*`
- Local: Built from source

## Data Flow

1. **User Request** → Frontend (Angular/nginx)
2. **API Call** → BFF (authentication & routing)
3. **Business Logic** → Semantic Search Service
4. **Data Storage** → Qdrant (content + vectors) and PostgreSQL (application data)
5. **Response** → Back through the chain

## Environment Variables

### Frontend
- `PRODUCTION` - Production mode flag
- `API_BASE_URL` - BFF endpoint (empty for proxy mode)
- `USE_KEYCLOAK` - Authentication mode

### BFF
- `ASPNETCORE_ENVIRONMENT` - Development/Production
- `USE_KEYCLOAK` - true/false
- `BACKEND_URL` - Semantic search service URL
- `FRONTEND_URL` - Origin the SPA is served from. Drives the OIDC redirect *and* the CORS
  allowlist, so each environment trusts only its own frontend. **Required** outside
  `Development`; startup fails if it is missing.
- `CORS_ALLOWED_ORIGINS` - Optional, comma-separated extra CORS origins for cases where more
  than one hostname serves the SPA. Unset in all current environments.
- `ADMIN_USER_IDS` - Optional, comma-separated user ids that get admin rights in addition to
  anyone carrying an admin claim (`AdminPolicy`). Values are compared to the same string the
  BFF forwards as `X-User`, i.e. the Keycloak `sub` claim or the `userId` field from
  `managed-users.json` - not e-mail addresses, not usernames. Comparison is ordinal and
  case-sensitive, matching how the Python service compares `SEMANTIC_SEARCH_ADMIN_USERS`;
  set both to the same value so one entry means one person on both sides. Unset means no
  extra admins and is not an error - the claim alone decides, as before. Whitespace around
  entries is trimmed.

  The id to enter is the `userId` field of `GET /api/user-info`, read while that person is
  logged in: it is exactly the string this check compares, whereas reading a `sub` claim by
  hand is a detour - .NET's inbound claim mapping renames `sub` to `nameidentifier` before
  the application sees it. The list is parsed once at startup, so changing it only takes
  effect after the BFF container is restarted. Never put `test-user-id-1` on the list: that
  is the id handed out by the dummy login that is active whenever `USE_KEYCLOAK=false`, and
  its password is documented in this repository (`mvp/backend/BFF/Program.cs:509-510`,
  `:554`, `:575`).

  It exists because the claim route needs a Keycloak protocol mapper: `OnTokenValidated`
  copies token claims unchanged, so a flat `isAdmin`/`role` claim has to come from the realm
  configuration, which lives outside this repository.

### Semantic Search

All settings use the `SEMANTIC_SEARCH_` prefix (see `app/core/config.py`):

- `SEMANTIC_SEARCH_QDRANT_URL` - Qdrant endpoint
- `SEMANTIC_SEARCH_QDRANT_COLLECTION` - Qdrant collection name
- `SEMANTIC_SEARCH_APP_DATABASE_URL` - PostgreSQL connection string
- `SEMANTIC_SEARCH_DATA_PATH` - Seed data path
- `SEMANTIC_SEARCH_METADATA_PATH` - Persistent metadata storage path
- `SEMANTIC_SEARCH_LOG_LEVEL` - DEBUG/INFO
- `OPENAI_API_KEY` (or `SEMANTIC_SEARCH_OPENAI_API_KEY`) - enables the suggested Unterschrift in the
  image form (`POST /api/v1/image/suggestCaption`); without it the person writes the Unterschrift.
  Setting it starts a transfer to a third country, see the privacy warning in `CLAUDE.md`
- `DOCKER_CONTAINER` - set to `true` inside containers to enforce strict path validation

## Startup Scripts

### Local Development
- `run-local.bat/.sh` - Starts services locally with PostgreSQL in Docker
- Services run with hot-reload for development

### Docker Development
- `run-docker.bat/.sh` - Starts all services in Docker
- Uses docker-compose.dev.yml

### Utilities
- `mvp/scripts/setup/check-environment.sh/.bat` - Checks prerequisites
- `mvp/scripts/utils/switch-to-docker.sh/.bat` and `switch-to-local.sh/.bat` - Switch the active frontend environment config
- `mvp/scripts/utils/clean-all.sh/.bat` - Removes containers, volumes and build artifacts
- `safe-commit.bat/.sh` - Handles pre-commit hooks

## Network Architecture

### Local
- Direct connections between services
- No network isolation

### Docker
- Bridge network `mvp_default`
- Service discovery by container name
- Isolated from host network

### Production
- Docker overlay network
- External nginx for ingress
- Internal service mesh

## Security Considerations

### Local/Test
- Direktanmeldung; locally with the example accounts from `managed-users.example.json`
- The old dummy `POST /login` stays reachable while `USE_KEYCLOAK=false`
- No TLS (HTTP only)
- Open CORS for development

### Production
- Keycloak SSO authentication
- TLS termination at nginx
- Restricted CORS policy
- Network isolation
- Secrets managed outside this repository

### Known gap: seeding router
- `/api/v1/seeding/*` (`api/v1/seeding.py`) has no auth dependency. It is closed by the BFF
  edge block (`BFF/Proxy/EndpointPolicy.cs`, `Blocked`) and by port 8000 not being published
  on the hosts. `require_admin` would add nothing yet: it trusts `X-Is-Admin`, which anyone
  who reaches port 8000 can set, because the identity headers are not signed (#26).
  **Secure the seeding router once #26 is implemented.**

## Monitoring & Logging

### Current State
- Basic console logging
- Docker logs for containers
- No centralized logging yet

### Planned
- OpenTelemetry integration
- Centralized log aggregation
- Metrics collection
- Health checks

## Build & CI/CD

### Local
- Manual builds
- Hot-reload development

### Test/Production
- Woodpecker checks every pull request on Forgejo (`.woodpecker/ci.yaml`, required status
  for `main`, see `docs/CI.md`)
- GitHub Actions on the mirror for automated builds (`.github/workflows/build.yml` on `main`,
  `.github/workflows/release.yml` on `v*` tags)
- Container registry at git.verdigado.com (`netzbegruenung-images`)
- Test: runs the floating `:main` tag, rolled out manually by the operators
- Production: pins `:latest` by digest; how it updates: `docs/DEPLOYMENT.md`, "Updating Production"

## Storage & Persistence

### Development
- PostgreSQL in Docker with local volume
- Data persists between restarts

### Production
- PostgreSQL with persistent volumes
- Backup & restore with rotation (`mvp/scripts/backup/`), scheduled on verdigado's internal infrastructure
- Migrations applied by the semantic service on start (`mvp/backend/postgres-app/migrations/README.md`)
