"""
Der Wrapper mvp/scripts/manual/beitraege_anonymisieren.py: Argumente, Umgebung und
Ausgabe. Die Logik selbst testet test_beitraege_anonymisieren.py; hier steht statt
des Servers ein Qdrant im Speicher-Modus.
"""

import importlib.util
from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from services.anzeigename_service import EHEMALIGE_PERSON_KENNUNG
from tests.unit.services.test_beitraege_anonymisieren import (
    COLLECTION,
    PERSON,
    punkte_anlegen,
)

pytestmark = pytest.mark.unit

REPO_WURZEL = next(p for p in Path(__file__).parents if (p / "mvp").is_dir())
SKRIPT = REPO_WURZEL / "mvp" / "scripts" / "manual" / "beitraege_anonymisieren.py"


@pytest.fixture
def qdrant():
    client = QdrantClient(":memory:")
    punkte_anlegen(client)
    return client


@pytest.fixture
def skript(monkeypatch, qdrant):
    spec = importlib.util.spec_from_file_location(
        "beitraege_anonymisieren_skript", SKRIPT
    )
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    aufrufe = []

    def client(**kwargs):
        aufrufe.append(kwargs)
        return qdrant

    monkeypatch.setattr(modul, "QdrantClient", client)
    monkeypatch.setenv("SEMANTIC_SEARCH_QDRANT_URL", "http://qdrant:6333")
    monkeypatch.setenv("SEMANTIC_SEARCH_QDRANT_COLLECTION", COLLECTION)

    def aufrufen(*argumente):
        monkeypatch.setattr("sys.argv", ["beitraege_anonymisieren.py", *argumente])
        return modul.main()

    aufrufen.client_aufrufe = aufrufe
    return aufrufen


def _original_author(qdrant, punkt_id):
    return qdrant.retrieve(COLLECTION, [punkt_id], with_payload=True)[0].payload[
        "original_author"
    ]


class TestSkript:
    def test_ohne_ausfuehren_nur_zeigen(self, skript, qdrant, capsys):
        assert skript(PERSON) == 0

        ausgabe = capsys.readouterr().out
        assert ausgabe.splitlines()[-1] == "zu anonymisieren: 2"
        assert "commentary" in ausgabe
        assert _original_author(qdrant, 1) == PERSON

    def test_mit_ausfuehren_schreiben(self, skript, qdrant, capsys):
        assert skript(PERSON, "--ausfuehren") == 0

        assert capsys.readouterr().out.splitlines()[-1] == "anonymisiert: 2"
        assert _original_author(qdrant, 1) == EHEMALIGE_PERSON_KENNUNG

    def test_url_aus_der_umgebung_des_containers(self, skript):
        skript(PERSON)

        assert skript.client_aufrufe[0]["url"] == "http://qdrant:6333"

    def test_ohne_kennung_bricht_ab(self, skript):
        with pytest.raises(SystemExit):
            skript()
