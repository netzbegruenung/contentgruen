"""
Unit tests for the usage tracking service.
"""

import uuid
from unittest.mock import AsyncMock, Mock, patch
import pytest

from domain.content_registry import BEITRAGSTYPEN_WERTE
from repositories.gesehene_nutzung_repository import GeseheneNutzungRepository
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
        session_id = "session123"
        device_category = "mobile"

        mock_repository.track_usage.return_value = True

        # Act
        result = service.track_content_usage(
            content_id=content_id,
            session_id=session_id,
            device_category=device_category,
        )

        # Assert
        assert result is True
        mock_repository.track_usage.assert_called_once()
        call_args = mock_repository.track_usage.call_args[1]
        assert str(call_args["content_id"]) == content_id
        assert call_args["session_id"] == session_id
        assert call_args["device_category"] == device_category
        assert call_args["event_type"] == "copy"

    def test_track_content_usage_passes_no_person_bound_fields(
        self, service, mock_repository
    ):
        """
        Weder Nutzerkennung noch IP noch User-Agent duerfen das Repository
        erreichen -- die Spalten dafuer gibt es nicht mehr.
        """
        mock_repository.track_usage.return_value = True

        service.track_content_usage(
            content_id=str(uuid.uuid4()),
            session_id="session123",
            device_category="desktop",
        )

        call_args = mock_repository.track_usage.call_args[1]
        assert set(call_args) == {
            "content_id",
            "event_type",
            "session_id",
            "device_category",
        }

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

    def test_get_trending_content_call_matches_repository_signature(
        self, service, mock_repository
    ):
        """
        Der Aufruf muss zur echten Repository-Signatur passen.

        Der Test darueber pruefte gegen ein Mock und hielt damit exakt den
        kaputten Aufruf fest: der Service uebergab hours=, die Signatur nahm
        days=. Ein Mock nimmt jedes Schluesselwort an, im Betrieb warf es einen
        TypeError und /api/v1/usage/trending lieferte durchgehend 500.

        inspect.signature().bind() prueft denselben Aufruf gegen die echte
        Methode, ohne eine Datenbank zu brauchen.
        """
        import inspect

        from repositories.usage_tracking_repository import UsageTrackingRepository

        # Der Trending-Cache ist ein prozessweiter Singleton und ueberdauert die
        # Service-Fixture; ohne Invalidierung antwortet der Aufruf je nach
        # Testreihenfolge aus dem Cache und erreicht das Repository nie.
        service.invalidate_trending_cache()

        service.get_trending_content(limit=5)
        _, kwargs = mock_repository.get_trending_content.call_args

        signature = inspect.signature(UsageTrackingRepository.get_trending_content)
        # self weglassen: gebunden wird der Aufruf an die ungebundene Methode.
        signature.bind(None, **kwargs)


class TestNutzungSeitLetztemBesuch:
    """Die Rueckmeldung beim Anmelden (#349) vergleicht die Nutzung der Beitraege."""

    @pytest.mark.asyncio
    async def test_nutzung_seit_letztem_besuch_vergleicht_die_nutzung_der_beitraege(
        self,
    ):
        repository = Mock()
        repository.get_user_statistics = AsyncMock(
            return_value={"total_usage_count": 9}
        )
        gesehen = Mock(spec=GeseheneNutzungRepository)
        gesehen.neu_seit_letztem_besuch.return_value = 2
        with patch(
            "services.usage_tracking_service.get_usage_repository",
            return_value=repository,
        ):
            service = UsageTrackingService(gesehene_nutzung=gesehen)

        assert await service.nutzung_seit_letztem_besuch("kim-1") == 2
        repository.get_user_statistics.assert_awaited_once_with(
            "kim-1", content_types=BEITRAGSTYPEN_WERTE
        )
        gesehen.neu_seit_letztem_besuch.assert_called_once_with(
            "kim-1", nutzung_jetzt=9
        )
