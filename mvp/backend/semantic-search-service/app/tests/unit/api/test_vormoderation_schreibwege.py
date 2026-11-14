"""
Vormoderation (Entscheidung des Maintainers vom 13.11.2026): Eine nicht
freigegebene unbeantwortete Suchanfrage wird weder ueber addReplysuggestionToStatement
sichtbar (409), noch nennt die Suche Nicht-Admins ihre ID oder ihren Wortlaut.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.search import _aussage_fuer_aufrufer
from api.v1.statement import router as statement_router
from dependencies import get_statement_service
from domain.models.content_origin import ContentOrigin
from services.beitrag_fuer_aufrufer import Aufrufer
from services.content.statement_service import SuchanfrageNichtFreigegeben

S = uuid.UUID(int=7)
ADMIN = Aufrufer(kennung="admin-1", admin_kopf=True)
MITWIRKENDE = Aufrufer(kennung="person-1", admin_kopf=False)

app = FastAPI()
app.include_router(statement_router, prefix="/api/v1/statement")


@pytest.mark.api
class TestAntwortAnhaengen:
    def test_nicht_freigegeben_409(self):
        service = MagicMock()
        service.add_statementreplysuggestion_to_statement = AsyncMock(
            side_effect=SuchanfrageNichtFreigegeben(str(S))
        )
        app.dependency_overrides[get_statement_service] = lambda: service
        try:
            resp = TestClient(app).post(
                "/api/v1/statement/addReplysuggestionToStatement",
                json={
                    "statement_id": str(S),
                    "replysuggestion_id": str(uuid.uuid4()),
                    "content_type": "commentary",
                    "relevance": 1.0,
                },
                headers={"X-User": "person-1"},
            )
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 409


def _aussage(origin=ContentOrigin.SEARCH_QUERY, antworten=0):
    return SimpleNamespace(id=S, origin=origin, replysuggestions_count=antworten)


def _dienste(aussage=None, sichtbar=frozenset(), fehler=None):
    statement_service = MagicMock()
    statement_service.get = AsyncMock(return_value=aussage, side_effect=fehler)
    suchen = MagicMock()
    suchen.sichtbar_fuer_alle = AsyncMock(return_value=sichtbar)
    return statement_service, suchen


@pytest.mark.asyncio
class TestSuchantwort:
    async def _antwort(self, aufrufer, neu, statement_service, suchen):
        return await _aussage_fuer_aufrufer(
            aufrufer, statement_service, suchen, neu, S, "Wortlaut von S", "meine Suche"
        )

    @pytest.mark.parametrize(
        "aufrufer", [ADMIN, MITWIRKENDE], ids=["admin", "mitwirkende"]
    )
    async def test_auch_admins_ohne_id_einer_verborgenen(self, aufrufer):
        # Sonst schickte das Formular die ID, und die Antwort hinge ins Leere.
        dienste = _dienste(_aussage(), sichtbar=frozenset())
        assert await self._antwort(aufrufer, False, *dienste) == (None, "meine Suche")

    async def test_eben_angelegt_ohne_id(self):
        statement_service, suchen = _dienste(_aussage())
        assert await self._antwort(MITWIRKENDE, True, statement_service, suchen) == (
            None,
            "meine Suche",
        )
        statement_service.get.assert_not_awaited()

    async def test_nicht_freigegeben_ohne_id_und_wortlaut(self):
        dienste = _dienste(_aussage(), sichtbar=frozenset())
        assert await self._antwort(MITWIRKENDE, False, *dienste) == (
            None,
            "meine Suche",
        )

    async def test_freigegeben_ueber_der_schwelle_wie_bisher(self):
        dienste = _dienste(_aussage(), sichtbar=frozenset({S}))
        assert await self._antwort(MITWIRKENDE, False, *dienste) == (
            S,
            "Wortlaut von S",
        )

    @pytest.mark.parametrize(
        "aussage",
        [
            _aussage(antworten=1),
            _aussage(origin=ContentOrigin.MANUALLY_CREATED),
        ],
        ids=["beantwortet", "gepflegt"],
    )
    async def test_andere_aussagen_wie_bisher(self, aussage):
        statement_service, suchen = _dienste(aussage)
        assert await self._antwort(MITWIRKENDE, False, statement_service, suchen) == (
            S,
            "Wortlaut von S",
        )
        suchen.sichtbar_fuer_alle.assert_not_awaited()

    async def test_unpruefbar_wird_verborgen(self):
        dienste = _dienste(fehler=RuntimeError("weg"))
        assert await self._antwort(MITWIRKENDE, False, *dienste) == (
            None,
            "meine Suche",
        )
