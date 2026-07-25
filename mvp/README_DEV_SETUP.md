# ContentGrün Development Setup

This guide explains how to run ContentGrün in different development modes.

## Prerequisites

- Docker Desktop installed and running
- Node.js 18+ (for local mode)
- .NET SDK 9.0 (for local mode)
- Python 3.10+ (for local mode)

## Development Modes

### 1. Full Docker Mode (Recommended for Quick Start)

Run everything in Docker containers. This is the easiest way to get started.

**Windows:**
```bash
cd mvp
run-docker.bat
```

**Linux/Mac:**
```bash
cd mvp
./run-docker.sh
```

This will:
- Build and start all services in Docker containers
- PostgreSQL with pgvector on port 5432
- Semantic Search Service on port 8000
- BFF (.NET) on port 5054
- Frontend (Angular) on port 80

**Access points:**
- Frontend: http://localhost/
- BFF API: http://localhost:5054/
- Semantic Search API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432

### 2. Local Development Mode (Recommended for Development)

Run services locally with only PostgreSQL in Docker. Better for development with hot-reload.

**Windows:**
```bash
cd mvp
run-local.bat
```

**Linux/Mac:**
```bash
cd mvp
./run-local.sh
```

This will:
- Start PostgreSQL in Docker on port 5432
- Run Semantic Search Service locally on port 8000
- Run BFF (.NET) locally on port 5054
- Run Frontend (Angular) locally on port 4200

**Access points:**
- Frontend: http://localhost:4200/
- BFF API: http://localhost:5054/
- Semantic Search API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432

### 3. Manual Setup

If you prefer to start services individually:

#### Start the databases only (Qdrant + PostgreSQL):
```bash
cd mvp
docker compose -f docker-compose.local-dbs.yml up -d
```

#### Start Semantic Search Service:
```bash
cd mvp/backend/semantic-search-service
python -m venv venv
# Windows: venv\Scripts\activate
# Unix: source venv/bin/activate
pip install -r requirements.txt
export SEMANTIC_SEARCH_APP_DATABASE_URL="postgresql+psycopg2://app_user:changeme@localhost:5433/contentgruen_app"
export SEMANTIC_SEARCH_QDRANT_URL="http://localhost:6333"
cd app
uvicorn main:app --reload
```

#### Start BFF:
```bash
cd mvp/backend/BFF
export USE_KEYCLOAK=false
export BACKEND_URL=http://localhost:8000
dotnet run
```

#### Start Frontend:
```bash
cd mvp/frontend/contentgruen-frontend
# For local development:
cp src/environments/environment.local.ts src/environments/environment.ts
npm install
npm start
```

## Default Credentials

- Username: `testuser`
- Password: `Liebe>Hass!`

## Switching Between Modes

### From Docker to Local:
1. Stop Docker containers: `docker-compose -f docker-compose.dev.yml down`
2. Run: `run-local.bat` or `./run-local.sh`

### From Local to Docker:
1. Stop all local services (Ctrl+C in each terminal)
2. Reset environment: `mvp/scripts/utils/switch-to-docker.bat` (Windows) or `bash mvp/scripts/utils/switch-to-docker.sh`
3. Run: `run-docker.bat` or `./run-docker.sh`

## Environment Configuration

The frontend uses different environment configurations:

- **Docker mode**: Uses empty `baseUrl` (nginx proxies to BFF)
- **Local mode**: Uses `http://localhost:5054` as `baseUrl`

Environment files:
- `src/environments/environment.ts` - Current active environment
- `src/environments/environment.local.ts` - Local development configuration
- `src/environments/environment.docker.ts` - Docker configuration
- `src/environments/environment.prod.ts` - Production configuration

## Troubleshooting

### Docker Issues
- Ensure Docker Desktop is running
- Check port conflicts: 80, 5054, 8000, 5432, 4200
- Run `docker-compose -f docker-compose.dev.yml down` to clean up

### Local Mode Issues
- Ensure PostgreSQL container is running: `docker ps`
- Check Python virtual environment is activated
- Verify .NET SDK version: `dotnet --version`
- Check Node.js version: `node --version`

### Login Issues
- In Docker mode: Frontend should be accessed via `http://localhost/`
- In local mode: Frontend should be accessed via `http://localhost:4200/`
- Check BFF logs for authentication errors
- Ensure `USE_KEYCLOAK=false` is set

### Database Issues
- PostgreSQL credentials: `semantic_search` / `changeme`
- Database name: `semantic_search`
- Connection issues: Check if container is running with `docker ps`

## Development Tips

1. **Hot Reload**: Local mode supports hot reload for all services
2. **Debugging**: Local mode allows easier debugging with IDE integration
3. **Docker Logs**: View logs with `docker-compose -f docker-compose.dev.yml logs -f [service-name]`
4. **Clean Start**: Remove volumes with `docker-compose -f docker-compose.dev.yml down -v`
5. **Rebuild**: Force rebuild with `docker-compose -f docker-compose.dev.yml build --no-cache`

## Service Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│   Frontend  │────▶│     BFF     │────▶│ Semantic Search  │
│  (Angular)  │     │   (.NET)    │     │   (FastAPI)      │
└─────────────┘     └─────────────┘     └──────────────────┘
                                                  │
                                                  ▼
                                         ┌──────────────────┐
                                         │   PostgreSQL     │
                                         │   + pgvector     │
                                         └──────────────────┘
```

## Ports Summary

| Service | Docker Mode | Local Mode |
|---------|------------|------------|
| Frontend | 80 | 4200 |
| BFF | 5054 | 5054 |
| Semantic Search | 8000 | 8000 |
| PostgreSQL | 5432 | 5432 |
