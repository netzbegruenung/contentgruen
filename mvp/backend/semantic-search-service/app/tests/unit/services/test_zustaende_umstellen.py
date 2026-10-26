"""
Bestehende Beitraege auf die drei Zustaende sichtbar, gesperrt, geloescht umstellen
(#214). Laeuft gegen qdrant_client im Speicher-Modus.
"""

import pytest
from qdrant_client import QdrantClient

from services.wartung import zustaende_umstellen as modul
from services.wartung.zustaende_umstellen import zustaende_umstellen
from tests.unit.services.zustaende_altbestand import (
    BESTAND,
    COLLECTION,
    punkte_anlegen,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def client():
    client = QdrantClient(":memory:")
    punkte_anlegen(client)
    return client


def _payload(client, punkt_id):
    return client.retrieve(COLLECTION, [punkt_id], with_payload=True)[0].payload


class TestZustaendeUmstellen:
    def test_zustaende_umstellen_ohne_ausfuehren_aendert_nichts(self, client):
        bericht = zustaende_umstellen(client, COLLECTION)

        assert not bericht.ausgefuehrt
        assert bericht.zu_aendern == 14
        for punkt_id, vorher in BESTAND.items():
            payload = _payload(client, punkt_id)
            assert payload.get("status") == vorher.get("status")
            assert ("visibility" in payload) == ("visibility" in vorher)

    @pytest.mark.parametrize(
        "punkt_id", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], ids=lambda i: str(i)
    )
    def test_zustaende_umstellen_bisher_auffindbar_wird_sichtbar(
        self, client, punkt_id
    ):
        zustaende_umstellen(client, COLLECTION, ausfuehren=True)

        assert _payload(client, punkt_id)["status"] == "visible"

    def test_zustaende_umstellen_gesperrt_bleibt_gesperrt(self, client):
        zustaende_umstellen(client, COLLECTION, ausfuehren=True)

        for punkt_id in (11, 12, 13, 18, 19):
            assert _payload(client, punkt_id)["status"] == "blocked"

    def test_zustaende_umstellen_status_vor_sperre_auf_neue_zustaende(self, client):
        """Entsperren darf keinen entfernten Zustand zurueckbringen."""
        zustaende_umstellen(client, COLLECTION, ausfuehren=True)

        assert _payload(client, 11)["status_vor_sperre"] == "visible"
        assert _payload(client, 12)["status_vor_sperre"] == "visible"
        assert _payload(client, 13)["status_vor_sperre"] == "visible"
        assert _payload(client, 18)["status_vor_sperre"] == "pending_description"

    def test_zustaende_umstellen_bild_vorstufen_bleiben(self, client):
        zustaende_umstellen(client, COLLECTION, ausfuehren=True)

        assert _payload(client, 14)["status"] == "pending_description"
        assert _payload(client, 15)["status"] == "description_failed"

    def test_zustaende_umstellen_entfernt_visibility_auch_leer(self, client):
        zustaende_umstellen(client, COLLECTION, ausfuehren=True)

        for punkt_id in BESTAND:
            assert "visibility" not in _payload(client, punkt_id)

    def test_zustaende_umstellen_unbekannter_status_bleibt_und_wird_gemeldet(
        self, client
    ):
        bericht = zustaende_umstellen(client, COLLECTION, ausfuehren=True)

        assert _payload(client, 17)["status"] == "voellig_unbekannt"
        assert _payload(client, 19)["status_vor_sperre"] == "voellig_unbekannt"
        assert bericht.unbekannt == {
            "voellig_unbekannt": 1,
            "status_vor_sperre=voellig_unbekannt": 1,
        }

    def test_zustaende_umstellen_bericht_zaehlt_je_alter_status(self, client):
        bericht = zustaende_umstellen(client, COLLECTION)

        assert bericht.status["released_internal"] == 1
        assert bericht.status["(ohne)"] == 1
        assert bericht.status["blocked"] == 5
        assert bericht.status["visible"] == 1
        assert bericht.visibility_entfernt == 3
        assert bericht.status_vor_sperre_umgestellt == 3

    def test_zustaende_umstellen_ist_wiederholbar(self, client):
        zustaende_umstellen(client, COLLECTION, ausfuehren=True)
        vorher = {i: _payload(client, i) for i in BESTAND}

        bericht = zustaende_umstellen(client, COLLECTION, ausfuehren=True)

        assert bericht.zu_aendern == 0
        assert {i: _payload(client, i) for i in BESTAND} == vorher

    def test_zustaende_umstellen_laesst_uebrige_felder_stehen(self, client):
        zustaende_umstellen(client, COLLECTION, ausfuehren=True)

        payload = _payload(client, 1)
        assert payload["text"] == "Kommentar 1"
        assert payload["content_type"] == "commentary"

    def test_zustaende_umstellen_ueber_mehrere_seiten(self, client, monkeypatch):
        monkeypatch.setattr(modul, "SEITE", 5)
        schreibvorgaenge = []
        original = client.batch_update_points

        def mitzaehlen(**kwargs):
            schreibvorgaenge.append(len(kwargs["update_operations"]))
            return original(**kwargs)

        monkeypatch.setattr(client, "batch_update_points", mitzaehlen)

        bericht = zustaende_umstellen(client, COLLECTION, ausfuehren=True)

        assert bericht.zu_aendern == 14
        assert len(schreibvorgaenge) == 3
        assert all(_payload(client, i)["status"] == "visible" for i in range(1, 11))
        assert zustaende_umstellen(client, COLLECTION).zu_aendern == 0

    def test_zustaende_umstellen_laesst_sperre_waehrend_des_laufs_stehen(
        self, client, monkeypatch
    ):
        """Ein Admin sperrt zwischen Lesen und Schreiben; die Sperre bleibt."""
        original = client.batch_update_points

        def admin_sperrt_vorher(**kwargs):
            client.set_payload(
                COLLECTION,
                payload={"status": "blocked", "status_vor_sperre": "released_internal"},
                points=[1],
            )
            return original(**kwargs)

        monkeypatch.setattr(client, "batch_update_points", admin_sperrt_vorher)

        zustaende_umstellen(client, COLLECTION, ausfuehren=True)

        assert _payload(client, 1)["status"] == "blocked"
        assert _payload(client, 2)["status"] == "visible"

        monkeypatch.setattr(client, "batch_update_points", original)
        zustaende_umstellen(client, COLLECTION, ausfuehren=True)

        assert _payload(client, 1)["status"] == "blocked"
        assert _payload(client, 1)["status_vor_sperre"] == "visible"
