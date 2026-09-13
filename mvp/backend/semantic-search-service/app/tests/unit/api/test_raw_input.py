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
from domain.models.raw_input import (
    AktionNichtErlaubt,
    EinwurfNichtGefunden,
    RawInputSource,
    RawInputStatus,
    UebergangNichtErlaubt,
)
from repositories.raw_input_repository import get_raw_input_repository

ADD_URL = "/api/v1/rawinput/addRawInput"
LIST_URL = "/api/v1/rawinput/getRawInputs"
EINWURF_ID = uuid.UUID("11111111-2222-3333-4444-555555555555")
EINZEL_URL = f"/api/v1/rawinput/{EINWURF_ID}"
ENTWURF_URL = f"/api/v1/rawinput/{EINWURF_ID}/draft"
STATUS_URL = f"/api/v1/rawinput/{EINWURF_ID}/status"

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
class TestHerkunftskanal:
    """
    source_channel sagt, wie ein Einwurf hereinkam. Der Wert ist selbst berichtet
    und traegt keine Rechte - geprueft wird nur, dass nichts Erfundenes durchkommt.
    """

    def test_ohne_angabe_zaehlt_der_einwurf_als_web(self, client, repository):
        client.post(ADD_URL, json={"content": "x"}, headers={"X-User": "testuser"})

        assert repository.create.call_args.kwargs["source_channel"] == (
            RawInputSource.WEB.value
        )

    def test_share_wird_uebernommen(self, client, repository):
        """Der Weg ueber das Android-Teilen-Menue."""
        antwort = client.post(
            ADD_URL,
            json={"url": "https://example.org/a", "source_channel": "share"},
            headers={"X-User": "testuser"},
        )

        assert antwort.status_code == 201
        assert repository.create.call_args.kwargs["source_channel"] == (
            RawInputSource.SHARE.value
        )

    def test_erfundener_kanal_wird_abgewiesen(self, client, repository):
        antwort = client.post(
            ADD_URL,
            json={"content": "x", "source_channel": "brieftaube"},
            headers={"X-User": "testuser"},
        )

        assert antwort.status_code == 422
        repository.create.assert_not_called()


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

        assert repository.get_all.call_args.kwargs == {
            "limit": 10,
            "offset": 20,
            "current_user": None,
        }

    def test_liste_ist_nicht_auf_eine_person_gefiltert(self, client, repository):
        """Der Fangkorb ist ein gemeinsamer Vorrat, nicht die eigene Ablage."""
        client.get(LIST_URL, headers={"X-User": "alice"})

        assert "submitted_by" not in repository.get_all.call_args.kwargs

    def test_liste_sortiert_fuer_die_anfragende_person(self, client, repository):
        """Eigene zuerst - dafuer muss das Repository wissen, wer fragt."""
        client.get(LIST_URL, headers={"X-User": "alice"})

        assert repository.get_all.call_args.kwargs["current_user"] == "alice"

    def test_anonymous_sortiert_ohne_person(self, client, repository):
        client.get(LIST_URL, headers={"X-User": "anonymous"})

        assert repository.get_all.call_args.kwargs["current_user"] is None

    def test_liste_liefert_entwurf_und_bearbeitungsstand(self, client, repository):
        verarbeitet_am = datetime(2026, 9, 13, 18, 0, tzinfo=timezone.utc)
        inhalt_id = str(uuid.uuid4())
        repository.get_all.return_value = [
            _gespeicherter_einwurf(own_draft="Mein Satz"),
            _gespeicherter_einwurf(
                status=RawInputStatus.PROCESSED.value,
                processed_content_id=inhalt_id,
                processed_by="bob",
                processed_at=verarbeitet_am,
            ),
        ]
        repository.count.return_value = 2

        daten = client.get(LIST_URL, headers={"X-User": "alice"}).json()

        assert daten["results"][0]["own_draft"] == "Mein Satz"
        assert daten["results"][0]["processed_by"] is None
        assert daten["results"][1]["processed_content_id"] == inhalt_id
        assert daten["results"][1]["processed_by"] == "bob"
        assert daten["results"][1]["processed_at"].startswith("2026-09-13T18:00")


