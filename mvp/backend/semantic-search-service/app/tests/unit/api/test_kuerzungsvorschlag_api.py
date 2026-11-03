"""
Kürzungsvorschlag (#403): POST /api/v1/kuerzungsvorschlag.

Nur für Angemeldete (das Kommentar-Formular ist es auch), auf Klick, mit eigenem
Rate-Limit. Nichts wird gespeichert.
"""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.kuerzungsvorschlag import TEXT_MAX
from api.v1.kuerzungsvorschlag import router as kuerzungsvorschlag_router
from dependencies import get_kuerzungsvorschlag_service
from utils.rate_limiter import kuerzungsvorschlag_rate_limiter

pytestmark = [pytest.mark.unit, pytest.mark.api]

PFAD = "/api/v1/kuerzungsvorschlag"
ANGEMELDET = {"X-User": "person-1"}


@pytest.fixture
def service():
    service = Mock()
    service.vorschlagen.return_value = "Die Wärmepumpe spart Geld."
    return service


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(kuerzungsvorschlag_router, prefix=PFAD)
    app.dependency_overrides[get_kuerzungsvorschlag_service] = lambda: service
    return TestClient(app)


@pytest.fixture(autouse=True)
def frisches_limit():
    kuerzungsvorschlag_rate_limiter._requests.clear()
    yield
    kuerzungsvorschlag_rate_limiter._requests.clear()


def test_liefert_den_vorschlag(client, service):
    response = client.post(
        PFAD,
        json={
            "text": "Die Wärmepumpe, die im Keller steht, spart Geld.",
            "aussage": "A",
        },
        headers=ANGEMELDET,
    )

    assert response.status_code == 200
    assert response.json() == {"vorschlag": "Die Wärmepumpe spart Geld."}
    service.vorschlagen.assert_called_once_with(
        "Die Wärmepumpe, die im Keller steht, spart Geld.", "A"
    )


def test_ohne_passenden_satz_ist_der_vorschlag_leer(client, service):
    service.vorschlagen.return_value = None

    response = client.post(PFAD, json={"text": "x"}, headers=ANGEMELDET)

    assert response.status_code == 200
    assert response.json() == {"vorschlag": None}


def test_nur_fuer_angemeldete(client):
    response = client.post(PFAD, json={"text": "Ein Satz."})

    assert response.status_code == 401


def test_zu_langer_text_wird_abgewiesen(client):
    response = client.post(
        PFAD, json={"text": "x" * (TEXT_MAX + 1)}, headers=ANGEMELDET
    )

    assert response.status_code == 422


def test_rate_limit(client):
    for _ in range(kuerzungsvorschlag_rate_limiter.max_requests):
        client.post(PFAD, json={"text": "Ein Satz."}, headers=ANGEMELDET)

    response = client.post(PFAD, json={"text": "Ein Satz."}, headers=ANGEMELDET)

    assert response.status_code == 429


def test_fehlendes_sprachmodell_ergibt_503(client, service):
    service.vorschlagen.side_effect = OSError("de_core_news_sm fehlt")

    response = client.post(PFAD, json={"text": "Ein Satz."}, headers=ANGEMELDET)

    assert response.status_code == 503
