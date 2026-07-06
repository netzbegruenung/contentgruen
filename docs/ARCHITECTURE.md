# ContentGrün Architecture Documentation

## Overview

ContentGrün is a progressive content platform with semantic search capabilities for green political activism. The application runs in multiple environments with different configurations.

## Environment Overview

### 1. Local Development
- **Purpose**: Active development with hot-reload
- **Access**: http://localhost:4200 (frontend), http://localhost:5054 (BFF), http://localhost:8000 (API)
- **Infrastructure**: Services run locally, only PostgreSQL in Docker
- **Authentication**: Dummy auth (testuser/Liebe>Hass!)

### 2. Docker Development
- **Purpose**: Testing containerized deployment locally
- **Access**: http://localhost (frontend via nginx proxy)
- **Infrastructure**: All services in Docker containers
- **Authentication**: Dummy auth (testuser/Liebe>Hass!)

### 3. Test Environment
- **Purpose**: Integration testing and demos
- **Access**: https://test.contentgruen.de
- **Infrastructure**: Docker containers on test server
- **Authentication**: Basic auth or dummy auth
- **Management**: Manual deployment

### 4. Production Environment
- **Purpose**: Live system for Netzbegrünung members
- **Access**: https://contentgruen.netzbegruenung.de (future: contentgruen.de)
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
                    │          Qdrant (Vector DB)          │
                    │  Port: 6333  │  PostgreSQL (Metadata) │
                    │              │  Port: 5433            │
                    └──────────────────────────────────────┘
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

### PostgreSQL + pgvector
- **Purpose**: Unified storage for all content with vector embeddings
- **Schema**: Single table with content type discrimination
- **Access**:
  - Local/Docker: localhost:5432
  - Test/Prod: Internal Docker network

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
  - Routes contentgruen.de → frontend container
  - Routes bff.contentgruen.de → BFF container
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
- **docker-compose.postgres.yml**: PostgreSQL only for local development
- **docker-compose.tst.yml**: Test environment configuration
- **docker-compose.prd.yml**: Reference to SaltStack managed production

### Container Registry
- Test/Prod images: `git.verdigado.com/netzbegruenung-images/*`
- Local: Built from source

## Data Flow

1. **User Request** → Frontend (Angular/nginx)
2. **API Call** → BFF (authentication & routing)
3. **Business Logic** → Semantic Search Service
4. **Data Storage** → PostgreSQL + pgvector
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
- `FRONTEND_URL` - Frontend URL for redirects

### Semantic Search
- `SEMANTIC_SEARCH_PGVECTOR_URL` - PostgreSQL connection
- `SEMANTIC_SEARCH_LOG_LEVEL` - DEBUG/INFO
- `SEEDING_METADATA_PATH` - Metadata storage path

## Startup Scripts

### Local Development
- `run-local.bat/.sh` - Starts services locally with PostgreSQL in Docker
- Services run with hot-reload for development

### Docker Development
- `run-docker.bat/.sh` - Starts all services in Docker
- Uses docker-compose.dev.yml

### Utilities
- `test-setup.bat` - Checks prerequisites
- `reset-to-docker.bat` - Resets environment config
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
- Woodpecker CI for automated builds
- Container registry at git.verdigado.com
- SaltStack for production deployment

## Storage & Persistence

### Development
- PostgreSQL in Docker with local volume
- Data persists between restarts

### Production
- PostgreSQL with persistent volumes
- Backup strategy (planned)
- Migration tooling (planned)
