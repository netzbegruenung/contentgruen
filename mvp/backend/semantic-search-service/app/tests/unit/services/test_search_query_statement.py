"""
Aussage aus der Suchanfrage: Rate-Limit je Aufrufer.

Die Suche ist offen erreichbar und schreibt dabei dauerhaft. Ist das Limit
erreicht, entfaellt nur das Anlegen; die Suche selbst laeuft weiter (siehe
TestSuchpfad unten). Die Sperre je Text sitzt in add_statement
(test_statement_service.py, TestAddStatementDubletten).
"""

import logging
import uuid
from datetime import date, datetime, time, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.search import router as search_router
from dependencies import (
    get_commentary_service,
    get_generic_text_service,
    get_post_service,
    get_reference_service,
    get_statement_service,
    get_suchen_ohne_treffer_service,
    get_voting_service,
)
from domain.models.content_origin import ContentOrigin, SEARCH_QUERY_AUTHOR
from services.search.search_query_statement import (
    SearchQueryStatementRecorder,
    get_search_query_statement_recorder,
)
from services.search_tracking_service import tagespseudonym
from tests.fixtures.direktsuche import direktsuche_ueber_dienste
from utils.rate_limiter import RateLimiter


def _recorder(max_requests: int = 100) -> SearchQueryStatementRecorder:
    return SearchQueryStatementRecorder(
        RateLimiter(max_requests=max_requests, window_minutes=10)
    )


def _dienst() -> MagicMock:
    service = MagicMock()
    service.add_statement = AsyncMock(return_value=(True, uuid.uuid4(), "klima"))
    return service


@pytest.mark.asyncio
class TestRecorder:
    async def test_anlegen_als_suchanfrage_mit_systemautor(self):
        service = _dienst()

        await _recorder().anlegen(service, "klima", "ip:a")

        statement, author, _, origin = service.add_statement.call_args[0]
        assert statement.text == "klima"
        assert statement.replysuggestions == []
        assert author == SEARCH_QUERY_AUTHOR
        assert origin is ContentOrigin.SEARCH_QUERY

    async def test_limit_erreicht_legt_nichts_an(self):
        service = _dienst()
        recorder = _recorder(max_requests=2)

        await recorder.anlegen(service, "eins", "ip:a")
        await recorder.anlegen(service, "zwei", "ip:a")
        ergebnis = await recorder.anlegen(service, "drei", "ip:a")

        assert ergebnis == (False, None, "drei")
        assert service.add_statement.await_count == 2

    async def test_limit_gilt_je_aufrufer(self):
        service = _dienst()
        recorder = _recorder(max_requests=1)

        await recorder.anlegen(service, "eins", "ip:a")
        _, statement_id, _ = await recorder.anlegen(service, "eins", "ip:b")

        assert statement_id is not None
        assert service.add_statement.await_count == 2

    async def test_anlegen_limit_erreicht_protokolliert_auf_info_nichts(self, caplog):
        """Je Suche eine Zeile mit Uhrzeit liesse sich ueber die Reihenfolge den
        Suchereignissen des Tages zuordnen (#239)."""
        service = _dienst()
        recorder = _recorder(max_requests=1)
        await recorder.anlegen(service, "eins", "ip:a")

        with caplog.at_level(logging.INFO):
            await recorder.anlegen(service, "zwei", "ip:a")

        assert caplog.records == []


SEARCH_URL = "/api/v1/search/searchByText"
# Ein Besucher hinter nginx: Adresse aus X-Real-IP, dazu der User-Agent.
BESUCHER = {"X-Real-IP": "198.51.100.5", "User-Agent": "Firefox"}
MERKMAL = "198.51.100.5|Firefox"


def _mittag(tag):
    """Das Tagespseudonym haengt nur am UTC-Datum; Mittag liegt sicher darin."""
    return datetime.combine(tag, time(12), timezone.utc)


@pytest.fixture
def suchen_ohne_treffer():
    return MagicMock()


