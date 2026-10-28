"""
Aussagen, Herkunft, Einwuerfe und Meine Beitraege ohne Kennung anderer Personen (#385).

Dieselbe Regel wie an Beitraegen (#333, test_beitrag_responses.py): Nicht-Admins
bekommen statt der Kennung den Anzeigenamen und ein Kennzeichen fuer den eigenen
Eintrag, beides nur angemeldet; Admins sehen die Kennung weiter. Geprueft an jeder
lesenden Route: Keine Kennung einer Person steht irgendwo im Antworttext.
"""

import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1 import contribution as contribution_module
from api.v1.contribution import router as contribution_router
from api.v1.raw_input import router as raw_input_router
from api.v1.reference import router as reference_router
from api.v1.statement import router as statement_router
from dependencies import (
    get_commentary_service,
    get_generic_text_service,
    get_post_service,
    get_reference_service,
    get_settings,
    get_statement_service,
)
from domain.models.base_content import BaseContentDbEntry
from domain.models.content_type import ContentType
from domain.models.reference import ReferenceDbEntry
from domain.models.statement import StatementDbEntry, StatementSearchResult
from dtos.contribution import ContributionEntry
from dtos.statement import AussageResponse
from repositories.raw_input_repository import get_raw_input_repository
from services.content.statement_service import StatementService
from tests.unit.api.test_beitrag_responses import (
    ADMIN,
    ANONYM,
    AUTORIN,
    BEARBEITER,
    EIGEN,
    FREMD,
    NAME,
    NICHT_NACH_AUSSEN,
    _personen,
)

GET = "get"
POST = "post"


def _namen(anzeigenamen_ohne_datenbank, *kennungen):
    """Nur die genannten Kennungen haben einen Anzeigenamen."""
    anzeigenamen_ohne_datenbank.anzeigenamen.side_effect = lambda ids: {
        k: NAME for k in ids if k in kennungen
    }


def _ohne_kennung(antwort, *kennungen):
    for kennung in kennungen or (AUTORIN, BEARBEITER):
        assert kennung not in antwort.text


def _abrufen(client, methode, url, headers, json=None):
    if methode == GET:
        antwort = client.get(url, headers=headers)
    else:
        antwort = client.request(methode.upper(), url, json=json, headers=headers)
    assert antwort.status_code == 200, antwort.text
    return antwort


def _liste(body):
    if "results" in body:
        return body["results"]
    return [body]


# --------------------------------------------------------------------------- #
# Aussagen
# --------------------------------------------------------------------------- #


def _aussage(klasse=StatementDbEntry, **extra):
    return klasse(
        **_personen(),
        **extra,
        id=uuid.uuid4(),
        content_type=ContentType.STATEMENT,
        text="Wärmepumpen funktionieren im Altbau nicht",
        replysuggestions=[],
        replysuggestions_count=0,
    )


AUSSAGE_ROUTEN = {
    "statement/getAll": (GET, "/api/v1/statement/getAll", None),
    "statement/searchStatements": (
        POST,
        "/api/v1/statement/searchStatements",
        {"query_text": "Wärmepumpe", "limit": 3},
    ),
    "statement/searchStatements gefiltert": (
        POST,
        "/api/v1/statement/searchStatements",
        {"query_text": "Wärmepumpe", "limit": 3, "nur_kuratiert": True},
    ),
    "statement/getStatementsOfTopic": (
        POST,
        "/api/v1/statement/getStatementsOfTopic",
        {"topic": "Energie"},
    ),
    "statement/getStatementsOfCategory": (
        POST,
        "/api/v1/statement/getStatementsOfCategory",
        {"category": "Energie"},
    ),
}

# Was der DbEntry fuehrt, die Aussage nach aussen aber nicht.
AUSSAGE_NICHT_NACH_AUSSEN = set(BaseContentDbEntry.model_fields) - set(
    AussageResponse.model_fields
)

aussage_app = FastAPI()
aussage_app.include_router(statement_router, prefix="/api/v1/statement")


