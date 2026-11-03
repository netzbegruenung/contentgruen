"""
Spracherkennung beim Schreiben (#405): POST /api/v1/spracherkennung.

Nur für Angemeldete (Beitragsformulare und "Aussage vorab anlegen" sind es auch), mit
eigenem Rate-Limit, weil die Formulare etwa jede Sekunde nachfragen. Nichts wird
gespeichert.
"""

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.v1.spracherkennung as spracherkennung_api
from api.v1.spracherkennung import TEXT_MAX
from api.v1.spracherkennung import router as spracherkennung_router
from dependencies import get_spracherkennung
from utils.rate_limiter import spracherkennung_rate_limiter

pytestmark = [pytest.mark.unit, pytest.mark.api]

PFAD = "/api/v1/spracherkennung"
ANGEMELDET = {"X-User": "person-1"}


@pytest.fixture
def erkennung():
    erkennung = Mock()
    erkennung.fremdsprache.return_value = "en"
    return erkennung


@pytest.fixture
def client(erkennung):
    app = FastAPI()
    app.include_router(spracherkennung_router, prefix=PFAD)
    app.dependency_overrides[get_spracherkennung] = lambda: erkennung
    return TestClient(app)


@pytest.fixture(autouse=True)
def frisches_limit():
    spracherkennung_rate_limiter._requests.clear()
    yield
    spracherkennung_rate_limiter._requests.clear()


def test_liefert_fremde_sprache(client, erkennung):
    response = client.post(
        PFAD, json={"text": "Heat pumps are too expensive."}, headers=ANGEMELDET
    )

    assert response.status_code == 200
    assert response.json() == {"sprache": "en"}
    erkennung.fremdsprache.assert_called_once_with("Heat pumps are too expensive.")


def test_deutsch_ohne_sprache(client, erkennung):
    erkennung.fremdsprache.return_value = None

    response = client.post(PFAD, json={"text": "Ein Text."}, headers=ANGEMELDET)

    assert response.status_code == 200
    assert response.json() == {"sprache": None}


@pytest.mark.parametrize("kopf", [{}, {"X-User": "anonymous"}])
def test_ohne_anmeldung_401(client, erkennung, kopf):
    response = client.post(PFAD, json={"text": "Text"}, headers=kopf)

    assert response.status_code == 401
    erkennung.fremdsprache.assert_not_called()


def test_zu_langer_text_422(client):
    response = client.post(
        PFAD, json={"text": "x" * (TEXT_MAX + 1)}, headers=ANGEMELDET
    )

    assert response.status_code == 422


def test_rate_limit_je_person(client):
    for _ in range(spracherkennung_rate_limiter.max_requests):
        assert (
            client.post(PFAD, json={"text": "T"}, headers=ANGEMELDET).status_code == 200
        )

    assert client.post(PFAD, json={"text": "T"}, headers=ANGEMELDET).status_code == 429
    assert (
        client.post(
            PFAD, json={"text": "T"}, headers={"X-User": "person-2"}
        ).status_code
        == 200
    )


@pytest.mark.parametrize("fehler", [ImportError("lingua"), AttributeError("EN")])
def test_ohne_lingua_503_ohne_text_im_log(
    client, erkennung, fehler, caplog, monkeypatch
):
    # Fehlt Lingua oder scheitert sein Bau, zeigt das Formular nur keinen Sprachhinweis;
    # geloggt wird der Fehlertyp, nie der Text.
    monkeypatch.setattr(spracherkennung_api, "_nicht_verfuegbar_geloggt", False)
    erkennung.fremdsprache.side_effect = fehler
    text = "Heat pumps are far too expensive."

    response = client.post(PFAD, json={"text": text}, headers=ANGEMELDET)

    assert response.status_code == 503
    assert type(fehler).__name__ in caplog.text
    assert text not in caplog.text
