"""
Bei der Pflichtaktion "Terms and Conditions" zeigt Keycloak den Text termsText aus der
Realm-Vorlage (#429). Er muss auf die Seite /nutzungsbedingungen verlinken und deren
Stand nennen: Keycloak speichert bei der Zustimmung nur den Zeitpunkt, welchem Text
jemand zugestimmt hat, sagt nur das Stand-Datum (NB §10).
"""

import json
import pathlib
import re

WURZEL = pathlib.Path(__file__).resolve().parents[2]
VORLAGE = WURZEL / "docs/keycloak/gutgesagt-realm.json"
SEITE = (
    WURZEL
    / "mvp/frontend/gutgesagt-frontend/src/app/nutzungsbedingungen"
    / "nutzungsbedingungen.component.html"
)


def _terms_text() -> str:
    return json.loads(VORLAGE.read_text())["localizationTexts"]["de"]["termsText"]


def _stand_der_seite() -> str:
    treffer = re.search(r"<strong>Stand:</strong>\s*([^<]+?)\s*</p>", SEITE.read_text())
    assert treffer, "keine Stand-Zeile auf der Seite gefunden"
    return treffer.group(1)


def test_terms_text_verlinkt_die_nutzungsbedingungen():
    assert re.search(r'href="https://[^"]+/nutzungsbedingungen"', _terms_text())


def test_terms_text_nennt_den_stand_der_seite():
    assert f"Stand: {_stand_der_seite()}" in _terms_text()
