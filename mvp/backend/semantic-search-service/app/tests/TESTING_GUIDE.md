# Testing Guide

## Test Structure

```
tests/
├── unit/                          # Unit tests
│   ├── repositories/              # Repository layer tests
│   └── services/                  # Service layer tests
├── integration/                   # Integration tests
│   └── api/v1/                    # API endpoint tests
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

### Integration Tests Against PostgreSQL

Repositories, migrations and SQL scripts that only show their behaviour in a real
database are tested in `tests/integration/` against PostgreSQL: migrations
(`test_migrationen.py`), the timestamp of a Suchereignis (`test_suchereignisse.py`),
"Suchen ohne Treffer" (`test_suchen_ohne_treffer.py`) and the deletion command
(`test_loeschkommando.py`).

```bash
# from mvp/backend/semantic-search-service/app
pytest tests/integration/test_migrationen.py tests/integration/test_suchereignisse.py \
       tests/integration/test_suchereignisse_tageszaehler.py \
       tests/integration/test_suchen_ohne_treffer.py tests/integration/test_loeschkommando.py
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

Tests run automatically in GitHub Actions (`.github/workflows/build.yml`) on:
- Push to the `main` branch
- Pull request creation/updates
- Manual dispatch (`workflow_dispatch`)

The `test` job includes:
- Dependency installation (Python 3.13)
- Unit test execution
- Integration test execution against a Qdrant service container
- JUnit report generation (uploaded as artifacts)
- Blocking image builds on failures
