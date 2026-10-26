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
- **Access**: https://gutgesagt-test.netzbegruenung.de (SaltStack-managed).
- **Infrastructure**: Docker containers on test server
- **Authentication**: Dummy auth (testuser/Liebe>Hass!)
- **Management**: SaltStack state, deployed manually (`state.apply`, then `docker compose pull && up -d`)

### 4. Production Environment
- **Purpose**: Live system for Netzbegrünung members
- **Access**: https://gutgesagt.netzbegruenung.de and
  https://gutgesagt.netzbegruenung.verdigado.net (contentgruen.de redirects here, upstream of SaltStack)
- **Infrastructure**: Docker containers managed by SaltStack
- **Authentication**: Keycloak SSO integration
- **Management**: SaltStack automation

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
  - Authentication handling (Keycloak or dummy)
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
- **Purpose**: Application data — votes, usage tracking, search tracking, moderation reports.
  Content and its vector embeddings live in Qdrant, not in PostgreSQL.
- **Image**: `postgres:16-alpine` (service `postgres-app`, container `gutgesagt-app-postgres`)
- **Access**:
  - Local/Docker: localhost:5433 (container port 5432)
  - Test/Prod: Internal Docker network

> The schema is defined once, in `mvp/backend/postgres-app/init.sql`. It is baked into the
> `gutgesagt-postgres-app` image used by test and production, and bind-mounted by the local
> compose files, so every environment provisions the same tables.

## Nginx Configuration

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
- **External nginx** (SaltStack managed):
  - TLS termination
  - Routes gutgesagt.netzbegruenung.de and gutgesagt.netzbegruenung.verdigado.net
    → frontend container (127.0.0.1:3000)
  - Routes bff.gutgesagt.netzbegruenung.de → BFF container (127.0.0.1:3001)
  - Keycloak integration

## Authentication Flow

### Managed Login (Local/Docker/Test)
1. User enters e-mail address and password in frontend ("Direktanmeldung")
2. Frontend POSTs to BFF `/api/auth/login/managed`
3. BFF validates against `managed-users.json` (bcrypt hashes; example users in
   `mvp/config/managed-users.example.json`, e.g. `test.user@example.com`/`Liebe>Hass!`)
4. BFF sets session cookie
5. BFF returns user info

With `USE_KEYCLOAK=false` the BFF also still answers the old dummy `POST /login`
(default `testuser`/`Liebe>Hass!`, overridable via `DUMMY_AUTH_USERNAME`/`DUMMY_AUTH_PASSWORD`;
user id `test-user-id-1`). The frontend no longer has a form for it.

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
- **docker-compose.prd.yml**: Reference to SaltStack managed production

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
  its password is documented in this repository (`mvp/backend/BFF/Program.cs:526-527`,
  `:571`).

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
- `OPENAI_API_KEY` (or `SEMANTIC_SEARCH_OPENAI_API_KEY`) - enables AI image captioning; without it
  the image type falls back to direct text ingestion
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
- Dummy authentication for testing
- No TLS (HTTP only)
- Open CORS for development

### Production
- Keycloak SSO authentication
- TLS termination at nginx
- Restricted CORS policy
- Network isolation
- Secrets managed by SaltStack

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
- GitHub Actions for automated builds (`.github/workflows/build.yml` on `main` and pull requests,
  `.github/workflows/release.yml` on `v*` tags)
- Container registry at git.verdigado.com (`netzbegruenung-images`)
- Test: runs the floating `:main` tag, deployed manually (Salt `state.apply`, then
  `docker compose pull && docker compose up -d`). The Watchtower block still in the Salt state
  is stuck in a restart loop (as of 2026-10-11) and is being removed (#22)
- Production: SaltStack, with images pinned by digest and bumped by Renovate — deploys happen
  when the Salt compose file is rewritten, not on a tag push

## Storage & Persistence

### Development
- PostgreSQL in Docker with local volume
- Data persists between restarts

### Production
- PostgreSQL with persistent volumes
- Backup & restore with rotation (`mvp/scripts/backup/`), scheduled via SaltStack
- Migration tooling (planned)
