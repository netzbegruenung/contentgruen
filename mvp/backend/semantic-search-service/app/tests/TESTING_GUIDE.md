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
make test-dev           # Fast unit tests (recommended)
make test-full          # Full suite with coverage
make test-html          # HTML coverage report
make test-watch         # Watch mode for TDD
make test-file FILE=... # Specific test file
make test-pattern PATTERN=... # Pattern matching
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

```bash
make test-html    # Generate HTML report
make test-coverage # Terminal coverage report
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

Tests run automatically in Woodpecker CI on:
- Push to main branch
- Pull request creation/updates
- Manual pipeline execution

Pipeline includes:
- Dependency installation
- Unit test execution
- JUnit report generation
- Automatic PR blocking on failures
