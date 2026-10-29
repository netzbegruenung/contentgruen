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
from unittest.mock import AsyncMock, MagicMock

import pytest

from repositories.implementations.qdrant.moderation_repository import (
    QdrantModerationRepository,
)
from domain.content_registry import BEITRAGSTYPEN_WERTE
from services.content.verweise_entfernen import VerweiseNichtEntfernt
from services.moderation_service import ModerationService
from tests.conftest import add_aussage_mit_verweis, create_base_content_fields

CONTENT_ID = str(uuid.uuid4())

# Sperren verlangt Sperrgrund und Begruendung (#448).
GRUND = {"sperrgrund": "ohne_bezug", "begruendung": "Kein Bezug zum Zweck."}


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
        vote_repo=MagicMock(),
        raw_input_repo=MagicMock(),
        sperre_repo=MagicMock(),
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestSperren:
    async def test_sperren_setzt_status_gesperrt(self, service, speicher):
        assert (
            await service.sperren(CONTENT_ID, gesperrt_von="admin-1", **GRUND) is True
        )

        assert _payload(speicher)["status"] == "blocked"

    async def test_sperren_setzt_meldungen_auf_bearbeitet(self, service):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1", **GRUND)

        aufruf = service.report_repo.update_reports_by_content_id.call_args.kwargs
        assert aufruf["content_id"] == uuid.UUID(CONTENT_ID)
        assert aufruf["status"] == "reviewed"
        assert aufruf["reviewed_by"] == "admin-1"

    async def test_sperren_loescht_nichts(self, service, speicher):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1", **GRUND)

        assert CONTENT_ID in speicher.get_data()

    async def test_sperren_unbekannter_beitrag(self, service):
        assert (
            await service.sperren(str(uuid.uuid4()), gesperrt_von="a", **GRUND) is False
        )
        service.report_repo.update_reports_by_content_id.assert_not_called()

    async def test_sperren_ungueltige_id(self, service):
        assert await service.sperren("kein-uuid", gesperrt_von="a", **GRUND) is False

    async def test_sperren_meldet_fehler_beim_meldungs_update(self, service, speicher):
        """Bleiben die Meldungen offen, darf Sperren keinen Erfolg melden."""
        service.report_repo.update_reports_by_content_id.side_effect = RuntimeError(
            "PostgreSQL weg"
        )

        with pytest.raises(RuntimeError):
            await service.sperren(CONTENT_ID, gesperrt_von="admin-1", **GRUND)

        # Gesperrt ist der Beitrag trotzdem; erneutes Sperren holt die Meldungen nach.
        assert _payload(speicher)["status"] == "blocked"

    async def test_zweimal_sperren_behaelt_status_von_vorher(self, service, speicher):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1", **GRUND)
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1", **GRUND)
        await service.entsperren(CONTENT_ID)

        assert _payload(speicher)["status"] == "visible"


