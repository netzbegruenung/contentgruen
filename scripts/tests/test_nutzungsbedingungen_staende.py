"""
Keycloak speichert bei der Zustimmung zu den Nutzungsbedingungen nur einen
Zeitstempel (#429). Welchem Text jemand zugestimmt hat, ergibt sich erst über das
Verzeichnis der Stände (#466). Trägt die Seite einen Stand, der dort fehlt, ist eine
Zustimmung nicht mehr zuzuordnen.
"""

import pathlib
import re

WURZEL = pathlib.Path(__file__).resolve().parents[2]
SEITE = (
    WURZEL
    / "mvp/frontend/gutgesagt-frontend/src/app/nutzungsbedingungen"
    / "nutzungsbedingungen.component.html"
)
VERZEICHNIS = WURZEL / "docs/NUTZUNGSBEDINGUNGEN_STAENDE.md"

TAG = r"\d{1,2}\. [A-ZÄÖÜ][a-zäöü]+ \d{4}"


def _stand_der_seite() -> str:
    treffer = re.search(r"<strong>Stand:</strong> ([^<]+)</p>", SEITE.read_text())
    assert treffer, "keine Stand-Zeile in den Nutzungsbedingungen"
    return treffer.group(1).strip()


def _staende_im_verzeichnis() -> list[str]:
    """Erste Spalte aller Tabellenzeilen ohne Kopfzeilen: aktuelle und alte Stände."""
    erste_spalten = re.findall(r"^\| ([^|]+?) \|", VERZEICHNIS.read_text(), re.M)
    return [s for s in erste_spalten if not s.startswith("Stand")]


def test_der_stand_der_seite_ist_ein_tag():
    assert re.fullmatch(TAG, _stand_der_seite())


def test_der_stand_der_seite_steht_im_verzeichnis():
    assert _stand_der_seite() in _staende_im_verzeichnis()


def test_jeder_stand_steht_nur_einmal_im_verzeichnis():
    staende = _staende_im_verzeichnis()
    assert len(staende) == len(set(staende))
