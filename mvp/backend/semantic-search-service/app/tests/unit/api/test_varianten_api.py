"""
Varianten (#356): "Als Vorlage nehmen" speichert ueber das Formular des Typs einen
neuen Beitrag, der auf dem Original beruht; am Original zaehlt "N Varianten", und
/api/v1/varianten/{id} listet sie.

Das Repository ist der Ersatz aus tests/conftest.py (``varianten_ohne_datenbank``);
gegen PostgreSQL prueft tests/integration/test_varianten_postgres.py.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.commentary import router as commentary_router
from api.v1.generic_text import router as generic_text_router
from api.v1.varianten import router as varianten_router
from dependencies import (
    get_aussage_themen_service,
    get_commentary_service,
    get_generic_text_service,
    get_reference_service,
    get_statement_service,
)
from dtos.beitrag import KommentarResponse
from services.content.base_content_service import Dublettenpruefung
from services.varianten import varianten_ergaenzen
from utils.text_normalisierung import SperreJeText

HEADERS = {"X-User": "person-2"}
ORIGINAL = uuid.uuid4()

app = FastAPI()
app.include_router(commentary_router, prefix="/api/v1/commentary")
app.include_router(generic_text_router, prefix="/api/v1/generic_text")
app.include_router(varianten_router, prefix="/api/v1/varianten")


def _kommentar(**extra) -> dict:
    return {
        "commentary": {
            "title": "Waermepumpen lohnen sich auch im Altbau",
            "text": "Mit Foerderung rechnet sich die Pumpe schon nach wenigen Jahren.",
            "content_type": "commentary",
            "references": [],
        },
        "references": [],
        **extra,
    }


def _hintergrundinfo(**extra) -> dict:
    return {
        "generictext": {
            "title": "Waermepumpen sparen im Altbau 40 Prozent Heizkosten",
            "text": "Laut Feldtest erreichen Waermepumpen im Altbau gute Jahresarbeitszahlen.",
            "content_type": "generic_text",
            "references": [],
        },
        "references": [],
        **extra,
    }


def _typdienst(neue_id, anlegen: str):
    dienst = MagicMock()
    setattr(dienst, anlegen, AsyncMock(return_value=(True, neue_id, "text")))
    dienst.pruefe_dublette = AsyncMock(
        return_value=Dublettenpruefung(vorhanden=None, aehnlichster=None)
    )
    dienst.sperre = lambda text: SperreJeText().halten(text)
    # Das Original ist sichtbar.
    dienst.get = AsyncMock(return_value=MagicMock(id=ORIGINAL))
    return dienst


@pytest.fixture
def dienste():
    neue_id = uuid.uuid4()
    kommentare = _typdienst(neue_id, "add_commentary")
    hintergrundinfos = _typdienst(neue_id, "add_generic_text")
    reference_service = MagicMock()
    reference_service.find_exact_match = AsyncMock(return_value=None)
    app.dependency_overrides[get_commentary_service] = lambda: kommentare
    app.dependency_overrides[get_generic_text_service] = lambda: hintergrundinfos
    app.dependency_overrides[get_reference_service] = lambda: reference_service
    app.dependency_overrides[get_statement_service] = lambda: MagicMock()
    app.dependency_overrides[get_aussage_themen_service] = lambda: MagicMock()
    yield neue_id, kommentare, hintergrundinfos
    app.dependency_overrides.clear()


def _dublette(dienst, vorhanden_id):
    dienst.pruefe_dublette.return_value = Dublettenpruefung(
        vorhanden=MagicMock(id=vorhanden_id, original_author="person-1", title="T"),
        aehnlichster=None,
    )


@pytest.mark.api
class TestAlsVorlageSpeichern:
    def test_neuer_kommentar_beruht_auf_dem_original(
        self, dienste, varianten_ohne_datenbank
    ):
        neue_id, kommentare, _ = dienste

        resp = TestClient(app).post(
            "/api/v1/commentary/addCommentary",
            json=_kommentar(beruht_auf=str(ORIGINAL)),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == str(neue_id)
        # Eigener Autor: gespeichert unter der Kennung der Person, die ihn als
        # Vorlage nahm, nicht unter der des Originals.
        assert kommentare.add_commentary.await_args.args[1] == "person-2"
        kommentare.get.assert_awaited_once_with(ORIGINAL)
        varianten_ohne_datenbank.festhalten.assert_called_once_with(neue_id, ORIGINAL)

    def test_neue_hintergrundinfo_beruht_auf_dem_original(
        self, dienste, varianten_ohne_datenbank
    ):
        neue_id, _, hintergrundinfos = dienste

        resp = TestClient(app).post(
            "/api/v1/generic_text/addGenericText",
            json=_hintergrundinfo(beruht_auf=str(ORIGINAL)),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        hintergrundinfos.get.assert_awaited_once_with(ORIGINAL)
        varianten_ohne_datenbank.festhalten.assert_called_once_with(neue_id, ORIGINAL)

    def test_ohne_vorlage_wird_nichts_festgehalten(
        self, dienste, varianten_ohne_datenbank
    ):
        resp = TestClient(app).post(
            "/api/v1/commentary/addCommentary", json=_kommentar(), headers=HEADERS
        )

        assert resp.status_code == 200
        varianten_ohne_datenbank.festhalten.assert_not_called()

    def test_dublette_legt_nichts_an_und_verknuepft_nichts(
        self, dienste, varianten_ohne_datenbank
    ):
        # Unveraendert gespeichert ist die Variante eine Dublette des Originals.
        _, kommentare, _ = dienste
        _dublette(kommentare, ORIGINAL)

        resp = TestClient(app).post(
            "/api/v1/commentary/addCommentary",
            json=_kommentar(beruht_auf=str(ORIGINAL)),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == str(ORIGINAL)
        assert resp.json()["vorhanden"] == {"titel": "T", "eigen": False}
        kommentare.add_commentary.assert_not_awaited()
        varianten_ohne_datenbank.festhalten.assert_not_called()

    def test_trotzdem_speichern_legt_die_variante_an(
        self, dienste, varianten_ohne_datenbank
    ):
        neue_id, _, hintergrundinfos = dienste
        _dublette(hintergrundinfos, ORIGINAL)

        resp = TestClient(app).post(
            "/api/v1/generic_text/addGenericText",
            json=_hintergrundinfo(
                beruht_auf=str(ORIGINAL), trotz_dublette_von=str(ORIGINAL)
            ),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()["vorhanden"] is None
        varianten_ohne_datenbank.festhalten.assert_called_once_with(neue_id, ORIGINAL)

    @pytest.mark.parametrize("nicht_da", [None, ValueError("gesperrt")])
    def test_original_nicht_sichtbar_speichert_ohne_verknuepfung(
        self, dienste, varianten_ohne_datenbank, nicht_da
    ):
        neue_id, kommentare, _ = dienste
        if nicht_da is None:
            kommentare.get.return_value = None
        else:
            kommentare.get.side_effect = nicht_da

        resp = TestClient(app).post(
            "/api/v1/commentary/addCommentary",
            json=_kommentar(beruht_auf=str(ORIGINAL)),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == str(neue_id)
        varianten_ohne_datenbank.festhalten.assert_not_called()

    def test_scheitert_das_festhalten_bleibt_der_kommentar(
        self, dienste, varianten_ohne_datenbank
    ):
        neue_id, _, _ = dienste
        varianten_ohne_datenbank.festhalten.side_effect = RuntimeError("weg")

        resp = TestClient(app).post(
            "/api/v1/commentary/addCommentary",
            json=_kommentar(beruht_auf=str(ORIGINAL)),
            headers=HEADERS,
        )

        assert resp.status_code == 200
        assert resp.json()["id"] == str(neue_id)


def _karte(beitrag_id, titel, erstellt, typ="commentary") -> dict:
    return {
        "id": beitrag_id,
        "content_type": typ,
        "title": titel,
        "text": f"Text zu {titel}",
        "created": erstellt,
        "status": "visible",
        "original_author": "person-1",
        "references": [],
        "result_type": typ,
    }


@pytest.fixture
def liste(varianten_ohne_datenbank):
    """Original mit drei Varianten; die dritte ist gesperrt oder geloescht."""
    erste, zweite, weg = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    alt = datetime(2026, 10, 1, tzinfo=timezone.utc)
    neu = datetime(2026, 11, 1, tzinfo=timezone.utc)
    bestand = {
        ORIGINAL: _karte(ORIGINAL, "Original", alt),
        erste: _karte(erste, "Erste", alt),
        zweite: _karte(zweite, "Zweite", neu),
    }

    async def laden(beitrag_id):
        eintrag = bestand.get(beitrag_id)
        return dict(eintrag) if eintrag else None

    varianten_ohne_datenbank.varianten_von.return_value = [erste, zweite, weg]
    varianten_ohne_datenbank.anzahl_je_original.return_value = {ORIGINAL: 3}
    nutzung = Mock()
    nutzung.enrich_content_with_usage.side_effect = lambda eintraege: [
        {**e, "usage_count": 5 if e["id"] == erste else 0} for e in eintraege
    ]
    app.dependency_overrides[get_reference_service] = lambda: MagicMock()
    with patch("api.v1.varianten.get_usage_service", return_value=nutzung), patch(
        "api.v1.varianten.karten_beitrag_laden", return_value=laden
    ):
        yield bestand, erste, zweite
    app.dependency_overrides.clear()


@pytest.mark.api
class TestVariantenListe:
    def test_original_und_sichtbare_varianten_meistgenutzte_zuerst(self, liste):
        _, erste, zweite = liste

        resp = TestClient(app).get(f"/api/v1/varianten/{ORIGINAL}")

        assert resp.status_code == 200
        daten = resp.json()
        assert daten["original"]["id"] == str(ORIGINAL)
        assert daten["original"]["varianten"] == 3
        assert daten["original"]["result_type"] == "commentary"
        assert [v["id"] for v in daten["varianten"]] == [str(erste), str(zweite)]
        # Besucher sehen keine Kennung (fuer_aufrufer).
        assert daten["original"]["original_author"] is None

    def test_gleiche_nutzung_die_neueste_zuerst_auch_mit_sekundenbruchteil(self, liste):
        """Sortiert wird nach dem Zeitpunkt, nicht nach seinem Text (".5Z" < "Z")."""
        bestand, erste, zweite = liste
        bestand[erste]["created"] = datetime(2026, 11, 2, 10, 0, 0, tzinfo=timezone.utc)
        bestand[zweite]["created"] = datetime(
            2026, 11, 2, 10, 0, 0, 500000, tzinfo=timezone.utc
        )

        with patch("api.v1.varianten.get_usage_service") as nutzung:
            nutzung.return_value.enrich_content_with_usage.side_effect = lambda e: e
            resp = TestClient(app).get(f"/api/v1/varianten/{ORIGINAL}")

        assert [v["id"] for v in resp.json()["varianten"]] == [str(zweite), str(erste)]

    def test_original_nicht_sichtbar_ist_404(self, liste):
        resp = TestClient(app).get(f"/api/v1/varianten/{uuid.uuid4()}")

        assert resp.status_code == 404


@pytest.mark.unit
class TestVariantenErgaenzen:
    def test_setzt_die_anzahl_aus_einer_abfrage(self, varianten_ohne_datenbank):
        mit, ohne = uuid.uuid4(), uuid.uuid4()
        beitraege = [
            KommentarResponse.model_validate(_karte(mit, "Mit", datetime.now())),
            KommentarResponse.model_validate(_karte(ohne, "Ohne", datetime.now())),
        ]
        varianten_ohne_datenbank.anzahl_je_original.return_value = {mit: 2}

        varianten_ergaenzen(beitraege, varianten_ohne_datenbank)

        assert [b.varianten for b in beitraege] == [2, 0]
        varianten_ohne_datenbank.anzahl_je_original.assert_called_once_with([mit, ohne])

    def test_ohne_datenbank_bleibt_es_bei_null(self, varianten_ohne_datenbank):
        beitrag = KommentarResponse.model_validate(
            _karte(uuid.uuid4(), "T", datetime.now())
        )
        varianten_ohne_datenbank.anzahl_je_original.side_effect = RuntimeError()

        varianten_ergaenzen([beitrag], varianten_ohne_datenbank)

        assert beitrag.varianten == 0
