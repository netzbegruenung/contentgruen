"""
GET /api/v1/sperren/meine und POST /api/v1/sperren/{id}/widerspruch (#448).

Nur angemeldete Personen; wessen Sperren, ergibt sich aus X-User. Was der Service
daraus macht, pruefen tests/unit/services/test_sperre_mit_grund.py.
"""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import sperren as sperren_module
from api.v1.sperren import router as sperren_router
from repositories.sperre_repository import Widerspruchsergebnis

AUTORIN = {"X-User": "autorin-1"}
SPERRE_ID = str(uuid.uuid4())
NACHRICHT = {
    "id": SPERRE_ID,
    "content_id": str(uuid.uuid4()),
    "content_type": "commentary",
    "titel": "Tempolimit rettet Leben",
    "sperrgrund": "unterstellung",
    "begruendung": "Unterstellt Bosheit.",
    "gesperrt_am": "2026-10-29T10:00:00+00:00",
    "widerspruch_am": None,
    "pruefung": None,
    "pruefung_begruendung": None,
    "geprueft_am": None,
}


@pytest.fixture
def service():
    mock = Mock()
    mock.meine_sperren = AsyncMock(return_value=[NACHRICHT])
    mock.widersprechen = AsyncMock(return_value=Widerspruchsergebnis.ANGENOMMEN)
    return mock


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(sperren_router, prefix="/api/v1/sperren")
    with patch.object(sperren_module, "get_moderation_service", lambda: service):
        yield TestClient(app)


@pytest.mark.unit
class TestMeineSperren:
    def test_liefert_die_sperrnachrichten_der_angemeldeten_person(
        self, client, service
    ):
        antwort = client.get("/api/v1/sperren/meine", headers=AUTORIN)

        assert antwort.status_code == 200
        assert antwort.json() == {"sperren": [NACHRICHT]}
        service.meine_sperren.assert_awaited_once_with("autorin-1")

    @pytest.mark.parametrize("kopf", [{}, {"X-User": "anonymous"}])
    def test_besucher_bekommen_401(self, client, service, kopf):
        antwort = client.get("/api/v1/sperren/meine", headers=kopf)

        assert antwort.status_code == 401
        service.meine_sperren.assert_not_called()


@pytest.mark.unit
class TestWiderspruch:
    PFAD = f"/api/v1/sperren/{SPERRE_ID}/widerspruch"

    def test_widerspruch_geht_mit_kennung_aus_der_anmeldung(self, client, service):
        antwort = client.post(
            self.PFAD, headers=AUTORIN, json={"text": "Das ist belegt."}
        )

        assert antwort.status_code == 200
        service.widersprechen.assert_awaited_once_with(
            SPERRE_ID, "autorin-1", "Das ist belegt."
        )

    def test_widerspruch_ohne_text(self, client, service):
        antwort = client.post(self.PFAD, headers=AUTORIN, json={})

        assert antwort.status_code == 200
        assert service.widersprechen.call_args.args[2] is None

    def test_fremde_oder_unbekannte_sperre_ist_404(self, client, service):
        service.widersprechen.return_value = Widerspruchsergebnis.NICHT_GEFUNDEN

        antwort = client.post(self.PFAD, headers=AUTORIN, json={})

        assert antwort.status_code == 404

    def test_zweiter_widerspruch_ist_409(self, client, service):
        service.widersprechen.return_value = Widerspruchsergebnis.SCHON_WIDERSPROCHEN

        antwort = client.post(self.PFAD, headers=AUTORIN, json={})

        assert antwort.status_code == 409

    def test_zu_langer_text_ist_422(self, client, service):
        antwort = client.post(self.PFAD, headers=AUTORIN, json={"text": "x" * 2001})

        assert antwort.status_code == 422
        service.widersprechen.assert_not_called()

    def test_besucher_bekommen_401(self, client, service):
        antwort = client.post(self.PFAD, json={})

        assert antwort.status_code == 401
        service.widersprechen.assert_not_called()
