"""
Unit tests for the search tracking service.

The point of these tests is the privacy contract: no raw user id, session id, IP
or search text may reach the repository, and the stored pseudonym must not be
correlatable across day boundaries.
"""

import logging
from datetime import date, datetime, timezone
from unittest.mock import Mock, patch

import pytest

from services.search_tracking_service import SearchTrackingService


class TestDeriveActorHash:
    """Test suite for the daily actor pseudonym."""

    @pytest.fixture(autouse=True)
    def fixed_secret(self):
        """Pin the hash secret so digests are reproducible within a test."""
        with patch("services.search_tracking_service.settings") as mock_settings:
            mock_settings.actor_hash_secret = "test-secret"
            yield mock_settings

    def test_derive_actor_hash_is_stable_within_a_day(self):
        moment = datetime(2026, 8, 19, 8, 0, tzinfo=timezone.utc)
        later_same_day = datetime(2026, 8, 19, 23, 59, tzinfo=timezone.utc)

        first = SearchTrackingService._derive_actor_hash(user_id="alice", moment=moment)
        second = SearchTrackingService._derive_actor_hash(
            user_id="alice", moment=later_same_day
        )

        assert first == second

    def test_derive_actor_hash_rotates_across_days(self):
        """The whole point: yesterday's searches cannot be tied to today's."""
        today = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)
        tomorrow = datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc)

        assert SearchTrackingService._derive_actor_hash(
            user_id="alice", moment=today
        ) != SearchTrackingService._derive_actor_hash(user_id="alice", moment=tomorrow)

    def test_derive_actor_hash_separates_actors(self):
        moment = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)

        assert SearchTrackingService._derive_actor_hash(
            user_id="alice", moment=moment
        ) != SearchTrackingService._derive_actor_hash(user_id="bob", moment=moment)

    def test_derive_actor_hash_does_not_contain_the_actor_id(self):
        moment = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)

        digest = SearchTrackingService._derive_actor_hash(
            user_id="alice@example.org", moment=moment
        )

        assert "alice" not in digest
        assert len(digest) == 64

    def test_derive_actor_hash_prefers_user_over_session(self):
        moment = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)

        with_session = SearchTrackingService._derive_actor_hash(
            user_id="alice", session_id="sess-1", moment=moment
        )
        without_session = SearchTrackingService._derive_actor_hash(
            user_id="alice", moment=moment
        )

        assert with_session == without_session

    def test_derive_actor_hash_falls_back_to_session(self):
        moment = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)

        digest = SearchTrackingService._derive_actor_hash(
            session_id="sess-1", moment=moment
        )

        assert digest is not None

    def test_derive_actor_hash_returns_none_without_any_actor(self):
        assert SearchTrackingService._derive_actor_hash() is None


class TestTrackSearch:
    """Test suite for the search tracking write path."""

    @pytest.fixture
    def mock_repository(self):
        return Mock()

    @pytest.fixture
    def service(self, mock_repository):
        with patch(
            "services.search_tracking_service.get_search_tracking_repository",
            return_value=mock_repository,
        ):
            return SearchTrackingService()

    def test_track_search_passes_only_pseudonym_and_count(
        self, service, mock_repository
    ):
        service.track_search(results_count=5, user_id="alice", session_id="sess-1")

        _, kwargs = mock_repository.track_search.call_args
        assert set(kwargs) == {"results_count", "actor_hash", "day"}
        assert kwargs["results_count"] == 5
        assert "alice" not in kwargs["actor_hash"]
        assert "sess-1" not in kwargs["actor_hash"]

    def test_track_search_without_actor_stores_no_pseudonym(
        self, service, mock_repository
    ):
        service.track_search(results_count=3)

        _, kwargs = mock_repository.track_search.call_args
        assert kwargs["actor_hash"] is None

    def test_track_search_rejects_negative_results_count(
        self, service, mock_repository
    ):
        assert service.track_search(results_count=-1) is False
        mock_repository.track_search.assert_not_called()

    def test_track_search_passes_only_the_utc_day(self, service, mock_repository):
        """No time of day: it would let a search event be matched with the
        statement the same search created."""
        moment = datetime(2026, 10, 26, 23, 30, tzinfo=timezone.utc)
        with patch("services.search_tracking_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = moment
            service.track_search(results_count=0, user_id="alice")

        _, kwargs = mock_repository.track_search.call_args
        assert kwargs["day"] == date(2026, 10, 26)
        assert not isinstance(kwargs["day"], datetime)

    def test_track_search_pseudonym_and_day_belong_to_the_same_moment(
        self, service, mock_repository
    ):
        moment = datetime(2026, 10, 26, 23, 59, 59, tzinfo=timezone.utc)
        with patch("services.search_tracking_service.datetime") as mock_datetime:
            mock_datetime.now.return_value = moment
            service.track_search(results_count=1, user_id="alice")

        _, kwargs = mock_repository.track_search.call_args
        assert kwargs["actor_hash"] == SearchTrackingService._derive_actor_hash(
            user_id="alice", moment=moment
        )

    def test_track_search_logs_nothing_at_info(self, service, mock_repository, caplog):
        """A log line per search carries its exact time; counted per day it lines
        up with the search events by order and undoes the coarsening."""
        with caplog.at_level(logging.INFO):
            service.track_search(results_count=0, user_id="alice")

        assert caplog.records == []
