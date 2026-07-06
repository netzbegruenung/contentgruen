"""
Test module for StatementService using the new dependency injection architecture.

This module demonstrates clean service testing patterns, focusing on the
architectural improvements rather than testing every service method.
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime

from services.content.statement_service import StatementService
from domain.models.statement import (
    Statement,
    StatementDbEntry,
    StatementSearchResult,
)
from domain.models.content_type import ContentType
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin
from tests.conftest import create_base_content_fields, create_statement_data


@pytest.mark.unit
class TestStatementService:
    """Test cases for StatementService demonstrating the new architecture."""

    @pytest.fixture
    def service(self, test_settings, repository_factory):
        """Create a statement service with injected repository factory."""
        return StatementService(test_settings, repository_factory=repository_factory)

    def test_service_initialization(self, service):
        """Test that service initializes correctly with dependency injection."""
        assert service is not None
        assert service._repository is not None
        assert service._content_repository is not None
        # Verify the repository is using our test embeddings manager
        assert hasattr(service._repository._shared_manager, "add_test_data")

    @pytest.mark.asyncio
    async def test_search_delegates_to_repository(
        self, service, test_embeddings_manager
    ):
        """Test that search delegates to repository correctly."""
        # Add test data directly to the test embeddings manager
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_statement_data(text="Climate policy statement"),
            "id": str(test_id),
            "content_type": "statement",
        }
        test_embeddings_manager.add_test_data("statement", [test_data])

        # Search through repository directly since service method has different signature
        results = await service._repository.search("climate policy", limit=10)

        # Assert
        assert len(results) == 1
        assert isinstance(results[0], StatementSearchResult)
        assert results[0].text == "Climate policy statement"

    @pytest.mark.asyncio
    async def test_search_statements_method(self, service, test_embeddings_manager):
        """Test the search_statements method with min_replysuggestions_count parameter."""
        # Add test data with different replysuggestions_count values
        test_data = []
        for i in range(5):
            test_id = uuid.uuid4()
            data = {
                **create_base_content_fields(),
                **create_statement_data(text=f"Statement {i} about climate"),
                "id": str(test_id),
                "content_type": "statement",
                "replysuggestions_count": i,  # 0, 1, 2, 3, 4 reply suggestions
                "replysuggestions": [
                    {
                        "id": str(uuid.uuid4()),
                        "content_type": "commentary",
                        "relevance": 0.9,
                        "created": datetime.now().isoformat(),
                        "updated": datetime.now().isoformat(),
                        "number_of_usages": 0,
                    }
                    for _ in range(i)
                ],
            }
            test_data.append(data)
        test_embeddings_manager.add_test_data("statement", test_data)

        # Test 1: Search without min_replysuggestions_count filter (default 0)
        results = await service.search_statements(
            "climate", limit=10, min_replysuggestions_count=0
        )
        assert len(results) == 5  # Should return all statements

        # Test 2: Search with min_replysuggestions_count = 2
        results = await service.search_statements(
            "climate", limit=10, min_replysuggestions_count=2
        )
        assert (
            len(results) == 3
        )  # Should return statements with 2, 3, 4 reply suggestions

        # Verify all results have at least 2 reply suggestions
        for result in results:
            assert result.replysuggestions_count >= 2

        # Test 3: Search with min_replysuggestions_count = 4
        results = await service.search_statements(
            "climate", limit=10, min_replysuggestions_count=4
        )
        assert (
            len(results) == 1
        )  # Should return only the statement with 4 reply suggestions
        assert results[0].replysuggestions_count == 4

    @pytest.mark.asyncio
    async def test_search_statements_with_limit(self, service, test_embeddings_manager):
        """Test that search_statements respects the limit parameter."""
        # Add many test statements
        test_data = []
        for i in range(20):
            test_id = uuid.uuid4()
            data = {
                **create_base_content_fields(),
                **create_statement_data(text=f"Climate action statement {i}"),
                "id": str(test_id),
                "content_type": "statement",
                "replysuggestions_count": 5,  # All have enough reply suggestions
                "replysuggestions": [],
            }
            test_data.append(data)
        test_embeddings_manager.add_test_data("statement", test_data)

        # Test with limit = 5
        results = await service.search_statements(
            "climate action", limit=5, min_replysuggestions_count=0
        )
        assert len(results) <= 5  # Should respect the limit

    @pytest.mark.asyncio
    async def test_get_by_id_through_service(self, service, test_embeddings_manager):
        """Test getting a statement by ID through the service."""
        # Add test data
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_statement_data(),
            "id": str(test_id),
            "content_type": "statement",
        }
        test_embeddings_manager.add_test_data("statement", [test_data])

        # Get through service
        result = await service.get(test_id)

        # Assert
        assert result is not None
        assert isinstance(result, StatementDbEntry)
        assert result.id == test_id
        assert result.text == "Climate change requires immediate action"

    @pytest.mark.asyncio
    async def test_repository_count_through_service(
        self, service, test_embeddings_manager
    ):
        """Test counting statements through the repository."""
        # Initially empty
        assert await service.count() == 0

        # Add test data directly to demonstrate the architecture
        test_data = [
            {
                **create_base_content_fields(),
                **create_statement_data(text=f"Statement {i}"),
                "id": str(uuid.uuid4()),
                "content_type": "statement",
            }
            for i in range(3)
        ]
        test_embeddings_manager.add_test_data("statement", test_data)

        # Count should now be 3
        assert await service.count() == 3

    def test_dependency_injection_isolation(
        self, test_settings, test_embeddings_manager
    ):
        """Test that each service instance gets its own repository instances."""
        # Create two services with the same test embeddings manager
        from repositories.implementations.qdrant.qdrant_repository_factory import (
            QdrantRepositoryFactory,
        )

        factory1 = QdrantRepositoryFactory(embeddings_manager=test_embeddings_manager)
        factory2 = QdrantRepositoryFactory(embeddings_manager=test_embeddings_manager)

        service1 = StatementService(test_settings, repository_factory=factory1)
        service2 = StatementService(test_settings, repository_factory=factory2)

        # They should have different repository instances
        assert service1._repository is not service2._repository

        # But they share the same embeddings manager (which is what we want for testing)
        assert (
            service1._repository._shared_manager is service2._repository._shared_manager
        )

    @pytest.mark.asyncio
    async def test_no_singleton_interference(self, service, test_embeddings_manager):
        """Test that the singleton doesn't interfere with our test embeddings manager."""
        # Add data through our test embeddings manager
        test_data = {
            **create_base_content_fields(),
            **create_statement_data(text="Test isolation"),
            "id": str(uuid.uuid4()),
            "content_type": "statement",
        }
        test_embeddings_manager.add_test_data("statement", [test_data])

        # Verify we can find it
        results = await service._repository.search("test isolation", limit=10)
        assert len(results) == 1

        # Clear the test data
        test_embeddings_manager.clear()

        # Verify it's gone
        results = await service._repository.search("test isolation", limit=10)
        assert len(results) == 0

        # And the count is zero
        assert await service.count() == 0
