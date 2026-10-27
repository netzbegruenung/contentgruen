"""
/api/v1/reference: Herkunftsangaben suchen, anlegen und lesen.

Aus tests/integration/api/v1/test_reference_api.py. Dort zielte der Patch auf
``api.v1.reference.get_reference_service``, das FastAPI aber schon beim Import in
``Depends`` gebunden hatte; jeder Test lief gegen den echten Service. Hier wie in
den uebrigen API-Tests ueber ``dependency_overrides``.
"""

import datetime
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.reference import router as reference_router
from dependencies import get_reference_service
from middleware import rate_limiter
from middleware.rate_limiter import RateLimiter

PREFIX = "/api/v1/reference"
ERSTELLT = datetime.datetime(2026, 1, 1)


def _herkunft(reference_string="https://example.org/rede", **felder):
    werte = dict(
        id=uuid.uuid4(),
        reference_string=reference_string,
        text="Rede im Landtag",
        created=ERSTELLT,
        last_modified=ERSTELLT,
        original_author="autor-1",
        usage_count=3,
        score=0.9,
    )
    werte.update(felder)
    return SimpleNamespace(**werte)


@pytest.fixture
def service():
    mock = MagicMock()
    mock.find_exact_match = AsyncMock(return_value=None)
    mock.add_reference = AsyncMock(return_value=(uuid.uuid4(), True, "Created"))
    mock.search = AsyncMock(return_value=[])
    mock.get = AsyncMock(return_value=None)
    return mock


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(reference_router, prefix=PREFIX)
    app.dependency_overrides[get_reference_service] = lambda: service
    # Frische Limiter je Test, sonst tragen die Fenster ineinander.
    with patch.object(
        rate_limiter, "reference_creation_limiter", RateLimiter(requests_per_minute=3)
    ), patch.object(rate_limiter, "reference_search_limiter", RateLimiter()):
        yield TestClient(app)


def _anlegen(client, headers=None, **body):
    headers = {"X-User": "user-1"} if headers is None else headers
    werte = {"reference_string": "https://example.org/rede", "text": "Rede"}
    werte.update(body)
    return client.post(f"{PREFIX}/add", json=werte, headers=headers)


@pytest.mark.api
class TestAnlegen:
    def test_neue_herkunft_wird_angelegt(self, client, service):
        antwort = _anlegen(client)

        assert antwort.status_code == 200
        assert antwort.json()["was_new"] is True
        herkunft, autor, *_ = service.add_reference.await_args.args
        assert herkunft.reference_string == "https://example.org/rede"
        assert autor == "user-1"

    def test_vorhandene_herkunft_wird_nicht_neu_angelegt(self, client, service):
        vorhanden = _herkunft()
        service.find_exact_match.return_value = vorhanden

        antwort = _anlegen(client)

        assert antwort.status_code == 200
        assert antwort.json()["was_new"] is False
        assert antwort.json()["id"] == str(vorhanden.id)
        service.add_reference.assert_not_awaited()

    def test_ohne_x_user_gibt_422(self, client, service):
        assert _anlegen(client, headers={}).status_code == 422
        service.add_reference.assert_not_awaited()

    def test_ueber_dem_limit_gibt_429(self, client):
        codes = [_anlegen(client).status_code for _ in range(4)]

        assert codes == [200, 200, 200, 429]


@pytest.mark.api
class TestSuchen:
    def test_genauer_treffer_wird_gemeldet(self, client, service):
        treffer = _herkunft("https://example.org/genau")
        service.search.return_value = [_herkunft(), treffer]

        antwort = client.post(
            f"{PREFIX}/search", json={"query_text": "https://example.org/genau"}
        )

        assert antwort.status_code == 200
        daten = antwort.json()
        assert len(daten["results"]) == 2
        assert daten["has_exact_match"] is True
        assert daten["exact_match_id"] == str(treffer.id)

    def test_ohne_genauen_treffer(self, client, service):
        service.search.return_value = [_herkunft()]

        antwort = client.post(f"{PREFIX}/search", json={"query_text": "rede"})

        assert antwort.status_code == 200
        daten = antwort.json()
        assert daten["has_exact_match"] is False
        assert daten["exact_match_id"] is None


@pytest.mark.api
class TestLesen:
    def test_herkunft_per_id(self, client, service):
        herkunft = _herkunft()
        service.get.return_value = herkunft

        antwort = client.get(f"{PREFIX}/getById", params={"reference_id": herkunft.id})

        assert antwort.status_code == 200
        assert antwort.json()["reference_string"] == "https://example.org/rede"
        assert antwort.json()["usage_count"] == 3

    def test_unbekannte_id_gibt_404(self, client):
        antwort = client.get(f"{PREFIX}/getById", params={"reference_id": uuid.uuid4()})

        assert antwort.status_code == 404
