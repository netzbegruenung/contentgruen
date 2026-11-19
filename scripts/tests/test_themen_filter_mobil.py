"""
Der Themenfilter steht mobil in einer Zeile zum Wischen (Persona-Runde 2, P24): umgebrochen
fuellten 13 Themen einen ganzen Bildschirm. Das Layout selbst prueft der Screenshot; dieser
Test haelt fest, dass die Regel fuer schmale Fenster da ist und nur den Filter trifft, nicht
die Auswahl im Formular.
"""

import pathlib
import re

WURZEL = pathlib.Path(__file__).resolve().parents[2]
THEMEN_CSS = WURZEL / "mvp/frontend/gutgesagt-frontend/src/app/shared/themen/themen.css"


def _mobil_block(text: str) -> str:
    start = text.index("@media (max-width: 599px)")
    offen = text.index("{", start)
    tiefe = 0
    for stelle in range(offen, len(text)):
        tiefe += {"{": 1, "}": -1}.get(text[stelle], 0)
        if tiefe == 0:
            return text[offen + 1 : stelle]
    raise ValueError("Block nicht geschlossen")


def test_filter_mobil_eine_zeile_zum_wischen():
    block = _mobil_block(THEMEN_CSS.read_text(encoding="utf-8"))
    filter_regel = re.search(r"\.themen-filter\s*\{([^}]*)\}", block).group(1)
    assert "flex-wrap: nowrap" in filter_regel
    assert "overflow-x: auto" in filter_regel
    assert ".themen-auswahl" not in block