@pytest.fixture
def suchapp(suchen_ohne_treffer):
    app = FastAPI()
    app.include_router(search_router, prefix="/api/v1/search")

    service = _dienst()
    service.search_statements = AsyncMock(return_value=[])
    leerer_dienst = MagicMock()
    leerer_dienst.get = AsyncMock(return_value=None)
    leerer_dienst.search = AsyncMock(return_value=[])

    app.dependency_overrides[get_statement_service] = lambda: service
    for abhaengigkeit in (
        get_commentary_service,
        get_generic_text_service,
        get_post_service,
        get_reference_service,
    ):
        app.dependency_overrides[abhaengigkeit] = lambda: leerer_dienst
    app.dependency_overrides[get_voting_service] = lambda: MagicMock(
        get_user_votes_for_contents=MagicMock(return_value={})
    )
    app.dependency_overrides[get_suchen_ohne_treffer_service] = lambda: (
        suchen_ohne_treffer
    )

    patches = [
        patch("api.v1.search.get_polarity_filter_service"),
        patch("api.v1.search.get_keyword_overlap_service"),
        patch("api.v1.search.get_usage_service"),
        patch("api.v1.search.get_search_tracking_service"),
        direktsuche_ueber_dienste(),
    ]
    gestartet = [p.start() for p in patches]
    gestartet[0].return_value.analyze_and_filter_statement_results.return_value = (
        [],
        {},
    )
    gestartet[1].return_value.analyze_and_boost_results.return_value = ([], {})

    yield app, service

    for p in patches:
        p.stop()


@pytest.mark.api
class TestSuchpfad:
    def test_suche_laeuft_ohne_aussage_weiter_wenn_limit_erreicht(self, suchapp):
        app, service = suchapp
        app.dependency_overrides[get_search_query_statement_recorder] = lambda: (
            _recorder(max_requests=0)
        )

        resp = TestClient(app).post(
            SEARCH_URL, json={"query_text": "klima", "limit": 10}
        )

        assert resp.status_code == 200
        assert resp.json()["statement_id"] is None
        assert resp.json()["query_was_newly_added_as_statement"] is False
        service.add_statement.assert_not_called()
        service.search_statements.assert_awaited()

    def test_limit_haengt_an_der_adresse_nicht_an_der_session(self, suchapp):
        """Eine neue X-Session-Id je Anfrage umgeht das Limit nicht (alte Clients)."""
        app, service = suchapp
        recorder = _recorder(max_requests=1)
        app.dependency_overrides[get_search_query_statement_recorder] = lambda: recorder
        client = TestClient(app)

        for _ in range(3):
            client.post(
                SEARCH_URL,
                json={"query_text": "klima", "limit": 10},
                headers={"X-Session-Id": str(uuid.uuid4())},
            )

        assert service.add_statement.await_count == 1


