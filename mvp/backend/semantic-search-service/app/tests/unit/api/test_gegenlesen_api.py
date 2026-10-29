"""
Gegenlesen beim Schreiben (#358): POST /api/v1/gegenlesen.

Nur für Angemeldete (die Beitragsformulare sind es auch), mit eigenem Rate-Limit, weil
das Formular etwa jede Sekunde nachfragt. Nichts wird gespeichert.
"""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.gegenlesen import router as gegenlesen_router
from dependencies import get_gegenlesen_service
from services.gegenlesen.gegenlesen_service import Anmerkung, Gegengelesen
from utils.rate_limiter import gegenlesen_rate_limiter

pytestmark = [pytest.mark.unit, pytest.mark.api]

PFAD = "/api/v1/gegenlesen"
ANGEMELDET = {"X-User": "person-1"}
ERGEBNIS = Gegengelesen(
    guete=7,
    anmerkungen=[
        Anmerkung(
            art="verneinung",
            stelle="titel",
            text="Der Titel beginnt mit „Nicht“.",
            woerter=["Nicht"],
        )
    ],
)


@pytest.fixture
def service():
    service = Mock()
    service.gegenlesen.return_value = ERGEBNIS
    return service


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(gegenlesen_router, prefix=PFAD)
    app.dependency_overrides[get_gegenlesen_service] = lambda: service
    return TestClient(app)


@pytest.fixture(autouse=True)
def frisches_limit():
    gegenlesen_rate_limiter._requests.clear()
    yield
    gegenlesen_rate_limiter._requests.clear()


def test_liefert_guete_und_anmerkungen(client, service):
    response = client.post(
        PFAD,
        json={"titel": "Nicht so", "text": "Ein Text.", "aussage": "Eine Aussage"},
        headers=ANGEMELDET,
    )

    assert response.status_code == 200
    assert response.json() == {
        "guete": 7,
        "anmerkungen": [
            {
                "art": "verneinung",
                "stelle": "titel",
                "text": "Der Titel beginnt mit „Nicht“.",
                "woerter": ["Nicht"],
            }
        ],
    }
    service.gegenlesen.assert_called_once_with("Nicht so", "Ein Text.", "Eine Aussage")


def test_aussage_und_text_sind_optional(client, service):
    response = client.post(PFAD, json={"titel": "Nur ein Titel"}, headers=ANGEMELDET)

    assert response.status_code == 200
    service.gegenlesen.assert_called_once_with("Nur ein Titel", "", None)


@pytest.mark.parametrize("kopf", [{}, {"X-User": "anonymous"}])
def test_ohne_anmeldung_401(client, service, kopf):
    response = client.post(PFAD, json={"titel": "Titel"}, headers=kopf)

    assert response.status_code == 401
    service.gegenlesen.assert_not_called()


def test_zu_langer_text_422(client):
    response = client.post(
        PFAD, json={"titel": "T", "text": "x" * 10_001}, headers=ANGEMELDET
    )

    assert response.status_code == 422


def test_rate_limit_je_person(client):
    for _ in range(gegenlesen_rate_limiter.max_requests):
        assert (
            client.post(PFAD, json={"titel": "T"}, headers=ANGEMELDET).status_code
            == 200
        )

    assert client.post(PFAD, json={"titel": "T"}, headers=ANGEMELDET).status_code == 429
    assert (
        client.post(
            PFAD, json={"titel": "T"}, headers={"X-User": "person-2"}
        ).status_code
        == 200
    )


def test_ohne_sprachmodell_503(client, service):
    service.gegenlesen.side_effect = ImportError("spacy")

    response = client.post(PFAD, json={"titel": "Titel"}, headers=ANGEMELDET)

    assert response.status_code == 503
