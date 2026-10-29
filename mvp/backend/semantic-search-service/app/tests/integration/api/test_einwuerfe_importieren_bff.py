"""
Das Importskript (#341) gegen den laufenden Dev-Stack: angemeldet am echten BFF,
ueber dieselben Endpunkte wie das Einwurf-Formular.

Braucht BFF, semantic-search und PostgreSQL des Dev-Stacks (``mvp/run-local.sh up``)
und das Testkonto aus ``mvp/config/managed-users.example.json``. Liegt deshalb unter
``api/``, das die GitHub-CI auslaesst. Ohne BFF ueberspringt sich das Modul; im
Pflichtmodus (``scripts/check.sh --integration``) scheitert es stattdessen,
ausser in der CI, die kein BFF startet (``stack.bff_pflicht``). Die
Links sind je Lauf neu, damit wiederholte Laeufe im selben Stack nicht aneinander
haengen bleiben.
"""

import importlib.util
import os
import uuid
from pathlib import Path

import pytest
import requests

from tests.integration import stack

BFF_URL = os.environ.get("GUTGESAGT_BFF_URL", "http://localhost:5054")
EMAIL = "test.user@example.com"
PASSWORT = "Liebe>Hass!"

REPO_WURZEL = next(p for p in Path(__file__).parents if (p / "mvp").is_dir())
SKRIPT = REPO_WURZEL / "mvp" / "scripts" / "manual" / "einwuerfe_importieren.py"


def _bff_erreichbar() -> bool:
    try:
        return requests.get(f"{BFF_URL}/api/auth/modes", timeout=2).status_code == 200
    except requests.RequestException:
        return False


BFF_FEHLT = f"BFF nicht erreichbar unter {BFF_URL} (mvp/run-local.sh up)"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not stack.bff_pflicht() and not _bff_erreichbar(), reason=BFF_FEHLT
    ),
]


@pytest.fixture(scope="module", autouse=True)
def bff():
    """Im Pflichtmodus ist ein fehlendes BFF ein Fehler, kein Skip (``stack.bff_pflicht``)."""
    if not _bff_erreichbar():
        pytest.fail(BFF_FEHLT)


@pytest.fixture(scope="module")
def skript():
    spec = importlib.util.spec_from_file_location("einwuerfe_importieren", SKRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@pytest.fixture
def aufrufen(skript, monkeypatch):
    monkeypatch.setenv("GUTGESAGT_PASSWORT", PASSWORT)

    def aufruf(liste, *optionen):
        return skript.main(
            [str(liste), "--email", EMAIL, "--adresse", BFF_URL, *optionen]
        )

    return aufruf


@pytest.fixture(scope="module")
def sitzung():
    """Eine eigene Anmeldung zum Nachsehen, unabhaengig vom Client des Skripts."""
    s = requests.Session()
    antwort = s.post(
        f"{BFF_URL}/api/auth/login/managed",
        json={"email": EMAIL, "password": PASSWORT},
        timeout=10,
    )
    assert antwort.status_code == 200
    return s


def _gleiche(sitzung, link):
    antwort = sitzung.post(
        f"{BFF_URL}/api/v1/rawinput/gleicherLink", json={"url": link}, timeout=10
    )
    assert antwort.status_code == 200
    return antwort.json()["results"]


@pytest.fixture
def links():
    lauf = uuid.uuid4().hex
    return (
        f"https://example.org/import-{lauf}/a",
        f"https://example.org/import-{lauf}/b",
    )


def test_trockenlauf_legt_nichts_an(aufrufen, sitzung, links, tmp_path, capsys):
    liste = tmp_path / "liste.csv"
    liste.write_text(f"link,hinweis\n{links[0]},Zitat\n{links[1]},\n")

    assert aufrufen(liste, "--trockenlauf") == 0

    assert _gleiche(sitzung, links[0]) == [] and _gleiche(sitzung, links[1]) == []
    assert "wuerden eingeworfen: 2" in capsys.readouterr().out


def test_einwerfen_dann_gleicher_link_uebersprungen(
    aufrufen, sitzung, links, tmp_path, capsys
):
    liste = tmp_path / "liste.md"
    liste.write_text(f"- {links[0]} – Zitat auf Seite 3\n- {links[1]}?fbclid=x\n")

    assert aufrufen(liste) == 0

    (a,) = _gleiche(sitzung, links[0])
    assert (a["url"], a["content"], a["status"]) == (
        links[0],
        "Zitat auf Seite 3",
        "open",
    )
    assert a["submitted_by"] == "user-001"
    assert a["source_channel"] == "import"
    # Tracking-Parameter entfernt der Server wie das Formular.
    (b,) = _gleiche(sitzung, links[1])
    assert b["url"] == links[1]
    capsys.readouterr()

    # Gleicher Link nach Bereinigung, nicht wortgleich: das entscheidet der Server.
    nochmal = tmp_path / "nochmal.csv"
    nochmal.write_text(
        f"link\n{links[0].replace('https://', 'http://www.')}/\n"
        f"{links[1]}?utm_source=liste\n"
    )

    assert aufrufen(nochmal) == 0

    assert len(_gleiche(sitzung, links[0])) == 1
    assert len(_gleiche(sitzung, links[1])) == 1
    assert "uebersprungen: 2" in capsys.readouterr().out
