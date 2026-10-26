"""
Sperren und Entsperren eines gemeldeten Beitrags (ModerationService).

Ein Admin sperrt, statt zu loeschen: Der Beitrag bleibt im Speicher, bekommt den
Status "blocked" und verschwindet damit aus allen Lesepfaden der Repositories.
Die Meldungen zum Beitrag stehen danach auf bearbeitet. Entsperren stellt den
Status von vor der Sperre wieder her.
"""

import uuid
import json
import logging
from unittest.mock import MagicMock

import pytest

from repositories.implementations.qdrant.moderation_repository import (
    QdrantModerationRepository,
)
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
                "status": "visible",
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
    report_repo.update_report_status = MagicMock(return_value=MagicMock())
    return ModerationService(
        report_repo=report_repo,
        moderation_repo=QdrantModerationRepository(embeddings_manager=speicher),
    )


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

    async def test_sperren_ungueltige_id(self, service):
        assert await service.sperren("kein-uuid", gesperrt_von="a") is False

    async def test_sperren_meldet_fehler_beim_meldungs_update(self, service, speicher):
        """Bleiben die Meldungen offen, darf Sperren keinen Erfolg melden."""
        service.report_repo.update_reports_by_content_id.side_effect = RuntimeError(
            "PostgreSQL weg"
        )

        with pytest.raises(RuntimeError):
            await service.sperren(CONTENT_ID, gesperrt_von="admin-1")

        # Gesperrt ist der Beitrag trotzdem; erneutes Sperren holt die Meldungen nach.
        assert _payload(speicher)["status"] == "blocked"

    async def test_zweimal_sperren_behaelt_status_von_vorher(self, service, speicher):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")
        await service.entsperren(CONTENT_ID)

        assert _payload(speicher)["status"] == "visible"


@pytest.mark.unit
@pytest.mark.asyncio
class TestEntsperren:
    async def test_entsperren_stellt_status_von_vorher_wieder_her(
        self, service, speicher
    ):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")

        assert await service.entsperren(CONTENT_ID) is True

        assert _payload(speicher)["status"] == "visible"
        assert "status_vor_sperre" not in _payload(speicher)

    async def test_entsperren_ohne_status_von_vorher_macht_sichtbar(
        self, service, speicher
    ):
        # Ohne gemerkten Zustand gilt sichtbar: Die Suche findet nur sichtbare,
        # ein Beitrag ohne Status-Feld waere nach dem Entsperren nicht auffindbar.
        del _payload(speicher)["status"]
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")

        await service.entsperren(CONTENT_ID)

        assert _payload(speicher)["status"] == "visible"
        assert "status_vor_sperre" not in _payload(speicher)

    async def test_entsperren_nicht_gesperrt_aendert_nichts(self, service, speicher):
        assert await service.entsperren(CONTENT_ID) is True

        assert _payload(speicher)["status"] == "visible"
        speicher.async_client.set_payload.assert_not_called()

    async def test_entsperren_unbekannter_beitrag(self, service):
        assert await service.entsperren(str(uuid.uuid4())) is False


@pytest.mark.unit
@pytest.mark.asyncio
class TestGesperrteBeitraege:
    """Admins finden gesperrte Beitraege auch ohne Meldung, etwa nach einem Loeschantrag."""

    async def test_listet_nur_gesperrte(self, service, speicher):
        anderer = str(uuid.uuid4())
        speicher.add_test_data(
            "reference",
            [
                {
                    **create_base_content_fields(),
                    "id": anderer,
                    "text": "Sichtbare Hintergrundinfo",
                    "status": "visible",
                }
            ],
        )
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1")

        gesperrte = await service.gesperrte_beitraege()

        assert [beitrag["id"] for beitrag in gesperrte] == [CONTENT_ID]
        assert gesperrte[0]["text"] == "Gemeldeter Kommentar"

    async def test_leer_ohne_sperre(self, service):
        assert await service.gesperrte_beitraege() == []


@pytest.mark.unit
@pytest.mark.asyncio
class TestLoeschen:
    async def test_loeschen_entfernt_beitrag_und_verweise_aus_aussagen(
        self, service, speicher
    ):
        aussage_id = str(uuid.uuid4())
        speicher.add_test_data(
            "statement",
            [
                {
                    **create_base_content_fields(),
                    "id": aussage_id,
                    "replysuggestions": json.dumps([{"id": CONTENT_ID}]),
                    "replysuggestions_count": 1,
                }
            ],
        )

        assert await service.delete_content(CONTENT_ID, "commentary", "admin-1")

        assert CONTENT_ID not in speicher.get_data()
        assert speicher.get_data()[aussage_id]["replysuggestions_count"] == 0
        aufruf = service.report_repo.update_reports_by_content_id.call_args.kwargs
        assert aufruf["reviewed_by"] == "admin-1"


ADMIN_KENNUNG = "admin.person@example.org"


@pytest.mark.unit
@pytest.mark.asyncio
class TestKeineAdminKennungImLog:
    """Wer moderiert hat, steht an den Meldungen (reviewed_by), nicht im Log."""

    async def test_sperren_und_entsperren(self, service, caplog):
        caplog.set_level(logging.DEBUG)

        await service.sperren(CONTENT_ID, gesperrt_von=ADMIN_KENNUNG)
        await service.entsperren(CONTENT_ID)

        assert "gesperrt" in caplog.text and "entsperrt" in caplog.text
        assert ADMIN_KENNUNG not in caplog.text

    async def test_loeschen(self, service, caplog):
        caplog.set_level(logging.DEBUG)

        await service.delete_content(CONTENT_ID, "commentary", ADMIN_KENNUNG)

        assert "deleted" in caplog.text
        assert ADMIN_KENNUNG not in caplog.text

    async def test_abweisen(self, service, caplog):
        caplog.set_level(logging.DEBUG)

        assert await service.dismiss_report(str(uuid.uuid4()), ADMIN_KENNUNG)

        assert "dismissed" in caplog.text
        assert ADMIN_KENNUNG not in caplog.text
