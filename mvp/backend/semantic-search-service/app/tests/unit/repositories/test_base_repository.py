"""
Test module for BaseRepository using the new dependency injection architecture.

This module demonstrates clean testing patterns without complex mocking.
"""

import datetime
import pytest
import pytest_asyncio
import uuid
from unittest.mock import MagicMock, patch
from typing import Optional

from repositories.implementations.qdrant.base_repository import (
    QdrantBaseRepository as BaseRepository,
)
from domain.models.base_content import (
    BaseContentDbEntry,
    BaseContentSearchResult,
)
from domain.models.content_type import ContentType
from core.config import Settings
from tests.conftest import create_base_content_fields


class MockDbEntry(BaseContentDbEntry):
    """Mock database entry for testing."""

    # Additional fields that might be extracted by ModelInformationExtractor
    updated: Optional[datetime.datetime] = None


class MockSearchResult(MockDbEntry, BaseContentSearchResult):
    """Mock search result for testing."""

    pass


class TestBaseRepository(BaseRepository[MockDbEntry, MockSearchResult]):
    """Concrete test implementation of BaseRepository."""

    def initialize_with_initial_data(self):
        """Implementation of abstract method for testing."""
        pass


# SQL-related static method tests removed as they don't apply to Qdrant


@pytest.mark.unit
class TestBaseRepositoryMethods:
    """Test BaseRepository instance methods."""

    @pytest.fixture
    def repository(self, test_settings, test_embeddings_manager):
        """Create test repository instance with test embeddings manager."""
        repo = TestBaseRepository(
            "test_repo",
            "statement",  # Use string content type
            test_settings,
            MockDbEntry,
            MockSearchResult,
            embeddings_manager=test_embeddings_manager,
        )
        return repo

    @pytest.mark.asyncio
    async def test_has_content_true(self, repository, test_embeddings_manager):
        """Test has_content when content exists."""
        # Add some test data
        test_embeddings_manager.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(),
                    "text": "Test statement",
                    "id": str(uuid.uuid4()),
                    "content_type": "statement",
                }
            ],
        )

        result = await repository.has_content()

        assert result is True

    @pytest.mark.asyncio
    async def test_has_content_false(self, repository, test_embeddings_manager):
        """Test has_content when no content exists."""
        # Ensure no data exists
        test_embeddings_manager.clear()

        result = await repository.has_content()

        assert result is False

    @pytest.mark.asyncio
    async def test_search_with_results(self, repository, test_embeddings_manager):
        """Test search method with results."""
        # Add test data
        test_id = uuid.uuid4()
        test_embeddings_manager.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(),
                    "id": str(test_id),
                    "text": "Test result 1",
                    "content_type": "statement",
                }
            ],
        )

        # Search with a term that matches the content
        results = await repository.search("result", 10)

        assert len(results) == 1
        assert isinstance(results[0], MockSearchResult)
        assert results[0].text == "Test result 1"
        assert (
            results[0].score == 0.95
        )  # TestEmbeddingsManager returns 0.95 for searches

    @pytest.mark.asyncio
    async def test_search_no_results(self, repository, test_embeddings_manager):
        """Test search method with no results."""
        # Ensure no data exists
        test_embeddings_manager.clear()

        results = await repository.search("test query", 10)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repository, test_embeddings_manager):
        """Test get by ID when entry is found."""
        test_id = uuid.uuid4()
        test_embeddings_manager.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(),
                    "id": str(test_id),
                    "text": "Test entry",
                    "content_type": "statement",
                }
            ],
        )

        result = await repository.get(test_id)

        assert result is not None
        assert result.id == test_id
        assert result.text == "Test entry"
        assert result.content_type == ContentType.STATEMENT

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository, test_embeddings_manager):
        """Test get by ID when entry is not found."""
        test_id = uuid.uuid4()
        test_embeddings_manager.clear()

        with pytest.raises(ValueError, match=f"Entry with id {test_id} not found"):
            await repository.get(test_id)

    @pytest.mark.asyncio
    async def test_upsert_success(self, repository, test_embeddings_manager):
        """Test upsert operation success."""
        test_id = uuid.uuid4()
        test_entry = MockDbEntry(
            **create_base_content_fields(),
            id=test_id,
            text="Test entry",
            content_type=ContentType.STATEMENT,
        )

        result = await repository.upsert(test_id, test_entry)

        # Verify it was added
        assert result == test_id
        stored_data = test_embeddings_manager.get_data()
        assert str(test_id) in stored_data
        assert stored_data[str(test_id)]["text"] == "Test entry"

    @pytest.mark.asyncio
    async def test_get_all_with_results(self, repository, test_embeddings_manager):
        """Test get_all method with results."""
        # Add test data
        test_data = [
            {
                **create_base_content_fields(),
                "id": str(uuid.uuid4()),
                "text": "Entry 1",
                "content_type": "statement",
            },
            {
                **create_base_content_fields(),
                "id": str(uuid.uuid4()),
                "text": "Entry 2",
                "content_type": "statement",
            },
        ]
        test_embeddings_manager.add_test_data("statement", test_data)

        results = await repository.get_all(limit=10, offset=0)

        assert len(results) == 2
        assert results[0].text == "Entry 1"
        assert results[1].text == "Entry 2"

    @pytest.mark.asyncio
    async def test_get_all_empty(self, repository, test_embeddings_manager):
        """Test get_all method with no results."""
        test_embeddings_manager.clear()

        results = await repository.get_all(limit=10, offset=0)

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_get_by_author_with_results(
        self, repository, test_embeddings_manager
    ):
        """Test get_by_author method with results."""
        # Add test data with specific author
        test_embeddings_manager.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(original_author="Test Author"),
                    "id": str(uuid.uuid4()),
                    "text": "Author entry",
                    "content_type": "statement",
                }
            ],
        )

        results = await repository.get_by_author("Test Author", limit=10, offset=0)

        # TestEmbeddingsManager doesn't filter by author properly, so it returns all
        assert len(results) >= 1
        # But we can verify at least one has the correct author
        author_results = [r for r in results if r.original_author == "Test Author"]
        assert len(author_results) >= 1

    @pytest.mark.asyncio
    async def test_count(self, repository, test_embeddings_manager):
        """Test count method."""
        # Add some test data
        for i in range(3):
            test_embeddings_manager.add_test_data(
                "statement",
                [
                    {
                        **create_base_content_fields(),
                        "id": str(uuid.uuid4()),
                        "text": f"Entry {i}",
                        "content_type": "statement",
                    }
                ],
            )

        count = await repository.count()

        assert count == 3


