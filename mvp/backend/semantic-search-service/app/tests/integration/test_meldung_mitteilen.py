"""
Wer die Entscheidung ueber eine Meldung per Mail erfaehrt (#493), gegen ein echtes
PostgreSQL: nur offene Meldungen mit E-Mail-Adresse, und jede nur einmal.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.orm import sessionmaker

from domain.models.meldung import MelderAngaben
from infrastructure.database.connection import AppDatabase
from infrastructure.database.models import Base, ContentReport
from repositories.content_report_repository import ContentReportRepository
from services.meldung_mitteilen import MeldungMitteilung
from services.moderation_service import ModerationService

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

BEITRAG = uuid.uuid4()


class Postausgang:
    def __init__(self):
        self.mails = []

    def senden(self, mail):
        self.mails.append(mail)


@pytest.fixture
def repo(wegwerf_schema):
    Base.metadata.create_all(wegwerf_schema.engine, tables=[ContentReport.__table__])
    app_db = AppDatabase(wegwerf_schema.url)
    app_db.engine = wegwerf_schema.engine
    app_db.SessionLocal = sessionmaker(autoflush=False, bind=wegwerf_schema.engine)
    with patch(
        "repositories.content_report_repository.get_app_database",
        return_value=app_db,
    ):
        yield ContentReportRepository()


def _melden(repo, email=None, beitrag=BEITRAG) -> uuid.UUID:
    """Legt eine Meldung an und gibt ihre Kennung, gefunden ueber die Admin-Liste."""
    vorher = {meldung["id"] for meldung in repo.get_reports(status="all")}
    repo.create_report(
        content_id=beitrag,
        content_type="commentary",
        reason="spam",
        reported_by_session_id="besucher:x",
        melder=MelderAngaben(guter_glaube=True, email=email),
    )
    [neu] = {meldung["id"] for meldung in repo.get_reports(status="all")} - vorher
    return uuid.UUID(neu)


class TestOffeneMelderAdressen:
    async def test_nur_offene_meldungen_mit_adresse_zum_beitrag(self, repo):
        _melden(repo, "anna@example.org")
        _melden(repo, None)
        erledigt = _melden(repo, "ben@example.org")
        repo.update_report_status(erledigt, "dismissed", reviewed_by="admin-1")
        _melden(repo, "carla@example.org", beitrag=uuid.uuid4())

        assert repo.offene_melder_adressen(content_id=BEITRAG) == [
            (BEITRAG, "anna@example.org")
        ]

    async def test_eine_meldung_nach_ihrer_kennung(self, repo):
        meldung = _melden(repo, "anna@example.org")

        assert repo.offene_melder_adressen(report_id=meldung) == [
            (BEITRAG, "anna@example.org")
        ]

    async def test_genau_ein_filter(self, repo):
        with pytest.raises(ValueError):
            repo.offene_melder_adressen()


class TestAbweisenTeiltMit:
    async def test_zweites_abweisen_schickt_keine_zweite_mail(self, repo):
        postausgang = Postausgang()
        moderation_repo = AsyncMock()
        moderation_repo.laden.return_value = {"title": "Ein gemeldeter Kommentar"}
        service = ModerationService(
            report_repo=repo,
            moderation_repo=moderation_repo,
            mitteilung=MeldungMitteilung(postausgang),
        )
        meldung = _melden(repo, "anna@example.org")

        assert await service.dismiss_report(str(meldung), "admin-1")
        assert await service.dismiss_report(str(meldung), "admin-1")

        [mail] = postausgang.mails
        assert mail.an == "anna@example.org"
        assert "„Ein gemeldeter Kommentar“" in mail.text
