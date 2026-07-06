"""
Test module for RegistryQdrantRepository used by the Image content type.
"""

import pytest
import uuid

from domain.models.image import ImageDbEntry, ImageSearchResult
from domain.models.content_type import ContentType
from tests.conftest import create_base_content_fields, create_image_data


@pytest.mark.unit
class TestImageRepository:
    """Test cases for the image RegistryQdrantRepository."""

    @pytest.fixture
    def repository(self, test_settings, test_embeddings_manager):
        from repositories.implementations.qdrant.registry_repository import (
            RegistryQdrantRepository,
        )

        return RegistryQdrantRepository(
            "image",
            ContentType.IMAGE.value,
            test_settings,
            ImageDbEntry,
            ImageSearchResult,
            test_embeddings_manager,
        )

    def test_repository_initialization(self, repository):
        assert repository.repository_name == "image"
        assert repository.content_type == ContentType.IMAGE.value
        assert repository._shared_manager is not None

    @pytest.mark.asyncio
    async def test_search_returns_empty_list_when_no_data(self, repository):
        results = await repository.search("climate protest", limit=10)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_returns_matching_results(
        self, repository, test_embeddings_manager
    ):
        test_embeddings_manager.clear()
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_image_data(
                text="Protesters at Berlin climate rally holding signs",
                title="Berlin Climate Rally",
            ),
            "id": str(test_id),
            "content_type": "image",
        }
        test_embeddings_manager.add_test_data("image", [test_data])

        results = await repository.search("climate", limit=10)

        assert len(results) == 1
        assert isinstance(results[0], ImageSearchResult)
        assert results[0].id == test_id
        assert results[0].text == "Protesters at Berlin climate rally holding signs"
        assert results[0].title == "Berlin Climate Rally"
        assert results[0].score == 0.95

    @pytest.mark.asyncio
    async def test_get_by_id_returns_item(self, repository, test_embeddings_manager):
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_image_data(
                text="Solar panels on rooftop of community center",
                title="Community Solar Panels",
            ),
            "id": str(test_id),
            "content_type": "image",
        }
        test_embeddings_manager.add_test_data("image", [test_data])

        result = await repository.get(test_id)

        assert isinstance(result, ImageDbEntry)
        assert result.id == test_id
        assert result.text == "Solar panels on rooftop of community center"
        assert result.title == "Community Solar Panels"
        assert result.content_type == ContentType.IMAGE

    @pytest.mark.asyncio
    async def test_get_by_id_raises_when_not_found(self, repository):
        test_id = uuid.uuid4()
        with pytest.raises(ValueError) as exc_info:
            await repository.get(test_id)
        assert f"Entry with id {test_id} not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upsert_adds_new_item(self, repository, test_embeddings_manager):
        test_id = uuid.uuid4()
        new_item = ImageDbEntry(
            id=test_id,
            content_type=ContentType.IMAGE,
            **create_base_content_fields(),
            **create_image_data(
                text="Wind turbines on a green hillside at sunset",
                title="Wind Energy Hillside",
            ),
        )

        result_id = await repository.upsert(test_id, new_item)

        assert result_id == test_id
        stored_data = test_embeddings_manager.get_data()
        assert str(test_id) in stored_data
        assert (
            stored_data[str(test_id)]["text"]
            == "Wind turbines on a green hillside at sunset"
        )
        assert stored_data[str(test_id)]["title"] == "Wind Energy Hillside"

    @pytest.mark.asyncio
    async def test_upsert_without_caption_stores_item(
        self, repository, test_embeddings_manager
    ):
        """Phase B path: image stored without caption (text=None)."""
        test_id = uuid.uuid4()
        new_item = ImageDbEntry(
            id=test_id,
            content_type=ContentType.IMAGE,
            **create_base_content_fields(),
            **create_image_data(text=None),
        )

        result_id = await repository.upsert(test_id, new_item)

        assert result_id == test_id
        stored_data = test_embeddings_manager.get_data()
        assert str(test_id) in stored_data

    @pytest.mark.asyncio
    async def test_count_returns_correct_number(
        self, repository, test_embeddings_manager
    ):
        test_data = []
        for i in range(3):
            test_data.append(
                {
                    **create_base_content_fields(),
                    **create_image_data(text=f"Image caption {i}", title=f"Image {i}"),
                    "id": str(uuid.uuid4()),
                    "content_type": "image",
                }
            )
        test_embeddings_manager.add_test_data("image", test_data)

        count = await repository.count()
        assert count == 3

    @pytest.mark.asyncio
    async def test_has_content_returns_correct_boolean(
        self, repository, test_embeddings_manager
    ):
        assert await repository.has_content() is False

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

        assert await repository.has_content() is True

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, repository, test_embeddings_manager):
        test_data = []
        for i in range(5):
            test_data.append(
                {
                    **create_base_content_fields(),
                    **create_image_data(text=f"Image {i}", title=f"Title {i}"),
                    "id": str(uuid.uuid4()),
                    "content_type": "image",
                }
            )
        test_embeddings_manager.add_test_data("image", test_data)

        first_page = await repository.get_all(limit=3, offset=0)
        assert len(first_page) == 3
        assert all(isinstance(r, ImageDbEntry) for r in first_page)

        second_page = await repository.get_all(limit=3, offset=3)
        assert len(second_page) == 2

    @pytest.mark.asyncio
    async def test_image_specific_fields_preserved(
        self, repository, test_embeddings_manager
    ):
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_image_data(
                text="Green party members at environmental conference",
                title="Conference Photo",
                image_url="https://example.com/photo.jpg",
                description_model="gpt-4o",
            ),
            "id": str(test_id),
            "content_type": "image",
        }
        test_embeddings_manager.add_test_data("image", [test_data])

        result = await repository.get(test_id)

        assert result.image_url == "https://example.com/photo.jpg"
        assert result.description_model == "gpt-4o"
        assert result.content_type == ContentType.IMAGE

    @pytest.mark.asyncio
    async def test_search_does_not_return_other_content_types(
        self, repository, test_embeddings_manager
    ):
        """Image repository must not return generic_text entries."""
        test_embeddings_manager.clear()
        test_embeddings_manager.add_test_data(
            "generic_text",
            [
                {
                    **create_base_content_fields(),
                    "text": "Climate justice protest",
                    "title": "Protest Text",
                    "references": [],
                    "references_count": 0,
                    "id": str(uuid.uuid4()),
                    "content_type": "generic_text",
                }
            ],
        )
        test_embeddings_manager.add_test_data(
            "image",
            [
                {
                    **create_base_content_fields(),
                    **create_image_data(
                        text="Climate justice protest photo", title="Protest Photo"
                    ),
                    "id": str(uuid.uuid4()),
                    "content_type": "image",
                }
            ],
        )

        results = await repository.search("climate justice protest", limit=10)

        assert len(results) == 1
        assert isinstance(results[0], ImageSearchResult)

    def test_initialize_with_initial_data_is_noop(self, repository):
        """Registry-driven types do not seed from JSON; method must not raise."""
        repository.initialize_with_initial_data()
