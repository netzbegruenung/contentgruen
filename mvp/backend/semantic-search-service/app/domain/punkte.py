"""
Punkte in drei Stufen (ADR 0004, Ergaenzung 28.10.2026; GLOSSARY.md "Punkte", #352).

- Tun bringt kleine Punkte, gedeckelt je Tag: ein Beitrag, der drei Tage ohne Sperre
  steht, und ein Einwurf, der ausformuliert wurde (fuer die einwerfende Person).
- Abgeschlossene Quests bringen mehr, ebenfalls je Tag gedeckelt.
- Die Wirkung bei anderen bringt die grossen Punkte: entdoppelte Nutzung und Zustimmung
  durch andere. Ablehnung zieht nichts ab, Bewerten bringt keine Punkte.

Hier steht nur die Rechnung. Woher die Zahlen kommen (welche Nutzung zaehlt, welche
Beitraege noch Punkte tragen), entscheidet services/punkte_service.py; die Gewichte
und Deckel stehen in der Konfiguration (core/config.py, ``punkte_*``).
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Dict


@dataclass(frozen=True)
class Punktegewichte:
    """Punkte je Ereignis und Deckel je Tag; aus der Konfiguration."""

    nutzung: int
    zustimmung: int
    beitrag: int
    einwurf_ausformuliert: int
    deckel_tun_je_tag: int
    quest: int
    deckel_quests_je_tag: int


@dataclass(frozen=True)
class Wirkungsdaten:
    """Was einer Person Punkte bringt, schon gefiltert und gezaehlt."""

    nutzungen: int = 0
    zustimmungen: int = 0
    beitraege_je_tag: Dict[date, int] = field(default_factory=dict)
    einwuerfe_ausformuliert_je_tag: Dict[date, int] = field(default_factory=dict)
    quests_je_tag: Dict[date, int] = field(default_factory=dict)


@dataclass(frozen=True)
class Punktestand:
    tun: int
    quests: int
    wirkung: int

    @property
    def gesamt(self) -> int:
        return self.tun + self.quests + self.wirkung


def punkte_berechnen(daten: Wirkungsdaten, gewichte: Punktegewichte) -> Punktestand:
    tage = set(daten.beitraege_je_tag) | set(daten.einwuerfe_ausformuliert_je_tag)
    tun = sum(
        min(
            gewichte.deckel_tun_je_tag,
            daten.beitraege_je_tag.get(tag, 0) * gewichte.beitrag
            + daten.einwuerfe_ausformuliert_je_tag.get(tag, 0)
            * gewichte.einwurf_ausformuliert,
        )
        for tag in tage
    )
    quests = sum(
        min(gewichte.deckel_quests_je_tag, anzahl * gewichte.quest)
        for anzahl in daten.quests_je_tag.values()
    )
    wirkung = (
        daten.nutzungen * gewichte.nutzung + daten.zustimmungen * gewichte.zustimmung
    )
    return Punktestand(tun=tun, quests=quests, wirkung=wirkung)
