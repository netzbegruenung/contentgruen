"""
PUT /api/v1/moderation/content/{id}/sperren und .../entsperren.

Admin-only; ein unbekannter Beitrag ist 404, eine ungueltige ID 422. Was Sperren am Beitrag und an den
Meldungen aendert, pruefen die Service-Tests (tests/unit/services/
test_moderation_service.py).
"""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import moderation as moderation_module
from api.v1.moderation import router as moderation_router
from dependencies import get_settings

CONTENT_ID = str(uuid.uuid4())
ADMIN = {"X-User": "admin-1", "X-Is-Admin": "true"}
MITWIRKENDE = {"X-User": "user-1", "X-Is-Admin": "false"}


@pytest.fixture
def service():
    mock = Mock()
    mock.sperren = AsyncMock(return_value=True)
    mock.entsperren = AsyncMock(return_value=True)
    mock.gesperrte_beitraege = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(moderation_router, prefix="/api/v1/moderation")
    app.dependency_overrides[get_settings] = lambda: Mock()
    with patch.object(moderation_module, "get_moderation_service", lambda: service):
        yield TestClient(app)


@pytest.mark.unit
@pytest.mark.parametrize("aktion", ["sperren", "entsperren"])
class TestSperrenApi:
    def test_admin_darf(self, client, service, aktion):
        antwort = client.put(
            f"/api/v1/moderation/content/{CONTENT_ID}/{aktion}", headers=ADMIN
        )

        assert antwort.status_code == 200
        assert antwort.json()["success"] is True
        getattr(service, aktion).assert_awaited_once()
        assert getattr(service, aktion).call_args.args[0] == CONTENT_ID

    def test_mitwirkende_duerfen_nicht(self, client, service, aktion):
        antwort = client.put(
            f"/api/v1/moderation/content/{CONTENT_ID}/{aktion}", headers=MITWIRKENDE
        )

        assert antwort.status_code == 403
        getattr(service, aktion).assert_not_called()

    def test_besucher_duerfen_nicht(self, client, service, aktion):
        antwort = client.put(f"/api/v1/moderation/content/{CONTENT_ID}/{aktion}")

        assert antwort.status_code == 401

    def test_unbekannter_beitrag_ist_404(self, client, service, aktion):
        getattr(service, aktion).return_value = False

        antwort = client.put(
            f"/api/v1/moderation/content/{CONTENT_ID}/{aktion}", headers=ADMIN
        )

        assert antwort.status_code == 404

    def test_ungueltige_id_ist_422(self, client, service, aktion):
        antwort = client.put(
            f"/api/v1/moderation/content/kein-uuid/{aktion}", headers=ADMIN
        )

        assert antwort.status_code == 422
        getattr(service, aktion).assert_not_called()


@pytest.mark.unit
def test_sperren_gibt_admin_als_sperrenden_weiter(client, service):
    client.put(f"/api/v1/moderation/content/{CONTENT_ID}/sperren", headers=ADMIN)

    assert service.sperren.call_args.kwargs["gesperrt_von"] == "admin-1"


@pytest.mark.unit
class TestGesperrteApi:
    def test_admin_bekommt_gesperrte(self, client, service):
        service.gesperrte_beitraege.return_value = [
            {"id": CONTENT_ID, "content_type": "commentary", "status": "blocked"}
        ]

        antwort = client.get("/api/v1/moderation/gesperrt", headers=ADMIN)

        assert antwort.status_code == 200
        assert antwort.json() == {
            "total": 1,
            "beitraege": [
                {"id": CONTENT_ID, "content_type": "commentary", "status": "blocked"}
            ],
        }

    def test_mitwirkende_duerfen_nicht(self, client, service):
        antwort = client.get("/api/v1/moderation/gesperrt", headers=MITWIRKENDE)

        assert antwort.status_code == 403
        service.gesperrte_beitraege.assert_not_called()

    def test_besucher_duerfen_nicht(self, client, service):
        antwort = client.get("/api/v1/moderation/gesperrt")

        assert antwort.status_code == 401
