"""
Kennzahl "Suchen ohne Treffer": welche Suchanfragen keinen Beitrag finden.

Jede Suche legt ihren Text ohnehin als Aussage an (Herkunft SEARCH_QUERY,
Systemautor, siehe services/search/search_query_statement.py). Findet sie keinen
Beitrag ueber der Schwelle des SearchOrchestrators, zaehlt dieser Service das an
der Aussage, je Kalenderwoche. Gespeichert wird nur (Aussage, Woche, Anzahl):

- kein Pseudonym, keine Sitzung, kein Bezug zur Zeile in search_events;
- kein Zeitpunkt, nur der Montag der Woche. Ein genauer Zeitpunkt liesse sich mit
  search_events (Zeitpunkt, results_count = 0, actor_hash) verbinden und koppelte
  so die Aussage an das Tagespseudonym der suchenden Person;
- kein zweiter Suchtext: der Text steht an der Aussage, und aehnliche
  Suchanfragen landen dort schon auf derselben Aussage.

Admins sehen nur Aussagen, die im Zeitraum mindestens MINDESTANZAHL-mal ohne
Treffer gesucht wurden. Eine einmalige Suchanfrage ist keine haeufige und koennte
eher etwas Persoenliches enthalten.
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

from core.logging import get_logger
from repositories.suchen_ohne_treffer_repository import (
    get_suchen_ohne_treffer_repository,
)

logger = get_logger(__name__)

# Wochen, die gespeichert bleiben. Mehr als die Anzeige (hoechstens WOCHEN_MAX),
# damit der Zeitraum immer voll belegt ist; aeltere Wochen loescht jedes Zaehlen.
AUFBEWAHRUNG_WOCHEN = 8
WOCHEN_STANDARD = 4
WOCHEN_MAX = AUFBEWAHRUNG_WOCHEN
MINDESTANZAHL = 2
LIMIT_STANDARD = 20


@dataclass(frozen=True)
class SucheOhneTreffer:
    """Eine Aussage, zu der Suchen keinen Beitrag fanden, mit ihrer Anzahl."""

    statement_id: uuid.UUID
    text: str
    anzahl: int


def wochenbeginn(tag: date) -> date:
    """Der Montag der Woche, in die der Tag faellt."""
    return tag - timedelta(days=tag.weekday())


class SuchenOhneTrefferService:
    def __init__(self, repository):
        self._repository = repository

    def erfassen(
        self,
        statement_id: Optional[uuid.UUID],
        treffer: int,
        heute: Optional[date] = None,
    ) -> None:
        """
        Eine Suche zaehlen, wenn sie keinen Beitrag fand.

        Ohne Aussage (das Rate-Limit hat das Anlegen ausgelassen) gibt es nichts,
        woran sich zaehlen liesse; die Suche faellt dann aus der Kennzahl.
        """
        if treffer > 0 or statement_id is None:
            return

        woche = wochenbeginn(heute or date.today())
        aelter_als = woche - timedelta(weeks=AUFBEWAHRUNG_WOCHEN - 1)
        self._repository.zaehlen(statement_id, woche, aelter_als)

    async def haeufigste(
        self,
        statement_service,
        wochen: int = WOCHEN_STANDARD,
        limit: int = LIMIT_STANDARD,
        heute: Optional[date] = None,
    ) -> List[SucheOhneTreffer]:
        """
        Die haeufigsten Suchanfragen ohne Treffer der letzten Wochen.

        Der Zeitraum umfasst die laufende Woche und die (wochen - 1) davor. Aussagen,
        die es nicht mehr gibt, fallen heraus.
        """
        seit_woche = wochenbeginn(heute or date.today()) - timedelta(weeks=wochen - 1)
        zeilen = self._repository.haeufigste(seit_woche, MINDESTANZAHL, limit)

        ergebnis: List[SucheOhneTreffer] = []
        for statement_id, anzahl in zeilen:
            try:
                aussage = await statement_service.get(statement_id)
            except ValueError:
                continue
            ergebnis.append(SucheOhneTreffer(statement_id, aussage.text, anzahl))
        return ergebnis


_service: Optional[SuchenOhneTrefferService] = None


def get_suchen_ohne_treffer_service() -> SuchenOhneTrefferService:
    global _service
    if _service is None:
        _service = SuchenOhneTrefferService(get_suchen_ohne_treffer_repository())
    return _service
