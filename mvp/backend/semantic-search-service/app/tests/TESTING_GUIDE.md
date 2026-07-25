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
│   └── test_embeddings_manager.py # In-memory test backend
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
pytest tests/integration/               # Integration tests (needs Qdrant on :6333)
```

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
