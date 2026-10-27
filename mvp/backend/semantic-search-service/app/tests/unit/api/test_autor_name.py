"""
``autor_name`` in den Antworten, die Karten mit Autor oder Einwerfer speisen.

Vier Eigenschaften:
- Angemeldete Aufrufer bekommen den Namen, anonyme nicht.
- Anonyme bekommen auch keine Kennung (Suche und Neueste sind ohne Anmeldung offen).
- Eine Abfrage je Antwort, egal wie viele Treffer (kein N+1).
- Der Name steht nie am DbEntry: der ist das Qdrant-Payload.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.commentary import router as commentary_router
from api.v1.content import router as content_router
from api.v1.generic_text import router as generic_text_router
from api.v1.post import router as post_router
from api.v1.raw_input import router as raw_input_router
from dependencies import (
    get_commentary_service,
    get_generic_text_service,
    get_post_service,
    get_reference_service,
    get_settings,
)
from domain.models.base_content import BaseContentDbEntry
from domain.models.content_type import ContentType
from domain.models.content_origin import ContentOrigin
from domain.models.content_status import NEW_CONTENT_STATUS
from domain.models.post import PostDbEntry
from domain.models.raw_input import RawInputSource, RawInputStatus
from dtos.search import CommentarySearchResult
from repositories.raw_input_repository import get_raw_input_repository
from services.search.search_orchestrator import (
    ContentTypeSearchSpec,
    SearchOrchestrator,
)
from tests.unit.api.test_search_ranking import (  # noqa: F401 - Fixture
    SEARCH_URL,
    _commentary,
    _generictext,
    _reply,
    _statement_result,
    search_client,
)

ANGEMELDET = {"X-User": "leserin"}
NAMEN = {"test": "Anna B.", "einwerferin": "Kim", "satz-person": "Jürgen Ö."}

app = FastAPI()
app.include_router(commentary_router, prefix="/api/v1/commentary")
app.include_router(generic_text_router, prefix="/api/v1/generic_text")
app.include_router(post_router, prefix="/api/v1/post")
app.include_router(content_router, prefix="/api/v1/content")
app.include_router(raw_input_router, prefix="/api/v1/rawinput")


def _post(post_id):
    jetzt = datetime(2026, 10, 27, tzinfo=timezone.utc)
    return PostDbEntry(
        id=post_id,
        title="Ein gelungener Post",
        text="Worum es im Post geht",
        platform="Instagram",
        author="@konto",
        url="https://www.instagram.com/p/abc/",
        created=jetzt,
        last_modified=jetzt,
        original_author="test",
        last_modified_by="test",
        status=NEW_CONTENT_STATUS,
        origin=ContentOrigin.MANUALLY_CREATED,
    )


@pytest.fixture
def namen(anzeigenamen_ohne_datenbank):
    """Das gemockte UserRepository aus tests/conftest.py, mit Namen bestueckt."""
    anzeigenamen_ohne_datenbank.anzeigenamen.side_effect = lambda ids: {
        kennung: NAMEN[kennung] for kennung in ids if kennung in NAMEN
    }
    return anzeigenamen_ohne_datenbank


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.unit
class TestKeinNameImQdrantPayload:
    def test_dbentry_hat_kein_feld_autor_name(self):
        """base_repository.py speichert model_dump_json() des DbEntry als Payload."""
        modelle = [BaseContentDbEntry, *BaseContentDbEntry.__subclasses__()]
        for modell in modelle:
            assert "autor_name" not in modell.model_fields, modell.__name__


@pytest.mark.unit
class TestSuche:
    def _antwort(self, search_client, headers):
        ids = [uuid.uuid4(), uuid.uuid4()]
        client = search_client(
            statement_results=[
                _statement_result(
                    0.95,
                    [
                        _reply(ContentType.COMMENTARY, 0.95, ids[0]),
                        _reply(ContentType.GENERIC_TEXT, 0.95, ids[1]),
                    ],
                )
            ]
        )
        response = client.post(
            SEARCH_URL, json={"query_text": "frage", "limit": 10}, headers=headers
        )
        assert response.status_code == 200
        return response.json()

    def test_angemeldet_mit_namen_aus_einer_abfrage(self, search_client, namen):
        body = self._antwort(search_client, ANGEMELDET)

        assert body["commentary_search_results"][0]["autor_name"] == "Anna B."
        assert body["generictext_search_results"][0]["autor_name"] == "Anna B."
        assert namen.anzeigenamen.call_count == 1

    def test_anonym_ohne_namen_und_ohne_abfrage(self, search_client, namen):
        body = self._antwort(search_client, {})

        assert body["commentary_search_results"][0]["autor_name"] is None
        namen.anzeigenamen.assert_not_called()

    def test_anonym_ohne_kennungen(self, search_client, namen):
        body = self._antwort(search_client, {})

        for feld in ("commentary_search_results", "generictext_search_results"):
            inhalt = body[feld][0][feld.replace("_search_results", "_result")]
            assert inhalt["original_author"] == ""
            assert inhalt["last_modified_by"] == ""
            assert inhalt["authors"] == []
            assert inhalt["edit_history"] == []

    def test_angemeldet_mit_kennung(self, search_client, namen):
        body = self._antwort(search_client, ANGEMELDET)

        assert (
            body["commentary_search_results"][0]["commentary_result"]["original_author"]
            == "test"
        )

    def test_leeren_veraendert_das_gelieferte_objekt_nicht(self):
        """Das Objekt kann aus einem Cache stammen und gleich angemeldet ausgeliefert werden."""
        original = _commentary(uuid.uuid4())
        spec = ContentTypeSearchSpec(
            content_type=ContentType.COMMENTARY,
            service=MagicMock(),
            result_cls=CommentarySearchResult,
            result_field="commentary_result",
        )
        orchestrator = SearchOrchestrator([spec], MagicMock(), MagicMock(), MagicMock())
        orchestrator.results_for(ContentType.COMMENTARY).append(
            CommentarySearchResult(
                score=1.0,
                statement_text="",
                statement_similarity_score=1.0,
                reply_relevance=1.0,
                commentary_result=original,
            )
        )

        orchestrator.strip_author_ids()

        geleert = orchestrator.results_for(ContentType.COMMENTARY)[0].commentary_result
        assert geleert.original_author == ""
        assert original.original_author == "test"

    def test_name_steht_nicht_im_inhalt(self, search_client, namen):
        body = self._antwort(search_client, ANGEMELDET)

        assert (
            "autor_name"
            not in body["commentary_search_results"][0]["commentary_result"]
        )


@pytest.mark.unit
class TestGetById:
    @pytest.fixture(autouse=True)
    def dienste(self):
        commentary = MagicMock(get=AsyncMock(side_effect=_commentary))
        generic_text = MagicMock(get=AsyncMock(side_effect=_generictext))
        post = MagicMock(get=AsyncMock(side_effect=_post))
        app.dependency_overrides[get_commentary_service] = lambda: commentary
        app.dependency_overrides[get_generic_text_service] = lambda: generic_text
        app.dependency_overrides[get_post_service] = lambda: post

    @pytest.mark.parametrize(
        "url",
        [
            "/api/v1/commentary/getById?commentary_id={id}",
            "/api/v1/generic_text/getById?generic_text_id={id}",
            "/api/v1/post/getById?post_id={id}",
        ],
    )
    def test_angemeldet_mit_namen(self, client, namen, url):
        response = client.get(url.format(id=uuid.uuid4()), headers=ANGEMELDET)

        assert response.status_code == 200
        assert response.json()["autor_name"] == "Anna B."
        assert response.json()["original_author"] == "test"

    @pytest.mark.parametrize(
        "url",
        [
            "/api/v1/commentary/getById?commentary_id={id}",
            "/api/v1/generic_text/getById?generic_text_id={id}",
            "/api/v1/post/getById?post_id={id}",
        ],
    )
    def test_ohne_anmeldung_ohne_namen(self, client, namen, url):
        response = client.get(url.format(id=uuid.uuid4()))

        assert response.status_code == 200
        assert "autor_name" not in response.json()


@pytest.mark.unit
class TestNeueste:
    @pytest.fixture(autouse=True)
    def quellen(self):
        commentary_repo = MagicMock(
            get_recent=AsyncMock(
                return_value=[_commentary(uuid.uuid4()), _commentary(uuid.uuid4())]
            )
        )
        generic_text_repo = MagicMock(
            get_recent=AsyncMock(return_value=[_generictext(uuid.uuid4())])
        )
        factory = MagicMock()
        factory.create_commentary_repository.return_value = commentary_repo
        factory.create_generic_text_repository.return_value = generic_text_repo
        nutzung = MagicMock()
        nutzung.enrich_content_with_usage.side_effect = lambda eintraege: eintraege
        app.dependency_overrides[get_settings] = lambda: MagicMock()
        app.dependency_overrides[get_reference_service] = lambda: MagicMock()
        with patch(
            "api.v1.content.QdrantRepositoryFactory", return_value=factory
        ), patch("api.v1.content.get_usage_service", return_value=nutzung):
            yield

    def test_angemeldet_mit_namen_aus_einer_abfrage(self, client, namen):
        response = client.get("/api/v1/content/recent?limit=6", headers=ANGEMELDET)

        ergebnisse = response.json()["results"]
        assert len(ergebnisse) == 3
        assert {eintrag["autor_name"] for eintrag in ergebnisse} == {"Anna B."}
        assert namen.anzeigenamen.call_count == 1

    def test_anonym_ohne_namen(self, client, namen):
        response = client.get(
            "/api/v1/content/recent?limit=6", headers={"X-User": "anonymous"}
        )

        assert all(
            "autor_name" not in eintrag for eintrag in response.json()["results"]
        )
        namen.anzeigenamen.assert_not_called()

    def test_anonym_ohne_kennungen(self, client, namen):
        response = client.get(
            "/api/v1/content/recent?limit=6", headers={"X-User": "anonymous"}
        )

        for eintrag in response.json()["results"]:
            assert eintrag["original_author"] == ""
            assert eintrag["last_modified_by"] == ""
            assert eintrag["authors"] == []
            assert eintrag["edit_history"] == []

    def test_angemeldet_mit_kennung(self, client, namen):
        response = client.get("/api/v1/content/recent?limit=6", headers=ANGEMELDET)

        assert {e["original_author"] for e in response.json()["results"]} == {"test"}


@pytest.mark.unit
class TestFangkorb:
    @pytest.fixture(autouse=True)
    def repository(self):
        def einwurf():
            return {
                "id": str(uuid.uuid4()),
                "content": "[anz-test] ein Satz",
                "submitted_by": "einwerferin",
                "source_channel": RawInputSource.WEB.value,
                "status": RawInputStatus.IN_PROGRESS.value,
                "created_at": datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc),
                "drafts": [
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": "satz-person",
                        "sentence": "Der Punkt.",
                        "updated_at": datetime(2026, 10, 11, tzinfo=timezone.utc),
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "user_id": "ohne-namen",
                        "sentence": "Noch einer.",
                        "updated_at": datetime(2026, 10, 11, tzinfo=timezone.utc),
                    },
                ],
            }

        repo = MagicMock()
        repo.get_all.side_effect = lambda **_: [einwurf(), einwurf()]
        repo.get_by_id.side_effect = lambda *_: einwurf()
        repo.count.return_value = 2
        app.dependency_overrides[get_raw_input_repository] = lambda: repo

    def test_liste_mit_namen_aus_einer_abfrage(self, client, namen):
        response = client.get("/api/v1/rawinput/getRawInputs", headers=ANGEMELDET)

        for eintrag in response.json()["results"]:
            assert eintrag["submitted_by_name"] == "Kim"
            assert [satz["user_name"] for satz in eintrag["drafts"]] == [
                "Jürgen Ö.",
                None,
            ]
        assert namen.anzeigenamen.call_count == 1

    def test_einzeln_mit_namen(self, client, namen):
        response = client.get(f"/api/v1/rawinput/{uuid.uuid4()}", headers=ANGEMELDET)

        assert response.json()["submitted_by_name"] == "Kim"
        assert response.json()["drafts"][0]["user_name"] == "Jürgen Ö."

    def test_lesefehler_liefert_antwort_ohne_namen(self, client, namen):
        namen.anzeigenamen.side_effect = RuntimeError("Datenbank weg")

        response = client.get("/api/v1/rawinput/getRawInputs", headers=ANGEMELDET)

        assert response.status_code == 200
        assert response.json()["results"][0]["submitted_by_name"] is None