@pytest.mark.unit
@pytest.mark.api
class TestEinzelabruf:
    def test_einzelabruf_liefert_einwurf_mit_eigenem_entwurf(self, client, repository):
        repository.get_by_id.return_value = _gespeicherter_einwurf(
            id=str(EINWURF_ID), own_draft="Mein Satz"
        )

        antwort = client.get(EINZEL_URL, headers={"X-User": "alice"})

        assert antwort.status_code == 200
        assert antwort.json()["own_draft"] == "Mein Satz"
        repository.get_by_id.assert_called_once_with(EINWURF_ID, "alice")

    def test_einzelabruf_unbekannte_id_ist_404(self, client, repository):
        repository.get_by_id.return_value = None

        antwort = client.get(EINZEL_URL, headers={"X-User": "alice"})

        assert antwort.status_code == 404

    def test_einzelabruf_ungueltige_id_ist_422(self, client, repository):
        antwort = client.get("/api/v1/rawinput/keine-uuid", headers={"X-User": "a"})

        assert antwort.status_code == 422
        repository.get_by_id.assert_not_called()

    def test_einzelabruf_verdeckt_die_liste_nicht(self, client, repository):
        """/getRawInputs steht vor /{id} und muss weiter die Liste liefern."""
        antwort = client.get(LIST_URL)

        assert antwort.status_code == 200
        repository.get_all.assert_called_once()
        repository.get_by_id.assert_not_called()


@pytest.mark.unit
@pytest.mark.api
class TestEntwurf:
    def test_entwurf_wird_fuer_die_person_gespeichert(self, client, repository):
        repository.save_draft.return_value = {
            "raw_input_id": str(EINWURF_ID),
            "sentence": "Waermepumpe lohnt sich auch im Altbau",
            "updated_at": datetime(2026, 9, 13, 18, 0, tzinfo=timezone.utc),
        }

        antwort = client.put(
            ENTWURF_URL,
            json={"sentence": "  Waermepumpe lohnt sich auch im Altbau "},
            headers={"X-User": "alice"},
        )

        assert antwort.status_code == 200
        assert antwort.json()["sentence"] == "Waermepumpe lohnt sich auch im Altbau"
        repository.save_draft.assert_called_once_with(
            EINWURF_ID, "alice", "Waermepumpe lohnt sich auch im Altbau"
        )

    def test_entwurf_120_zeichen_sind_erlaubt(self, client, repository):
        repository.save_draft.return_value = {
            "raw_input_id": str(EINWURF_ID),
            "sentence": "a" * 120,
            "updated_at": None,
        }

        antwort = client.put(
            ENTWURF_URL, json={"sentence": "a" * 120}, headers={"X-User": "alice"}
        )

        assert antwort.status_code == 200

    def test_entwurf_121_zeichen_werden_abgewiesen(self, client, repository):
        """Der Satz wird der Titel - und der hat 120 Zeichen."""
        antwort = client.put(
            ENTWURF_URL, json={"sentence": "a" * 121}, headers={"X-User": "alice"}
        )

        assert antwort.status_code == 422
        repository.save_draft.assert_not_called()

    def test_leerer_satz_loescht_den_entwurf(self, client, repository):
        repository.save_draft.return_value = {
            "raw_input_id": str(EINWURF_ID),
            "sentence": None,
            "updated_at": None,
        }

        client.put(ENTWURF_URL, json={"sentence": "   "}, headers={"X-User": "alice"})

        repository.save_draft.assert_called_once_with(EINWURF_ID, "alice", None)

    @pytest.mark.parametrize("kopfzeilen", [{}, {"X-User": "anonymous"}])
    def test_entwurf_ohne_anmeldung_ist_401(self, client, repository, kopfzeilen):
        antwort = client.put(ENTWURF_URL, json={"sentence": "x"}, headers=kopfzeilen)

        assert antwort.status_code == 401
        repository.save_draft.assert_not_called()

    def test_entwurf_zu_unbekanntem_einwurf_ist_404(self, client, repository):
        repository.save_draft.side_effect = EinwurfNichtGefunden(EINWURF_ID)

        antwort = client.put(
            ENTWURF_URL, json={"sentence": "x"}, headers={"X-User": "alice"}
        )

        assert antwort.status_code == 404


