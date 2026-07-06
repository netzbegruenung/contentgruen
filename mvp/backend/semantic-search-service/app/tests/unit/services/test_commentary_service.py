"""
Test module for CommentaryService using the new dependency injection architecture.

This module demonstrates clean testing patterns without complex mocking.
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime

from domain.models.commentary import (
    Commentary,
    CommentaryDbEntry,
    CommentarySearchResult,
)
from domain.models.content_type import ContentType
from tests.conftest import create_base_content_fields, create_commentary_data


@pytest.mark.unit
class TestCommentaryService:
    """Test cases for CommentaryService."""

    @pytest.fixture
    def service(self, test_settings, repository_factory):
        """Create a commentary service with injected repository factory."""
        from services.content.commentary_service import CommentaryService

        return CommentaryService(test_settings, repository_factory)

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
            **create_commentary_data(
                text="Climate policy analysis shows urgent action needed",
                title="Climate Policy Analysis",
            ),
            "id": str(test_id),
            "content_type": "commentary",
        }
        test_embeddings_manager.add_test_data("commentary", [test_data])

        # Search through service
        results = await service.search("climate policy", limit=5)

        # Assert
        assert len(results) == 1
        assert isinstance(results[0], CommentarySearchResult)
        assert results[0].text == "Climate policy analysis shows urgent action needed"
        assert results[0].title == "Climate Policy Analysis"

    @pytest.mark.asyncio
    async def test_get_by_id_through_service(self, service, test_embeddings_manager):
        """Test getting item by ID through service layer."""
        # Add test data
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_commentary_data(
                text="Detailed environmental commentary", title="Environmental Analysis"
            ),
            "id": str(test_id),
            "content_type": "commentary",
        }
        test_embeddings_manager.add_test_data("commentary", [test_data])

        # Get through service
        result = await service.get(test_id)

        # Assert
        assert isinstance(result, CommentaryDbEntry)
        assert result.id == test_id
        assert result.text == "Detailed environmental commentary"
        assert result.title == "Environmental Analysis"

    @pytest.mark.asyncio
    async def test_add_commentary(self, service, test_embeddings_manager):
        """Test adding a new commentary through service."""
        # Create new commentary
        new_commentary = Commentary(
            text="New climate change commentary with insights",
            title="Climate Insights",
            short_text="Climate insights",
            long_text="New climate change commentary with insights",
            references=[],
        )

        # Add through service
        from domain.models.content_status import ContentStatus
        from domain.models.content_origin import ContentOrigin

        success, result_id, message = await service.add_commentary(
            new_commentary,
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
            == "New climate change commentary with insights"
        )
        assert stored_data[str(result_id)]["title"] == "Climate Insights"

    @pytest.mark.asyncio
    async def test_update_commentary(self, service, test_embeddings_manager):
        """Test updating an existing commentary."""
        # Add existing commentary
        test_id = uuid.uuid4()
        existing_data = {
            **create_base_content_fields(),
            **create_commentary_data(
                text="Original commentary text", title="Original Title"
            ),
            "id": str(test_id),
            "content_type": "commentary",
        }
        test_embeddings_manager.add_test_data("commentary", [existing_data])

        # Update commentary
        updated_commentary = Commentary(
            text="Updated commentary with new insights",
            title="Updated Title",
            short_text="Updated insights",
            long_text="Updated commentary with new insights",
            references=[],
        )

        from domain.models.content_status import ContentStatus
        from domain.models.content_origin import ContentOrigin

        # Use add_commentary with existing ID to update
        success, result_id, message = await service.add_commentary(
            updated_commentary,
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
        assert updated.text == "Updated commentary with new insights"
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
                    **create_commentary_data(text=f"Commentary {i}"),
                    "id": str(uuid.uuid4()),
                    "content_type": "commentary",
                }
            )
        test_embeddings_manager.add_test_data("commentary", test_data)

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
                    **create_commentary_data(
                        text=f"Commentary {i}", title=f"Title {i}"
                    ),
                    "id": str(uuid.uuid4()),
                    "content_type": "commentary",
                }
            )
        test_embeddings_manager.add_test_data("commentary", test_data)

        # Get all through service
        results = await service.get_all(limit=10, offset=0)

        assert len(results) == 2
        assert all(isinstance(r, CommentaryDbEntry) for r in results)
        assert results[0].title == "Title 0"
        assert results[1].title == "Title 1"

    @pytest.mark.asyncio
    async def test_initialize_repository_with_existing_content(
        self, service, test_embeddings_manager
    ):
        """Test repository initialization when content exists."""
        # Add existing content
        test_embeddings_manager.add_test_data(
            "commentary",
            [
                {
                    **create_base_content_fields(),
                    **create_commentary_data(),
                    "id": str(uuid.uuid4()),
                    "content_type": "commentary",
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
        from services.content.commentary_service import CommentaryService
        from repositories.implementations.qdrant.qdrant_repository_factory import (
            QdrantRepositoryFactory,
        )
        from domain.models.content_status import ContentStatus
        from domain.models.content_origin import ContentOrigin

        # Create two separate factory instances with same embeddings manager
        factory1 = QdrantRepositoryFactory(embeddings_manager=test_embeddings_manager)
        factory2 = QdrantRepositoryFactory(embeddings_manager=test_embeddings_manager)

        # Create two service instances
        service1 = CommentaryService(test_settings, factory1)
        service2 = CommentaryService(test_settings, factory2)

        # Add data through service1
        commentary1 = Commentary(
            text="Service 1 commentary",
            title="Service 1 Title",
            short_text="Service 1",
            long_text="Service 1 commentary",
            references=[],
        )
        success, id1, message = await service1.add_commentary(
            commentary1,
            author="test_user",
            status=ContentStatus.APPROVED,
            origin=ContentOrigin.MANUALLY_CREATED,
        )

        # Both services should see the same data (shared embeddings)
        result = await service2.get(id1)
        assert result.text == "Service 1 commentary"

    @pytest.mark.asyncio
    async def test_no_singleton_interference(self, test_settings):
        """Test that service doesn't interfere with singleton state."""
        from services.content.commentary_service import CommentaryService
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

        service1 = CommentaryService(test_settings, factory1)
        service2 = CommentaryService(test_settings, factory2)

        # Add data to service1
        commentary = Commentary(
            text="Isolated commentary",
            title="Isolated Title",
            short_text="Isolated",
            long_text="Isolated commentary",
            references=[],
        )
        success, id1, message = await service1.add_commentary(
            commentary,
            author="test_user",
            status=ContentStatus.APPROVED,
            origin=ContentOrigin.MANUALLY_CREATED,
        )

        # Service2 should NOT see this data (different embeddings managers)
        with pytest.raises(ValueError):
            await service2.get(id1)
