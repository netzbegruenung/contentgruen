"""
Die Themen: eine feste, kurze Liste, mit der Aussagen geordnet werden (Glossar
"Thema"). Freie Schlagworte gibt es nicht.

Die Liste steht in themen.json neben dieser Datei und wird per PR gepflegt. Der
Schluessel ist das, was an einer Aussage gespeichert wird; der Name ist nur die
Anzeige und darf sich aendern. Ein Schluessel, der wegfaellt, laesst seine
Zuordnungen in der Datenbank stehen; sie werden dann nicht mehr angezeigt
(AussageThemenService).
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

# Glossar: "eine Aussage hat hoechstens zwei".
HOECHSTENS_JE_AUSSAGE = 2

_DATEI = Path(__file__).with_name("themen.json")


@dataclass(frozen=True)
class Thema:
    schluessel: str
    name: str


class ThemaUngueltig(ValueError):
    """Ein Schluessel steht nicht in der Liste, oder es sind mehr als zwei."""


def _laden() -> Tuple[Thema, ...]:
    with _DATEI.open(encoding="utf-8") as datei:
        return tuple(Thema(e["schluessel"], e["name"]) for e in json.load(datei))


THEMEN: Tuple[Thema, ...] = _laden()
NACH_SCHLUESSEL: Dict[str, Thema] = {t.schluessel: t for t in THEMEN}


def themen_pruefen(schluessel: Iterable[str]) -> List[str]:
    """
    Die Themen einer Zuordnung, ohne Doppelte und in der gegebenen Reihenfolge.
    Leer ist erlaubt (die Zuordnung ist optional).

    Raises:
        ThemaUngueltig: ein Schluessel steht nicht in der Liste, oder es sind
            mehr als HOECHSTENS_JE_AUSSAGE.
    """
    ergebnis: List[str] = []
    for eintrag in schluessel:
        if eintrag not in NACH_SCHLUESSEL:
            raise ThemaUngueltig(f"Unbekanntes Thema: {eintrag!r}")
        if eintrag not in ergebnis:
            ergebnis.append(eintrag)
    if len(ergebnis) > HOECHSTENS_JE_AUSSAGE:
        raise ThemaUngueltig(
            f"Hoechstens {HOECHSTENS_JE_AUSSAGE} Themen je Aussage, nicht {len(ergebnis)}"
        )
    return ergebnis
