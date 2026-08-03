"""
Test module for the Image content service built via the content registry.
"""

import pytest
import uuid
import datetime

from domain.models.image import ImageDbEntry, ImageSearchResult
from domain.models.content_type import ContentType
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin
from domain.models.author_entry import AuthorEntry
from tests.conftest import create_base_content_fields, create_image_data


def _make_image_entry(**overrides) -> ImageDbEntry:
    """Build a minimal valid ImageDbEntry for testing."""
    now = datetime.datetime.now()
    defaults = dict(
        id=uuid.uuid4(),
        title="Test Image",
        image_url="https://example.com/test.jpg",
        text="Wind turbines against a blue sky",
        content_type=ContentType.IMAGE,
        created=now,
        last_modified=now,
        original_author="test_user",
        last_modified_by="test_user",
        authors=[AuthorEntry(name="test_user")],
        status=ContentStatus.PENDING_REVIEW,
        origin=ContentOrigin.MANUALLY_CREATED,
    )
    defaults.update(overrides)
    return ImageDbEntry(**defaults)


@pytest.mark.unit
class TestImageService:
    """Test cases for the Image content service (registry-driven)."""

    @pytest.fixture
    def service(self, test_settings, repository_factory):
        from domain.content_registry import REGISTRY, create_content_service

        spec = REGISTRY[ContentType.IMAGE]
        return create_content_service(spec, test_settings, repository_factory)

    def test_service_initialization(self, service):
        assert service is not None
        assert service.settings is not None
        assert service._repository is not None

    @pytest.mark.asyncio
    async def test_search_delegates_to_repository(
        self, service, test_embeddings_manager
    ):
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_image_data(
                text="Young activists planting trees in urban park",
                title="Urban Reforestation",
            ),
            "id": str(test_id),
            "content_type": "image",
        }
        test_embeddings_manager.add_test_data("image", [test_data])

        results = await service.search("urban park", limit=5)

        assert len(results) == 1
        assert isinstance(results[0], ImageSearchResult)
        assert results[0].text == "Young activists planting trees in urban park"
        assert results[0].title == "Urban Reforestation"

    @pytest.mark.asyncio
    async def test_search_returns_empty_when_no_match(
        self, service, test_embeddings_manager
    ):
        test_embeddings_manager.add_test_data(
            "image",
            [
                {
                    **create_base_content_fields(),
                    **create_image_data(text="Solar farm in Brandenburg"),
                    "id": str(uuid.uuid4()),
                    "content_type": "image",
                }
            ],
        )

        results = await service.search("nuclear power", limit=5)

        assert results == []

    @pytest.mark.asyncio
    async def test_get_by_id_through_service(self, service, test_embeddings_manager):
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_image_data(
                text="Solar farm in Brandenburg",
                title="Brandenburg Solar Farm",
                image_url="https://example.com/solar.jpg",
            ),
            "id": str(test_id),
            "content_type": "image",
        }
        test_embeddings_manager.add_test_data("image", [test_data])

        result = await service.get(test_id)

        assert isinstance(result, ImageDbEntry)
        assert result.id == test_id
        assert result.text == "Solar farm in Brandenburg"
        assert result.image_url == "https://example.com/solar.jpg"

    @pytest.mark.asyncio
    async def test_get_raises_for_unknown_id(self, service):
        with pytest.raises(ValueError):
            await service.get(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_add_image_with_caption_phase_a(
        self, service, test_embeddings_manager
    ):
        """Phase A: caption provided — entry is stored and retrievable."""
        entry = _make_image_entry(
            title="Wind Park Niedersachsen",
            image_url="https://example.com/wind.jpg",
            text="Wind turbines in Lower Saxony near an organic farm",
            status=ContentStatus.PENDING_REVIEW,
        )

        image_id = await service.add(entry)

        assert isinstance(image_id, uuid.UUID)
        stored = test_embeddings_manager.get_data()
        assert str(image_id) in stored
        assert (
            stored[str(image_id)]["text"]
            == "Wind turbines in Lower Saxony near an organic farm"
        )

    @pytest.mark.asyncio
    async def test_add_image_without_caption_phase_b(
        self, service, test_embeddings_manager
    ):
        """Phase B: no caption — entry stored with text=None."""
        entry = _make_image_entry(
            title="Unprocessed Image",
            image_url="https://example.com/raw.jpg",
            text=None,
            status=ContentStatus.PENDING_DESCRIPTION,
        )

        image_id = await service.add(entry)

        assert isinstance(image_id, uuid.UUID)
        stored = test_embeddings_manager.get_data()
        assert str(image_id) in stored

    @pytest.mark.asyncio
    async def test_count_through_service(self, service, test_embeddings_manager):
        test_data = []
        for i in range(4):
            test_data.append(
                {
                    **create_base_content_fields(),
                    **create_image_data(text=f"Image caption {i}", title=f"Photo {i}"),
                    "id": str(uuid.uuid4()),
                    "content_type": "image",
                }
            )
        test_embeddings_manager.add_test_data("image", test_data)

        count = await service.count()
        assert count == 4

    @pytest.mark.asyncio
    async def test_get_all_through_service(self, service, test_embeddings_manager):
        test_data = []
        for i in range(3):
            test_data.append(
                {
                    **create_base_content_fields(),
                    **create_image_data(text=f"Photo caption {i}", title=f"Photo {i}"),
                    "id": str(uuid.uuid4()),
                    "content_type": "image",
                }
            )
        test_embeddings_manager.add_test_data("image", test_data)

        results = await service.get_all(limit=10, offset=0)

        assert len(results) == 3
        assert all(isinstance(r, ImageDbEntry) for r in results)

    @pytest.mark.asyncio
    async def test_get_all_pagination(self, service, test_embeddings_manager):
        test_data = []
        for i in range(5):
            test_data.append(
                {
                    **create_base_content_fields(),
                    **create_image_data(text=f"Photo {i}", title=f"Title {i}"),
                    "id": str(uuid.uuid4()),
                    "content_type": "image",
                }
            )
        test_embeddings_manager.add_test_data("image", test_data)

        page1 = await service.get_all(limit=3, offset=0)
        page2 = await service.get_all(limit=3, offset=3)

        assert len(page1) == 3
        assert len(page2) == 2

    @pytest.mark.asyncio
    async def test_initialize_repository_returns_json_when_empty(
        self, service, test_embeddings_manager
    ):
        """Image type has no JSON seed, so DataSource.JSON is returned when empty."""
        test_embeddings_manager.clear()
        from utils.data_utils import DataSource

        result = await service.initialize_repository()
        assert result == DataSource.JSON

    @pytest.mark.asyncio
    async def test_initialize_repository_returns_storage_when_populated(
        self, service, test_embeddings_manager
    ):
        test_embeddings_manager.add_test_data(
            "image",
            [
                {
                    **create_base_content_fields(),
                    **create_image_data(),
                    "id": str(uuid.uuid4()),
                    "content_type": "image",
                }
            ],
        )
        from utils.data_utils import DataSource

        result = await service.initialize_repository()
        assert result == DataSource.STORAGE

    @pytest.mark.asyncio
    async def test_no_singleton_interference(self, test_settings):
        """Two services with separate embeddings managers must not share state."""
        from domain.content_registry import REGISTRY, create_content_service
        from repositories.implementations.qdrant.qdrant_repository_factory import (
            QdrantRepositoryFactory,
        )
        from tests.fixtures.embeddings_manager import TestEmbeddingsManager

        em1 = TestEmbeddingsManager()
        em2 = TestEmbeddingsManager()
        spec = REGISTRY[ContentType.IMAGE]
        svc1 = create_content_service(
            spec, test_settings, QdrantRepositoryFactory(embeddings_manager=em1)
        )
        svc2 = create_content_service(
            spec, test_settings, QdrantRepositoryFactory(embeddings_manager=em2)
        )

        entry = _make_image_entry(
            title="Isolation Test Image",
            text="Test image for isolation check",
        )
        image_id = await svc1.add(entry)

        with pytest.raises(ValueError):
            await svc2.get(image_id)
