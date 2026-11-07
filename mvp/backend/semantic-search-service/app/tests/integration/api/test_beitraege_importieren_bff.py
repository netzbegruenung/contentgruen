"""
Das Skript beitraege_importieren.py (#592) gegen den laufenden Dev-Stack.

Import: angemeldet am echten BFF als Testkonto, ueber denselben Endpunkt wie das
Kommentar-Formular. Entfernen: der Admin-Endpunkt direkt am Suchdienst mit den
Kopfzeilen, die sonst das BFF setzt, weil das Admin-Konto des Dev-Stacks kein
bekanntes Passwort hat; das Skript selbst laeuft dabei unveraendert, nur die
Adresse und die Kopfzeilen kommen aus dem Test.

Braucht BFF, semantic-search und PostgreSQL des Dev-Stacks (``mvp/run-local.sh up``).
Liegt deshalb unter ``api/``, das die GitHub-CI auslaesst; ohne BFF ueberspringt
sich das Modul, im Pflichtmodus scheitert es (``stack.pflicht_ausser_in_ci``).
Titel und Texte sind je Lauf neu, damit die Dublettenpruefung wiederholte Laeufe
nicht abweist.
"""

import importlib.util
import os
import uuid
from pathlib import Path

import pytest
import requests

from tests.integration import stack

BFF_URL = os.environ.get("GUTGESAGT_BFF_URL", "http://localhost:5054")
SUCHDIENST_URL = os.environ.get("GUTGESAGT_SUCHDIENST_URL", "http://localhost:8000")
EMAIL = "test.user@example.com"
PASSWORT = "Liebe>Hass!"

REPO_WURZEL = next(p for p in Path(__file__).parents if (p / "mvp").is_dir())
SKRIPT = REPO_WURZEL / "mvp" / "scripts" / "manual" / "beitraege_importieren.py"


def _erreichbar(url: str) -> bool:
    try:
        return requests.get(url, timeout=2).status_code < 500
    except requests.RequestException:
        return False


def _bff_erreichbar() -> bool:
    return _erreichbar(f"{BFF_URL}/api/auth/modes")


BFF_FEHLT = f"BFF nicht erreichbar unter {BFF_URL} (mvp/run-local.sh up)"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not stack.pflicht_ausser_in_ci() and not _bff_erreichbar(), reason=BFF_FEHLT
    ),
]


@pytest.fixture(scope="module", autouse=True)
def bff():
    """Im Pflichtmodus ist ein fehlendes BFF ein Fehler, kein Skip."""
    if not _bff_erreichbar():
        pytest.fail(BFF_FEHLT)


