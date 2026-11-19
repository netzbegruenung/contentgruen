"""
Meldung schliessen (Folge zu #673): Eine offene Meldung zu einem schon gesperrten
Beitrag wird erledigt, mit der vorhandenen Mail "gesperrt", ohne neue Sperre.
Abweisen passt dort nicht; auch Sperren von vor #448 (nur Status BLOCKED) zaehlen.
"""

from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.moderation import BEITRAG_NICHT_GESPERRT, MELDUNG_NICHT_OFFEN
from api.v1.moderation import router as moderation_router
from dependencies import get_moderation_service, get_settings
from domain.models.meldung import MelderAdresse
from repositories.content_report_repository import (
    BeitragGesperrt,
    BeitragNichtGesperrt,
    MeldungNichtOffen,
)
from services.meldung_mitteilen import Entscheidung
from services.moderation_service import ModerationService

ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}
REPORT_ID = "00000000-0000-4000-8000-000000000002"
CONTENT_ID = UUID("00000000-0000-4000-8000-000000000001")


def _client(service) -> TestClient:
    app = FastAPI()
    app.include_router(moderation_router, prefix="/api/v1/moderation")
    app.dependency_overrides[get_settings] = lambda: Mock()
    app.dependency_overrides[get_moderation_service] = lambda: service
    return TestClient(app)


def _service(*, sperre=None, status="visible", adresse=True):
    report_repo = MagicMock()
    report_repo.content_id_von = MagicMock(return_value=CONTENT_ID)

    def aktualisieren(**kwargs):
        if adresse:
            kwargs["melder_adressen"].append(
                MagicMock(spec=MelderAdresse, content_id=CONTENT_ID)
            )
        return MagicMock()

    report_repo.update_report_status = MagicMock(side_effect=aktualisieren)
    moderation_repo = AsyncMock()
    moderation_repo.laden.return_value = {"title": "Ein Titel", "status": status}
    service = ModerationService(
        report_repo=report_repo,
        moderation_repo=moderation_repo,
        sperre_repo=MagicMock(**{"aktive.return_value": sperre}),
    )
    service._entscheidung_mitteilen = AsyncMock()
    return service, report_repo


@pytest.mark.unit
def test_nur_admins_duerfen_schliessen():
    service = Mock()
    service.meldung_schliessen = AsyncMock(return_value=True)

    antwort = _client(service).put(
        f"/api/v1/moderation/reports/{REPORT_ID}/schliessen",
        headers={"X-User": "person-1"},
    )

    assert antwort.status_code in (401, 403)
    service.meldung_schliessen.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.parametrize(
    "fehler, detail",
    [
        (BeitragNichtGesperrt("x"), BEITRAG_NICHT_GESPERRT),
        (MeldungNichtOffen("x"), MELDUNG_NICHT_OFFEN),
    ],
)
def test_konflikte_sind_409(fehler, detail):
    service = Mock()
    service.meldung_schliessen = AsyncMock(side_effect=fehler)

    antwort = _client(service).put(
        f"/api/v1/moderation/reports/{REPORT_ID}/schliessen", headers=ADMIN
    )

    assert antwort.status_code == 409
    assert antwort.json()["detail"] == detail


@pytest.mark.unit
@pytest.mark.asyncio
async def test_schliessen_setzt_bearbeitet_und_schickt_die_mail_gesperrt():
    service, report_repo = _service(sperre=object())

    assert await service.meldung_schliessen(REPORT_ID, "admin-1")

    kwargs = report_repo.update_report_status.call_args.kwargs
    assert kwargs["status"] == "reviewed"
    assert kwargs["nur_offene"] is True
    assert kwargs["resolution_notes"] == "Beitrag gesperrt"
    entscheidung = service._entscheidung_mitteilen.await_args.args[1]
    assert entscheidung is Entscheidung.GESPERRT


@pytest.mark.unit
@pytest.mark.asyncio
async def test_schliessen_geht_auch_bei_einer_sperre_von_vor_448():
    service, _ = _service(sperre=None, status="blocked")

    assert await service.meldung_schliessen(REPORT_ID, "admin-1")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_schliessen_bei_sichtbarem_beitrag_ist_konflikt():
    service, report_repo = _service(sperre=None, status="visible")

    with pytest.raises(BeitragNichtGesperrt):
        await service.meldung_schliessen(REPORT_ID, "admin-1")

    report_repo.update_report_status.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_abweisen_lehnt_auch_eine_sperre_von_vor_448_ab():
    """Review zu 62e5d9a4: ohne Sperr-Eintrag zaehlt der Status BLOCKED am Beitrag."""
    service, report_repo = _service(sperre=None, status="blocked")

    with pytest.raises(BeitragGesperrt):
        await service.dismiss_report(REPORT_ID, "admin-1", notes="x")

    report_repo.update_report_status.assert_not_called()