@pytest.fixture
def aussage_client(anzeigenamen_ohne_datenbank):
    _namen(anzeigenamen_ohne_datenbank, AUTORIN)
    dienst = MagicMock(spec=StatementService)
    dienst.get_all = AsyncMock(side_effect=lambda **_: [_aussage(), _aussage()])
    dienst.count = AsyncMock(return_value=2)
    treffer = lambda *_, **__: [
        _aussage(StatementSearchResult, score=0.9)
    ]  # noqa: E731
    dienst.search = AsyncMock(side_effect=treffer)
    dienst.search_filtered = AsyncMock(side_effect=treffer)
    dienst.get_items_of_topic.side_effect = lambda *_: [_aussage()]
    dienst.get_items_of_category.side_effect = lambda *_: [_aussage()]
    aussage_app.dependency_overrides[get_statement_service] = lambda: dienst
    client = TestClient(aussage_app)

    def abrufen(route, headers):
        methode, url, json = AUSSAGE_ROUTEN[route]
        return _abrufen(client, methode, url, headers, json)

    yield abrufen
    aussage_app.dependency_overrides.clear()


@pytest.mark.unit
@pytest.mark.parametrize("route", AUSSAGE_ROUTEN)
class TestAussagen:
    def test_angemeldet_ohne_kennung_mit_namen(self, aussage_client, route):
        antwort = aussage_client(route, FREMD)

        _ohne_kennung(antwort)
        for aussage in _liste(antwort.json()):
            assert not AUSSAGE_NICHT_NACH_AUSSEN & set(aussage)
            assert aussage["autor_name"] == NAME
            assert aussage["ist_eigene_aussage"] is False

    def test_eigene_aussage_erkannt(self, aussage_client, route):
        antwort = aussage_client(route, EIGEN)

        for aussage in _liste(antwort.json()):
            assert aussage["ist_eigene_aussage"] is True

    def test_anonym_ohne_kennung_ohne_namen(self, aussage_client, route):
        antwort = aussage_client(route, ANONYM)

        _ohne_kennung(antwort)
        for aussage in _liste(antwort.json()):
            assert aussage["autor_name"] is None
            assert aussage["ist_eigene_aussage"] is None

    def test_admin_sieht_kennung(self, aussage_client, route):
        antwort = aussage_client(route, ADMIN)

        assert BEARBEITER not in antwort.text
        for aussage in _liste(antwort.json()):
            assert aussage["original_author"] == AUTORIN


# --------------------------------------------------------------------------- #
# Herkunft
# --------------------------------------------------------------------------- #


def _herkunft():
    return ReferenceDbEntry(
        **_personen(),
        id=uuid.uuid4(),
        content_type=ContentType.REFERENCE,
        reference_string="https://example.org/rede",
        text="Rede im Landtag",
        usage_count=3,
    )


herkunft_app = FastAPI()
herkunft_app.include_router(reference_router, prefix="/api/v1/reference")


@pytest.fixture
def herkunft_client(anzeigenamen_ohne_datenbank):
    _namen(anzeigenamen_ohne_datenbank, AUTORIN)
    dienst = MagicMock(get=AsyncMock(side_effect=lambda _: _herkunft()))
    herkunft_app.dependency_overrides[get_reference_service] = lambda: dienst
    client = TestClient(herkunft_app)

    def abrufen(headers):
        url = f"/api/v1/reference/getById?reference_id={uuid.uuid4()}"
        return _abrufen(client, GET, url, headers)

    yield abrufen
    herkunft_app.dependency_overrides.clear()


@pytest.mark.unit
class TestHerkunft:
    def test_angemeldet_ohne_kennung_mit_namen(self, herkunft_client):
        antwort = herkunft_client(FREMD)

        _ohne_kennung(antwort)
        herkunft = antwort.json()
        assert herkunft["autor_name"] == NAME
        assert herkunft["ist_eigene_herkunft"] is False

    def test_eigene_herkunft_erkannt(self, herkunft_client):
        assert herkunft_client(EIGEN).json()["ist_eigene_herkunft"] is True

    def test_anonym_ohne_kennung_ohne_namen(self, herkunft_client):
        antwort = herkunft_client(ANONYM)

        _ohne_kennung(antwort)
        assert antwort.json()["autor_name"] is None
        assert antwort.json()["ist_eigene_herkunft"] is None

    def test_admin_sieht_kennung(self, herkunft_client):
        assert herkunft_client(ADMIN).json()["original_author"] == AUTORIN


# --------------------------------------------------------------------------- #
# Einwuerfe und Saetze
# --------------------------------------------------------------------------- #

EINWURF_ID = uuid.uuid4()
SATZ_AUTORIN = "kennung-der-satz-autorin"


