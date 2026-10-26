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

Admins sehen nur Aussagen, zu denen im Zeitraum mindestens MINDESTANZAHL Suchen
ohne Treffer gezaehlt wurden - gezaehlt werden Suchen, nicht Personen. Die Schwelle
haelt Einzelfaelle aus der Liste, die ja die *haeufigen* Luecken zeigen soll.
Gesperrte oder als Dublette markierte Aussagen erscheinen nicht.

Wochen vor der Aufbewahrungsgrenze loescht der taegliche Aufraeumlauf
(services/cleanup/usage_cleanup_service.py).
"""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

from fastapi import Depends

from core.logging import get_logger
from dependencies import get_statement_service
from domain.models.content_status import FREIGEGEBEN
from repositories.suchen_ohne_treffer_repository import (
    SuchenOhneTrefferRepository,
    get_suchen_ohne_treffer_repository,
)
from services.content.statement_service import StatementService

logger = get_logger(__name__)

# Wochen, die gespeichert bleiben, die laufende eingeschlossen. Zugleich der
# laengste Zeitraum, den Admins abfragen koennen.
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


def aufbewahrungsgrenze(heute: Optional[date] = None) -> date:
    """Die aelteste Woche, die bleibt; alles davor wird geloescht."""
    return wochenbeginn(heute or date.today()) - timedelta(
        weeks=AUFBEWAHRUNG_WOCHEN - 1
    )


class SuchenOhneTrefferService:
    def __init__(
        self,
        repository: SuchenOhneTrefferRepository,
        statement_service: StatementService,
    ):
        self._repository = repository
        self._statement_service = statement_service

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
        Datenbankfehler gehen an den Aufrufer.
        """
        if treffer > 0 or statement_id is None:
            return
        self._repository.zaehlen(statement_id, wochenbeginn(heute or date.today()))

    async def haeufigste(
        self,
        wochen: int = WOCHEN_STANDARD,
        limit: int = LIMIT_STANDARD,
        heute: Optional[date] = None,
    ) -> List[SucheOhneTreffer]:
        """
        Die haeufigsten Suchanfragen ohne Treffer der letzten Wochen.

        Der Zeitraum umfasst die laufende Woche und die (wochen - 1) davor. Aussagen,
        die es nicht mehr gibt oder die nicht freigegeben sind (gesperrt, Dublette),
        fallen heraus; die Liste kann dadurch kuerzer als limit sein.
        """
        seit_woche = wochenbeginn(heute or date.today()) - timedelta(weeks=wochen - 1)
        zeilen = self._repository.haeufigste(seit_woche, MINDESTANZAHL, limit)

        ergebnis: List[SucheOhneTreffer] = []
        for statement_id, anzahl in zeilen:
            try:
                aussage = await self._statement_service.get(statement_id)
            except ValueError:
                continue
            if aussage.status not in FREIGEGEBEN:
                continue
            ergebnis.append(SucheOhneTreffer(statement_id, aussage.text, anzahl))
        return ergebnis


def get_suchen_ohne_treffer_service(
    statement_service: StatementService = Depends(get_statement_service),
) -> SuchenOhneTrefferService:
    return SuchenOhneTrefferService(
        get_suchen_ohne_treffer_repository(), statement_service
    )
