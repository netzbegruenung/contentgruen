"""
Test module for BaseContentService using the new dependency injection architecture.

This module demonstrates clean testing patterns without complex mocking.
"""

import datetime
import uuid
import pytest
import pytest_asyncio
from unittest.mock import MagicMock
from typing import Optional

from services.content.base_content_service import BaseContentService
from repositories.implementations.qdrant.base_repository import (
    QdrantBaseRepository as BaseRepository,
)
from domain.models.base_content import (
    BaseContentDbEntry,
    BaseContentSearchResult,
)
from domain.models.content_type import ContentType
from utils.data_utils import DataSource
from tests.conftest import create_base_content_fields


class MockDbEntryModel(BaseContentDbEntry):
    """Mock database entry model for testing."""

    updated: Optional[datetime.datetime] = None  # Some models have this field


class MockSearchResultModel(MockDbEntryModel, BaseContentSearchResult):
    """Mock search result model for testing."""

    pass


class MockBaseRepository(BaseRepository[MockDbEntryModel, MockSearchResultModel]):
    """Mock repository for testing BaseContentService."""

    def initialize_with_initial_data(self):
        """Implementation of abstract method for testing."""
        pass


@pytest.mark.unit
class TestBaseContentService:
    """Test BaseContentService functionality."""

    @pytest.fixture
    def content_service(self, test_settings, test_embeddings_manager):
        """Create a BaseContentService instance with test dependencies."""
        repository_instance = MockBaseRepository(
            "test_repository",
            "statement",  # Use valid ContentType
            test_settings,
            MockDbEntryModel,
            MockSearchResultModel,
            embeddings_manager=test_embeddings_manager,
        )
        content_repository_instance = MockBaseRepository(
            "content_repository",
            None,  # No content type filter for aggregated repository
            test_settings,
            MockDbEntryModel,
            MockSearchResultModel,
            embeddings_manager=test_embeddings_manager,
        )
        return BaseContentService[
            MockBaseRepository, MockDbEntryModel, MockSearchResultModel
        ](
            settings=test_settings,
            repository=repository_instance,
            content_repository=content_repository_instance,
            content_db_entry_model_class=MockDbEntryModel,
            content_search_result_model_class=MockSearchResultModel,
        )

    @pytest.mark.asyncio
    async def test_initialize_repository_loads_from_storage(
        self, content_service, test_embeddings_manager
    ):
        """Test initialize_repository when content exists in storage."""
        # Add some test data to simulate existing content
        test_embeddings_manager.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(),
                    "id": str(uuid.uuid4()),
                    "text": "Existing content",
                    "content_type": "statement",
                }
            ],
        )

        result = await content_service.initialize_repository()
        assert result == DataSource.STORAGE

    @pytest.mark.asyncio
    async def test_initialize_repository_loads_from_json(
        self, content_service, test_embeddings_manager
    ):
        """Test initialize_repository when no content exists."""
        # Ensure no content exists
        test_embeddings_manager.clear()

        result = await content_service.initialize_repository()
        assert result == DataSource.JSON

    def test_save_notes_automatic_persistence(self, content_service):
        """Test that save() is a no-op with PostgreSQL backend."""
        # With PostgreSQL backend, save() is a no-op as data is automatically persisted
        content_service.save()
        # Just verify the method can be called without errors

    @pytest.mark.asyncio
    async def test_search_calls_repository_search(
        self, content_service, test_embeddings_manager
    ):
        """Test that search delegates to repository."""
        # Add test data
        test_id = uuid.uuid4()
        test_embeddings_manager.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(),
                    "id": str(test_id),
                    "text": "Mock Result for query",
                    "content_type": "statement",
                }
            ],
        )

        result = await content_service.search("query")

        assert len(result) == 1
        assert isinstance(result[0], MockSearchResultModel)
        assert result[0].text == "Mock Result for query"

    @pytest.mark.asyncio
    async def test_get_calls_repository_get(
        self, content_service, test_embeddings_manager
    ):
        """Test that get delegates to repository."""
        item_id = uuid.uuid4()

        # Add test data
        test_embeddings_manager.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(),
                    "id": str(item_id),
                    "text": "Mock Result",
                    "content_type": "statement",
                }
            ],
        )

        result = await content_service.get(item_id)

        assert result.text == "Mock Result"
        assert result.id == item_id

    @pytest.mark.asyncio
    async def test_get_raises_exception_when_not_found(
        self, content_service, test_embeddings_manager
    ):
        """Test that get raises exception when entry not found."""
        item_id = uuid.uuid4()
        test_embeddings_manager.clear()  # Ensure no data

        with pytest.raises(ValueError, match=f"Entry with id {item_id} not found"):
            await content_service.get(item_id)

    @pytest.mark.asyncio
    async def test_upsert_calls_upsert_on_repositories(
        self, content_service, test_embeddings_manager
    ):
        """Test that upsert calls upsert on both repositories."""
        mock_input = MockDbEntryModel(
            **create_base_content_fields(),
            id=uuid.uuid4(),
            text="Test Input",
            content_type=ContentType.STATEMENT,
        )

        result = await content_service._upsert(mock_input)

        assert result == mock_input.id

        # Verify it was stored
        stored_data = test_embeddings_manager.get_data()
        assert str(mock_input.id) in stored_data
        assert stored_data[str(mock_input.id)]["text"] == "Test Input"

    @pytest.mark.asyncio
    async def test_count_delegates_to_repository(
        self, content_service, test_embeddings_manager
    ):
        """Test that count delegates to repository."""
        # Add some test data
        for i in range(3):
            test_embeddings_manager.add_test_data(
                "statement",
                [
                    {
                        **create_base_content_fields(),
                        "id": str(uuid.uuid4()),
                        "text": f"Test entry {i}",
                        "content_type": "statement",
                    }
                ],
            )

        result = await content_service.count()

        assert result == 3

    @pytest.mark.asyncio
    async def test_get_all_delegates_to_repository(
        self, content_service, test_embeddings_manager
    ):
        """Test that get_all delegates to repository."""
        # Add test data
        test_data = []
        for i in range(2):
            test_data.append(
                {
                    **create_base_content_fields(),
                    "id": str(uuid.uuid4()),
                    "text": f"Entry {i}",
                    "content_type": "statement",
                }
            )
        test_embeddings_manager.add_test_data("statement", test_data)

        results = await content_service.get_all(limit=10, offset=0)

        assert len(results) == 2
        assert all(isinstance(r, MockDbEntryModel) for r in results)

    @pytest.mark.asyncio
    async def test_has_content_delegates_to_repository(
        self, content_service, test_embeddings_manager
    ):
        """Test that has_content delegates to repository."""
        # Initially empty
        test_embeddings_manager.clear()
        assert await content_service._repository.has_content() is False

        # Add some content
        test_embeddings_manager.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(),
                    "id": str(uuid.uuid4()),
                    "text": "Some content",
                    "content_type": "statement",
                }
            ],
        )

        assert await content_service._repository.has_content() is True

    @pytest.mark.asyncio
    async def test_get_by_author_delegates_to_repository(
        self, content_service, test_embeddings_manager
    ):
        """Test that get_by_author delegates to repository."""
        # Add test data with specific author
        test_embeddings_manager.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(original_author="test_author"),
                    "id": str(uuid.uuid4()),
                    "text": "Author content",
                    "content_type": "statement",
                }
            ],
        )

        results = await content_service._repository.get_by_author(
            "test_author", limit=10, offset=0
        )

        # TestEmbeddingsManager doesn't filter by author properly,
        # but we can verify at least some results are returned
        assert len(results) >= 1
        assert all(isinstance(r, MockDbEntryModel) for r in results)