def _einwurf():
    """Ein Einwurf von AUTORIN, destilliert und ausformuliert von BEARBEITER."""
    zeit = datetime.datetime(2026, 10, 28, tzinfo=datetime.timezone.utc)
    return {
        "id": str(EINWURF_ID),
        "content": "Guter Thread zu Wärmepumpen",
        "url": "https://example.org/thread",
        "image_url": None,
        "submitted_by": AUTORIN,
        "source_channel": "web",
        "status": "processed",
        "created_at": zeit,
        "destilled_by": BEARBEITER,
        "own_draft": None,
        "processed_content_id": str(uuid.uuid4()),
        "processed_by": BEARBEITER,
        "processed_at": zeit,
        "drafts": [
            {
                "id": str(uuid.uuid4()),
                "user_id": SATZ_AUTORIN,
                "sentence": "Wärmepumpe lohnt sich auch im Altbau",
                "updated_at": zeit,
            }
        ],
        "links": [
            {
                "content_id": str(uuid.uuid4()),
                "content_type": "commentary",
                "draft_id": None,
                "processed_by": BEARBEITER,
                "processed_at": zeit,
            }
        ],
    }


EINWURF_ROUTEN = {
    "rawinput/getRawInputs": (GET, "/api/v1/rawinput/getRawInputs", None),
    "rawinput/getOwnRawInputs": (GET, "/api/v1/rawinput/getOwnRawInputs", None),
    "rawinput/gleicherLink": (
        POST,
        "/api/v1/rawinput/gleicherLink",
        {"url": "https://example.org/thread"},
    ),
    "rawinput/{id}": (GET, f"/api/v1/rawinput/{EINWURF_ID}", None),
    "rawinput/{id}/status": (
        "patch",
        f"/api/v1/rawinput/{EINWURF_ID}/status",
        {"status": "discarded"},
    ),
}
ALLE_KENNUNGEN = (AUTORIN, BEARBEITER, SATZ_AUTORIN)

einwurf_app = FastAPI()
einwurf_app.include_router(raw_input_router, prefix="/api/v1/rawinput")


@pytest.fixture
def einwurf_client(anzeigenamen_ohne_datenbank):
    _namen(anzeigenamen_ohne_datenbank, AUTORIN, SATZ_AUTORIN)
    repository = MagicMock()
    repository.get_all.side_effect = lambda **_: [_einwurf()]
    repository.count.return_value = 1
    repository.mit_gleichem_link.side_effect = lambda *_: [_einwurf()]
    repository.get_by_id.side_effect = lambda *_: _einwurf()
    repository.set_status.side_effect = lambda *_, **__: _einwurf()
    einwurf_app.dependency_overrides[get_raw_input_repository] = lambda: repository
    # Verworfen wird ohne Beitragspruefung; die Dienste muessen nur aufloesbar sein.
    for dienst in (get_commentary_service, get_generic_text_service, get_post_service):
        einwurf_app.dependency_overrides[dienst] = lambda: MagicMock()
    client = TestClient(einwurf_app)

    def abrufen(route, headers):
        methode, url, json = EINWURF_ROUTEN[route]
        return _abrufen(client, methode, url, headers, json)

    yield abrufen
    einwurf_app.dependency_overrides.clear()


def _einwuerfe(antwort):
    return _liste(antwort.json())


@pytest.mark.unit
@pytest.mark.parametrize("route", EINWURF_ROUTEN)
class TestEinwuerfe:
    def test_angemeldet_ohne_kennung_mit_namen(self, einwurf_client, route):
        antwort = einwurf_client(route, FREMD)

        _ohne_kennung(antwort, *ALLE_KENNUNGEN)
        for einwurf in _einwuerfe(antwort):
            assert einwurf["submitted_by_name"] == NAME
            assert einwurf["ist_eigener_einwurf"] is False
            (satz,) = einwurf["drafts"]
            assert satz["user_name"] == NAME
            assert satz["ist_eigener_satz"] is False

    def test_eigener_einwurf_erkannt(self, einwurf_client, route):
        for einwurf in _einwuerfe(einwurf_client(route, EIGEN)):
            assert einwurf["ist_eigener_einwurf"] is True
            assert einwurf["drafts"][0]["ist_eigener_satz"] is False

    def test_eigener_satz_erkannt(self, einwurf_client, route):
        antwort = einwurf_client(route, {"X-User": SATZ_AUTORIN})

        for einwurf in _einwuerfe(antwort):
            assert einwurf["ist_eigener_einwurf"] is False
            assert einwurf["drafts"][0]["ist_eigener_satz"] is True

    def test_admin_sieht_kennungen(self, einwurf_client, route):
        for einwurf in _einwuerfe(einwurf_client(route, ADMIN)):
            assert einwurf["submitted_by"] == AUTORIN
            assert einwurf["destilled_by"] == BEARBEITER
            assert einwurf["processed_by"] == BEARBEITER
            assert einwurf["drafts"][0]["user_id"] == SATZ_AUTORIN
            assert einwurf["links"][0]["processed_by"] == BEARBEITER
            assert einwurf["ist_eigener_einwurf"] is False


