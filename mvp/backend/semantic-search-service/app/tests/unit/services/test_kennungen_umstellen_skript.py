"""
Der Wrapper mvp/scripts/manual/kennungen_umstellen.py: Argumente, Umgebung und
Ausgabe. Die Logik testen test_kennungen_umstellen.py (Qdrant) und
tests/integration/test_kennungen_umstellen_postgres.py; hier ist umstellen() eine
Attrappe, die festhaelt, womit es aufgerufen wird.
"""

import importlib.util
from pathlib import Path

import pytest

from services.wartung.kennungen_umstellen import PostgresBericht, Umstellung

pytestmark = pytest.mark.unit

REPO_WURZEL = next(p for p in Path(__file__).parents if (p / "mvp").is_dir())
SKRIPT = REPO_WURZEL / "mvp" / "scripts" / "manual" / "kennungen_umstellen.py"


@pytest.fixture
def skript(monkeypatch):
    spec = importlib.util.spec_from_file_location("kennungen_umstellen_skript", SKRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    aufrufe = []

    def umstellen(verbindung, qdrant, collection, realm, idp, **kwargs):
        aufrufe.append(dict(collection=collection, idp=idp, realm=realm, **kwargs))
        return Umstellung(
            ausgefuehrt=kwargs["ausfuehren"],
            zuordnung={"alt": "neu"},
            postgres=PostgresBericht(geaendert={"votes.user_id": 3}),
            qdrant={collection: 2},
            listen={
                n: ["neu" if w == "alt" else w for w in v]
                for n, v in kwargs["listen"].items()
            },
            loeschliste=[*kwargs["loeschliste"], "neu-geloescht"],
            ohne_konto=["user-001"],
        )

    monkeypatch.setattr(modul, "umstellen", umstellen)
    monkeypatch.setattr(modul, "QdrantClient", lambda **kwargs: "qdrant")
    monkeypatch.setenv("SEMANTIC_SEARCH_APP_DATABASE_URL", "sqlite://")
    monkeypatch.setenv("SEMANTIC_SEARCH_QDRANT_COLLECTION", "beitraege")
    monkeypatch.setenv("SEMANTIC_SEARCH_KEYCLOAK_URL", "https://login.example.org")
    monkeypatch.setenv(
        "SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_ID", "gutgesagt-einladungen"
    )
    monkeypatch.setenv("SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_SECRET", "geheim")
    monkeypatch.setenv("SEMANTIC_SEARCH_ADMIN_USERS", "alt, user-001")

    def aufrufen(*argumente):
        monkeypatch.setattr("sys.argv", ["kennungen_umstellen.py", *argumente])
        return modul.main()

    aufrufen.aufrufe = aufrufe
    return aufrufen


class TestSkript:
    def test_ohne_ausfuehren_trockenlauf_mit_zahlen(self, skript, capsys):
        assert skript() == 0

        ausgabe = capsys.readouterr().out
        assert skript.aufrufe[0]["ausfuehren"] is False
        assert skript.aufrufe[0]["idp"] == "netzbegruenung"
        assert skript.aufrufe[0]["collection"] == "beitraege"
        assert "Trockenlauf: nichts geaendert" in ausgabe
        assert "  votes.user_id: 3" in ausgabe
        assert "  beitraege: 2" in ausgabe
        assert "Ohne Konto im Realm, bleiben: 1" in ausgabe
        # Kennungen nur auf Wunsch einzeln
        assert "  user-001\n" not in ausgabe

    def test_mit_ausfuehren_schreiben(self, skript, capsys):
        skript("--ausfuehren")

        assert skript.aufrufe[0]["ausfuehren"] is True
        assert "Lauf: geschrieben" in capsys.readouterr().out

    def test_admins_aus_der_umgebung_und_weitere_listen(self, skript, capsys):
        skript("--liste", "ADMIN_USER_IDS=alt,andere")

        assert skript.aufrufe[0]["listen"] == {
            "SEMANTIC_SEARCH_ADMIN_USERS": ["alt", "user-001"],
            "ADMIN_USER_IDS": ["alt", "andere"],
        }
        ausgabe = capsys.readouterr().out
        assert "  SEMANTIC_SEARCH_ADMIN_USERS=neu,user-001" in ausgabe
        assert "  ADMIN_USER_IDS=neu,andere" in ausgabe

    def test_loeschliste_wird_ergaenzt_ausgegeben(self, skript, capsys):
        skript("--loeschliste", "alt-geloescht")

        assert skript.aufrufe[0]["loeschliste"] == ["alt-geloescht"]
        ausgabe = capsys.readouterr().out
        assert "  alt-geloescht\n  neu-geloescht\n" in ausgabe

    def test_konten_aus_datei(self, skript, tmp_path):
        datei = tmp_path / "konten.csv"
        datei.write_text("# alte Kennung, Adresse\nalt, anna@example.org\n\n")

        skript("--konten-anlegen", str(datei))

        assert skript.aufrufe[0]["anzulegen"] == {"alt": "anna@example.org"}

    def test_ohne_keycloak_bricht_ab_ohne_zu_schreiben(
        self, skript, monkeypatch, capsys
    ):
        monkeypatch.delenv("SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_SECRET")

        assert skript("--ausfuehren") == 2
        assert skript.aufrufe == []
        assert "SEMANTIC_SEARCH_KEYCLOAK_ADMIN_CLIENT_SECRET" in capsys.readouterr().err
