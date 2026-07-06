# Configuration Guide

## Overview

The semantic search service uses environment variables for configuration, with support for both Docker and local development environments.

## Environment Detection

The service automatically detects whether it's running in Docker or locally:
- **Docker**: When `DOCKER_CONTAINER=true` is set
- **Local**: When running directly with Python

## Configuration Methods

### 1. Docker (Production/Test)

Configuration is provided via environment variables in `docker-compose.yml`:

```yaml
environment:
  - DOCKER_CONTAINER=true
  - SEMANTIC_SEARCH_DATA_PATH=/data/seed/v1.0
  - SEMANTIC_SEARCH_METADATA_PATH=/metadata
  - SEMANTIC_SEARCH_PGVECTOR_URL=postgresql+psycopg2://...
```

### 2. Local Development

For local development, create a `.env` file in the `semantic-search-service` directory:

```bash
# Copy the example file
cp .env.example .env

# Edit with your local settings
nano .env
```

## Path Configuration

### Docker Paths
- **Application**: `/app` (working directory)
- **Seed Data**: `/data/seed/v1.0` (mounted from `./data`)
- **Metadata**: `/metadata` (persistent named volume)

### Local Development Paths
- **Application**: `mvp/backend/semantic-search-service/app`
- **Seed Data**: `mvp/data/seed/v1.0` (relative to project root)
- **Metadata**: `mvp/temp_data/metadata`

## Key Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DOCKER_CONTAINER` | Set to `true` when running in Docker | `false` |
| `SEMANTIC_SEARCH_DATA_PATH` | Path to seed data directory | Auto-detected |
| `SEMANTIC_SEARCH_METADATA_PATH` | Path for seeding metadata | Auto-detected |
| `SEMANTIC_SEARCH_PGVECTOR_URL` | PostgreSQL connection string | localhost:5432 |
| `APP_DATABASE_URL` | App database connection string | localhost:5433 |
| `SEMANTIC_SEARCH_LOG_LEVEL` | Logging level (DEBUG, INFO, etc.) | INFO |

## Path Validation

At startup, the service:
1. Validates that the data path exists (required for seeding)
2. Creates metadata directory if it doesn't exist
3. For local development, attempts to find data in common locations

## Troubleshooting

### Seeding Issues

If seeding fails with "No JSON files found":
1. Check that data is mounted correctly: `docker-compose logs contentgruen-semantic-search`
2. Verify the data path exists: `docker exec contentgruen-semantic-search ls -la /data/seed/v1.0`
3. Check environment variables: `docker exec contentgruen-semantic-search env | grep SEMANTIC`
4. Ensure seed data files exist in `mvp/data/seed/v1.0/` on the host

### Local Development Issues

If paths are not found locally:
1. Ensure you're running from the correct directory
2. Check that `.env` file exists and is loaded
3. Verify paths in `.env` are correct relative to your working directory

## Configuration Changes (2025)

### Simplified Path Structure
- Standardized Docker mount point: `/data` (was `/seeddata`)
- Removed hardcoded paths from Dockerfile
- All paths now configurable via environment variables

### Deprecated Fields
The following fields are maintained for backward compatibility but will be removed:
- `initial_data_path` → Use `data_path`
- `index_initial_data_path` → Legacy, no longer used
- `index_storage_path` → Removed (using PostgreSQL now)

### Version Flexibility
To use different seed data versions, simply change the environment variable:
```yaml
# For v1.0 (default)
SEMANTIC_SEARCH_DATA_PATH=/data/seed/v1.0

# For v2.0
SEMANTIC_SEARCH_DATA_PATH=/data/seed/v2.0
```
