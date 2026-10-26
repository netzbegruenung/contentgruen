"""
Sperren und Entsperren eines gemeldeten Beitrags (ModerationService).

Ein Admin sperrt, statt zu loeschen: Der Beitrag bleibt im Speicher, bekommt den
Status "blocked" und verschwindet damit aus allen Lesepfaden der Repositories.
Die Meldungen zum Beitrag stehen danach auf bearbeitet. Entsperren stellt den
Status von vor der Sperre wieder her.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.moderation_service import ModerationService

CONTENT_ID = str(uuid.uuid4())


@pytest.fixture
def speicher():
    """Ein Beitrag im Speicher; get_by_id liefert, was gerade im Payload steht."""
    payload = {"id": CONTENT_ID, "content_type": "commentary", "status": "approved"}

    manager = MagicMock()
    manager.collection_name = "content_collection"

    async def get_by_id(point_id):
        return dict(payload) if point_id == CONTENT_ID else None

    async def set_payload(collection_name, payload: dict, points):
        speicher.payload.update(payload)

    async def delete_payload(collection_name, keys, points):
        for key in keys:
            speicher.payload.pop(key, None)

    manager.get_by_id = AsyncMock(side_effect=get_by_id)
    manager.async_client.set_payload = AsyncMock(side_effect=set_payload)
    manager.async_client.delete_payload = AsyncMock(side_effect=delete_payload)
    speicher.payload = payload
    speicher.manager = manager
    return speicher


@pytest.fixture
def service(speicher):
    report_repo = MagicMock()
    report_repo.update_reports_by_content_id = MagicMock(return_value=2)
    with patch(
        "services.moderation_service.get_content_report_repository",
        return_value=report_repo,
    ), patch(
        "services.moderation_service.get_embeddings_manager",
        return_value=speicher.manager,
    ):
        yield ModerationService()


@pytest.mark.unit
@pytest.mark.asyncio
class TestSperren:
    async def test_sperren_setzt_status_gesperrt(self, service, speicher):
        assert await service.sperren(CONTENT_ID, gesperrt_von="admin-1") is True

        assert speicher.payload["status"] == "blocked"

    async def test_sperren_setzt_meldungen_auf_bearbeitet(self, service):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")

        aufruf = service.report_repo.update_reports_by_content_id.call_args.kwargs
        assert aufruf["content_id"] == uuid.UUID(CONTENT_ID)
        assert aufruf["status"] == "reviewed"
        assert aufruf["reviewed_by"] == "admin-1"

    async def test_sperren_loescht_nichts(self, service, speicher):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")

        speicher.manager.delete_by_id.assert_not_called()

    async def test_sperren_unbekannter_beitrag(self, service):
        assert await service.sperren(str(uuid.uuid4()), gesperrt_von="a") is False
        service.report_repo.update_reports_by_content_id.assert_not_called()

    async def test_sperren_ungueltige_kennung(self, service):
        assert await service.sperren("kein-uuid", gesperrt_von="a") is False

    async def test_zweimal_sperren_behaelt_status_von_vorher(self, service, speicher):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")
        await service.entsperren(CONTENT_ID, entsperrt_von="admin-1")

        assert speicher.payload["status"] == "approved"


@pytest.mark.unit
@pytest.mark.asyncio
class TestEntsperren:
    async def test_entsperren_stellt_status_von_vorher_wieder_her(
        self, service, speicher
    ):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")

        assert await service.entsperren(CONTENT_ID, entsperrt_von="admin-1") is True

        assert speicher.payload["status"] == "approved"
        assert "status_vor_sperre" not in speicher.payload

    async def test_entsperren_ohne_status_von_vorher_macht_sichtbar(
        self, service, speicher
    ):
        # Altbestand ohne Status-Feld: nach dem Entsperren sichtbar wie neu angelegt.
        del speicher.payload["status"]
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")

        await service.entsperren(CONTENT_ID, entsperrt_von="admin-1")

        assert speicher.payload["status"] == "released_internal"

    async def test_entsperren_nicht_gesperrt_aendert_nichts(self, service, speicher):
        assert await service.entsperren(CONTENT_ID, entsperrt_von="admin-1") is True

        assert speicher.payload["status"] == "approved"
        speicher.manager.async_client.set_payload.assert_not_called()

    async def test_entsperren_unbekannter_beitrag(self, service):
        assert await service.entsperren(str(uuid.uuid4()), entsperrt_von="a") is False