@pytest.mark.unit
def test_einwuerfe_namen_aus_einer_abfrage(einwurf_client, anzeigenamen_ohne_datenbank):
    einwurf_client("rawinput/getRawInputs", FREMD)

    assert anzeigenamen_ohne_datenbank.anzeigenamen.call_count == 1


# --------------------------------------------------------------------------- #
# Meine Beitraege
# --------------------------------------------------------------------------- #

MEINE_URL = "/api/v1/contribution/getContributionsOfUser"

meine_app = FastAPI()
meine_app.include_router(contribution_router, prefix="/api/v1/contribution")


@pytest.fixture
def meine_client(anzeigenamen_ohne_datenbank):
    _namen(anzeigenamen_ohne_datenbank, AUTORIN)
    eintrag = lambda: ContributionEntry.model_validate(  # noqa: E731
        {
            **_personen(),
            "id": str(uuid.uuid4()),
            "content_type": "commentary",
            "title": "Wärmepumpe lohnt sich auch im Altbau",
            "text": "Kommentartext",
        }
    )
    repository = MagicMock(
        getByAuthor=AsyncMock(side_effect=lambda **_: [eintrag(), eintrag()]),
        getCountByAuthor=AsyncMock(return_value=2),
    )
    factory = MagicMock()
    factory.create_content_repository.return_value = repository
    nutzung = MagicMock()
    nutzung.enrich_content_with_usage.side_effect = lambda eintraege: eintraege
    meine_app.dependency_overrides[get_settings] = lambda: MagicMock()
    meine_app.dependency_overrides[get_reference_service] = lambda: MagicMock()
    with patch.object(
        contribution_module, "QdrantRepositoryFactory", return_value=factory
    ), patch.object(contribution_module, "get_usage_service", return_value=nutzung):
        client = TestClient(meine_app)
        yield client, repository
    meine_app.dependency_overrides.clear()


@pytest.mark.unit
class TestMeineBeitraege:
    def test_nur_eigene_ohne_kennung(self, meine_client):
        client, repository = meine_client

        antwort = _abrufen(client, GET, MEINE_URL, EIGEN)

        _ohne_kennung(antwort)
        assert repository.getByAuthor.call_args.kwargs["user_id"] == AUTORIN
        for beitrag in _liste(antwort.json()):
            assert not NICHT_NACH_AUSSEN & set(beitrag)
            assert beitrag["ist_eigener_beitrag"] is True
            assert beitrag["title"] == "Wärmepumpe lohnt sich auch im Altbau"

    def test_admin_sieht_nur_die_eigene_kennung(self, meine_client):
        client, _ = meine_client

        antwort = _abrufen(
            client, GET, MEINE_URL, {"X-User": AUTORIN, "X-Is-Admin": "true"}
        )

        assert BEARBEITER not in antwort.text
        for beitrag in _liste(antwort.json()):
            assert beitrag["original_author"] == AUTORIN

    @pytest.mark.parametrize("headers", [ANONYM, {}])
    def test_ohne_anmeldung_nichts(self, meine_client, headers):
        client, repository = meine_client

        antwort = client.get(MEINE_URL, headers=headers)

        assert antwort.status_code == 401
        repository.getByAuthor.assert_not_called()


@pytest.mark.unit
def test_einwurf_ohne_person_ohne_kennzeichen(
    einwurf_client, anzeigenamen_ohne_datenbank
):
    """Ohne Einwerfer (Wege ohne Sitzung) gibt es kein "eigen" und kein "fremd"."""
    repository = einwurf_app.dependency_overrides[get_raw_input_repository]()
    repository.get_by_id.side_effect = lambda *_: {**_einwurf(), "submitted_by": None}

    einwurf = einwurf_client("rawinput/{id}", FREMD).json()

    assert einwurf["submitted_by_name"] is None
    assert einwurf["ist_eigener_einwurf"] is None