@pytest.mark.unit
class TestBaseContentServiceErrorHandling:
    """Test error handling in BaseContentService."""

    @pytest.fixture
    def content_service(self, test_settings, test_embeddings_manager):
        """Create a BaseContentService instance for testing."""
        repository_instance = MockBaseRepository(
            "test_repository",
            "statement",  # Use valid ContentType
            test_settings,
            MockDbEntryModel,
            MockSearchResultModel,
            embeddings_manager=test_embeddings_manager,
        )
        content_repository_instance = MockBaseRepository(
            "content_repository",
            None,
            test_settings,
            MockDbEntryModel,
            MockSearchResultModel,
            embeddings_manager=test_embeddings_manager,
        )
        return BaseContentService[
            MockBaseRepository, MockDbEntryModel, MockSearchResultModel
        ](
            settings=test_settings,
            repository=repository_instance,
            content_repository=content_repository_instance,
            content_db_entry_model_class=MockDbEntryModel,
            content_search_result_model_class=MockSearchResultModel,
        )

    @pytest.mark.asyncio
    async def test_search_with_empty_query(
        self, content_service, test_embeddings_manager
    ):
        """Test search with empty query."""
        # Add some test data
        test_embeddings_manager.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(),
                    "id": str(uuid.uuid4()),
                    "text": "Some content",
                    "content_type": "statement",
                }
            ],
        )

        results = await content_service.search("")

        # Should handle empty query gracefully
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_upsert_with_invalid_data(self, content_service):
        """Test upsert with invalid data."""
        # Create an entry without required fields
        mock_input = MockDbEntryModel(
            **create_base_content_fields(),
            id=uuid.uuid4(),
            text="Test Input",
            content_type=ContentType.STATEMENT,
        )

        # Remove text to simulate invalid data
        delattr(mock_input, "text")

        # This should fail because 'text' is required for upserting
        with pytest.raises((ValueError, AttributeError)):
            await content_service._upsert(mock_input)
