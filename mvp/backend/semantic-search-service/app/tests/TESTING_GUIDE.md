# Testing Guide

## Test Structure

```
tests/
├── unit/                          # Unit tests
│   ├── api/                       # API endpoint tests (TestClient, mocked services)
│   ├── repositories/              # Repository layer tests
│   └── services/                  # Service layer tests
├── integration/                   # Integration tests against real Qdrant and PostgreSQL
│   └── api/                       # Against the running dev-stack BFF (skipped by GitHub CI)
├── fixtures/                      # Test utilities
│   └── embeddings_manager.py      # In-memory test backend
└── conftest.py                    # Shared fixtures
```

## Running Tests

### Quick Commands

```bash
# Fast unit tests (local venv)
make test-backend-fast

# Unit tests in the CI container image (python:3.13)
make test-backend

# Full CI simulation (tests + all image builds)
make test-ci
```

Or invoke pytest directly from `mvp/backend/semantic-search-service/app`:

```bash
pytest                                  # Unit tests (pytest.ini testpaths)
pytest tests/unit/path/to/test_x.py     # Specific test file
pytest -k "pattern"                     # Pattern matching
pytest tests/integration/               # Integration tests (Qdrant on :6333, PostgreSQL see below)
```

### Integration Tests as a Gate

One command runs the full check plus the integration suite, from the repository root:

```bash
bash scripts/check.sh --integration
```

It needs Qdrant (`QDRANT_URL`, default `http://localhost:6333`; `mvp/run-local.sh up`
starts it) and PostgreSQL (`POSTGRES_TEST_DATABASE_URL` or Docker for a throwaway
container, see below). If either is missing, the run aborts before the first test and
names what is missing, instead of skipping silently. The switch behind it is
`INTEGRATION_STACK_PFLICHT=1` (`tests/integration/stack.py`); a plain
`pytest tests/integration/` without it still skips when the stack is absent. The
check lives in `tests/integration/conftest.py` and only runs when `tests/integration/`
is among the paths given to pytest: `INTEGRATION_STACK_PFLICHT=1 pytest tests/` would
still skip the Qdrant tests silently. The tests in `tests/integration/api/` also need
the dev-stack BFF (`GUTGESAGT_BFF_URL`, default `http://localhost:5054`); in this mode
a missing BFF fails them, in a plain run they skip. In CI (`CI` set) they skip in this
mode too, because the pipeline starts no BFF (`stack.pflicht_ausser_in_ci`).

`tests/integration/` holds only tests that talk to a real Qdrant or PostgreSQL, or,
under `api/`, to the running BFF.
A test that mocks the services belongs in `tests/unit/api/`: `TestClient` with
`dependency_overrides` for services the router takes via `Depends`; where the router
calls the getter directly (moderation: `get_moderation_service()`), patch that name in
the router module instead, an override would not take effect. With a running stack no integration test is skipped; a new skip
needs a reason that names what is missing.

### Integration Tests Against PostgreSQL

Repositories, migrations and SQL scripts that only show their behaviour in a real
database are tested in `tests/integration/` against PostgreSQL: migrations and
`init.sql` against the model (`test_migrationen.py`), the timestamp of a
Suchereignis (`test_suchereignisse.py`), the shuffled rewrite of closed days
(`test_suchereignisse_mischen.py`), "Suchen ohne Treffer"
(`test_suchen_ohne_treffer.py`), the Rückmeldung on usage (`test_rueckmeldung_nutzung.py`),
the deletion command (`test_loeschkommando.py`), Meldungen with each Meldegrund
(`test_meldegrund.py`), Sperren with Sperrgrund and Widerspruch
(`test_sperren_postgres.py`) and the Löschfristen (`test_loeschfristen.py`, its Qdrant
part needs a running Qdrant).

```bash
# from mvp/backend/semantic-search-service/app
pytest tests/integration/test_migrationen.py tests/integration/test_suchereignisse.py \
       tests/integration/test_suchereignisse_tageszaehler.py \
       tests/integration/test_suchereignisse_mischen.py \
       tests/integration/test_suchen_ohne_treffer.py tests/integration/test_rueckmeldung_nutzung.py \
       tests/integration/test_loeschkommando.py tests/integration/test_meldegrund.py \
       tests/integration/test_sperren_postgres.py tests/integration/test_loeschfristen.py
```

- **Database:** without further setup the run starts a throwaway container with
  Docker (the base image of `mvp/backend/postgres-app/Dockerfile`, published on
  `127.0.0.1` at a free port, removed afterwards; the first run pulls the image).
  Leftovers of a hard abort carry the label `gutgesagt-itest`:
  `docker ps --filter label=gutgesagt-itest`.
  To use an existing database instead, set
  `POSTGRES_TEST_DATABASE_URL`, e.g. the dev stack:
  `postgresql+psycopg2://app_user:changeme@localhost:5433/gutgesagt_app`. It must be
  reachable, otherwise the tests fail. Without the variable and without Docker the
  tests are skipped, except in CI (`CI` set), where they fail.
