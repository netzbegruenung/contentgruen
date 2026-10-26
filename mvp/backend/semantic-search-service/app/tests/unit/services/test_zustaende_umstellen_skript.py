"""
Der Wrapper mvp/scripts/manual/zustaende_umstellen.py: Argumente, Umgebung und
Ausgabe. Die Logik selbst testet test_zustaende_umstellen.py; hier steht statt des
Servers ein Qdrant im Speicher-Modus.
"""

import importlib.util
from pathlib import Path

import pytest
from qdrant_client import QdrantClient

from tests.unit.services.test_zustaende_umstellen import COLLECTION, punkte_anlegen

pytestmark = pytest.mark.unit

REPO_WURZEL = next(p for p in Path(__file__).parents if (p / "mvp").is_dir())
SKRIPT = REPO_WURZEL / "mvp" / "scripts" / "manual" / "zustaende_umstellen.py"


@pytest.fixture
def qdrant():
    client = QdrantClient(":memory:")
    punkte_anlegen(client)
    return client


@pytest.fixture
def skript(monkeypatch, qdrant):
    spec = importlib.util.spec_from_file_location("zustaende_umstellen_skript", SKRIPT)
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
        monkeypatch.setattr("sys.argv", ["zustaende_umstellen.py", *argumente])
        return modul.main()

    aufrufen.client_aufrufe = aufrufe
    return aufrufen


def _status(qdrant, punkt_id):
    return qdrant.retrieve(COLLECTION, [punkt_id], with_payload=True)[0].payload[
        "status"
    ]


class TestSkript:
    def test_skript_ohne_ausfuehren_nur_zaehlen(self, skript, qdrant, capsys):
        skript()

        ausgabe = capsys.readouterr().out
        assert ausgabe.splitlines()[-1] == "umzustellen: 14"
        assert "status released_internal: 1" in ausgabe
        assert _status(qdrant, 1) == "released_internal"

    def test_skript_mit_ausfuehren_schreiben(self, skript, qdrant, capsys):
        skript("--ausfuehren")

        assert capsys.readouterr().out.splitlines()[-1] == "umgestellt: 14"
        assert _status(qdrant, 1) == "visible"

    def test_skript_meldet_unbekannte_status_mit_exit_1(self, skript, capsys):
        assert skript() == 1

        assert (
            "UNBEKANNT, bleibt stehen: voellig_unbekannt: 1" in capsys.readouterr().out
        )

    def test_skript_url_aus_der_umgebung_des_containers(self, skript):
        skript()

        assert skript.client_aufrufe[0]["url"] == "http://qdrant:6333"
