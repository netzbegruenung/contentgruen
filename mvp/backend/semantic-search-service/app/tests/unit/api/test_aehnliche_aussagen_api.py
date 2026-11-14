"""
/statement/aehnliche (#642): aehnliche Aussagen unter "Nicht dabei?", auch ohne
Anmeldung. Dieselbe Auswahl wie die Vorschlaege im Feld "Antwort auf"; Rate-Limit je
Adresse. Die Personenfelder prueft test_personenbezug_responses.py.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.v1.statement as statement_api
from api.v1.statement import router as statement_router
from core.config import Settings
from dependencies import get_statement_service, get_suchen_ohne_treffer_service
from utils.rate_limiter import RateLimiter

URL = "/api/v1/statement/aehnliche"
ANONYM = {"X-User": "anonymous"}

app = FastAPI()
app.include_router(statement_router, prefix="/api/v1/statement")


@pytest.fixture
def statement_service(monkeypatch):
    monkeypatch.setattr(
        statement_api,
        "aehnliche_aussagen_rate_limiter",
        RateLimiter(max_requests=60, window_minutes=10),
    )
    service = MagicMock()
    service.settings = Settings(aussage_vorschlag_schwelle=0.9)
    service.search = AsyncMock(return_value=[])
    service.search_filtered = AsyncMock(return_value=[])
    service.ohne_widerspruch = AsyncMock(return_value=[])
    schwelle = MagicMock(sichtbar_fuer_alle=AsyncMock(return_value=frozenset({"x"})))
    app.dependency_overrides[get_statement_service] = lambda: service
    app.dependency_overrides[get_suchen_ohne_treffer_service] = lambda: schwelle
    yield service
    app.dependency_overrides.clear()


@pytest.mark.api
class TestAehnlicheAussagen:
    @pytest.mark.parametrize(
        "headers",
        [ANONYM, {"X-User": "nutzer-1"}, {"X-User": "admin-1", "X-Is-Admin": "true"}],
        ids=["besucher", "angemeldet", "admin"],
    )
    def test_jede_rolle_bekommt_nur_die_vorschlags_auswahl(
        self, statement_service, headers
    ):
        resp = TestClient(app).post(
            URL, json={"query_text": "waermepumpe"}, headers=headers
        )

        assert resp.status_code == 200
        assert resp.json() == {"results": []}
        # Nur gepflegte Aussagen ab der Schwelle des Dienstes, ohne Suchanfragen
        # ueber der Schwelle der Kennzahl, mit Vorrat fuer den Widerspruchsfilter.
        args, kwargs = statement_service.search_filtered.await_args
        assert args[0] == "waermepumpe"
        assert kwargs == {
            "nur_kuratiert": True,
            "min_similarity": 0.9,
            "ueber_der_schwelle": frozenset(),
        }
        statement_service.search.assert_not_awaited()
        statement_service.ohne_widerspruch.assert_awaited_once()

    def test_hoechstens_fuenf(self, statement_service):
        resp = TestClient(app).post(
            URL, json={"query_text": "waermepumpe", "limit": 6}, headers=ANONYM
        )
        assert resp.status_code == 422

    @pytest.mark.parametrize("text", ["", "   "])
    def test_leerer_text_abgelehnt(self, statement_service, text):
        resp = TestClient(app).post(URL, json={"query_text": text}, headers=ANONYM)
        assert resp.status_code == 422
        statement_service.search_filtered.assert_not_awaited()

    def test_rate_limit_je_adresse(self, statement_service, monkeypatch):
        monkeypatch.setattr(
            statement_api,
            "aehnliche_aussagen_rate_limiter",
            RateLimiter(max_requests=2, window_minutes=10),
        )
        client = TestClient(app)
        codes = [
            client.post(
                URL, json={"query_text": "waermepumpe"}, headers=ANONYM
            ).status_code
            for _ in range(3)
        ]
        assert codes == [200, 200, 429]
        assert statement_service.search_filtered.await_count == 2