@pytest.fixture(scope="module")
def skript():
    spec = importlib.util.spec_from_file_location("beitraege_importieren", SKRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


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


@pytest.fixture(scope="module", autouse=True)
def eingewilligt(sitzung):
    """Anlegen verlangt die Art.-9-Einwilligung (#489); ein zweites Mal aendert nichts."""
    basis = f"{BFF_URL}/api/v1/art9-einwilligung"
    stand = sitzung.get(basis, timeout=10)
    if stand.status_code == 404:
        return
    assert stand.status_code == 200
    kennung = stand.json()["aktueller_wortlaut"]["kennung"]
    assert (
        sitzung.post(basis, json={"wortlaut": kennung}, timeout=10).status_code == 204
    )


@pytest.fixture
def lauf():
    return uuid.uuid4().hex[:12]


ALS_ADMIN = {"X-User": "user-002", "X-Is-Admin": "true"}


@pytest.fixture
def aufraeumen():
    """
    Was der Test anlegt, entfernt er am Ende auch, wenn er vorher scheitert: Die
    Texte unterscheiden sich je Lauf nur in der Laufkennung, und die
    Dublettenpruefung hielte uebrig gebliebene fuer dieselben.
    """
    ids = []
    yield ids
    for kennung in ids:
        try:
            requests.delete(
                f"{SUCHDIENST_URL}/api/v1/moderation/content/commentary/{kennung}",
                headers=ALS_ADMIN,
                timeout=10,
            )
        except requests.RequestException:
            pass


def _bestand(lauf: str) -> str:
    # Zwei sehr verschiedene Kommentare, damit die Dublettenpruefung sie trennt.
    return f"""\
# 1. Testblock

## 1.1 „Import-Test {lauf}: Windräder töten die Vögel!“

### (a) Kommentarspalte

**Titel:** Glasscheiben gefährden Vögel weit mehr, Lauf {lauf}

**Kurz:** Kurzfassung {lauf} über Glasscheiben.

**Mittel:** Mittelfassung {lauf}: An Glasscheiben sterben viel mehr Vögel als an Windrädern.

**Herkunft:** https://example.org/import-{lauf}/voegel – Übersicht {lauf}.
geprüft: ja

### (b) Sachlich

**Titel:** Der Standort entscheidet über den Artenschutz, Lauf {lauf}

**Mittel:** Mittelfassung {lauf}: Abstände zu Brutplätzen und Abschaltzeiten schützen seltene Greifvögel.

**Lang:** Langfassung {lauf}.
Zweite Zeile.
"""


def _kommentar(sitzung, kommentar_id):
    return sitzung.get(
        f"{BFF_URL}/api/v1/commentary/getById",
        params={"commentary_id": kommentar_id},
        timeout=10,
    )


def _ids(ausgabe: str):
    """(Kommentar, Aussage) aus den Zeilen "angelegt als <id> an Aussage <id>: …"."""
    return [
        tuple(zeile.split("angelegt als ", 1)[1].split(":", 1)[0].split(" an Aussage "))
        for zeile in ausgabe.splitlines()
        if "angelegt als " in zeile
    ]


def test_import_dann_dubletten_dann_entfernen(
    skript, sitzung, lauf, aufraeumen, tmp_path, capsys, monkeypatch
):
    monkeypatch.setenv("GUTGESAGT_PASSWORT", PASSWORT)
    datei = tmp_path / "bestand.md"
    datei.write_text(_bestand(lauf), encoding="utf-8")
    aufruf = [str(datei), "--email", EMAIL, "--adresse", BFF_URL]

    # Trockenlauf: nichts angelegt.
    assert skript.main([str(datei)]) == 0
    assert "Trockenlauf, wuerden angelegt: 2" in capsys.readouterr().out

    # Anlegen: zwei Kommentare an derselben Aussage, mit Fassungen und Herkunft.
    assert skript.main([*aufruf, "--ausfuehren"]) == 0
    ausgabe = capsys.readouterr().out
    assert "angelegt: 2, uebersprungen: 0, Fehler: 0" in ausgabe
    (a_id, aussage_id), (b_id, aussage_b) = _ids(ausgabe)
    aufraeumen.extend([a_id, b_id])
    assert aussage_id == aussage_b
    a, b = _kommentar(sitzung, a_id).json(), _kommentar(sitzung, b_id).json()
    assert a["title"] == f"Glasscheiben gefährden Vögel weit mehr, Lauf {lauf}"
    assert a["text"].startswith(f"Mittelfassung {lauf}: An Glasscheiben")
    assert a["short_text"] == f"Kurzfassung {lauf} über Glasscheiben."
    assert b["long_text"] == f"Langfassung {lauf}.\nZweite Zeile."
    # Die Herkunft mit Beschreibung, ohne den Pruefvermerk darunter.
    assert f"Übersicht {lauf}." in str(a["references"])

    # Nochmal: der Server erkennt beide als Dublette, nichts wird angelegt.
    assert skript.main([*aufruf, "--ausfuehren"]) == 0
    ausgabe = capsys.readouterr().out
    assert "angelegt: 0, uebersprungen: 2, Fehler: 0" in ausgabe
    assert "aehnlicher Kommentar schon da" in ausgabe

    # Entfernen ohne Admin: Abbruch, nichts entfernt.
    liste = tmp_path / "entfernen.txt"
    liste.write_text(f"commentary {a_id}\ncommentary {b_id}\n", encoding="utf-8")
    assert skript.main([str(liste), "--entfernen", *aufruf[1:], "--ausfuehren"]) == 2
    assert "Admin-Konto" in capsys.readouterr().err
    assert _kommentar(sitzung, a_id).status_code == 200

    # Trockenlauf des Entfernens: je Eintrag eine Zeile, nichts entfernt. Die
    # Titel liest er aus /content/beitrag (#300); die Formatierung pruefen die
    # Unit-Tests, weil ein Dev-Stack von vor #300 die Adresse nicht kennt.
    assert skript.main([str(liste), "--entfernen", *aufruf[1:]]) == 0
    ausgabe = capsys.readouterr().out
    assert a_id in ausgabe and b_id in ausgabe
    assert _kommentar(sitzung, b_id).status_code == 200

    # Entfernen als Admin, am Suchdienst mit den Kopfzeilen des BFF.
    if not _erreichbar(f"{SUCHDIENST_URL}/docs"):
        pytest.skip(f"Suchdienst nicht direkt erreichbar unter {SUCHDIENST_URL}")

    class AlsAdmin(skript.BffBestand):
        def _kopfzeilen(self):
            return {**super()._kopfzeilen(), **ALS_ADMIN}

        def anmelden(self, email, passwort):
            pass

    assert (
        skript.main(
            [
                str(liste),
                "--entfernen",
                "--email",
                "admin",
                "--adresse",
                SUCHDIENST_URL,
                "--ausfuehren",
            ],
            AlsAdmin,
        )
        == 0
    )
    assert "entfernt: 2" in capsys.readouterr().out
    # Weg: getById antwortet fuer einen fehlenden Kommentar heute mit 500 statt
    # 404 (die 404 faengt dort das allgemeine except), deshalb nur "nicht 200".
    assert _kommentar(sitzung, a_id).status_code != 200
    assert _kommentar(sitzung, b_id).status_code != 200
    # Die Aussage bleibt, nur ohne diese Antworten.
    bleibt = sitzung.get(
        f"{BFF_URL}/api/v1/statement/getById",
        params={"statement_id": aussage_id},
        timeout=10,
    )
    assert bleibt.status_code == 200

    # Ein zweites Mal: nichts mehr da.
    assert (
        skript.main(
            [
                str(liste),
                "--entfernen",
                "--email",
                "admin",
                "--adresse",
                SUCHDIENST_URL,
                "--ausfuehren",
            ],
            AlsAdmin,
        )
        == 0
    )
    assert "uebersprungen: 2" in capsys.readouterr().out
