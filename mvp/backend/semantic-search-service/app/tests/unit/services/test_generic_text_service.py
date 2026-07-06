"""
Test module for GenericTextService using the new dependency injection architecture.

This module demonstrates clean testing patterns without complex mocking.
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime

from domain.models.generic_text import (
    GenericText,
    GenericTextDbEntry,
    GenericTextSearchResult,
)
from domain.models.content_type import ContentType
from tests.conftest import create_base_content_fields, create_generic_text_data


@pytest.mark.unit
class TestGenericTextService:
    """Test cases for GenericTextService."""

    @pytest.fixture
    def service(self, test_settings, repository_factory):
        """Create a generic text service with injected repository factory."""
        from services.content.generic_text_service import GenericTextService

        return GenericTextService(test_settings, repository_factory)

    def test_service_initialization(self, service):
        """Test that service initializes correctly."""
        assert service is not None
        assert service.settings is not None
        assert service._repository is not None
        assert service._content_repository is not None

    @pytest.mark.asyncio
    async def test_search_delegates_to_repository(
        self, service, test_embeddings_manager
    ):
        """Test search delegates to repository with correct parameters."""
        # Add test data
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_generic_text_data(
                text="Comprehensive guide to sustainable living practices",
                title="Sustainable Living Guide",
            ),
            "id": str(test_id),
            "content_type": "generic_text",
        }
        test_embeddings_manager.add_test_data("generic_text", [test_data])

        # Search through service
        results = await service.search("sustainable", limit=5)

        # Assert
        assert len(results) == 1
        assert isinstance(results[0], GenericTextSearchResult)
        assert results[0].text == "Comprehensive guide to sustainable living practices"
        assert results[0].title == "Sustainable Living Guide"

    @pytest.mark.asyncio
    async def test_get_by_id_through_service(self, service, test_embeddings_manager):
        """Test getting item by ID through service layer."""
        # Add test data
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_generic_text_data(
                text="Detailed environmental policy overview",
                title="Environmental Policy",
            ),
            "id": str(test_id),
            "content_type": "generic_text",
        }
        test_embeddings_manager.add_test_data("generic_text", [test_data])

        # Get through service
        result = await service.get(test_id)

        # Assert
        assert isinstance(result, GenericTextDbEntry)
        assert result.id == test_id
        assert result.text == "Detailed environmental policy overview"
        assert result.title == "Environmental Policy"

    @pytest.mark.asyncio
    async def test_add_generic_text(self, service, test_embeddings_manager):
        """Test adding a new generic text through service."""
        # Create new generic text
        new_generic_text = GenericText(
            text="New climate change information with insights",
            title="Climate Change Insights",
            references=[],
        )

        # Add through service
        from domain.models.content_status import ContentStatus
        from domain.models.content_origin import ContentOrigin

        success, result_id, text = await service.add_generic_text(
            new_generic_text,
            author="test_user",
            status=ContentStatus.APPROVED,
            origin=ContentOrigin.MANUALLY_CREATED,
        )

        # Verify it was created
        assert success is True
        assert isinstance(result_id, uuid.UUID)

        # Check it's in the data store
        stored_data = test_embeddings_manager.get_data()
        assert str(result_id) in stored_data
        assert (
            stored_data[str(result_id)]["text"]
            == "New climate change information with insights"
        )
        assert stored_data[str(result_id)]["title"] == "Climate Change Insights"

    @pytest.mark.asyncio
    async def test_update_generic_text(self, service, test_embeddings_manager):
        """Test updating an existing generic text."""
        # Add existing generic text
        test_id = uuid.uuid4()
        existing_data = {
            **create_base_content_fields(),
            **create_generic_text_data(
                text="Original generic text",
                title="Original Title",
            ),
            "id": str(test_id),
            "content_type": "generic_text",
        }
        test_embeddings_manager.add_test_data("generic_text", [existing_data])

        # Update generic text
        updated_generic_text = GenericText(
            text="Updated generic text with new insights",
            title="Updated Title",
            references=[],
        )

        from domain.models.content_status import ContentStatus
        from domain.models.content_origin import ContentOrigin

        # Use add_generic_text with existing ID to update
        success, result_id, text = await service.add_generic_text(
            updated_generic_text,
            author="test_user",
            status=ContentStatus.APPROVED,
            origin=ContentOrigin.MANUALLY_CREATED,
            id=test_id,
        )

        # Verify update
        assert success is True
        assert result_id == test_id

        # Get updated item
        updated = await service.get(test_id)
        assert updated.text == "Updated generic text with new insights"
        assert updated.title == "Updated Title"

    @pytest.mark.asyncio
    async def test_repository_count_through_service(
        self, service, test_embeddings_manager
    ):
        """Test counting items through service layer."""
        # Add test data
        test_data = []
        for i in range(3):
            test_data.append(
                {
                    **create_base_content_fields(),
                    **create_generic_text_data(
                        text=f"Generic text {i}",
                        title=f"Title {i}",
                    ),
                    "id": str(uuid.uuid4()),
                    "content_type": "generic_text",
                }
            )
        test_embeddings_manager.add_test_data("generic_text", test_data)

        # Count through service
        count = await service.count()

        assert count == 3

    @pytest.mark.asyncio
    async def test_get_all_through_service(self, service, test_embeddings_manager):
        """Test getting all items through service layer."""
        # Add test data
        test_data = []
        for i in range(2):
            test_data.append(
                {
                    **create_base_content_fields(),
                    **create_generic_text_data(
                        text=f"Generic text {i}",
                        title=f"Title {i}",
                    ),
                    "id": str(uuid.uuid4()),
                    "content_type": "generic_text",
                }
            )
        test_embeddings_manager.add_test_data("generic_text", test_data)

        # Get all through service
        results = await service.get_all(limit=10, offset=0)

        assert len(results) == 2
        assert all(isinstance(r, GenericTextDbEntry) for r in results)
        assert results[0].title == "Title 0"
        assert results[1].title == "Title 1"

    @pytest.mark.asyncio
    async def test_initialize_repository_with_existing_content(
        self, service, test_embeddings_manager
    ):
        """Test repository initialization when content exists."""
        # Add existing content
        test_embeddings_manager.add_test_data(
            "generic_text",
            [
                {
                    **create_base_content_fields(),
                    **create_generic_text_data(),
                    "id": str(uuid.uuid4()),
                    "content_type": "generic_text",
                }
            ],
        )

        # Initialize repository
        from utils.data_utils import DataSource

        result = await service.initialize_repository()

        # Should return STORAGE since content exists
        assert result == DataSource.STORAGE

    @pytest.mark.asyncio
    async def test_initialize_repository_without_content(
        self, service, test_embeddings_manager
    ):
        """Test repository initialization when no content exists."""
        # Ensure no content
        test_embeddings_manager.clear()

        # Mock the initialize_with_initial_data method
        service._repository.initialize_with_initial_data = lambda: None

        # Initialize repository
        from utils.data_utils import DataSource

        result = await service.initialize_repository()

        # Should return JSON since no content exists
        assert result == DataSource.JSON

    def test_save_is_noop(self, service):
        """Test that save operation is a no-op with PostgreSQL backend."""
        # Should not raise any exceptions
        service.save()

    @pytest.mark.asyncio
    async def test_dependency_injection_isolation(
        self, test_settings, test_embeddings_manager
    ):
        """Test that each service instance has isolated dependencies."""
        from services.content.generic_text_service import GenericTextService
        from repositories.implementations.qdrant.qdrant_repository_factory import (
            QdrantRepositoryFactory,
        )

        # Create two separate factory instances with same embeddings manager
        factory1 = QdrantRepositoryFactory(embeddings_manager=test_embeddings_manager)
        factory2 = QdrantRepositoryFactory(embeddings_manager=test_embeddings_manager)

        # Create two service instances
        service1 = GenericTextService(test_settings, factory1)
        service2 = GenericTextService(test_settings, factory2)

        # Add data through service1
        generic_text1 = GenericText(
            text="Service 1 generic text",
            title="Service 1 Title",
            references=[],
        )

        from domain.models.content_status import ContentStatus
        from domain.models.content_origin import ContentOrigin

        success, id1, text = await service1.add_generic_text(
            generic_text1,
            author="test_user",
            status=ContentStatus.APPROVED,
            origin=ContentOrigin.MANUALLY_CREATED,
        )

        # Both services should see the same data (shared embeddings)
        result = await service2.get(id1)
        assert result.text == "Service 1 generic text"

    @pytest.mark.asyncio
    async def test_no_singleton_interference(self, test_settings):
        """Test that service doesn't interfere with singleton state."""
        from services.content.generic_text_service import GenericTextService
        from repositories.implementations.qdrant.qdrant_repository_factory import (
            QdrantRepositoryFactory,
        )
        from tests.fixtures.test_embeddings_manager import TestEmbeddingsManager
        from domain.models.content_status import ContentStatus
        from domain.models.content_origin import ContentOrigin

        # Create separate test embeddings managers
        embeddings1 = TestEmbeddingsManager()
        embeddings2 = TestEmbeddingsManager()

        factory1 = QdrantRepositoryFactory(embeddings_manager=embeddings1)
        factory2 = QdrantRepositoryFactory(embeddings_manager=embeddings2)

        service1 = GenericTextService(test_settings, factory1)
        service2 = GenericTextService(test_settings, factory2)

        # Add data to service1
        generic_text = GenericText(
            text="Isolated generic text",
            title="Isolated Title",
            references=[],
        )
        success, id1, text = await service1.add_generic_text(
            generic_text,
            author="test_user",
            status=ContentStatus.APPROVED,
            origin=ContentOrigin.MANUALLY_CREATED,
        )

        # Service2 should NOT see this data (different embeddings managers)
        with pytest.raises(ValueError):
            await service2.get(id1)
