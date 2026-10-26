"""
Sperren und Entsperren eines gemeldeten Beitrags (ModerationService).

Ein Admin sperrt, statt zu loeschen: Der Beitrag bleibt im Speicher, bekommt den
Status "blocked" und verschwindet damit aus allen Lesepfaden der Repositories.
Die Meldungen zum Beitrag stehen danach auf bearbeitet. Entsperren stellt den
Status von vor der Sperre wieder her.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from services.moderation_service import ModerationService
from tests.conftest import create_base_content_fields

CONTENT_ID = str(uuid.uuid4())


@pytest.fixture
def speicher(test_embeddings_manager):
    """Ein freigegebener Kommentar im Test-Speicher."""
    test_embeddings_manager.add_test_data(
        "commentary",
        [
            {
                **create_base_content_fields(),
                "id": CONTENT_ID,
                "text": "Gemeldeter Kommentar",
                "status": "approved",
            }
        ],
    )
    return test_embeddings_manager


def _payload(speicher) -> dict:
    return speicher.get_data()[CONTENT_ID]


@pytest.fixture
def service(speicher):
    report_repo = MagicMock()
    report_repo.update_reports_by_content_id = MagicMock(return_value=2)
    with patch(
        "services.moderation_service.get_content_report_repository",
        return_value=report_repo,
    ), patch(
        "services.moderation_service.get_embeddings_manager",
        return_value=speicher,
    ):
        yield ModerationService()


@pytest.mark.unit
@pytest.mark.asyncio
class TestSperren:
    async def test_sperren_setzt_status_gesperrt(self, service, speicher):
        assert await service.sperren(CONTENT_ID, gesperrt_von="admin-1") is True

        assert _payload(speicher)["status"] == "blocked"

    async def test_sperren_setzt_meldungen_auf_bearbeitet(self, service):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")

        aufruf = service.report_repo.update_reports_by_content_id.call_args.kwargs
        assert aufruf["content_id"] == uuid.UUID(CONTENT_ID)
        assert aufruf["status"] == "reviewed"
        assert aufruf["reviewed_by"] == "admin-1"

    async def test_sperren_loescht_nichts(self, service, speicher):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")

        assert CONTENT_ID in speicher.get_data()

    async def test_sperren_unbekannter_beitrag(self, service):
        assert await service.sperren(str(uuid.uuid4()), gesperrt_von="a") is False
        service.report_repo.update_reports_by_content_id.assert_not_called()

    async def test_sperren_ungueltige_kennung(self, service):
        assert await service.sperren("kein-uuid", gesperrt_von="a") is False

    async def test_zweimal_sperren_behaelt_status_von_vorher(self, service, speicher):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")
        await service.entsperren(CONTENT_ID, entsperrt_von="admin-1")

        assert _payload(speicher)["status"] == "approved"


@pytest.mark.unit
@pytest.mark.asyncio
class TestEntsperren:
    async def test_entsperren_stellt_status_von_vorher_wieder_her(
        self, service, speicher
    ):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")

        assert await service.entsperren(CONTENT_ID, entsperrt_von="admin-1") is True

        assert _payload(speicher)["status"] == "approved"
        assert "status_vor_sperre" not in _payload(speicher)

    async def test_entsperren_ohne_status_von_vorher_macht_sichtbar(
        self, service, speicher
    ):
        # Altbestand ohne Status-Feld: nach dem Entsperren sichtbar wie neu angelegt.
        del _payload(speicher)["status"]
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")

        await service.entsperren(CONTENT_ID, entsperrt_von="admin-1")

        assert _payload(speicher)["status"] == "released_internal"

    async def test_entsperren_nicht_gesperrt_aendert_nichts(self, service, speicher):
        assert await service.entsperren(CONTENT_ID, entsperrt_von="admin-1") is True

        assert _payload(speicher)["status"] == "approved"
        speicher.async_client.set_payload.assert_not_called()

    async def test_entsperren_unbekannter_beitrag(self, service):
        assert await service.entsperren(str(uuid.uuid4()), entsperrt_von="a") is False
