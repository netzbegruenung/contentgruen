"""
Aussagen melden und entfernen (Aussagekarte in "Hier fehlt eine Antwort").

Aussagen liegen in derselben Qdrant-Collection wie Beitraege. Die Melde-Route prueft
die Existenz ueber den Moderationsspeicher und nimmt jeden content_type an; die
Moderation zeigt Meldungen mit content_type "statement". Ein Admin entfernt eine
Aussage ueber DELETE /moderation/content/statement/{id} (delete_content). Diese Tests
halten fest, dass beides fuer Aussagen ohne eigenen Code funktioniert.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from domain.models.meldung import MelderAngaben
from repositories.implementations.qdrant.moderation_repository import (
    QdrantModerationRepository,
)
from services.moderation_service import ModerationService
from tests.conftest import create_base_content_fields

AUSSAGE_ID = str(uuid.uuid4())


@pytest.fixture
def speicher(test_embeddings_manager):
    test_embeddings_manager.add_test_data(
        "statement",
        [
            {
                **create_base_content_fields(),
                "id": AUSSAGE_ID,
                "content_type": "statement",
                "text": "Windraeder toeten die Voegel",
                "status": "visible",
            }
        ],
    )
    return test_embeddings_manager


@pytest.fixture
def report_repo():
    repo = MagicMock()
    repo.has_report_from_user = MagicMock(return_value=False)
    repo.create_report = MagicMock(return_value=MagicMock())
    repo.update_reports_by_content_id = MagicMock(return_value=1)
    return repo


@pytest.fixture
def service(speicher, report_repo):
    return ModerationService(
        report_repo=report_repo,
        moderation_repo=QdrantModerationRepository(embeddings_manager=speicher),
        vote_repo=MagicMock(),
        einwurf_repo=MagicMock(),
        sperre_repo=MagicMock(),
        varianten_repo=MagicMock(),
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestAussageMelden:
    async def test_aussage_gilt_als_vorhanden(self, service):
        assert await service.content_exists(AUSSAGE_ID) is True

    async def test_meldung_zu_einer_aussage_wird_mit_ihrem_typ_gespeichert(
        self, service, report_repo
    ):
        ergebnis = await service.report_content(
            AUSSAGE_ID,
            "statement",
            "inappropriate",
            user_id="person-1",
            melder=MelderAngaben(guter_glaube=True),
        )

        assert ergebnis
        aufruf = report_repo.create_report.call_args.kwargs
        assert aufruf["content_type"] == "statement"
        assert str(aufruf["content_id"]) == AUSSAGE_ID


@pytest.mark.unit
@pytest.mark.asyncio
class TestAussageEntfernen:
    async def test_admin_entfernt_aussage_endgueltig_und_schliesst_meldungen(
        self, service, speicher, report_repo
    ):
        with patch("services.moderation_service.get_suchanfrage_freigabe_repository"):
            assert await service.delete_content(AUSSAGE_ID, "statement", "admin-1")

        assert AUSSAGE_ID not in speicher.get_data()
        aufruf = report_repo.update_reports_by_content_id.call_args.kwargs
        assert aufruf["status"] == "reviewed"
        assert aufruf["nur_offene"] is True
