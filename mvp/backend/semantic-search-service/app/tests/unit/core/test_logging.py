"""
Tests fuer die Log-Pseudonymisierung.

Der Punkt dieser Datei ist eine Zusicherung, keine Abdeckungszahl: eine
Nutzerkennung darf in keiner Logzeile im Klartext landen -- auch nicht auf
DEBUG, weil der Dev-Stack mit SEMANTIC_SEARCH_LOG_LEVEL=DEBUG laeuft.
"""

import asyncio
import logging
import uuid
from unittest.mock import Mock, patch

from api.v1.usage import run_cleanup_manually
from core.logging import log_pseudonym
from services.voting_service import VotingService


class TestLogPseudonym:
    """Das Pseudonym selbst."""

    def test_does_not_contain_the_identifier(self):
        assert "user-001" not in log_pseudonym("user-001")

    def test_is_stable_for_the_same_identifier(self):
        # Wiederkehrende Akteure muessen unterscheidbar bleiben, sonst ist die
        # Zeile fuer die Fehleranalyse wertlos.
        assert log_pseudonym("user-001") == log_pseudonym("user-001")

    def test_differs_between_identifiers(self):
        assert log_pseudonym("user-001") != log_pseudonym("user-002")

    def test_is_short_enough_to_read(self):
        assert len(log_pseudonym("user-001")) == 8

    def test_anonymous_stays_readable(self):
        # "anonymous" ist keine Kennung, sondern deren Abwesenheit -- ein Hash
        # davon wuerde die Zeile nur unlesbar machen.
        assert log_pseudonym("anonymous") == "anonymous"

    def test_empty_identifier_is_treated_as_anonymous(self):
        assert log_pseudonym("") == "anonymous"


class TestVotingServiceLogging:
    """Der Fundort: acht Zeilen pro Vote, alle mit der Kennung darin."""

    def _service(self):
        with patch("services.voting_service.VoteRepository"):
            service = VotingService()
        service.vote_repository = Mock()
        return service

    def test_set_like_does_not_log_the_raw_user_id(self, caplog):
        service = self._service()
        content_id = uuid.uuid4()

        with caplog.at_level(logging.DEBUG):
            service.set_like("user-001", content_id)

        assert "user-001" not in caplog.text
        assert log_pseudonym("user-001") in caplog.text

    def test_remove_like_does_not_log_the_raw_user_id(self, caplog):
        service = self._service()
        service.vote_repository.get_user_vote.return_value = Mock(vote_type="like")
        content_id = uuid.uuid4()

        with caplog.at_level(logging.DEBUG):
            service.remove_like("user-001", content_id)

        assert "user-001" not in caplog.text

    def test_set_dislike_does_not_log_the_raw_user_id(self, caplog):
        service = self._service()
        content_id = uuid.uuid4()

        with caplog.at_level(logging.DEBUG):
            service.set_dislike("user-001", content_id)

        assert "user-001" not in caplog.text

    def test_remove_dislike_does_not_log_the_raw_user_id(self, caplog):
        service = self._service()
        service.vote_repository.get_user_vote.return_value = Mock(vote_type="dislike")
        content_id = uuid.uuid4()

        with caplog.at_level(logging.DEBUG):
            service.remove_dislike("user-001", content_id)

        assert "user-001" not in caplog.text


class TestManualCleanupLogging:
    """Der manuelle Cleanup nannte die Kennung des Admins im Klartext auf INFO (#277)."""

    def test_run_cleanup_manually_does_not_log_the_raw_admin_id(self, caplog):
        settings = Mock()
        settings.is_admin_user.return_value = True
        usage_service = Mock()
        usage_service.cleanup_old_events.return_value = 0

        with patch("api.v1.usage.get_usage_service", return_value=usage_service):
            with caplog.at_level(logging.DEBUG):
                asyncio.run(
                    run_cleanup_manually(
                        days_to_keep=30, current_user="admin-001", settings=settings
                    )
                )

        assert "admin-001" not in caplog.text
        assert log_pseudonym("admin-001") in caplog.text
