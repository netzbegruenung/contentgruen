"""
Kennzahlen der Bilanz je Kalenderwoche (#467; Signale und Basislinie in #417).

- K1 Personen pro Tag, die suchen: verschiedene Tagespseudonyme je Tag, gemittelt
  ueber die Tage der Woche (Tage ohne Suche zaehlen mit 0).
- K2 Nutzungen pro Woche: Nutzungsereignisse der Woche.
- K3 Anteil der Suchen ohne Treffer, in Prozent.
- H Nutzungen je Suche: K2 geteilt durch die Suchen der Woche.

Feste Zielwerte gibt es bewusst nicht: Die Signale sind Abweichungen von der
Basislinie aus dem internen Launch (#417).

Wochen beginnen am Montag (UTC), wie bei den Suchen ohne Treffer. Die laufende
Woche zaehlt die Tage bis heute. Was nicht mehr bekannt ist, bleibt leer (None)
statt 0: Nutzungen vor der Frist der Nutzungsereignisse und Suchen ohne Treffer
aus Tageszaehlern von vor #467.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Protocol

from repositories.search_tracking_repository import Tageswert


@dataclass(frozen=True)
class BilanzWoche:
    woche_ab: date
    tage: int
    suchen: int
    personen_pro_tag: float
    nutzungen: Optional[int]
    anteil_ohne_treffer: Optional[float]
    nutzungen_je_suche: Optional[float]


class _Suchen(Protocol):
    def get_tageswerte(self, erster: date, letzter: date) -> List[Tageswert]: ...


class _Nutzungen(Protocol):
    def get_nutzungen_je_tag(self, erster: date, letzter: date) -> Dict[date, int]: ...


def _montag(tag: date) -> date:
    return tag - timedelta(days=tag.weekday())


def bilanz_je_woche(
    tageswerte: Iterable[Tageswert],
    nutzungen_je_tag: Dict[date, int],
    heute: date,
    wochen: int,
    nutzung_ab: Optional[date] = None,
) -> List[BilanzWoche]:
    """Die letzten ``wochen`` Kalenderwochen bis heute, die laufende zuerst.

    nutzung_ab: erster Tag, ab dem die Nutzungsereignisse vollstaendig sind;
    Wochen, die frueher beginnen, haben keine Nutzungen (None).
    """
    tage_je_datum = {t.tag: t for t in tageswerte}
    laufender_montag = _montag(heute)
    ergebnis = []
    for i in range(wochen):
        woche_ab = laufender_montag - timedelta(weeks=i)
        tage = [
            woche_ab + timedelta(days=d)
            for d in range(7)
            if woche_ab + timedelta(days=d) <= heute
        ]
        werte = [tage_je_datum[t] for t in tage if t in tage_je_datum]

        suchen = sum(w.suchen for w in werte)
        personen = sum(w.personen for w in werte)
        nutzungen = (
            None
            if nutzung_ab is not None and woche_ab < nutzung_ab
            else sum(nutzungen_je_tag.get(t, 0) for t in tage)
        )
        ohne_treffer_bekannt = all(w.ohne_treffer is not None for w in werte)

        ergebnis.append(
            BilanzWoche(
                woche_ab=woche_ab,
                tage=len(tage),
                suchen=suchen,
                personen_pro_tag=round(personen / len(tage), 1),
                nutzungen=nutzungen,
                anteil_ohne_treffer=(
                    round(sum(w.ohne_treffer for w in werte) / suchen * 100, 1)
                    if suchen and ohne_treffer_bekannt
                    else None
                ),
                nutzungen_je_suche=(
                    round(nutzungen / suchen, 2)
                    if suchen and nutzungen is not None
                    else None
                ),
            )
        )
    return ergebnis


class BilanzService:
    """Liest Tageswerte und Nutzungen und rechnet sie zu Wochen."""

    def __init__(
        self,
        suchen: _Suchen,
        nutzungen: _Nutzungen,
        nutzung_frist_tage: Optional[int],
    ):
        """nutzung_frist_tage: Frist der Nutzungsereignisse, None ohne Bereinigung."""
        self._suchen = suchen
        self._nutzungen = nutzungen
        self._nutzung_frist_tage = nutzung_frist_tage

    def wochen(self, anzahl: int, heute: Optional[date] = None) -> List[BilanzWoche]:
        heute = heute or datetime.now(timezone.utc).date()
        erster = _montag(heute) - timedelta(weeks=anzahl - 1)
        # Der Bereinigungsjob loescht, was aelter als die Frist ist, gemessen am
        # Zeitpunkt seines Laufs: Der Tag an der Grenze ist schon angebrochen.
        nutzung_ab = (
            heute - timedelta(days=self._nutzung_frist_tage - 1)
            if self._nutzung_frist_tage is not None
            else None
        )
        return bilanz_je_woche(
            self._suchen.get_tageswerte(erster, heute),
            self._nutzungen.get_nutzungen_je_tag(erster, heute),
            heute=heute,
            wochen=anzahl,
            nutzung_ab=nutzung_ab,
        )
