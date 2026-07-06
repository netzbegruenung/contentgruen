"""
Unit tests for the usage tracking service.
"""

import uuid
from unittest.mock import Mock, patch
import pytest

from services.usage_tracking_service import UsageTrackingService


class TestUsageTrackingService:
    """Test suite for UsageTrackingService."""

    @pytest.fixture
    def mock_repository(self):
        """Create a mock repository."""
        return Mock()

    @pytest.fixture
    def service(self, mock_repository):
        """Create a service instance with mocked repository."""
        with patch(
            "services.usage_tracking_service.get_usage_repository",
            return_value=mock_repository,
        ):
            return UsageTrackingService()

    def test_track_content_usage_success(self, service, mock_repository):
        """Test successful content usage tracking."""
        # Arrange
        content_id = str(uuid.uuid4())
        user_id = "testuser"
        session_id = "session123"
        ip_address = "192.168.1.1"
        user_agent = "Mozilla/5.0"

        mock_repository.track_usage.return_value = True

        # Act
        result = service.track_content_usage(
            content_id=content_id,
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Assert
        assert result is True
        mock_repository.track_usage.assert_called_once()
        call_args = mock_repository.track_usage.call_args[1]
        assert str(call_args["content_id"]) == content_id
        assert call_args["user_id"] == user_id
        assert call_args["event_type"] == "copy"

    def test_track_content_usage_invalid_uuid(self, service, mock_repository):
        """Test tracking with invalid UUID format."""
        # Arrange
        invalid_content_id = "not-a-uuid"

        # Act
        result = service.track_content_usage(content_id=invalid_content_id)

        # Assert
        assert result is False
        mock_repository.track_usage.assert_not_called()

    def test_get_content_usage(self, service, mock_repository):
        """Test getting usage count for a content item."""
        # Arrange
        content_id = str(uuid.uuid4())
        expected_count = 42
        mock_repository.get_usage_count.return_value = expected_count

        # Act
        result = service.get_content_usage(content_id)

        # Assert
        assert result == expected_count
        mock_repository.get_usage_count.assert_called_once()

    def test_enrich_content_with_usage(self, service, mock_repository):
        """Test enriching content items with usage statistics."""
        # Arrange
        content_id_1 = str(uuid.uuid4())
        content_id_2 = str(uuid.uuid4())

        content_items = [
            {"id": content_id_1, "text": "Content 1"},
            {"id": content_id_2, "text": "Content 2"},
            {"text": "Content without ID"},
        ]

        mock_repository.get_usage_counts_batch.return_value = {
            content_id_1: 10,
            content_id_2: 20,
        }

        # Act
        result = service.enrich_content_with_usage(content_items)

        # Assert
        assert len(result) == 3
        assert result[0]["usage_count"] == 10
        assert result[1]["usage_count"] == 20
        assert result[2]["usage_count"] == 0  # No ID

        mock_repository.get_usage_counts_batch.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_usage_stats(self, service, mock_repository):
        """Test getting user usage statistics."""
        # Arrange
        user_id = "testuser"
        expected_stats = {
            "user_id": user_id,
            "unique_contents_contributed": 5,
            "total_usage_count": 100,
            "top_content": [],
        }

        # Mock as async function
        async def mock_get_user_statistics(user_id):
            return expected_stats

        mock_repository.get_user_statistics = mock_get_user_statistics

        # Act
        result = await service.get_user_usage_stats(user_id)

        # Assert
        assert result == expected_stats

    def test_get_trending_content(self, service, mock_repository):
        """Test getting trending content."""
        # Arrange
        limit = 5
        expected_trending = [
            {"content_id": str(uuid.uuid4()), "recent_uses": 50, "total_uses": 100}
        ]
        mock_repository.get_trending_content.return_value = expected_trending

        # Act
        result = service.get_trending_content(limit=limit)

        # Assert
        assert result == expected_trending
        mock_repository.get_trending_content.assert_called_once_with(
            limit=limit, hours=24
        )

    def test_initialize_content_usage(self, service, mock_repository):
        """Test initializing content usage with a specific count."""
        # Arrange
        content_id = str(uuid.uuid4())
        initial_count = 25

        # Act
        service.initialize_content_usage(content_id, initial_count)

        # Assert
        mock_repository.initialize_usage_data.assert_called_once()
        call_args = mock_repository.initialize_usage_data.call_args[0]
        assert str(call_args[0]) == content_id
        assert call_args[1] == initial_count
