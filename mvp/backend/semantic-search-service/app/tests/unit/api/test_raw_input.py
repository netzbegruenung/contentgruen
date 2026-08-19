"""
Der Fangkorb-Eingang: was hineinkommt und was abgewiesen wird.

Der Kern der Idee ist, dass ein Einwurf drei Sekunden dauert. Getestet wird
deshalb vor allem, was *nicht* verlangt wird: kein Titel, kein Zieltyp, kein
Text, wenn ein Link da ist. Die einzige Pflicht ist, dass ueberhaupt etwas
dasteht - und dass eine URL keine Waffe ist.
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from api.v1.raw_input import router as raw_input_router
from domain.models.raw_input import RawInputSource, RawInputStatus
from repositories.raw_input_repository import get_raw_input_repository

ADD_URL = "/api/v1/rawinput/addRawInput"
LIST_URL = "/api/v1/rawinput/getRawInputs"

app = FastAPI()
app.include_router(raw_input_router, prefix="/api/v1/rawinput")


def _gespeicherter_einwurf(**overrides):
    eintrag = {
        "id": str(uuid.uuid4()),
        "content": "ein Satz",
        "url": None,
        "image_url": None,
        "submitted_by": "testuser",
        "source_channel": RawInputSource.WEB.value,
        "status": RawInputStatus.OPEN.value,
        "created_at": datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc),
    }
    eintrag.update(overrides)
    return eintrag


@pytest.fixture
def repository():
    repo = MagicMock()
    repo.create.return_value = _gespeicherter_einwurf()
    repo.get_all.return_value = []
    repo.count.return_value = 0
    app.dependency_overrides[get_raw_input_repository] = lambda: repo
    yield repo
    app.dependency_overrides.clear()


@pytest.fixture
def client(repository):
    return TestClient(app)


@pytest.mark.unit
@pytest.mark.api
class TestEinwerfen:
    def test_nur_ein_satz_genuegt(self, client, repository):
        antwort = client.post(
            ADD_URL,
            json={"content": "Guter Thread zu Waermepumpen"},
            headers={"X-User": "testuser"},
        )

        assert antwort.status_code == 201
        assert repository.create.call_args.kwargs["content"] == (
            "Guter Thread zu Waermepumpen"
        )

    def test_nur_ein_link_genuegt(self, client, repository):
        antwort = client.post(
            ADD_URL,
            json={"url": "https://example.org/post/1"},
            headers={"X-User": "testuser"},
        )

        assert antwort.status_code == 201
        assert repository.create.call_args.kwargs["url"] == "https://example.org/post/1"
        assert repository.create.call_args.kwargs["content"] is None

    def test_nur_eine_bild_url_genuegt(self, client, repository):
        antwort = client.post(
            ADD_URL,
            json={"image_url": "https://example.org/bild.png"},
            headers={"X-User": "testuser"},
        )

        assert antwort.status_code == 201

    def test_leerer_einwurf_wird_abgewiesen(self, client, repository):
        antwort = client.post(ADD_URL, json={}, headers={"X-User": "testuser"})

        assert antwort.status_code == 422
        repository.create.assert_not_called()

    def test_nur_leerzeichen_ist_ein_leerer_einwurf(self, client, repository):
        antwort = client.post(
            ADD_URL, json={"content": "   "}, headers={"X-User": "testuser"}
        )

        assert antwort.status_code == 422
        repository.create.assert_not_called()

    def test_leerraum_wird_abgeschnitten(self, client, repository):
        client.post(
            ADD_URL, json={"content": "  ein Satz  "}, headers={"X-User": "testuser"}
        )

        assert repository.create.call_args.kwargs["content"] == "ein Satz"

    def test_einwurf_startet_immer_als_offen(self, client, repository):
        """Der Eingang waehlt keinen Zustand - das tut spaeter die Queue."""
        client.post(ADD_URL, json={"content": "x"}, headers={"X-User": "testuser"})

        # Der Status wird im Repository gesetzt, nicht vom Router uebergeben.
        assert "status" not in repository.create.call_args.kwargs
        assert repository.create.call_args.kwargs["source_channel"] == (
            RawInputSource.WEB.value
        )

    def test_kein_titel_und_kein_zieltyp_noetig(self, client, repository):
        """Wer einen Zieltyp waehlen muss, destilliert schon."""
        antwort = client.post(
            ADD_URL, json={"content": "x"}, headers={"X-User": "testuser"}
        )

        assert antwort.status_code == 201
        assert set(repository.create.call_args.kwargs) == {
            "content",
            "url",
            "image_url",
            "submitted_by",
            "source_channel",
        }


@pytest.mark.unit
@pytest.mark.api
class TestUrlPruefung:
    @pytest.mark.parametrize(
        "url",
        [
            "javascript:alert(1)",
            "data:text/html;base64,PHNjcmlwdD4=",
            "file:///etc/passwd",
            "example.org/ohne-schema",
        ],
    )
    def test_gefaehrliche_oder_schemalose_urls_werden_abgewiesen(
        self, client, repository, url
    ):
        antwort = client.post(ADD_URL, json={"url": url}, headers={"X-User": "u"})

        assert antwort.status_code == 422
        repository.create.assert_not_called()

    def test_gefaehrliche_bild_url_wird_abgewiesen(self, client, repository):
        antwort = client.post(
            ADD_URL,
            json={"image_url": "javascript:alert(1)"},
            headers={"X-User": "u"},
        )

        assert antwort.status_code == 422
        repository.create.assert_not_called()


@pytest.mark.unit
@pytest.mark.api
class TestEinwerfendePerson:
    def test_nutzerkennung_wird_uebernommen(self, client, repository):
        client.post(ADD_URL, json={"content": "x"}, headers={"X-User": "alice"})

        assert repository.create.call_args.kwargs["submitted_by"] == "alice"

    def test_ohne_header_wird_null_gespeichert(self, client, repository):
        """submitted_by nullable - sonst waere der Share-Eingang spaeter verbaut."""
        client.post(ADD_URL, json={"content": "x"})

        assert repository.create.call_args.kwargs["submitted_by"] is None

    def test_anonymous_ist_keine_kennung(self, client, repository):
        """Das BFF setzt "anonymous"; als Pseudo-Kennung gespeichert waere es Unsinn."""
        client.post(ADD_URL, json={"content": "x"}, headers={"X-User": "anonymous"})

        assert repository.create.call_args.kwargs["submitted_by"] is None


@pytest.mark.unit
@pytest.mark.api
class TestFangkorbListe:
    def test_liste_ist_leer_wenn_nichts_da_ist(self, client, repository):
        antwort = client.get(LIST_URL)

        assert antwort.status_code == 200
        assert antwort.json() == {
            "results_count": 0,
            "results": [],
            "total_records_count": 0,
        }

    def test_liste_gibt_einwuerfe_zurueck(self, client, repository):
        repository.get_all.return_value = [
            _gespeicherter_einwurf(content="a"),
            _gespeicherter_einwurf(content="b", submitted_by=None),
        ]
        repository.count.return_value = 2

        antwort = client.get(LIST_URL)
        daten = antwort.json()

        assert daten["results_count"] == 2
        assert daten["total_records_count"] == 2
        assert [e["content"] for e in daten["results"]] == ["a", "b"]
        assert daten["results"][1]["submitted_by"] is None

    def test_seitenwechsel_rechnet_offset_aus(self, client, repository):
        client.get(LIST_URL, params={"page": 3, "page_size": 10})

        assert repository.get_all.call_args.kwargs == {"limit": 10, "offset": 20}

    def test_liste_ist_nicht_auf_eine_person_gefiltert(self, client, repository):
        """Der Fangkorb ist ein gemeinsamer Vorrat, nicht die eigene Ablage."""
        client.get(LIST_URL, headers={"X-User": "alice"})

        assert "submitted_by" not in repository.get_all.call_args.kwargs
