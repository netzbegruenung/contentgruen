"""
Beitraege einer geloeschten Person anonymisieren (Loeschkonzept Schritt 3) und die
einmalige Umstellung des alten Platzhalters ``geloeschter-nutzer``.

Laeuft gegen qdrant_client im Speicher-Modus. Der wertet Filter wie
``authors[].name`` selbst aus, nicht der Server; dieselben Faelle gegen einen echten
Qdrant: tests/integration/test_beitraege_anonymisieren_qdrant.py.
"""

import uuid

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from services.anzeigename_service import EHEMALIGE_PERSON_KENNUNG
from services.wartung.beitraege_anonymisieren import (
    ALTER_PLATZHALTER,
    anonymisieren,
)

# Am Modul, nicht an der Klasse: Die Integrationstests erben die Klasse und sind
# keine Unit-Tests.
pytestmark = pytest.mark.unit

# Eigener Name je Lauf: Auf dem Server laufen parallel andere Tests und Dev-Daten.
COLLECTION = f"test_anonymisieren_{uuid.uuid4().hex[:8]}"
PERSON = "person-die-loescht"
ANDERE = "andere-person"


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
    punkte_anlegen(client)
    return client


def punkte_anlegen(client):
    client.create_collection(
        COLLECTION, vectors_config=VectorParams(size=2, distance=Distance.COSINE)
    )
    punkte = {
        1: _payload(PERSON, authors=[PERSON], editors=[PERSON]),
        # Fremder Beitrag, an dem die Person mitgeschrieben und editiert hat.
        2: _payload(ANDERE, PERSON, authors=[ANDERE, PERSON], editors=[ANDERE, PERSON]),
        3: _payload(ANDERE, authors=[ANDERE], editors=[ANDERE]),
    }
    client.upsert(
        COLLECTION,
        [PointStruct(id=i, vector=[1.0, 0.0], payload=p) for i, p in punkte.items()],
    )


def _gelesen(client, punkt_id):
    return client.retrieve(COLLECTION, [punkt_id], with_payload=True)[0].payload


def _kennungen(payload):
    return {
        payload["original_author"],
        payload["last_modified_by"],
        *(a["name"] for a in payload["authors"]),
        *(e["editor"] for e in payload["edit_history"]),
    }


class TestAnonymisieren:
    def test_alle_vier_felder_bekommen_den_platzhalter(self, client):
        anonymisieren(client, COLLECTION, PERSON, ausfuehren=True)

        assert _kennungen(_gelesen(client, 1)) == {EHEMALIGE_PERSON_KENNUNG}

    def test_fremde_kennungen_am_selben_beitrag_bleiben(self, client):
        anonymisieren(client, COLLECTION, PERSON, ausfuehren=True)

        payload = _gelesen(client, 2)
        assert payload["original_author"] == ANDERE
        assert payload["last_modified_by"] == EHEMALIGE_PERSON_KENNUNG
        assert [a["name"] for a in payload["authors"]] == [
            ANDERE,
            EHEMALIGE_PERSON_KENNUNG,
        ]
        assert [e["editor"] for e in payload["edit_history"]] == [
            ANDERE,
            EHEMALIGE_PERSON_KENNUNG,
        ]
        # Was neben der Kennung im Eintrag steht, bleibt.
        assert payload["authors"][1]["role"] == "author"
        assert payload["text"] == "Waermepumpen lohnen sich auch im Altbau"

    def test_unbeteiligte_beitraege_bleiben_unberuehrt(self, client):
        vorher = _gelesen(client, 3)

        bericht = anonymisieren(client, COLLECTION, PERSON, ausfuehren=True)

        assert _gelesen(client, 3) == vorher
        assert sorted(p.id for p in bericht.treffer) == [1, 2]

    def test_ohne_ausfuehren_wird_nur_gezeigt(self, client):
        bericht = anonymisieren(client, COLLECTION, PERSON)

        assert len(bericht.treffer) == 2
        assert not bericht.ausgefuehrt
        assert PERSON in _kennungen(_gelesen(client, 1))

    def test_zweiter_lauf_findet_nichts(self, client):
        anonymisieren(client, COLLECTION, PERSON, ausfuehren=True)

        assert anonymisieren(client, COLLECTION, PERSON, ausfuehren=True).treffer == []

    def test_bericht_nennt_typ_und_text_fuer_die_einzelfallpruefung(self, client):
        bericht = anonymisieren(client, COLLECTION, PERSON)

        punkt = next(p for p in bericht.treffer if p.id == 1)
        assert punkt.content_type == "commentary"
        assert punkt.text == "Waermepumpen lohnen sich auch im Altbau"

    def test_alter_platzhalter_wird_umgestellt(self, client):
        anonymisieren(client, COLLECTION, PERSON, ausfuehren=True)
        # Bestand vor #236: der alte Platzhalter statt des neuen.
        client.set_payload(
            COLLECTION,
            _payload(ALTER_PLATZHALTER, authors=[ALTER_PLATZHALTER]),
            points=[3],
        )

        anonymisieren(client, COLLECTION, ALTER_PLATZHALTER, ausfuehren=True)

        assert _kennungen(_gelesen(client, 3)) == {EHEMALIGE_PERSON_KENNUNG}
        assert _kennungen(_gelesen(client, 1)) == {EHEMALIGE_PERSON_KENNUNG}

    @pytest.mark.parametrize(
        "kennung",
        ["", " ", " person-die-loescht", EHEMALIGE_PERSON_KENNUNG, "anonymous"],
    )
    def test_keine_kennung_die_niemanden_bezeichnet(self, client, kennung):
        with pytest.raises(ValueError):
            anonymisieren(client, COLLECTION, kennung, ausfuehren=True)