@pytest.mark.unit
@pytest.mark.asyncio
class TestEntsperren:
    async def test_entsperren_stellt_status_von_vorher_wieder_her(
        self, service, speicher
    ):
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1", **GRUND)

        assert await service.entsperren(CONTENT_ID) is True

        assert _payload(speicher)["status"] == "visible"
        assert "status_vor_sperre" not in _payload(speicher)

    async def test_entsperren_ohne_status_von_vorher_macht_sichtbar(
        self, service, speicher
    ):
        # Ohne gemerkten Zustand gilt sichtbar: Die Suche findet nur sichtbare,
        # ein Beitrag ohne Status-Feld waere nach dem Entsperren nicht auffindbar.
        del _payload(speicher)["status"]
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1", **GRUND)

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
        await service.sperren(CONTENT_ID, gesperrt_von="admin-1", **GRUND)

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
        aussage_id = add_aussage_mit_verweis(speicher, CONTENT_ID)

        assert await service.delete_content(CONTENT_ID, "commentary", "admin-1")

        assert CONTENT_ID not in speicher.get_data()
        assert speicher.get_data()[aussage_id]["replysuggestions_count"] == 0
        aufruf = service.report_repo.update_reports_by_content_id.call_args.kwargs
        assert aufruf["reviewed_by"] == "admin-1"

    @pytest.mark.parametrize("typ", BEITRAGSTYPEN_WERTE)
    async def test_loeschen_entfernt_verweise_fuer_jeden_beitragstyp(
        self, service, speicher, typ
    ):
        """Aussagen verweisen auf Beitraege jedes Typs, nicht nur auf Kommentare."""
        beitrag_id = str(uuid.uuid4())
        speicher.add_test_data(
            typ, [{**create_base_content_fields(), "id": beitrag_id, "text": "x"}]
        )
        aussage_id = add_aussage_mit_verweis(speicher, beitrag_id)

        assert await service.delete_content(beitrag_id, typ, "admin-1")

        assert beitrag_id not in speicher.get_data()
        assert speicher.get_data()[aussage_id]["replysuggestions_count"] == 0

    async def test_loeschen_verweise_scheitern_meldet_fehler_beitrag_bleibt(
        self, service, speicher
    ):
        """Erst die Verweise, dann der Beitrag: Ein erneuter Versuch raeumt noch auf."""
        add_aussage_mit_verweis(speicher, CONTENT_ID)
        service.moderation_repo.aus_aussagen_entfernen = AsyncMock(
            side_effect=RuntimeError("Qdrant nicht erreichbar")
        )

        with pytest.raises(VerweiseNichtEntfernt):
            await service.delete_content(CONTENT_ID, "commentary", "admin-1")

        assert CONTENT_ID in speicher.get_data()
        service.report_repo.update_reports_by_content_id.assert_not_called()

    async def test_loeschen_nimmt_stimmen_und_ausformuliert_in_mit(self, service):
        """Nach dem Beitrag zeigt nichts mehr auf ihn (#421)."""
        assert await service.delete_content(CONTENT_ID, "commentary", None)

        kennung = uuid.UUID(CONTENT_ID)
        service._vote_repo.loeschen_fuer_beitrag.assert_called_once_with(kennung)
        service._raw_input_repo.ausformuliert_in_loeschen.assert_called_once_with(
            kennung
        )
        aufruf = service.report_repo.update_reports_by_content_id.call_args.kwargs
        assert aufruf["reviewed_by"] is None
        # Bearbeitete Meldungen behalten Entscheidung und Loeschfrist.
        assert aufruf["nur_offene"] is True

    async def test_loeschen_stimmen_scheitern_beitrag_bleibt(self, service, speicher):
        """Erst Stimmen und "ausformuliert in", dann der Beitrag: Ein neuer Versuch findet ihn."""
        service._vote_repo.loeschen_fuer_beitrag.side_effect = RuntimeError("weg")

        with pytest.raises(RuntimeError):
            await service.delete_content(CONTENT_ID, "commentary", "admin-1")

        assert CONTENT_ID in speicher.get_data()

    async def test_loeschen_unbekannter_beitrag_ist_false(self, service):
        service.moderation_repo.aus_aussagen_entfernen = AsyncMock()

        assert not await service.delete_content(str(uuid.uuid4()), "post", "a")

        service.moderation_repo.aus_aussagen_entfernen.assert_not_awaited()


ADMIN_KENNUNG = "admin.person@example.org"


@pytest.mark.unit
@pytest.mark.asyncio
class TestKeineAdminKennungImLog:
    """Wer moderiert hat, steht an den Meldungen (reviewed_by), nicht im Log."""

    async def test_sperren_und_entsperren(self, service, caplog):
        caplog.set_level(logging.DEBUG)

        await service.sperren(CONTENT_ID, gesperrt_von=ADMIN_KENNUNG, **GRUND)
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
