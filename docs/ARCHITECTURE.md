# ContentGrün Architecture Documentation

## Overview

ContentGrün is a progressive content platform with semantic search capabilities for green political activism. The application runs in multiple environments with different configurations.

## Environment Overview

### 1. Local Development
- **Purpose**: Active development with hot-reload
- **Access**: http://localhost:4200 (frontend), http://localhost:5054 (BFF), http://localhost:8000 (API)
- **Infrastructure**: Services run locally, only Qdrant and PostgreSQL in Docker (`docker-compose.local-dbs.yml`)
- **Authentication**: Dummy auth (testuser/Liebe>Hass!)

### 2. Docker Development
- **Purpose**: Testing containerized deployment locally
- **Access**: http://localhost (frontend via nginx proxy)
- **Infrastructure**: All services in Docker containers
- **Authentication**: Dummy auth (testuser/Liebe>Hass!)

### 3. Test Environment
- **Purpose**: Integration testing and demos
- **Access**: https://contentgruen-test.netzbegruenung.de (SaltStack-managed).
  The older manually-managed https://test.contentgruen.de is being discontinued.
- **Infrastructure**: Docker containers on test server
- **Authentication**: Dummy auth (testuser/Liebe>Hass!)
- **Management**: Manual deployment via `docker-compose.tst.yml`

### 4. Production Environment
- **Purpose**: Live system for Netzbegrünung members
- **Access**: https://contentgruen.netzbegruenung.de and
  https://contentgruen.netzbegruenung.verdigado.net (contentgruen.de redirects here, upstream of SaltStack)
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
  - `environment.local.ts` - Local development (baseUrl: http://localhost:5054)
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
- **Image**: `postgres:16-alpine` (service `postgres-app`, container `contentgruen-app-postgres`)
- **Access**:
  - Local/Docker: localhost:5433 (container port 5432)
  - Test/Prod: Internal Docker network

> A `pgvector`-based image is still built and published by CI
> (`mvp/backend/postgres-semantic/`), but it is used by **nothing** — not by any compose file
> here, and not by the production SaltStack state. Treat it as a dead build artifact.

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
  - Routes contentgruen.netzbegruenung.de and contentgruen.netzbegruenung.verdigado.net
    → frontend container (127.0.0.1:3000)
  - Routes bff.contentgruen.netzbegruenung.de → BFF container (127.0.0.1:3001)
  - Keycloak integration

## Authentication Flow

### Dummy Auth (Local/Docker/Test)
1. User enters credentials in frontend
2. Frontend POSTs to BFF `/login`
3. BFF validates (hardcoded: testuser/Liebe>Hass!)
4. BFF sets session cookie
5. BFF returns user info

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
- **docker-compose.tst.yml**: Test environment configuration
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
- Test: tracks the floating `:main` tag via a Watchtower sidecar
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
