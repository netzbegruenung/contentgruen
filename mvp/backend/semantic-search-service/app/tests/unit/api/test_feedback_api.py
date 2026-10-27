"""
Feedback an das Team (#343): POST /api/v1/feedback/senden und die Admin-Liste
GET /api/v1/feedback.

Senden darf jede Person, auch ohne Anmeldung. Gespeichert wird nur, was sie
eingibt (Freitext, optional Kontakt), und der Tag; keine Kennung, keine Sitzung.
"""

import uuid
from datetime import date
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.feedback import router as feedback_router
from dependencies import get_feedback_service
from services.feedback_service import FeedbackEintrag
from utils.rate_limiter import feedback_rate_limiter

pytestmark = [pytest.mark.unit, pytest.mark.api]

SENDEN = "/api/v1/feedback/senden"
LISTE = "/api/v1/feedback"
ADMIN = {"X-User": "admin", "X-Is-Admin": "true"}
EINTRAG = FeedbackEintrag(
    id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
    text="Der Kopieren-Knopf ist mobil schwer zu treffen.",
    kontakt="anna@example.org",
    eingegangen_am=date(2026, 10, 27),
)


@pytest.fixture
def service():
    service = Mock()
    service.neueste.return_value = [EINTRAG]
    return service


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(feedback_router, prefix="/api/v1/feedback")
    app.dependency_overrides[get_feedback_service] = lambda: service
    return TestClient(app)


@pytest.fixture(autouse=True)
def frisches_limit():
    feedback_rate_limiter._requests.clear()
    yield
    feedback_rate_limiter._requests.clear()


class TestSenden:
    def test_besucher_sendet_feedback_ohne_kontakt(self, client, service):
        response = client.post(SENDEN, json={"text": "Gefällt mir."})

        assert response.status_code == 201
        service.senden.assert_called_once_with("Gefällt mir.", None)

    def test_kontakt_wird_mitgespeichert(self, client, service):
        client.post(SENDEN, json={"text": "Bitte melden", "kontakt": " anna@x.org "})

        service.senden.assert_called_once_with("Bitte melden", "anna@x.org")

    def test_leerer_kontakt_gilt_als_keiner(self, client, service):
        client.post(SENDEN, json={"text": "Hallo", "kontakt": "   "})

        service.senden.assert_called_once_with("Hallo", None)

    def test_angemeldete_person_wird_nicht_mitgespeichert(self, client, service):
        client.post(SENDEN, json={"text": "Hallo"}, headers={"X-User": "user-001"})

        # Nur Text und Kontakt gehen an den Service, keine Kennung.
        service.senden.assert_called_once_with("Hallo", None)

    @pytest.mark.parametrize("text", ["", "   ", "x" * 2001])
    def test_text_leer_oder_zu_lang_ist_ungueltig(self, client, service, text):
        response = client.post(SENDEN, json={"text": text})

        assert response.status_code == 422
        service.senden.assert_not_called()

    def test_kontakt_zu_lang_ist_ungueltig(self, client, service):
        response = client.post(SENDEN, json={"text": "Hallo", "kontakt": "x" * 201})

        assert response.status_code == 422

    def test_zu_viele_sendungen_werden_abgewiesen(self, client, service):
        antworten = [
            client.post(SENDEN, json={"text": f"Nummer {i}"}).status_code
            for i in range(6)
        ]

        assert antworten == [201] * 5 + [429]
        assert service.senden.call_count == 5


class TestListe:
    def test_anonym_ist_nicht_angemeldet(self, client):
        assert client.get(LISTE).status_code == 401

    def test_angemeldet_ohne_admin_ist_verboten(self, client):
        assert client.get(LISTE, headers={"X-User": "normalo"}).status_code == 403

    def test_admin_sieht_feedback_mit_kontakt_und_tag(self, client):
        response = client.get(LISTE, headers=ADMIN)

        assert response.status_code == 200
        assert response.json() == {
            "aufbewahrung_tage": 180,
            "eintraege": [
                {
                    "id": "11111111-1111-1111-1111-111111111111",
                    "text": "Der Kopieren-Knopf ist mobil schwer zu treffen.",
                    "kontakt": "anna@example.org",
                    "eingegangen_am": "2026-10-27",
                }
            ],
        }