@pytest.mark.api
class TestSuchenOhneTreffer:
    """Der Suchpfad meldet jede Suche mit Aussage und Trefferzahl zur Kennzahl."""

    def test_suche_ohne_treffer_meldet_aussage_und_null_treffer(
        self, suchapp, suchen_ohne_treffer
    ):
        app, service = suchapp
        aussage = uuid.uuid4()
        service.add_statement = AsyncMock(return_value=(False, aussage, "klima"))
        app.dependency_overrides[get_search_query_statement_recorder] = _recorder

        TestClient(app).post(
            SEARCH_URL,
            json={"query_text": "klima", "limit": 10},
            headers=BESUCHER,
        )

        aufruf = suchen_ohne_treffer.erfassen.call_args
        heute = aufruf.kwargs["heute"]
        assert aufruf.args == (
            aussage,
            0,
            tagespseudonym(besucher=MERKMAL, moment=_mittag(heute)),
        )

    def test_angemeldet_meldet_dieselbe_kennung_wie_das_suchereignis(
        self, suchapp, suchen_ohne_treffer
    ):
        """Beide Kennzahlen bilden das Tagespseudonym aus der Nutzerkennung."""
        app, service = suchapp
        aussage = uuid.uuid4()
        service.add_statement = AsyncMock(return_value=(False, aussage, "klima"))
        app.dependency_overrides[get_search_query_statement_recorder] = _recorder

        with patch("api.v1.search.get_search_tracking_service") as tracking:
            TestClient(app).post(
                SEARCH_URL,
                json={"query_text": "klima", "limit": 10},
                headers={"X-User": "person-1", **BESUCHER},
            )

        _, ereignis = tracking.return_value.track_search.call_args
        assert ereignis["results_count"] == 0
        # Angemeldet geht weder Adresse noch User-Agent ein.
        assert ereignis["besucher"] is None
        assert ereignis["user_id"] == "person-1"
        aufruf = suchen_ohne_treffer.erfassen.call_args
        assert aufruf.args[2] == tagespseudonym(
            user_id="person-1", moment=_mittag(aufruf.kwargs["heute"])
        )
        # Derselbe Zeitpunkt fuer beide, also dasselbe Tagespseudonym.
        assert ereignis["moment"].date() == aufruf.kwargs["heute"]
        assert aufruf.args[2] == tagespseudonym(
            user_id="person-1", moment=ereignis["moment"]
        )

    def test_suchereignis_und_kennzahl_teilen_den_zeitpunkt_vor_mitternacht(
        self, suchapp, suchen_ohne_treffer
    ):
        """Auch wenn die Uhr zwischen beiden Aufrufen ueber Mitternacht laeuft,
        bekommen Suchereignis und Kennzahl dasselbe Tagespseudonym."""
        app, service = suchapp
        aussage = uuid.uuid4()
        service.add_statement = AsyncMock(return_value=(False, aussage, "klima"))
        app.dependency_overrides[get_search_query_statement_recorder] = _recorder
        vor_mitternacht = datetime(
            2026, 10, 26, 23, 59, 59, 999999, tzinfo=timezone.utc
        )

        with patch("api.v1.search.get_search_tracking_service") as tracking, patch(
            "api.v1.search.datetime"
        ) as uhr:
            uhr.now.return_value = vor_mitternacht
            TestClient(app).post(
                SEARCH_URL,
                json={"query_text": "klima", "limit": 10},
                headers=BESUCHER,
            )

        _, ereignis = tracking.return_value.track_search.call_args
        assert ereignis["moment"] == vor_mitternacht
        assert ereignis["besucher"] == MERKMAL
        aufruf = suchen_ohne_treffer.erfassen.call_args
        assert aufruf.kwargs["heute"] == date(2026, 10, 26)
        assert aufruf.args[2] == tagespseudonym(
            besucher=MERKMAL, moment=vor_mitternacht
        )

    def _pseudonyme(self, app, suchen_ohne_treffer, *kopfzeilen):
        client = TestClient(app)
        for headers in kopfzeilen:
            client.post(
                SEARCH_URL, json={"query_text": "klima", "limit": 10}, headers=headers
            )
        return [a.args[2] for a in suchen_ohne_treffer.erfassen.call_args_list]

    def test_besucher_ist_ohne_kennung_im_browser_dieselbe_person(
        self, suchapp, suchen_ohne_treffer
    ):
        """Eine wechselnde X-Session-Id macht keine weitere Person mehr (#446)."""
        app, service = suchapp
        service.add_statement = AsyncMock(return_value=(False, uuid.uuid4(), "klima"))
        app.dependency_overrides[get_search_query_statement_recorder] = _recorder

        eins, zwei = self._pseudonyme(
            app,
            suchen_ohne_treffer,
            {**BESUCHER, "X-Session-Id": str(uuid.uuid4())},
            {**BESUCHER, "X-Session-Id": str(uuid.uuid4())},
        )

        assert eins is not None
        assert eins == zwei

    def test_anderer_browser_am_selben_anschluss_ist_eine_weitere_person(
        self, suchapp, suchen_ohne_treffer
    ):
        app, service = suchapp
        service.add_statement = AsyncMock(return_value=(False, uuid.uuid4(), "klima"))
        app.dependency_overrides[get_search_query_statement_recorder] = _recorder

        eins, zwei = self._pseudonyme(
            app,
            suchen_ohne_treffer,
            BESUCHER,
            {**BESUCHER, "User-Agent": "Chrome"},
        )

        assert eins != zwei

    def test_fehler_der_kennzahl_laesst_die_suche_nicht_scheitern(
        self, suchapp, suchen_ohne_treffer
    ):
        app, _ = suchapp
        app.dependency_overrides[get_search_query_statement_recorder] = _recorder
        suchen_ohne_treffer.erfassen.side_effect = RuntimeError("weg")

        resp = TestClient(app).post(
            SEARCH_URL, json={"query_text": "klima", "limit": 10}
        )

        assert resp.status_code == 200
