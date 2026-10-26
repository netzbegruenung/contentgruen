"""
Bestehende Beitraege auf die drei Zustaende sichtbar, gesperrt, geloescht umstellen
(#214). Laeuft gegen qdrant_client im Speicher-Modus.
"""

import uuid

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from services.wartung.zustaende_umstellen import zustaende_umstellen

pytestmark = pytest.mark.unit

COLLECTION = f"test_zustaende_{uuid.uuid4().hex[:8]}"

# Punkt-ID -> Payload vor der Migration.
BESTAND = {
    1: {"status": "released_internal", "visibility": "internal"},
    2: {"status": "approved", "visibility": None},
    3: {"status": "published_external"},
    4: {"status": "draft"},
    5: {"status": "pending_review"},
    6: {"status": "archived"},
    7: {"status": "duplicate"},
    8: {"status": "rejected"},
    9: {"status": "flagged"},
    10: {},  # Altbestand ohne Status
    11: {"status": "blocked", "status_vor_sperre": "released_internal"},
    12: {"status": "blocked", "status_vor_sperre": None},
    13: {"status": "blocked"},
    14: {"status": "pending_description", "visibility": "visible"},
    15: {"status": "description_failed"},
    16: {"status": "visible"},
    17: {"status": "voellig_unbekannt"},
    18: {"status": "blocked", "status_vor_sperre": "pending_description"},
}


def punkte_anlegen(client):
    client.create_collection(
        COLLECTION, vectors_config=VectorParams(size=2, distance=Distance.COSINE)
    )
    client.upsert(
        COLLECTION,
        points=[
            PointStruct(
                id=i,
                vector=[1.0, 0.0],
                payload={"content_type": "commentary", "text": f"Satz {i}", **p},
            )
            for i, p in BESTAND.items()
        ],
    )


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

        for punkt_id in (11, 12, 13, 18):
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
        assert bericht.unbekannt == {"voellig_unbekannt": 1}

    def test_zustaende_umstellen_bericht_zaehlt_je_alter_status(self, client):
        bericht = zustaende_umstellen(client, COLLECTION)

        assert bericht.status["released_internal"] == 1
        assert bericht.status["(ohne)"] == 1
        assert bericht.status["blocked"] == 4
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
        assert payload["text"] == "Satz 1"
        assert payload["content_type"] == "commentary"
