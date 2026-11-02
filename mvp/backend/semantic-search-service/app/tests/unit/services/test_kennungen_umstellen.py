"""
Kennungen auf den Realm von Gut gesagt umstellen (#487): Qdrant, Listen aus der
Konfiguration und die Pruefung der Zuordnung.

Laeuft gegen qdrant_client im Speicher-Modus; PostgreSQL steht in
tests/integration/test_kennungen_umstellen_postgres.py.
"""

import uuid

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from services.anzeigename_service import EHEMALIGE_PERSON_KENNUNG
from services.wartung.kennungen_umstellen import (
    kennungen_in_qdrant,
    liste_umschreiben,
    qdrant_umschreiben,
    zuordnung_pruefen,
)

pytestmark = pytest.mark.unit

COLLECTION = f"test_kennungen_{uuid.uuid4().hex[:8]}"
ALT = "alt-netzbegruenung-1"
NEU = "neu-gutgesagt-1"
ALT_2 = "alt-netzbegruenung-2"
NEU_2 = "neu-gutgesagt-2"
BETA = "user-001"


def _payload(original_author, last_modified_by=None, authors=(), editors=()):
    return {
        "content_type": "commentary",
        "text": "Waermepumpen lohnen sich auch im Altbau",
        "original_author": original_author,
        "last_modified_by": last_modified_by or original_author,
        "authors": [{"name": n, "role": "author"} for n in authors],
        "edit_history": [
            {"editor": e, "timestamp": "2026-10-01T00:00:00"} for e in editors
        ],
    }


@pytest.fixture
def client():
    client = QdrantClient(":memory:")
    client.create_collection(
        COLLECTION, vectors_config=VectorParams(size=2, distance=Distance.COSINE)
    )
    punkte = {
        1: _payload(ALT, authors=[ALT], editors=[ALT]),
        # Fremder Beitrag, an dem ALT_2 mitgeschrieben und editiert hat.
        2: _payload(BETA, ALT_2, authors=[BETA, ALT_2], editors=[BETA, ALT_2]),
        3: _payload(BETA, authors=[BETA], editors=[BETA]),
        4: _payload(EHEMALIGE_PERSON_KENNUNG, authors=[EHEMALIGE_PERSON_KENNUNG]),
    }
    client.upsert(
        COLLECTION,
        [PointStruct(id=i, vector=[1.0, 0.0], payload=p) for i, p in punkte.items()],
    )
    return client


def _gelesen(client, punkt_id):
    return client.retrieve(COLLECTION, [punkt_id], with_payload=True)[0].payload


def _kennungen(payload):
    return {
        payload["original_author"],
        payload["last_modified_by"],
        *(a["name"] for a in payload["authors"]),
        *(e["editor"] for e in payload["edit_history"]),
    }


class TestKennungenFinden:
    def test_findet_alle_kennungen_ausser_platzhaltern(self, client):
        assert kennungen_in_qdrant(client, COLLECTION) == {ALT, ALT_2, BETA}


class TestQdrantUmschreiben:
    def test_alle_vier_felder_bekommen_die_neue_kennung(self, client):
        qdrant_umschreiben(client, COLLECTION, {ALT: NEU}, ausfuehren=True)

        assert _kennungen(_gelesen(client, 1)) == {NEU}

    def test_fremde_kennungen_am_selben_beitrag_bleiben(self, client):
        qdrant_umschreiben(client, COLLECTION, {ALT_2: NEU_2}, ausfuehren=True)

        payload = _gelesen(client, 2)
        assert payload["original_author"] == BETA
        assert payload["last_modified_by"] == NEU_2
        assert [a["name"] for a in payload["authors"]] == [BETA, NEU_2]
        assert [e["editor"] for e in payload["edit_history"]] == [BETA, NEU_2]
        assert payload["authors"][1]["role"] == "author"

    def test_zaehlt_punkte_und_laesst_unbeteiligte(self, client):
        vorher = _gelesen(client, 3)

        anzahl = qdrant_umschreiben(
            client, COLLECTION, {ALT: NEU, ALT_2: NEU_2}, ausfuehren=True
        )

        assert anzahl == 2
        assert _gelesen(client, 3) == vorher

    def test_trockenlauf_zaehlt_und_aendert_nichts(self, client):
        anzahl = qdrant_umschreiben(client, COLLECTION, {ALT: NEU, ALT_2: NEU_2})

        assert anzahl == 2
        assert _kennungen(_gelesen(client, 1)) == {ALT}

    def test_zweiter_lauf_findet_nichts(self, client):
        zuordnung = {ALT: NEU, ALT_2: NEU_2}
        qdrant_umschreiben(client, COLLECTION, zuordnung, ausfuehren=True)

        assert qdrant_umschreiben(client, COLLECTION, zuordnung, ausfuehren=True) == 0

    def test_eintrag_ohne_objekt_in_einer_liste_bleibt_stehen(self, client):
        client.set_payload(
            COLLECTION, {"authors": ["Altbestand", {"name": ALT}]}, points=[1]
        )

        qdrant_umschreiben(client, COLLECTION, {ALT: NEU}, ausfuehren=True)

        assert _gelesen(client, 1)["authors"] == ["Altbestand", {"name": NEU}]

    def test_feld_mit_objekt_statt_kennung_bricht_nicht_ab(self, client):
        """Ein Objekt oder eine Liste laesst sich nicht nachschlagen (unhashable)."""
        client.set_payload(
            COLLECTION,
            {"last_modified_by": {"name": ALT}, "edit_history": [{"editor": [ALT]}]},
            points=[1],
        )

        assert qdrant_umschreiben(client, COLLECTION, {ALT: NEU}, ausfuehren=True) == 1

        payload = _gelesen(client, 1)
        assert payload["original_author"] == NEU
        assert payload["last_modified_by"] == {"name": ALT}

    def test_leere_zuordnung_aendert_nichts(self, client):
        assert qdrant_umschreiben(client, COLLECTION, {}, ausfuehren=True) == 0


class TestListeUmschreiben:
    def test_ersetzt_zugeordnete_und_behaelt_den_rest_in_der_reihenfolge(self):
        assert liste_umschreiben([BETA, ALT, ALT_2], {ALT: NEU}) == [BETA, NEU, ALT_2]


class TestZuordnungPruefen:
    @pytest.mark.parametrize(
        "zuordnung",
        [
            {ALT: ALT},
            {"": NEU},
            {ALT: ""},
            {ALT: " neu"},
            {"anonymous": NEU},
            {ALT: EHEMALIGE_PERSON_KENNUNG},
            {EHEMALIGE_PERSON_KENNUNG: NEU},
            {ALT: "ehemalige-person-1234"},
            # Eine neue Kennung, die selbst umgestellt wird, macht den Lauf von
            # der Reihenfolge abhaengig.
            {ALT: NEU, NEU: NEU_2},
            # Zwei alte auf dieselbe neue: zwei Konten fielen zusammen.
            {ALT: NEU, ALT_2: NEU},
        ],
    )
    def test_weist_zuordnungen_ab_die_niemanden_oder_falsch_bezeichnen(self, zuordnung):
        with pytest.raises(ValueError):
            zuordnung_pruefen(zuordnung)

    def test_laesst_eine_saubere_zuordnung_durch(self):
        zuordnung_pruefen({ALT: NEU, ALT_2: NEU_2})