@pytest.mark.unit
@pytest.mark.api
class TestStatuswechsel:
    def test_verwerfen_ruft_das_repository_ohne_beitrag(self, client, repository):
        repository.set_status.return_value = _gespeicherter_einwurf(
            id=str(EINWURF_ID), status=RawInputStatus.DISCARDED.value
        )

        antwort = client.patch(
            STATUS_URL, json={"status": "discarded"}, headers={"X-User": "alice"}
        )

        assert antwort.status_code == 200
        assert antwort.json()["status"] == "discarded"
        repository.set_status.assert_called_once_with(
            EINWURF_ID, RawInputStatus.DISCARDED, "alice", None
        )

    def test_verarbeitet_gibt_beitrag_und_bearbeitenden_zurueck(
        self, client, repository
    ):
        inhalt_id = uuid.uuid4()
        repository.set_status.return_value = _gespeicherter_einwurf(
            id=str(EINWURF_ID),
            status=RawInputStatus.PROCESSED.value,
            processed_content_id=str(inhalt_id),
            processed_by="alice",
            processed_at=datetime(2026, 9, 13, 18, 0, tzinfo=timezone.utc),
        )

        antwort = client.patch(
            STATUS_URL,
            json={"status": "processed", "content_id": str(inhalt_id)},
            headers={"X-User": "alice"},
        )

        assert antwort.status_code == 200
        assert antwort.json()["processed_by"] == "alice"
        repository.set_status.assert_called_once_with(
            EINWURF_ID, RawInputStatus.PROCESSED, "alice", inhalt_id
        )

    @pytest.mark.parametrize(
        "koerper",
        [
            {"status": "processed"},
            {"status": "discarded", "content_id": str(uuid.uuid4())},
            {"status": "in_progress"},
            {"status": "open"},
            {"status": "processed", "content_id": "keine-uuid"},
        ],
    )
    def test_ungueltige_statuswechsel_werden_abgewiesen(
        self, client, repository, koerper
    ):
        antwort = client.patch(STATUS_URL, json=koerper, headers={"X-User": "alice"})

        assert antwort.status_code == 422
        repository.set_status.assert_not_called()

    @pytest.mark.parametrize("kopfzeilen", [{}, {"X-User": "anonymous"}])
    def test_statuswechsel_ohne_anmeldung_ist_401(self, client, repository, kopfzeilen):
        antwort = client.patch(
            STATUS_URL, json={"status": "discarded"}, headers=kopfzeilen
        )

        assert antwort.status_code == 401
        repository.set_status.assert_not_called()

    @pytest.mark.parametrize(
        "fehler, code",
        [
            (EinwurfNichtGefunden(EINWURF_ID), 404),
            (AktionNichtErlaubt("nur Einwerfer"), 403),
            (
                UebergangNichtErlaubt(
                    RawInputStatus.PROCESSED, RawInputStatus.DISCARDED
                ),
                409,
            ),
        ],
    )
    def test_fehler_aus_dem_repository_werden_uebersetzt(
        self, client, repository, fehler, code
    ):
        repository.set_status.side_effect = fehler

        antwort = client.patch(
            STATUS_URL, json={"status": "discarded"}, headers={"X-User": "alice"}
        )

        assert antwort.status_code == code
