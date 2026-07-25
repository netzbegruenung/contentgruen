# ContentGrün Local Build & Test Commands

.PHONY: help build-frontend build-bff build-semantic-search build-all test-backend test-backend-fast test-ci clean

# Default target
help:
	@echo "ContentGrün Development Commands"
	@echo "================================="
	@echo "Build commands:"
	@echo "  build-frontend         Build frontend Docker image locally"
	@echo "  build-bff              Build BFF Docker image locally"
	@echo "  build-semantic-search  Build semantic search service Docker image locally"
	@echo "  build-all              Build all Docker images"
	@echo ""
	@echo "Test commands:"
	@echo "  test-backend           Run backend unit tests"
	@echo "  test-backend-fast      Run backend unit tests (fast, local venv)"
	@echo "  test-ci                Simulate full CI pipeline locally"
	@echo ""
	@echo "Utility commands:"
	@echo "  clean                  Remove local test images"

# Build individual services (matching the GitHub Actions build workflow)
build-frontend:
	@echo "🔨 Building frontend (matching GitHub Actions CI)..."
	cd mvp/frontend/contentgruen-frontend && \
	docker buildx build \
		--platform linux/amd64 \
		-f Dockerfile \
		-t contentgruen-frontend-local:latest \
		.

build-bff:
	@echo "🔨 Building BFF (matching GitHub Actions CI)..."
	cd mvp/backend/BFF && \
	docker buildx build \
		--platform linux/amd64 \
		-f Dockerfile \
		-t contentgruen-bff-local:latest \
		.

build-semantic-search:
	@echo "🔨 Building semantic search service (matching GitHub Actions CI)..."
	cd mvp/backend/semantic-search-service && \
	docker buildx build \
		--platform linux/amd64 \
		-f Dockerfile \
		-t contentgruen-semantic-search-local:latest \
		.

# Build all application services.
# Note: CI additionally builds the contentgruen-postgres-app and
# contentgruen-postgres-semantic images; those are not built locally.
build-all: build-frontend build-bff build-semantic-search
	@echo "✅ All services built successfully!"

# Test backend (matching the GitHub Actions test job)
test-backend:
	@echo "🧪 Running backend tests (matching GitHub Actions CI)..."
	@echo "Note: On Windows, use 'make test-backend-fast' for better performance"
	@echo "This command replicates the CI test environment (python:3.13)"
	cd mvp/backend/semantic-search-service && \
	docker run --rm \
		-v "$(CURDIR)/mvp/backend/semantic-search-service:/app" \
		-w /app \
		python:3.13 \
		/bin/bash -c "pip install -r requirements.txt && cd app && python -m pytest tests/unit/ --ignore=tests/unit/services/test_seeding_implementation.py --tb=short -v"

# Fast backend tests (for pre-commit - uses local venv)
test-backend-fast:
	@echo "⚡ Running backend tests (fast, local venv)..."
	cd mvp/backend/semantic-search-service && \
	if [ -f "./venv/Scripts/python.exe" ]; then PYTHON="./venv/Scripts/python.exe"; else PYTHON="./venv/bin/python"; fi && \
	$$PYTHON -m pytest app/tests/unit/ --ignore=app/tests/unit/services/test_seeding_implementation.py --tb=short -q

# Simulate full CI pipeline
test-ci: test-backend build-all
	@echo "🎉 Full CI simulation completed successfully!"

# Clean up local test images
clean:
	@echo "🧹 Cleaning up local test images..."
	-docker rmi contentgruen-frontend-local:latest
	-docker rmi contentgruen-bff-local:latest
	-docker rmi contentgruen-semantic-search-local:latest
	@echo "✅ Cleanup complete!"