- **Isolation:** every test works in its own schema (`search_path`) and drops it
  afterwards, so existing data stays untouched.
- **Writing a test:** take the `wegwerf_schema` fixture (an empty schema, see
  `tests/integration/conftest.py`), create the tables with `Base.metadata.create_all`
  or apply a migration with `postgres.migration(...)`, and hand the schema to a
  repository by patching its `get_app_database`. Helpers: `tests/integration/postgres.py`.

### Setup (One-Time)

```bash
cd mvp/backend/semantic-search-service
pip install -r requirements.txt
pre-commit install
```

### Pre-Commit Integration

Tests run automatically on commit via pre-commit hooks:
- Unit tests (186 tests in <1 second)
- Code formatting (black)
- Basic quality checks

Skip with `git commit --no-verify` (emergency only).

## Writing Tests

### Test Pattern (AAA)

```python
def test_search_returns_results(self, service, test_embeddings_manager):
    # Arrange
    test_data = {**create_base_content_fields(), "text": "test content"}
    test_embeddings_manager.add_test_data("statement", [test_data])

    # Act
    results = service.search("test")

    # Assert
    assert len(results) == 1
    assert results[0].text == "test content"
```

### Fixture Usage

```python
@pytest.fixture
def service(self, test_settings, test_embeddings_manager):
    return StatementService(test_settings, embeddings_manager=test_embeddings_manager)
```

### Content Type Data

Use data factories from `conftest.py`:
- `create_statement_data()` - Statements
- `create_commentary_data()` - Commentary
- `create_reference_data()` - References
- `create_generic_text_data()` - Generic text

When building test data manually, each content type expects specific field names:

| Content type | Expected fields |
|--------------|-----------------|
| Statement    | `text`, `title`, `party`, `author` |
| Commentary   | `text`, `title`, `short_text`, `long_text` |
| Reference    | `text`, `reference_string` (NOT `title`) |
| GenericText  | `text_snippet`, `title` |

### Service Return Patterns

- **Commentary / GenericText services**: return `(success: bool, id: UUID, message: str)`
- **Reference / Statement services**: return `UUID` directly
- **Repository methods**: return model instances or raise `ValueError`

## Test Categories

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.api` - API endpoint tests

## Architecture

### Dependency Injection

Tests use **TestEmbeddingsManager** instead of mocking:
- In-memory storage
- No external dependencies
- Realistic behavior simulation
- Fast execution

### Service Patterns

- **Repository tests**: Test data persistence and retrieval
- **Service tests**: Test business logic
- **API tests**: Test endpoint behavior

## Coverage

Coverage is **not enabled by default** — `pytest-cov` is not in `requirements.txt` and the
coverage `addopts` line in `app/pytest.ini` is commented out. To enable it:

```bash
pip install pytest-cov
# from mvp/backend/semantic-search-service/app
pytest --cov=. --cov-report=html --cov-report=term-missing
```

Coverage reports show:
- Line coverage per file
- Branch coverage
- Missing coverage areas

## Debugging

```bash
pytest --pdb           # Drop into debugger on failure
pytest -v -s           # Verbose output with prints
pytest --lf            # Run only last failed tests
pytest -x              # Stop on first failure
```

## Best Practices

### Do
- Use dependency injection fixtures
- Follow AAA pattern (Arrange, Act, Assert)
- Test both success and failure scenarios
- Use descriptive test names: `test_search_with_empty_query_returns_empty_list`
- Clean up test data (handled automatically by fixtures)

### Don't
- Mock the embeddings manager (use TestEmbeddingsManager)
- Test implementation details
- Write overly complex test setup
- Ignore test failures in CI

## Common Issues

1. **ContentType validation**: Use valid enum values (`"statement"`, not `"test_type"`)
2. **Field mapping**: Each content type expects specific fields
3. **Abstract methods**: Test classes must implement `initialize_with_initial_data()`
4. **Model validation**: Include required fields like `updated` when needed

## CI Integration

Every pull request runs `.woodpecker/ci.yaml` on Woodpecker: the same steps as
`bash scripts/check.sh --integration`, with Qdrant and PostgreSQL as services
(`POSTGRES_TEST_DATABASE_URL`, no throwaway container) and `INTEGRATION_STACK_PFLICHT=1`.
Once set up, its status `ci/woodpecker/pr/ci` is required for `main`; a red pull-request run gets a
comment with the red steps. Details, the setup steps for a person and how to run one step
locally (`check.sh --schritt <name>`): [docs/CI.md](../../../../../docs/CI.md).

After the merge, GitHub Actions on the mirror (`.github/workflows/build.yml`) run the tests
again and build the images.
