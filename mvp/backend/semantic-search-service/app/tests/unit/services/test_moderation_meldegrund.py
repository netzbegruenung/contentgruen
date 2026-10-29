"""
Meldegruende im ModerationService (#423).

Schema der Route und Service pruefen denselben Wertebereich: ein Grund, den die
Route annimmt, darf der Service nicht still mit False abweisen.
"""

import re
import uuid
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from domain.models.meldegrund import MELDEGRUENDE
from repositories.content_report_repository import ContentReportRepository
from repositories.interfaces.moderation_repository import IModerationRepository
from services.moderation_service import ModerationService

CONTENT_ID = str(uuid.uuid4())

FRONTEND_MELDEGRUENDE = (
    Path(__file__).resolve().parents[6]
    / "frontend/gutgesagt-frontend/src/app/shared/meldegruende.ts"
)


@pytest.fixture
def report_repo():
    repo = MagicMock(spec=ContentReportRepository)
    repo.has_report_from_user = MagicMock(return_value=False)
    repo.create_report = MagicMock(return_value=MagicMock())
    return repo


@pytest.fixture
def service(report_repo):
    return ModerationService(
        report_repo=report_repo, moderation_repo=MagicMock(spec=IModerationRepository)
    )


@pytest.mark.unit
class TestMeldegruende:
    def test_meldegruende_bisherige_bleiben_gueltig(self):
        # Gespeicherte Meldungen tragen diese Werte; sie muessen gueltig bleiben.
        assert {"spam", "inappropriate", "duplicate", "other"} <= set(MELDEGRUENDE)

    @pytest.mark.skipif(
        not FRONTEND_MELDEGRUENDE.exists(), reason="Frontend nicht im Checkout"
    )
    def test_meldegruende_gleich_wie_im_frontend(self):
        quelltext = FRONTEND_MELDEGRUENDE.read_text(encoding="utf-8")
        werte = re.findall(r"value: '([^']+)'", quelltext)

        assert sorted(werte) == sorted(MELDEGRUENDE)


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
