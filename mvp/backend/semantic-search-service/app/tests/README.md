# Test Suite

Clean, fast test suite with dependency injection architecture. **186 tests pass in <1 second**.

## Quick Start

```bash
# Install dependencies and setup
cd mvp/backend/semantic-search-service
pip install -r requirements.txt
pre-commit install

# Verify setup
make test-dev
```

## Daily Workflow

```bash
# Quick verification (most common)
make test-dev

# Full validation (before commits)
make test-full

# Test-driven development
make test-watch

# Commit (tests run automatically)
git commit -m "Changes"
```

## Test Commands

```bash
make test-dev           # Fast unit tests
make test-full          # Tests + coverage + linting
make test-html          # HTML coverage report
make test-file FILE=... # Specific test file
make test-pattern PATTERN=... # Pattern matching
make clean              # Clean artifacts
make help               # All commands
```

## Documentation

- **[TESTING_GUIDE.md](./TESTING_GUIDE.md)** - Writing and running tests
- **[ARCHITECTURE_GUIDE.md](./ARCHITECTURE_GUIDE.md)** - System architecture

## Status

- ✅ **186/186 unit tests passing**
- ✅ **Dependency injection architecture**
- ✅ **Pre-commit hooks integrated**
- ✅ **Woodpecker CI automated**
- ✅ **No external test dependencies**

## Legacy Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test category
pytest -m unit
```

## 🏗️ Test Structure

```
tests/
├── conftest.py                    # Shared fixtures and configuration
├── fixtures/                      # Test utilities
│   └── test_embeddings_manager.py # In-memory embeddings for testing
├── unit/                          # Unit tests
│   ├── repositories/              # Repository layer tests
│   └── services/                  # Service layer tests
└── integration/                   # Integration tests
    └── api/v1/                    # API endpoint tests
```

## 🔑 Key Features

- **Dependency Injection**: Clean test isolation without complex mocking
- **In-Memory Testing**: Fast execution with TestEmbeddingsManager
- **Comprehensive Fixtures**: Well-organized test utilities in conftest.py
- **Clear Patterns**: Consistent test structure across all components
- **100% Pass Rate**: Example tests demonstrate the patterns

## 📈 Current Status

- ✅ Architecture refactored for testability
- ✅ Dependency injection implemented
- ✅ Example tests passing (16/16)
- ✅ Documentation consolidated
- 📝 Full test coverage in progress

## 🤝 Contributing

1. Read the [TESTING_GUIDE.md](./TESTING_GUIDE.md) for test writing guidelines
2. Follow patterns from existing tests
3. Use provided fixtures from conftest.py
4. Keep tests simple and focused
5. Document any new patterns

## ⚡ Performance

After architectural improvements:
- Test execution: ~3 seconds (was ~45 seconds)
- No flaky tests
- Parallel execution supported
- Minimal mocking overhead

## 📞 Support

For questions or issues:
1. Check the documentation guides
2. Review existing test examples
3. Consult [LESSONS_LEARNED.md](./LESSONS_LEARNED.md) for common pitfalls
4. Create an issue with a minimal reproducible example

---

*This test suite demonstrates best practices for testing Python applications with complex dependencies. The architectural patterns and testing strategies can be applied to other projects facing similar challenges.*
