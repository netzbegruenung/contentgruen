"""
Die Moderations-Endpunkte schreiben keine Admin-Kennung ins Log.

Unter Keycloak ist die Kennung aus X-User eine Mail-Adresse, also ein
Personendatum. Wer gesperrt, entsperrt, geloescht oder abgewiesen hat, steht an
den Meldungen in PostgreSQL (reviewed_by); das Log braucht es nicht.
"""

import logging
import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import moderation as moderation_module
from api.v1.moderation import router as moderation_router
from dependencies import get_settings

ADMIN_KENNUNG = "admin.person@example.org"
ADMIN = {"X-User": ADMIN_KENNUNG, "X-Is-Admin": "true"}
CONTENT_ID = str(uuid.uuid4())
REPORT_ID = str(uuid.uuid4())


@pytest.fixture
def service():
    mock = Mock()
    mock.get_reports = AsyncMock(return_value=[])
    mock.sperren = AsyncMock(return_value=True)
    mock.entsperren = AsyncMock(return_value=True)
    mock.gesperrte_beitraege = AsyncMock(return_value=[])
    mock.sperre_bestaetigen = AsyncMock(return_value=True)
    mock.delete_content = AsyncMock(return_value=True)
    mock.dismiss_report = AsyncMock(return_value=True)
    mock.get_report_stats = Mock(
        return_value={
            "total": 0,
            "by_status": {},
            "pending": 0,
            "reviewed": 0,
            "dismissed": 0,
        }
    )
    return mock


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(moderation_router, prefix="/api/v1/moderation")
    app.dependency_overrides[get_settings] = lambda: Mock()
    with patch.object(moderation_module, "get_moderation_service", lambda: service):
        yield TestClient(app)


@pytest.mark.unit
@pytest.mark.parametrize(
    "methode, pfad",
    [
        ("get", "/reports"),
        ("put", f"/content/{CONTENT_ID}/sperren"),
        ("put", f"/content/{CONTENT_ID}/entsperren"),
        ("put", f"/sperren/{REPORT_ID}/bestaetigen"),
        ("get", "/gesperrt"),
        ("delete", f"/content/commentary/{CONTENT_ID}"),
        ("put", f"/reports/{REPORT_ID}/dismiss"),
        ("get", "/stats"),
    ],
)
def test_admin_endpunkt_loggt_keine_admin_kennung(client, caplog, methode, pfad):
    caplog.set_level(logging.DEBUG)

    # Sperren und Bestaetigen verlangen eine Begruendung (#448).
    koerper = {"sperrgrund": "unterstellung", "begruendung": "x"}
    extra = {"json": koerper} if methode == "put" else {}
    antwort = getattr(client, methode)(
        f"/api/v1/moderation{pfad}", headers=ADMIN, **extra
    )

    assert antwort.status_code == 200
    assert any(
        r.name == moderation_module.__name__ for r in caplog.records
    ), "Der Endpunkt soll seine Aktion weiter loggen"
    assert ADMIN_KENNUNG not in caplog.text
