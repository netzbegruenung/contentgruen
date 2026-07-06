# Makefile for semantic search service testing

.PHONY: help test test-unit test-api test-coverage test-html test-watch clean install-test-deps

# Default target
help:
	@echo "Available commands:"
	@echo "  make test           - Run all tests"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-api       - Run API tests only"
	@echo "  make test-coverage  - Run tests with coverage report"
	@echo "  make test-html      - Run tests with HTML coverage report"
	@echo "  make test-parallel  - Run tests in parallel"
	@echo "  make test-watch     - Run tests in watch mode"
	@echo "  make test-fast      - Run fast tests only"
	@echo "  make clean          - Clean test artifacts"
	@echo "  make install-test-deps - Install test dependencies"

# Install test dependencies
install-test-deps:
	pip install -r tests/requirements.txt

# Run all tests
test:
	python -m pytest

# Run unit tests only
test-unit:
	python -m pytest -m unit

# Run API tests only
test-api:
	python -m pytest -m api

# Run tests with coverage
test-coverage:
	python -m pytest --cov=. --cov-report=term-missing

# Run tests with HTML coverage report
test-html:
	python -m pytest --cov=. --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

# Run tests in parallel
test-parallel:
	python -m pytest -n auto

# Run tests in watch mode (requires pytest-watch)
test-watch:
	pytest-watch -- --cov=. --cov-report=term-missing

# Run fast tests only
test-fast:
	python -m pytest -m "not slow"

# Run specific test file
test-file:
	@if [ -z "$(FILE)" ]; then echo "Usage: make test-file FILE=path/to/test_file.py"; exit 1; fi
	python -m pytest $(FILE) -v

# Run tests matching pattern
test-pattern:
	@if [ -z "$(PATTERN)" ]; then echo "Usage: make test-pattern PATTERN=test_name_pattern"; exit 1; fi
	python -m pytest -k "$(PATTERN)" -v

# Clean test artifacts
clean:
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Lint and format code (if tools available)
lint:
	@if command -v ruff >/dev/null 2>&1; then \
		echo "Running ruff linter..."; \
		ruff check .; \
	elif command -v flake8 >/dev/null 2>&1; then \
		echo "Running flake8..."; \
		flake8 .; \
	else \
		echo "No linter found. Install ruff or flake8."; \
	fi

# Format code (if tools available)
format:
	@if command -v black >/dev/null 2>&1; then \
		echo "Running black formatter..."; \
		black .; \
	else \
		echo "Black formatter not found. Install black."; \
	fi

# Full test suite with coverage and linting
test-full: clean lint test-coverage
	@echo "Full test suite completed!"

# Quick development test (unit tests only, fast)
test-dev:
	python -m pytest -m unit --tb=short -q

# CI/CD pipeline test command
test-ci:
	python -m pytest --cov=. --cov-report=xml --cov-report=term --junit-xml=pytest-results.xml
