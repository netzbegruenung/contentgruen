# Configuration Guide

## Overview

The semantic search service uses environment variables for configuration, with support for both Docker and local development environments.

## Environment Detection

The service automatically detects whether it's running in Docker or locally:
- **Docker**: When `DOCKER_CONTAINER=true` is set
- **Local**: When running directly with Python

## Configuration Methods

### 1. Docker (Production/Test)

Configuration is provided via environment variables in `mvp/docker-compose.dev.yml`:

```yaml
environment:
  - DOCKER_CONTAINER=true
  - SEMANTIC_SEARCH_DATA_PATH=/data/seed/v1.0
  - SEMANTIC_SEARCH_METADATA_PATH=/metadata
  - SEMANTIC_SEARCH_QDRANT_URL=http://qdrant:6333
  - SEMANTIC_SEARCH_QDRANT_COLLECTION=content_collection
  - SEMANTIC_SEARCH_APP_DATABASE_URL=postgresql+psycopg2://...
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
| `SEMANTIC_SEARCH_QDRANT_URL` | Qdrant endpoint | `http://localhost:6333` |
| `SEMANTIC_SEARCH_QDRANT_COLLECTION` | Qdrant collection name | `content_collection` |
| `SEMANTIC_SEARCH_EMBEDDING_THREADS` | Torch threads for computing embeddings (integer, at least 1; leave unset rather than empty), set once at startup for the whole process. Limits CPU contention on a busy host (#480); whether and which value production uses is the maintainer's call | unset (one per visible core) |
| `SEMANTIC_SEARCH_NLI_BESTAETIGER` | Second NLI model (Bestätiger) for the same-Aussage check, only with the NLI-Stufe on (`schatten` or `an`). Up to ~2.2 GB more RAM; check the host before switching it on (`docs/DEPLOYMENT.md`) | `false` |
| `SEMANTIC_SEARCH_NLI_BESTAETIGER_VETO_AB` | Veto of the first NLI model on the Bestätiger path: it must entail both directions at least this much (`tests/regression/MESSSET.md`) | `0.1` |
| `SEMANTIC_SEARCH_SUCHE_POLARITAET_NLI` | Polarity penalty of the search (#574): `aus` (word lists), `schatten` (word lists decide, the NLI model judges in the background and is only counted in the log) or `an` (the NLI model decides; questions, keyword queries and no model fall back to the word lists). Same model as the NLI-Stufe (no extra RAM unless the NLI-Stufe is `aus`); with `an` each search waits for the model, median +0.3 to 0.45 s on the dev VM (`tests/regression/SUCHTESTSET.md`, `docs/DEPLOYMENT.md`) | `schatten` |
| `SEMANTIC_SEARCH_SUCHE_POLARITAET_WIDERSPRUCH_AB` | With `an`: an Aussage counts as the opposite of the query when the NLI model sees a contradiction in both directions at least this likely | `0.9` |
| `SEMANTIC_SEARCH_SUCHE_BEZUG_AB` | For a query of three words or more (keyword queries are not checked): an Aussage below this embedding similarity is no hit (`services/search/bezug.py`; against "Erkannt als" with an unrelated Aussage that only shares a keyword). Its answers come via the direct path only with `…_BEZUG_DIREKT_AB` | `0.87` |
| `SEMANTIC_SEARCH_SUCHE_BEZUG_NLI` | For a statement query (no question): Aussagen between `…_BEZUG_AB` and `…_BEZUG_SICHER_AB` count only if the NLI model sees entailment in one direction of at least `…_BEZUG_FOLGERUNG_AB` (no model or busy for 2 s: they count). Keeps out sentences that are merely built alike; the search waits for the model (median +0.07 s, 95th percentile +0.25 s on the shared dev VM). `false` leaves only the lower limit; `tests/regression/SUCHTESTSET.md`, section Bezug | `true` |
| `SEMANTIC_SEARCH_SUCHE_BEZUG_SICHER_AB` | With `…_BEZUG_NLI`: from this similarity an Aussage counts without the model | `0.92` |
| `SEMANTIC_SEARCH_SUCHE_BEZUG_FOLGERUNG_AB` | With `…_BEZUG_NLI`: minimum entailment (either direction) for an Aussage in the band | `0.2` |
| `SEMANTIC_SEARCH_SUCHE_BEZUG_DIREKT_AB` | Answers of an Aussage without Bezug come via the direct path only if their own raw similarity to the query reaches this value (otherwise a short answer to the unrelated Aussage stood there as best answer, 0.83 on production 0.9.2). `1.01` turns the exception off | `0.86` |
| `SEMANTIC_SEARCH_SUCHE_INHALTSTOR` | Inhaltstor (`services/search/inhaltstor.py`): for a query of three words or more, a hit in the uncertain band counts only if a lemma of the query's nouns and proper nouns appears in the Aussage, the contribution's title or text, or (direct path only) the Aussagen it answers. Query without nouns, keyword queries or spaCy model not loaded yet: gate open. Same model as Gegenlesen, no extra RAM; `tests/regression/SUCHTESTSET.md`, section Inhaltstor | `true` |
| `SEMANTIC_SEARCH_SUCHE_INHALTSTOR_AB` | With `…_INHALTSTOR`: lower end of the band (Aussage similarity, raw score on the direct path) | `0.82` |
| `SEMANTIC_SEARCH_SUCHE_INHALTSTOR_AUSSAGE_BIS` | With `…_INHALTSTOR`: from this Aussage similarity a statement hit counts without a shared word | `0.92` |
| `SEMANTIC_SEARCH_SUCHE_INHALTSTOR_DIREKT_BIS` | With `…_INHALTSTOR`: from this raw score a direct hit counts without a shared word | `0.90` |
| `SEMANTIC_SEARCH_APP_DATABASE_URL` | App database connection string | localhost:5433 |
| `SEMANTIC_SEARCH_LOG_LEVEL` | Logging level (DEBUG, INFO, etc.) | INFO |
| `SEMANTIC_SEARCH_KEYCLOAK_URL`, `…_KEYCLOAK_ADMIN_CLIENT_ID`, `…_KEYCLOAK_ADMIN_CLIENT_SECRET` | Keycloak admin API for redeeming Einladungen; without them Einladungen can only be managed. Set only together with the BFF switch to the new realm (`docs/KEYCLOAK_REALM.md`, order) | unset |
| `SEMANTIC_SEARCH_KEYCLOAK_REALM` | Realm the accounts are created in | `gutgesagt` |
| `SEMANTIC_SEARCH_KEYCLOAK_APP_CLIENT_ID`, `SEMANTIC_SEARCH_APP_URL` | Where the link in the "set password" mail leads afterwards | unset |

## Path Validation

At startup, the service:
1. Validates that the data path exists (required for seeding)
2. Creates metadata directory if it doesn't exist
3. For local development, attempts to find data in common locations

## Troubleshooting

### Seeding Issues

If seeding fails with "No JSON files found":
1. Check that data is mounted correctly: `docker-compose logs gutgesagt-semantic-search`
2. Verify the data path exists: `docker exec gutgesagt-semantic-search ls -la /data/seed/v1.0`
3. Check environment variables: `docker exec gutgesagt-semantic-search env | grep SEMANTIC`
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
