"""
Den unbenannten Vektor einer Collection von vor #395 als benannten Vektor fuehren.

Laeuft gegen qdrant_client im Speicher-Modus; dieselben Faelle gegen einen echten
Qdrant (Payload-Indizes, Aliase des Servers):
tests/integration/test_vektor_benennen_qdrant.py.
"""

import importlib.util
import uuid
from pathlib import Path

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import (
    DeleteAlias,
    DeleteAliasOperation,
    Distance,
    PointStruct,
    VectorParams,
)

from core.config import EMBEDDING_VEKTOR
from services.wartung.vektor_benennen import benennen, ziel_collection

# Am Modul, nicht an der Klasse: Die Integrationstests erben die Klasse.
pytestmark = pytest.mark.unit

# Eigener Name je Lauf: Auf dem Server laufen parallel andere Tests und Dev-Daten.
COLLECTION = f"test_benennen_{uuid.uuid4().hex[:8]}"

REPO_WURZEL = next(p for p in Path(__file__).parents if (p / "mvp").is_dir())
SKRIPT = REPO_WURZEL / "mvp" / "scripts" / "manual" / "vektor_benennen.py"

PUNKTE = {
    1: ([1.0, 0.0], {"content_type": "statement", "text": "Tempolimit rettet Leben"}),
    2: ([0.6, 0.8], {"content_type": "commentary", "text": "Weniger Unfaelle"}),
    3: ([0.0, 1.0], {"content_type": "commentary", "text": "Waermepumpen"}),
}


def punkte_anlegen(client):
    """Collection wie vor #395: ein unbenannter Vektor, Kosinus."""
    client.create_collection(
        COLLECTION, vectors_config=VectorParams(size=2, distance=Distance.COSINE)
    )
    client.create_payload_index(COLLECTION, "content_type", field_schema="keyword")
    client.upsert(
        COLLECTION,
        [PointStruct(id=i, vector=v, payload=p) for i, (v, p) in PUNKTE.items()],
        wait=True,
    )


def abraeumen(client):
    for name in (COLLECTION, ziel_collection(COLLECTION)):
        if client.collection_exists(name):
            client.delete_collection(name)


@pytest.fixture
def client():
    client = QdrantClient(":memory:")
    punkte_anlegen(client)
    return client


def _rangfolge(client, using=None):
    """IDs und Scores einer Suche, wie die Suche des Dienstes sie bekommt."""
    antwort = client.query_points(
        COLLECTION, query=[0.8, 0.6], using=using, limit=10, with_payload=True
    )
    return [(p.id, round(p.score, 6), p.payload) for p in antwort.points]


class TestVektorBenennen:
    def test_ohne_ausfuehren_nur_gezaehlt(self, client):
        bericht = benennen(client, COLLECTION)

        assert bericht.ausgefuehrt is False
        assert bericht.vorher == "unbenannt"
        assert bericht.punkte == 3
        assert bericht.kopiert == 0
        assert not isinstance(
            client.get_collection(COLLECTION).config.params.vectors, dict
        )
        assert not client.collection_exists(ziel_collection(COLLECTION))

    def test_ausfuehren_fuehrt_vektor_unter_seinem_namen(self, client):
        bericht = benennen(client, COLLECTION, ausfuehren=True)

        assert bericht.ausgefuehrt is True
        assert bericht.kopiert == 3
        assert bericht.nachher == "benannt"
        vektoren = client.get_collection(COLLECTION).config.params.vectors
        assert set(vektoren) == {EMBEDDING_VEKTOR}
        assert vektoren[EMBEDDING_VEKTOR].size == 2
        assert vektoren[EMBEDDING_VEKTOR].distance == Distance.COSINE

    def test_name_bleibt_als_alias_auf_der_neuen_collection(self, client):
        benennen(client, COLLECTION, ausfuehren=True)

        aliase = {a.alias_name: a.collection_name for a in client.get_aliases().aliases}
        assert aliase[COLLECTION] == ziel_collection(COLLECTION)

    def test_treffer_und_reihenfolge_unveraendert(self, client):
        vorher = _rangfolge(client)

        benennen(client, COLLECTION, ausfuehren=True)

        assert _rangfolge(client, using=EMBEDDING_VEKTOR) == vorher
        assert [i for i, _, _ in vorher] == [2, 1, 3]

    def test_vektoren_unveraendert(self, client):
        benennen(client, COLLECTION, ausfuehren=True)

        punkte = client.retrieve(COLLECTION, list(PUNKTE), with_vectors=True)
        assert len(punkte) == len(PUNKTE)
        for punkt in punkte:
            assert punkt.vector[EMBEDDING_VEKTOR] == pytest.approx(PUNKTE[punkt.id][0])
            assert punkt.payload == PUNKTE[punkt.id][1]

    def test_zweiter_lauf_aendert_nichts(self, client):
        benennen(client, COLLECTION, ausfuehren=True)

        bericht = benennen(client, COLLECTION, ausfuehren=True)

        assert bericht.vorher == "benannt"
        assert bericht.kopiert == 0
        assert bericht.punkte == 3

    def test_rest_eines_abgebrochenen_laufs_wird_ersetzt(self, client):
        client.create_collection(
            ziel_collection(COLLECTION),
            vectors_config={
                EMBEDDING_VEKTOR: VectorParams(size=2, distance=Distance.COSINE)
            },
        )
        client.upsert(
            ziel_collection(COLLECTION),
            [PointStruct(id=99, vector={EMBEDDING_VEKTOR: [1.0, 0.0]}, payload={})],
            wait=True,
        )

        bericht = benennen(client, COLLECTION, ausfuehren=True)

        assert bericht.kopiert == 3
        assert client.count(COLLECTION, exact=True).count == 3

    def test_abbruch_nach_dem_loeschen_setzt_nur_den_alias(self, client):
        """Zwischen Loeschen der alten Collection und Alias abgebrochen."""
        benennen(client, COLLECTION, ausfuehren=True)
        client.update_collection_aliases(
            change_aliases_operations=[
                DeleteAliasOperation(delete_alias=DeleteAlias(alias_name=COLLECTION))
            ]
        )

        bericht = benennen(client, COLLECTION, ausfuehren=True)

        assert bericht.vorher == "kein_alias"
        assert bericht.nachher == "benannt"
        assert bericht.punkte == 3
        assert client.count(COLLECTION, exact=True).count == 3


class TestSkript:
    """Der Wrapper mvp/scripts/manual/vektor_benennen.py: Umgebung und Ausgabe."""

    @pytest.fixture
    def skript(self, monkeypatch, client):
        spec = importlib.util.spec_from_file_location("vektor_benennen_skript", SKRIPT)
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        monkeypatch.setattr(modul, "QdrantClient", lambda **_: client)
        monkeypatch.setenv("SEMANTIC_SEARCH_QDRANT_COLLECTION", COLLECTION)

        def aufrufen(*argumente):
            monkeypatch.setattr("sys.argv", ["vektor_benennen.py", *argumente])
            return modul.main()

        return aufrufen

    def test_ohne_ausfuehren_zaehlt_nur(self, skript, client, capsys):
        assert skript() == 0

        assert '"punkte": 3' in capsys.readouterr().out
        assert not client.collection_exists(ziel_collection(COLLECTION))

    def test_mit_ausfuehren_nennt_den_neustart(self, skript, capsys):
        assert skript("--ausfuehren") == 0

        ausgabe = capsys.readouterr().out
        assert '"kopiert": 3' in ausgabe
        assert "docker restart" in ausgabe
