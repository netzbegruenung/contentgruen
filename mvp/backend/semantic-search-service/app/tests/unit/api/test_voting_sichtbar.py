"""
Stimmen nur auf sichtbare Beitraege (#272, Review von #319, Befund 15).

Gesperrt, geloescht oder nie vorhanden heisst fuer das Repository "nicht da"
(ValueError); dann gibt es keine neue Stimme, sondern 404. Zuruecknehmen bleibt
moeglich: Eine alte Stimme an einem inzwischen gesperrten Beitrag soll die Person
loswerden koennen. Ein Datensatz, der da ist, sich aber nicht lesen laesst, ist
kaputt und nicht abwesend: Die Stimme zaehlt wie bei der Nutzung. Ebenso, wenn
der Suchindex nicht antwortet: Stimmen liegen in PostgreSQL.
"""

import uuid
from functools import partial
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from api.v1.voting import router as voting_router
from dependencies import get_beitrag_laden, get_voting_service
from domain.models.vote import VoteResponse
from services.beitrag_laden import beitrag_laden

pytestmark = pytest.mark.unit

BEITRAG = uuid.uuid4()
ANGEMELDET = {"X-User": "kennung-1"}


def _unlesbar() -> ValidationError:
    class Pflicht(BaseModel):
        feld: int

    try:
        Pflicht.model_validate({})
    except ValidationError as fehler:
        return fehler


@pytest.fixture
def repository():
    repo = MagicMock()
    repo.get = AsyncMock(return_value=object())
    return repo


@pytest.fixture
def dienst():
    dienst = MagicMock()
    for methode in ("set_like", "set_dislike", "remove_like", "remove_dislike"):
        getattr(dienst, methode).return_value = VoteResponse(
            content_id=BEITRAG, vote_type=None, message="ok"
        )
    return dienst


@pytest.fixture
def client(repository, dienst):
    """Echtes beitrag_laden (services/beitrag_laden.py) ueber ein gemocktes Repository."""
    app = FastAPI()
    app.include_router(voting_router, prefix="/api/v1/voting")
    app.dependency_overrides[get_beitrag_laden] = lambda: partial(
        beitrag_laden, repository=repository
    )
    app.dependency_overrides[get_voting_service] = lambda: dienst
    return TestClient(app)


@pytest.mark.parametrize("art", ["like", "dislike"])
class TestAbstimmen:
    def test_sichtbarer_beitrag_bekommt_die_stimme(self, client, dienst, art):
        antwort = client.put(
            f"/api/v1/voting/content/{BEITRAG}/{art}", headers=ANGEMELDET
        )

        assert antwort.status_code == 200
        getattr(dienst, f"set_{art}").assert_called_once_with("kennung-1", BEITRAG)

    def test_nicht_sichtbarer_beitrag_gibt_404_ohne_stimme(
        self, client, repository, dienst, art
    ):
        repository.get.side_effect = ValueError("nicht da")

        antwort = client.put(
            f"/api/v1/voting/content/{BEITRAG}/{art}", headers=ANGEMELDET
        )

        assert antwort.status_code == 404
        getattr(dienst, f"set_{art}").assert_not_called()

    def test_unlesbarer_beitrag_bekommt_die_stimme(
        self, client, repository, dienst, art
    ):
        repository.get.side_effect = _unlesbar()

        antwort = client.put(
            f"/api/v1/voting/content/{BEITRAG}/{art}", headers=ANGEMELDET
        )

        assert antwort.status_code == 200
        getattr(dienst, f"set_{art}").assert_called_once()

    def test_ohne_suchindex_bekommt_der_beitrag_die_stimme(
        self, client, repository, dienst, art
    ):
        repository.get.side_effect = ConnectionError("Qdrant weg")

        antwort = client.put(
            f"/api/v1/voting/content/{BEITRAG}/{art}", headers=ANGEMELDET
        )

        assert antwort.status_code == 200
        getattr(dienst, f"set_{art}").assert_called_once()

    def test_ohne_repository_bekommt_der_beitrag_die_stimme(self, dienst, art):
        """Scheitert schon das Repository, zaehlt die Stimme wie ohne Suchindex."""
        app = FastAPI()
        app.include_router(voting_router, prefix="/api/v1/voting")
        app.dependency_overrides[get_voting_service] = lambda: dienst

        with patch(
            "dependencies.get_content_repository",
            side_effect=RuntimeError("Embeddings nicht gestartet"),
        ):
            antwort = TestClient(app).put(
                f"/api/v1/voting/content/{BEITRAG}/{art}", headers=ANGEMELDET
            )

        assert antwort.status_code == 200
        getattr(dienst, f"set_{art}").assert_called_once()

    def test_uebersprungene_pruefung_loggt_den_stacktrace(
        self, client, repository, art, caplog
    ):
        repository.get.side_effect = ConnectionError("Qdrant weg")

        with caplog.at_level("WARNING"):
            client.put(f"/api/v1/voting/content/{BEITRAG}/{art}", headers=ANGEMELDET)

        eintrag = next(
            r for r in caplog.records if "Visibility check" in r.getMessage()
        )
        assert eintrag.exc_info is not None

    def test_ohne_anmeldung_401_vor_der_pruefung(self, client, repository, art):
        antwort = client.put(f"/api/v1/voting/content/{BEITRAG}/{art}")

        assert antwort.status_code == 401
        repository.get.assert_not_awaited()

    def test_zuruecknehmen_geht_auch_am_nicht_sichtbaren(
        self, client, repository, dienst, art
    ):
        repository.get.side_effect = ValueError("nicht da")

        antwort = client.delete(
            f"/api/v1/voting/content/{BEITRAG}/{art}", headers=ANGEMELDET
        )

        assert antwort.status_code == 200
        getattr(dienst, f"remove_{art}").assert_called_once()
