"""
Keycloak speichert bei der Zustimmung zu den Nutzungsbedingungen nur einen
Zeitstempel (#429). Welchem Text jemand zugestimmt hat, ergibt sich erst über das
Verzeichnis der Stände (#466), seit #500 ein Ordner je Stand. Trägt die Seite einen
Stand, der dort fehlt, ist eine Zustimmung nicht mehr zuzuordnen.
"""

import pathlib
import re

import pytest

import rechtstexte_uebersicht as uebersicht

WURZEL = pathlib.Path(__file__).resolve().parents[2]
SEITE = (
    WURZEL
    / "mvp/frontend/gutgesagt-frontend/src/app/nutzungsbedingungen"
    / "nutzungsbedingungen.component.html"
)
TAG = r"\d{1,2}\. [A-ZÄÖÜ][a-zäöü]+ \d{4}"


def _stand_der_seite() -> str:
    treffer = re.search(r"<strong>Stand:</strong> ([^<]+)</p>", SEITE.read_text())
    assert treffer, "keine Stand-Zeile in den Nutzungsbedingungen"
    return treffer.group(1).strip()


def test_der_stand_der_seite_ist_ein_tag():
    assert re.fullmatch(TAG, _stand_der_seite())


def test_der_stand_der_seite_steht_im_verzeichnis():
    stand = _stand_der_seite()
    ordner = uebersicht.STAENDE / uebersicht.stand_als_ordner(stand)

    assert uebersicht.stand(ordner)[0] == stand


@pytest.mark.parametrize(
    "ordner", uebersicht.staende_ordner(uebersicht.STAENDE), ids=lambda o: o.name
)
def test_jeder_ordner_ist_nach_seinem_stand_benannt_und_nennt_aenderungen(ordner):
    """Der Ordnername ist das Datum: Damit steht jeder Stand nur einmal im Verzeichnis."""
    name, _, aenderungen = uebersicht.stand(ordner)

    assert uebersicht.stand_als_ordner(name) == ordner.name
    assert aenderungen
