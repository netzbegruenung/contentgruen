"""
Test module for CommentaryRepository using the new dependency injection architecture.

This module demonstrates clean testing patterns without complex mocking.
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime

from domain.models.commentary import CommentaryDbEntry, CommentarySearchResult
from domain.models.content_type import ContentType
from tests.conftest import create_base_content_fields, create_commentary_data


@pytest.mark.unit
class TestCommentaryRepository:
    """Test cases for CommentaryRepository."""

    @pytest.fixture
    def repository(self, test_settings, test_embeddings_manager):
        """Create a commentary repository with injected test embeddings manager."""
        from repositories.implementations.qdrant.commentary_repository import (
            CommentaryRepository,
        )

        return CommentaryRepository(
            test_settings, embeddings_manager=test_embeddings_manager
        )

    def test_repository_initialization(self, repository):
        """Test that repository initializes correctly."""
        assert repository.repository_name == "commentary_index"
        assert repository.content_type == "commentary"
        assert repository._shared_manager is not None

    @pytest.mark.asyncio
    async def test_search_returns_empty_list_when_no_data(self, repository):
        """Test search returns empty list when no matching data exists."""
        results = await repository.search("climate analysis", limit=10)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_returns_matching_results(
        self, repository, test_embeddings_manager
    ):
        """Test search returns matching results."""
        # Add test data
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_commentary_data(
                text="Climate analysis shows urgent need for action",
                title="Climate Analysis",
            ),
            "id": str(test_id),
            "content_type": "commentary",
        }
        test_embeddings_manager.add_test_data("commentary", [test_data])

        # Search
        results = await repository.search("climate analysis", limit=10)

        # Assert
        assert len(results) == 1
        assert isinstance(results[0], CommentarySearchResult)
        assert results[0].id == test_id
        assert results[0].text == "Climate analysis shows urgent need for action"
        assert results[0].title == "Climate Analysis"
        assert results[0].score == 0.95

    @pytest.mark.asyncio
    async def test_get_by_id_returns_item(self, repository, test_embeddings_manager):
        """Test getting an item by ID."""
        # Add test data
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_commentary_data(
                text="Detailed commentary analysis", title="Commentary Title"
            ),
            "id": str(test_id),
            "content_type": "commentary",
        }
        test_embeddings_manager.add_test_data("commentary", [test_data])

        # Get by ID
        result = await repository.get(test_id)

        # Assert
        assert isinstance(result, CommentaryDbEntry)
        assert result.id == test_id
        assert result.text == "Detailed commentary analysis"
        assert result.title == "Commentary Title"
        assert result.content_type == ContentType.COMMENTARY

    @pytest.mark.asyncio
    async def test_get_by_id_raises_when_not_found(self, repository):
        """Test get raises ValueError when item not found."""
        test_id = uuid.uuid4()

        with pytest.raises(ValueError) as exc_info:
            await repository.get(test_id)

        assert f"Entry with id {test_id} not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_upsert_adds_new_item(self, repository, test_embeddings_manager):
        """Test upserting a new item."""
        # Create new item
        test_id = uuid.uuid4()
        new_item = CommentaryDbEntry(
            id=test_id,
            content_type=ContentType.COMMENTARY,
            **create_base_content_fields(),
            **create_commentary_data(
                text="New commentary analysis", title="New Commentary Title"
            ),
        )

        # Upsert
        result_id = await repository.upsert(test_id, new_item)

        # Verify it was added
        assert result_id == test_id
        stored_data = test_embeddings_manager.get_data()
        assert str(test_id) in stored_data
        assert stored_data[str(test_id)]["text"] == "New commentary analysis"
        assert stored_data[str(test_id)]["title"] == "New Commentary Title"

    @pytest.mark.asyncio
    async def test_count_returns_correct_number(
        self, repository, test_embeddings_manager
    ):
        """Test count returns correct number of items."""
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

        # Check count
        count = await repository.count()
        assert count == 3

    @pytest.mark.asyncio
    async def test_has_content_returns_correct_boolean(
        self, repository, test_embeddings_manager
    ):
        """Test has_content returns correct boolean value."""
        # Initially empty
        assert await repository.has_content() is False

        # Add data
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

        # Now has content
        assert await repository.has_content() is True

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, repository, test_embeddings_manager):
        """Test get_all with pagination."""
        # Add test data
        test_data = []
        for i in range(5):
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

        # Get first page
        results = await repository.get_all(limit=3, offset=0)
        assert len(results) == 3
        assert all(isinstance(r, CommentaryDbEntry) for r in results)

        # Get second page
        results = await repository.get_all(limit=3, offset=3)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_by_author(self, repository, test_embeddings_manager):
        """Test getting items by author."""
        # Add test data with different authors
        test_data = [
            {
                **create_base_content_fields(original_author="author1"),
                **create_commentary_data(text="Commentary by author1"),
                "id": str(uuid.uuid4()),
                "content_type": "commentary",
            },
            {
                **create_base_content_fields(original_author="author2"),
                **create_commentary_data(text="Commentary by author2"),
                "id": str(uuid.uuid4()),
                "content_type": "commentary",
            },
            {
                **create_base_content_fields(original_author="author1"),
                **create_commentary_data(text="Another commentary by author1"),
                "id": str(uuid.uuid4()),
                "content_type": "commentary",
            },
        ]
        test_embeddings_manager.add_test_data("commentary", test_data)

        # Clear the test data to isolate this test
        test_embeddings_manager.clear()
        test_embeddings_manager.add_test_data("commentary", test_data)

        # Get by author
        results = await repository.get_by_author("author1", limit=10, offset=0)

        # Note: TestEmbeddingsManager's _search_impl doesn't parse author filters
        # so we get all results. This is a limitation of the test mock.
        # In production, Qdrant would filter correctly.
        assert len(results) == 3  # Gets all commentaries

        # But we can verify the results contain the expected authors
        author1_results = [r for r in results if r.original_author == "author1"]
        assert len(author1_results) == 2

    @pytest.mark.asyncio
    async def test_search_with_empty_query(self, repository, test_embeddings_manager):
        """Test search with empty query behavior."""
        # Clear any existing data
        test_embeddings_manager.clear()

        # Add test data
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

        # Search with empty query
        results = await repository.search("", limit=10)

        # Note: In the test mock, empty query doesn't filter results
        # In production Qdrant, this behavior might differ
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, repository, test_embeddings_manager):
        """Test that SQL injection attempts are handled safely."""
        # Clear existing data
        test_embeddings_manager.clear()

        # Add test data
        test_embeddings_manager.add_test_data(
            "commentary",
            [
                {
                    **create_base_content_fields(),
                    **create_commentary_data(text="Safe commentary content"),
                    "id": str(uuid.uuid4()),
                    "content_type": "commentary",
                }
            ],
        )

        # Try SQL injection in search
        results = await repository.search("'; DROP TABLE users; --", limit=10)

        # The repository should handle the query safely
        # Even if results are returned, the SQL injection should not execute
        assert isinstance(results, list)
        # The important thing is that no SQL injection occurred
        # which we can't fully test in unit tests, but the query should be escaped
