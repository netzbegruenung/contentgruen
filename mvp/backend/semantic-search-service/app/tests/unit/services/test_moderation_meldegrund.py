"""
Meldegruende im ModerationService (#423).

Schema der Route und Service pruefen denselben Wertebereich: ein Grund, den die
Route annimmt, darf der Service nicht still mit False abweisen.
"""

import uuid
from unittest.mock import MagicMock

import pytest

from domain.models.meldegrund import MELDEGRUENDE
from services.moderation_service import ModerationService

CONTENT_ID = str(uuid.uuid4())


@pytest.fixture
def report_repo():
    repo = MagicMock()
    repo.has_report_from_user = MagicMock(return_value=False)
    repo.create_report = MagicMock(return_value=MagicMock())
    return repo


@pytest.fixture
def service(report_repo):
    return ModerationService(report_repo=report_repo, moderation_repo=MagicMock())


def test_meldegruende_enthalten_erfunden_oder_sachlich_falsch():
    assert "fabricated_or_false" in MELDEGRUENDE


def test_bisherige_meldegruende_bleiben_gueltig():
    # Gespeicherte Meldungen tragen diese Werte; sie muessen gueltig bleiben.
    assert {"spam", "inappropriate", "duplicate", "other"} <= set(MELDEGRUENDE)


@pytest.mark.unit
@pytest.mark.asyncio
class TestReportContent:
    @pytest.mark.parametrize("grund", MELDEGRUENDE)
    async def test_report_content_jeder_meldegrund_wird_gespeichert(
        self, service, report_repo, grund
    ):
        assert await service.report_content(
            CONTENT_ID, "commentary", grund, user_id="person-1"
        )

        assert report_repo.create_report.call_args.kwargs["reason"] == grund

    async def test_report_content_unbekannter_grund_wird_abgewiesen(
        self, service, report_repo
    ):
        assert not await service.report_content(
            CONTENT_ID, "commentary", "fake_news", user_id="person-1"
        )

        report_repo.create_report.assert_not_called()
