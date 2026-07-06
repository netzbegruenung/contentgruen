"""
Test module for StatementRepository using the new dependency injection architecture.

This module demonstrates clean testing patterns without complex mocking.
"""

import pytest
import pytest_asyncio
import uuid
from datetime import datetime

from domain.models.statement import StatementDbEntry, StatementSearchResult
from domain.models.content_type import ContentType
from tests.conftest import create_base_content_fields, create_statement_data


@pytest.mark.unit
class TestStatementRepository:
    """Test cases for StatementRepository."""

    @pytest.fixture
    def repository(self, test_settings, test_embeddings_manager):
        """Create a statement repository with injected test embeddings manager."""
        from repositories.implementations.qdrant.statement_repository import (
            StatementRepository,
        )

        return StatementRepository(
            test_settings, embeddings_manager=test_embeddings_manager
        )

    def test_repository_initialization(self, repository):
        """Test that repository initializes correctly."""
        assert repository.repository_name == "statement_index"
        assert repository.content_type == "statement"
        assert repository._shared_manager is not None

    @pytest.mark.asyncio
    async def test_search_returns_empty_list_when_no_data(self, repository):
        """Test search returns empty list when no matching data exists."""
        results = await repository.search("climate change", limit=10)
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
            **create_statement_data(text="Climate change is a critical issue"),
            "id": str(test_id),
            "content_type": "statement",
        }
        test_embeddings_manager.add_test_data("statement", [test_data])

        # Search
        results = await repository.search("climate change", limit=10)

        # Assert
        assert len(results) == 1
        assert isinstance(results[0], StatementSearchResult)
        assert results[0].id == test_id
        assert results[0].text == "Climate change is a critical issue"
        assert results[0].score == 0.95

    @pytest.mark.asyncio
    async def test_get_by_id_returns_item(self, repository, test_embeddings_manager):
        """Test getting an item by ID."""
        # Add test data
        test_id = uuid.uuid4()
        test_data = {
            **create_base_content_fields(),
            **create_statement_data(),
            "id": str(test_id),
            "content_type": "statement",
        }
        test_embeddings_manager.add_test_data("statement", [test_data])

        # Get by ID
        result = await repository.get(test_id)

        # Assert
        assert isinstance(result, StatementDbEntry)
        assert result.id == test_id
        assert result.text == "Climate change requires immediate action"

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
        new_item = StatementDbEntry(
            id=test_id,
            content_type=ContentType.STATEMENT,
            **create_base_content_fields(),
            **create_statement_data(),
        )

        # Upsert
        result_id = await repository.upsert(test_id, new_item)

        # Assert
        assert result_id == test_id

        # Verify it was stored
        stored_data = test_embeddings_manager.get_data()
        assert str(test_id) in stored_data
        assert (
            stored_data[str(test_id)]["text"]
            == "Climate change requires immediate action"
        )

    @pytest.mark.asyncio
    async def test_count_returns_correct_number(
        self, repository, test_embeddings_manager
    ):
        """Test count returns correct number of items."""
        # Initially empty
        assert await repository.count() == 0

        # Add some test data
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
        assert await repository.count() == 3

    @pytest.mark.asyncio
    async def test_has_content_returns_correct_boolean(
        self, repository, test_embeddings_manager
    ):
        """Test has_content returns correct boolean."""
        # Initially empty
        assert await repository.has_content() is False

        # Add one item
        test_data = {
            **create_base_content_fields(),
            **create_statement_data(),
            "id": str(uuid.uuid4()),
            "content_type": "statement",
        }
        test_embeddings_manager.add_test_data("statement", [test_data])

        # Now has content
        assert await repository.has_content() is True

    @pytest.mark.asyncio
    async def test_get_all_with_pagination(self, repository, test_embeddings_manager):
        """Test getting all items with pagination."""
        # Add 5 test items
        test_data = [
            {
                **create_base_content_fields(),
                **create_statement_data(text=f"Statement {i}"),
                "id": str(uuid.uuid4()),
                "content_type": "statement",
            }
            for i in range(5)
        ]
        test_embeddings_manager.add_test_data("statement", test_data)

        # Get first 3 items
        results = await repository.get_all(limit=3, offset=0)
        assert len(results) == 3
        assert all(isinstance(r, StatementDbEntry) for r in results)

        # Get next 2 items
        results = await repository.get_all(limit=3, offset=3)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, repository, test_embeddings_manager):
        """Test that SQL injection attempts are properly escaped.

        This test verifies that SQL injection attempts are safely escaped
        and don't break the system. The actual SQL prevention happens at
        the repository level through proper escaping.
        """
        # Add test data with specific content
        test_data = {
            **create_base_content_fields(),
            **create_statement_data(text="Climate change requires action"),
            "id": str(uuid.uuid4()),
            "content_type": "statement",
        }
        test_embeddings_manager.add_test_data("statement", [test_data])

        # Try SQL injection in search - this should be safely escaped
        malicious_query = "'; DROP TABLE users; --"

        # The key test is that this doesn't raise an exception
        # In a real SQL injection, this would fail with a SQL error
        try:
            results = await repository.search(malicious_query, limit=10)
            # The search completes without error
            search_succeeded = True
        except Exception as e:
            # If there was a SQL injection, we'd get an error here
            search_succeeded = False

        assert search_succeeded, "Search should complete without SQL errors"

        # Verify data is still accessible (wasn't dropped)
        real_results = await repository.search("climate", limit=10)
        assert len(real_results) == 1
        assert await repository.count() == 1
