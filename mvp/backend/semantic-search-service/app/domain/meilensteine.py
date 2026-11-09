"""
Meilensteine (GLOSSARY.md "Meilenstein", docs/VISION.md "Motivation", ADR 0004, #351).

Eine erreichte Schwelle bei der Wirkung der eigenen Beitraege: erste Nutzung durch
andere, 10, 50 und 100 Nutzungen, erste Zustimmung. Dazu Meilensteine fuer
Unterstuetzungsarbeit, die selbst keine Nutzung erzeugt (ADR 0004, "Drei Stufen"):
10 Einwuerfe ausformuliert und 10 eigene Einwuerfe, die andere ausformuliert haben.

Hier steht nur die Rechnung. Woher die Zahlen kommen (entdoppelte Nutzung, Stimmen
ohne eigene und ohne Startkonten), entscheidet services/meilensteine_service.py.
Die Schwellen sind Teil der Produktentscheidung in docs/VISION.md, keine
Stellschrauben wie die Punktegewichte; deshalb stehen sie hier und nicht in der
Konfiguration.
"""

from dataclasses import dataclass
from typing import List, Tuple

WIRKUNG = "wirkung"
UNTERSTUETZUNG = "unterstuetzung"


@dataclass(frozen=True)
class Meilensteindaten:
    """Was zu Meilensteinen zaehlt, schon gefiltert und gezaehlt."""

    nutzungen: int = 0
    zustimmungen: int = 0
    einwuerfe_ausformuliert: int = 0
    eigene_einwuerfe_von_anderen_ausformuliert: int = 0


@dataclass(frozen=True)
class Meilenstein:
    kennung: str
    name: str
    art: str
    schwelle: int
    stand: int

    @property
    def erreicht(self) -> bool:
        return self.stand >= self.schwelle


# (Kennung, Name, Art, Feld in Meilensteindaten, Schwelle), in der Reihenfolge der Anzeige.
MEILENSTEINE: Tuple[Tuple[str, str, str, str, int], ...] = (
    ("nutzung-1", "Erste Nutzung durch andere", WIRKUNG, "nutzungen", 1),
    ("nutzung-10", "10 Nutzungen", WIRKUNG, "nutzungen", 10),
    ("nutzung-50", "50 Nutzungen", WIRKUNG, "nutzungen", 50),
    ("nutzung-100", "100 Nutzungen", WIRKUNG, "nutzungen", 100),
    ("zustimmung-1", "Erste Zustimmung", WIRKUNG, "zustimmungen", 1),
    (
        "ausformuliert-10",
        "10 Einwürfe ausformuliert",
        UNTERSTUETZUNG,
        "einwuerfe_ausformuliert",
        10,
    ),
    (
        "eingeworfen-10",
        "10 deiner Einwürfe von anderen ausformuliert",
        UNTERSTUETZUNG,
        "eigene_einwuerfe_von_anderen_ausformuliert",
        10,
    ),
)


def meilensteine_berechnen(daten: Meilensteindaten) -> List[Meilenstein]:
    """Alle Meilensteine mit Stand; ``erreicht`` sagt, welche schon geschafft sind."""
    return [
        Meilenstein(
            kennung=kennung,
            name=name,
            art=art,
            schwelle=schwelle,
            stand=getattr(daten, feld),
        )
        for kennung, name, art, feld, schwelle in MEILENSTEINE
    ]
