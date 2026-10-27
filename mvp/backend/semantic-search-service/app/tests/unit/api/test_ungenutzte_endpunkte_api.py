"""
Eingebundene Endpunkte von Kommentar und Hintergrundinfo ohne Aufrufer in
Frontend und BFF: die Wurzel-Stubs, die Suche je Typ und ``generic_text/getAll``.

Aus tests/integration/api/v1/test_commentary_api.py und test_generic_text_api.py.
Dort liefen nur die Tests ohne Patch wirklich (Wurzel, Validierung); die Patches
auf ``dependencies.get_*_service`` griffen nicht, weil FastAPI die Funktionen schon
beim Import in ``Depends`` gebunden hatte. Solange die Endpunkte eingebunden sind,
bleiben sie hier geprueft.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.commentary import router as commentary_router
from api.v1.generic_text import router as generic_text_router
from dependencies import get_commentary_service, get_generic_text_service

SUCHEN = [
    "/api/v1/commentary/searchCommentaries",
    "/api/v1/generic_text/searchGenericText",
]


@pytest.fixture
def service():
    mock = MagicMock()
    mock.search = AsyncMock(return_value=[])
    mock.get_all = AsyncMock(return_value=[])
    mock.count = AsyncMock(return_value=7)
    return mock


@pytest.fixture
def client(service):
    app = FastAPI()
    app.include_router(commentary_router, prefix="/api/v1/commentary")
    app.include_router(generic_text_router, prefix="/api/v1/generic_text")
    app.dependency_overrides[get_commentary_service] = lambda: service
    app.dependency_overrides[get_generic_text_service] = lambda: service
    return TestClient(app)


@pytest.mark.api
@pytest.mark.parametrize("pfad", ["/api/v1/commentary/", "/api/v1/generic_text/"])
def test_wurzel_antwortet(client, pfad):
    assert client.get(pfad).status_code == 200


@pytest.mark.api
@pytest.mark.parametrize("url", SUCHEN)
class TestSucheJeTyp:
    def test_ohne_treffer_leere_liste(self, client, service, url):
        antwort = client.post(url, json={"query_text": "klima", "limit": 3})

        assert antwort.status_code == 200
        assert antwort.json() == {"results": []}
        service.search.assert_awaited_once_with("klima", 3)

    def test_ohne_text_gibt_422(self, client, service, url):
        assert client.post(url, json={"limit": 5}).status_code == 422
        service.search.assert_not_awaited()

    def test_kein_json_gibt_422(self, client, service, url):
        antwort = client.post(
            url, content="kein json", headers={"Content-Type": "application/json"}
        )

        assert antwort.status_code == 422
        service.search.assert_not_awaited()

    def test_fehler_im_service_gibt_500(self, client, service, url):
        service.search.side_effect = RuntimeError("weg")

        assert client.post(url, json={"query_text": "klima"}).status_code == 500


@pytest.mark.api
class TestHintergrundinfosAlle:
    def test_seite_wird_in_offset_umgerechnet(self, client, service):
        antwort = client.get(
            "/api/v1/generic_text/getAll", params={"page": 3, "page_size": 10}
        )

        assert antwort.status_code == 200
        assert antwort.json() == {
            "results_count": 0,
            "results": [],
            "total_records_count": 7,
        }
        service.get_all.assert_awaited_once_with(limit=10, offset=20)

    @pytest.mark.parametrize("params", [{"page": 0}, {"page_size": 101}])
    def test_ungueltige_seite_gibt_422(self, client, service, params):
        antwort = client.get("/api/v1/generic_text/getAll", params=params)

        assert antwort.status_code == 422
        service.get_all.assert_not_awaited()
