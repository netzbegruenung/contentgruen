"""
Abweisen nur fuer offene Meldungen (Review zu #673, 13.11.2026).

Ein Abweisen aus einem veralteten Fenster schrieb eine schon bearbeitete Meldung
(Beitrag gesperrt) zu "abgewiesen" um. Jetzt antwortet der Endpunkt mit 409, und die
Begruendung kommt als Query-Parameter ``notes`` an.
"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.moderation import MELDUNG_NICHT_OFFEN
from api.v1.moderation import router as moderation_router
from dependencies import get_moderation_service, get_settings
from repositories.content_report_repository import MeldungNichtOffen
from services.moderation_service import ModerationService

ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}
REPORT_ID = "00000000-0000-4000-8000-000000000002"


def _client(service) -> TestClient:
    app = FastAPI()
    app.include_router(moderation_router, prefix="/api/v1/moderation")
    app.dependency_overrides[get_settings] = lambda: Mock()
    app.dependency_overrides[get_moderation_service] = lambda: service
    return TestClient(app)


@pytest.mark.unit
def test_abweisen_einer_nicht_offenen_meldung_ist_409():
    service = Mock()
    service.dismiss_report = AsyncMock(side_effect=MeldungNichtOffen(REPORT_ID))

    antwort = _client(service).put(
        f"/api/v1/moderation/reports/{REPORT_ID}/dismiss", headers=ADMIN
    )

    assert antwort.status_code == 409
    assert antwort.json()["detail"] == MELDUNG_NICHT_OFFEN


@pytest.mark.unit
def test_abweisen_nimmt_die_begruendung_aus_dem_query_parameter():
    service = Mock()
    service.dismiss_report = AsyncMock(return_value=True)

    antwort = _client(service).put(
        f"/api/v1/moderation/reports/{REPORT_ID}/dismiss",
        params={"notes": "Zulässige Meinungsäußerung: Zuspitzung"},
        headers=ADMIN,
    )

    assert antwort.status_code == 200
    assert (
        service.dismiss_report.await_args.kwargs["notes"]
        == "Zulässige Meinungsäußerung: Zuspitzung"
    )


@pytest.mark.unit
def test_abweisen_lehnt_eine_begruendung_ueber_500_zeichen_ab():
    service = Mock()
    service.dismiss_report = AsyncMock(return_value=True)

    antwort = _client(service).put(
        f"/api/v1/moderation/reports/{REPORT_ID}/dismiss",
        params={"notes": "x" * 501},
        headers=ADMIN,
    )

    assert antwort.status_code == 422
    service.dismiss_report.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_der_dienst_weist_nur_offene_ab_und_reicht_den_konflikt_durch():
    report_repo = MagicMock()
    report_repo.update_report_status = MagicMock(
        side_effect=MeldungNichtOffen(REPORT_ID)
    )
    service = ModerationService.__new__(ModerationService)
    service.report_repo = report_repo

    with pytest.raises(MeldungNichtOffen):
        await service.dismiss_report(REPORT_ID, "admin-1", notes="x")

    assert report_repo.update_report_status.call_args.kwargs["nur_offene"] is True