@pytest.mark.unit
class TestAutorenzuordnungOhneSuchanfragen:
    """
    Was einer Person zugeordnet wird, blendet Statements aus Suchanfragen aus.

    Eine Suchanfrage faellt automatisch an, sobald jemand das Suchfeld benutzt -
    sie ist kein Beitrag. Der Ausschluss sitzt bewusst im Repository und nicht
    in api/v1/contribution.py, weil get_by_author ausser "Meine Beitraege" auch
    die Nutzungsstatistik speist (repositories/usage_tracking_repository.py,
    get_user_statistics). Er greift zusaetzlich zum Systemautor, damit auch
    Altbestand aussen vor bleibt, an dem noch eine Person haengt.
    """

    @pytest.fixture
    def repository_mit_client(self, test_settings, test_embeddings_manager):
        from unittest.mock import AsyncMock

        client = MagicMock()
        client.scroll = AsyncMock(return_value=([], None))
        client.count = AsyncMock(return_value=MagicMock(count=0))

        manager = MagicMock()
        manager.async_client = client
        manager.collection_name = "content_collection"

        repository = TestBaseRepository(
            "test_index",
            "statement",
            test_settings,
            MockDbEntry,
            MockSearchResult,
            test_embeddings_manager,
        )
        repository._shared_manager = manager
        return repository, client

    @staticmethod
    def _suchanfragen_ausgeschlossen(such_filter) -> bool:
        return any(
            bedingung.key == "origin" and bedingung.match.value == "search_query"
            for bedingung in (such_filter.must_not or [])
        )

    @pytest.mark.asyncio
    async def test_get_by_author_blendet_suchanfragen_aus(self, repository_mit_client):
        repository, client = repository_mit_client

        await repository.get_by_author("testuser", limit=10, offset=0)

        such_filter = client.scroll.call_args.kwargs["scroll_filter"]
        assert self._suchanfragen_ausgeschlossen(such_filter)

    @pytest.mark.asyncio
    async def test_get_count_by_author_blendet_suchanfragen_aus(
        self, repository_mit_client
    ):
        repository, client = repository_mit_client

        await repository.get_count_by_author("testuser")

        such_filter = client.count.call_args.kwargs["count_filter"]
        assert self._suchanfragen_ausgeschlossen(such_filter)

    @pytest.mark.asyncio
    async def test_autor_bleibt_das_hauptkriterium(self, repository_mit_client):
        repository, client = repository_mit_client

        await repository.get_by_author("testuser", limit=10, offset=0)

        such_filter = client.scroll.call_args.kwargs["scroll_filter"]
        bedingungen = {bedingung.key: bedingung for bedingung in such_filter.must}
        assert bedingungen["original_author"].match.value == "testuser"
        assert bedingungen["content_type"].match.value == "statement"
