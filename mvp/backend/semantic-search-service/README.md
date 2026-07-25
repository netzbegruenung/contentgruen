# Semantic Search Service

## Repository Design

We use a repository pattern approach with individual repositories per content type and additional aggregated repositories as required.
As of now we have one shared content repository containing all content types as the only aggregated repository.

The service uses PostgreSQL with pgvector for unified content storage and semantic search capabilities.

Entities are modeled as pydantic models in app/index_managers/models

## Development Setup

### Prerequisites

1. Python 3.12+ installed
2. **Windows only**: Visual Studio 2022 Build Tools with C++ components (see below)
3. Virtual environment set up with all dependencies:
```bash
cd mvp/backend/semantic-search-service
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

#### Windows Build Requirements

For Python 3.12 on Windows, some packages (annoy, hnswlib) require compilation. Install:
- [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
- Select: **MSVC v143 - C++ Buildtools für x64/86 in VS 2022**
- Select: **Windows 10/11 SDK** (latest version)

**Note**: This requires ~5GB disk space. Linux/Mac/Docker users don't need these tools.

### Running Tests

The project includes comprehensive unit and integration tests. Tests can be run in multiple ways:

#### Using pytest directly:
```bash
cd app
pytest                          # Run all tests
pytest tests/unit/              # Run only unit tests
pytest tests/integration/       # Run only integration tests
pytest -v                       # Verbose output
pytest --cov=.                  # With coverage report
```

#### Using the test runner script:
```bash
cd app
python run_tests.py             # Run all tests
python run_tests.py --unit      # Run only unit tests
python run_tests.py --api       # Run only API tests
python run_tests.py --coverage  # Run with coverage report
python run_tests.py --html      # Generate HTML coverage report
python run_tests.py --parallel  # Run tests in parallel
```

### Code Quality

#### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality. These run automatically on every commit:
- Unit tests for the semantic search service
- Python code formatting with Black
- File hygiene checks (trailing whitespace, end-of-file, YAML validation)

To set up pre-commit hooks:
```bash
# Install pre-commit globally
pip install --user pre-commit

# From project root, install the hooks
cd ../../..  # Navigate to project root
pre-commit install
```

#### Code Formatting

The project uses Black for consistent Python formatting:
```bash
cd app
black .                         # Format all Python files
black --check .                 # Check formatting without changes
black --diff .                  # Show what would change
```

### Testing Guidelines

- All new features should include corresponding tests
- Maintain test coverage above 70%
- Use meaningful test names: `test_method_name_scenario`
- Mock external dependencies in unit tests
- Test both positive and negative cases

For more details on testing architecture and patterns, see:
- `app/tests/README.md` - Testing overview
- `app/tests/TESTING_GUIDE.md` - Detailed testing guide
