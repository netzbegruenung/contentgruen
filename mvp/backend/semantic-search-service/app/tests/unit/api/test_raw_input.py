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
from unittest.mock import AsyncMock, MagicMock

from pydantic import BaseModel, ValidationError

from api.v1.raw_input import router as raw_input_router
from dependencies import get_commentary_service, get_generic_text_service
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
    # Ohne das waere der Rueckgabewert ein MagicMock und damit wahr - jede
    # Beitragspruefung wuerde als Wiederholung uebersprungen.
    repo.statuswechsel_vorpruefen.return_value = False
    app.dependency_overrides[get_raw_input_repository] = lambda: repo
    yield repo
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def beitraege():
    """
    Kommentar- und Hintergrundinfo-Dienst fuer die Beitragspruefung bei processed.
    Standard: den Beitrag gibt es. Nicht gefunden meldet der echte Dienst als
    ValueError - so auch hier.
    """
    dienste = {
        "commentary": MagicMock(get=AsyncMock(return_value=MagicMock())),
        "generic_text": MagicMock(get=AsyncMock(return_value=MagicMock())),
    }
    app.dependency_overrides[get_commentary_service] = lambda: dienste["commentary"]
    app.dependency_overrides[get_generic_text_service] = lambda: dienste["generic_text"]
    yield dienste


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
        assert daten["results"][0]["drafts"] == []
        assert daten["results"][0]["links"] == []
        assert daten["results"][1]["processed_content_id"] == inhalt_id
        assert daten["results"][1]["processed_by"] == "bob"
        assert daten["results"][1]["processed_at"].startswith("2026-09-13T18:00")

    def test_liste_liefert_alle_saetze_und_verknuepften_beitraege(
        self, client, repository
    ):
        """Spec Fangkorb v2, Abschnitt A: alles, was die Karte braucht."""
        am = datetime(2026, 9, 13, 18, 0, tzinfo=timezone.utc)
        satz_id = str(uuid.uuid4())
        inhalt_id = str(uuid.uuid4())
        repository.get_all.return_value = [
            _gespeicherter_einwurf(
                status=RawInputStatus.PROCESSED.value,
                destilled_by="bob",
                drafts=[
                    {
                        "id": satz_id,
                        "user_id": "bob",
                        "sentence": "Waermepumpe lohnt sich auch im Altbau",
                        "updated_at": am,
                    }
                ],
                links=[
                    {
                        "content_id": inhalt_id,
                        "content_type": "commentary",
                        "draft_id": satz_id,
                        "processed_by": "carol",
                        "processed_at": am,
                    }
                ],
            )
        ]
        repository.count.return_value = 1

        (eintrag,) = client.get(LIST_URL, headers={"X-User": "alice"}).json()["results"]

        assert eintrag["status"] == "processed"
        assert eintrag["destilled_by"] == "bob"
        (satz,) = eintrag["drafts"]
        assert satz["user_id"] == "bob"
        assert satz["sentence"] == "Waermepumpe lohnt sich auch im Altbau"
        assert satz["updated_at"].startswith("2026-09-13T18:00")
        assert eintrag["links"] == [
            {
                "content_id": inhalt_id,
                "content_type": "commentary",
                "draft_id": satz_id,
                "processed_by": "carol",
                "processed_at": eintrag["links"][0]["processed_at"],
            }
        ]


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
            EINWURF_ID, RawInputStatus.DISCARDED, "alice", None, None
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
            json={
                "status": "processed",
                "content_id": str(inhalt_id),
                "content_type": "commentary",
            },
            headers={"X-User": "alice"},
        )

        assert antwort.status_code == 200
        assert antwort.json()["processed_by"] == "alice"
        repository.set_status.assert_called_once_with(
            EINWURF_ID, RawInputStatus.PROCESSED, "alice", inhalt_id, "commentary"
        )

    def test_verarbeitet_ohne_beitragstyp_bleibt_erlaubt(self, client, repository):
        """Eine noch zwischengespeicherte aeltere App schickt keinen Typ mit."""
        inhalt_id = uuid.uuid4()
        repository.set_status.return_value = _gespeicherter_einwurf(
            id=str(EINWURF_ID), status=RawInputStatus.PROCESSED.value
        )

        antwort = client.patch(
            STATUS_URL,
            json={"status": "processed", "content_id": str(inhalt_id)},
            headers={"X-User": "alice"},
        )

        assert antwort.status_code == 200
        repository.set_status.assert_called_once_with(
            EINWURF_ID, RawInputStatus.PROCESSED, "alice", inhalt_id, None
        )

    @pytest.mark.parametrize(
        "koerper",
        [
            {"status": "processed"},
            {"status": "discarded", "content_id": str(uuid.uuid4())},
            {"status": "in_progress"},
            {"status": "open"},
            {"status": "processed", "content_id": "keine-uuid"},
            {"status": "discarded", "content_type": "commentary"},
            {
                "status": "processed",
                "content_id": str(uuid.uuid4()),
                "content_type": "image",
            },
            {
                "status": "processed",
                "content_id": str(uuid.uuid4()),
                "content_type": "brieftaube",
            },
        ],
    )
    def test_ungueltige_statuswechsel_werden_abgewiesen(
        self, client, repository, koerper
    ):
        antwort = client.patch(STATUS_URL, json=koerper, headers={"X-User": "alice"})

        assert antwort.status_code == 422
        repository.set_status.assert_not_called()

    def test_verarbeitet_mit_unbekanntem_beitrag_ist_422(
        self, client, repository, beitraege
    ):
        """Eine erfundene ID schiebt keinen fremden Einwurf nach "Erledigt"."""
        beitraege["commentary"].get.side_effect = ValueError("not found")
        inhalt_id = uuid.uuid4()

        antwort = client.patch(
            STATUS_URL,
            json={
                "status": "processed",
                "content_id": str(inhalt_id),
                "content_type": "commentary",
            },
            headers={"X-User": "alice"},
        )

        assert antwort.status_code == 422
        assert antwort.json()["detail"] == "Diesen Beitrag gibt es nicht."
        beitraege["commentary"].get.assert_awaited_once_with(inhalt_id)
        repository.set_status.assert_not_called()

    def test_verarbeitet_mit_beitrag_anderen_typs_ist_422(
        self, client, repository, beitraege
    ):
        """Der Dienst des genannten Typs findet die ID nicht; der andere wird nicht gefragt."""
        beitraege["generic_text"].get.side_effect = ValueError("wrong content_type")

        antwort = client.patch(
            STATUS_URL,
            json={
                "status": "processed",
                "content_id": str(uuid.uuid4()),
                "content_type": "generic_text",
            },
            headers={"X-User": "alice"},
        )

        assert antwort.status_code == 422
        beitraege["commentary"].get.assert_not_called()
        repository.set_status.assert_not_called()

    def test_verarbeitet_ohne_typ_genuegt_ein_beitrag_eines_der_typen(
        self, client, repository, beitraege
    ):
        beitraege["commentary"].get.side_effect = ValueError("wrong content_type")
        repository.set_status.return_value = _gespeicherter_einwurf(
            id=str(EINWURF_ID), status=RawInputStatus.PROCESSED.value
        )

        antwort = client.patch(
            STATUS_URL,
            json={"status": "processed", "content_id": str(uuid.uuid4())},
            headers={"X-User": "alice"},
        )

        assert antwort.status_code == 200
        beitraege["generic_text"].get.assert_awaited_once()

    def test_verarbeitet_ohne_typ_und_ohne_beitrag_ist_422(
        self, client, repository, beitraege
    ):
        for dienst in beitraege.values():
            dienst.get.side_effect = ValueError("not found")

        antwort = client.patch(
            STATUS_URL,
            json={"status": "processed", "content_id": str(uuid.uuid4())},
            headers={"X-User": "alice"},
        )

        assert antwort.status_code == 422
        repository.set_status.assert_not_called()

    def test_speicher_nicht_erreichbar_ist_500_nicht_422(
        self, client, repository, beitraege
    ):
        beitraege["commentary"].get.side_effect = ConnectionError("qdrant weg")

        antwort = client.patch(
            STATUS_URL,
            json={
                "status": "processed",
                "content_id": str(uuid.uuid4()),
                "content_type": "commentary",
            },
            headers={"X-User": "alice"},
        )

        assert antwort.status_code == 500
        repository.set_status.assert_not_called()

    def test_unbekannter_einwurf_mit_unbekanntem_beitrag_bleibt_404(
        self, client, repository, beitraege
    ):
        """Erst der Einwurf, dann der Beitrag - 404 wird nicht zu 422."""
        repository.statuswechsel_vorpruefen.side_effect = EinwurfNichtGefunden(
            EINWURF_ID
        )
        for dienst in beitraege.values():
            dienst.get.side_effect = ValueError("not found")

        antwort = client.patch(
            STATUS_URL,
            json={
                "status": "processed",
                "content_id": str(uuid.uuid4()),
                "content_type": "commentary",
            },
            headers={"X-User": "alice"},
        )

        assert antwort.status_code == 404
        for dienst in beitraege.values():
            dienst.get.assert_not_called()
        repository.set_status.assert_not_called()

    def test_unerlaubter_uebergang_bleibt_409_vor_der_beitragspruefung(
        self, client, repository, beitraege
    ):
        repository.statuswechsel_vorpruefen.side_effect = UebergangNichtErlaubt(
            RawInputStatus.PROCESSED, RawInputStatus.PROCESSED
        )
        beitraege["commentary"].get.side_effect = ValueError("not found")

        antwort = client.patch(
            STATUS_URL,
            json={
                "status": "processed",
                "content_id": str(uuid.uuid4()),
                "content_type": "commentary",
            },
            headers={"X-User": "alice"},
        )

        assert antwort.status_code == 409
        beitraege["commentary"].get.assert_not_called()

    def test_wiederholung_nach_geloeschtem_beitrag_bleibt_unschaedlich(
        self, client, repository, beitraege
    ):
        """
        Die Antwort ging verloren, der Beitrag ist inzwischen weg: Die Verknuepfung
        steht schon, die Wiederholung darf nicht an der Beitragspruefung scheitern.
        """
        inhalt_id = uuid.uuid4()
        repository.statuswechsel_vorpruefen.return_value = True
        beitraege["commentary"].get.side_effect = ValueError("not found")
        repository.set_status.return_value = _gespeicherter_einwurf(
            id=str(EINWURF_ID), status=RawInputStatus.PROCESSED.value
        )

        antwort = client.patch(
            STATUS_URL,
            json={
                "status": "processed",
                "content_id": str(inhalt_id),
                "content_type": "commentary",
            },
            headers={"X-User": "alice"},
        )

        assert antwort.status_code == 200
        repository.statuswechsel_vorpruefen.assert_called_once_with(
            EINWURF_ID, RawInputStatus.PROCESSED, "alice", inhalt_id
        )
        beitraege["commentary"].get.assert_not_called()
        repository.set_status.assert_called_once()

    def test_unlesbarer_beitrag_ist_500_nicht_422(self, client, repository, beitraege):
        """ValidationError erbt von ValueError, heisst aber nicht "gibt es nicht"."""

        class Streng(BaseModel):
            zahl: int

        try:
            Streng.model_validate({"zahl": "keine"})
        except ValidationError as fehler:
            beitraege["commentary"].get.side_effect = fehler

        antwort = client.patch(
            STATUS_URL,
            json={
                "status": "processed",
                "content_id": str(uuid.uuid4()),
                "content_type": "commentary",
            },
            headers={"X-User": "alice"},
        )

        assert antwort.status_code == 500
        beitraege["generic_text"].get.assert_not_called()
        repository.set_status.assert_not_called()

    def test_verwerfen_prueft_keinen_beitrag(self, client, repository, beitraege):
        repository.set_status.return_value = _gespeicherter_einwurf(
            id=str(EINWURF_ID), status=RawInputStatus.DISCARDED.value
        )

        client.patch(
            STATUS_URL, json={"status": "discarded"}, headers={"X-User": "alice"}
        )

        for dienst in beitraege.values():
            dienst.get.assert_not_called()

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
