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
Aussagen, die nicht freigegeben sind (Status BLOCKED, DUPLICATE), erscheinen nicht.
Admins sehen den Text der Aussage, nicht die eingegebene Suchanfrage: aehnliche
Suchanfragen landen auf derselben Aussage.

Wochen vor der Aufbewahrungsgrenze loescht loeschen_im_takt, ein eigener
Hintergrund-Task aus main.py. Er haengt bewusst nicht am Usage-Cleanup, der sich
abschalten laesst: Die Datenschutzerklaerung sagt die Loeschung nach acht Wochen
ohne Bedingung zu. Gerechnet wird in UTC wie bei search_events.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

from core.logging import get_logger
from domain.models.content_status import FREIGEGEBEN
from repositories.suchen_ohne_treffer_repository import SuchenOhneTrefferRepository
from services.content.statement_service import StatementService

logger = get_logger(__name__)

# Wochen, die gespeichert bleiben, die laufende eingeschlossen. Zugleich der
# laengste Zeitraum, den Admins abfragen koennen.
AUFBEWAHRUNG_WOCHEN = 8
WOCHEN_STANDARD = 4
WOCHEN_MAX = AUFBEWAHRUNG_WOCHEN
MINDESTANZAHL = 2
LIMIT_STANDARD = 20
LOESCH_TAKT_SEKUNDEN = 24 * 60 * 60


@dataclass(frozen=True)
class SucheOhneTreffer:
    """Eine Aussage, zu der Suchen keinen Beitrag fanden, mit ihrer Anzahl."""

    statement_id: uuid.UUID
    text: str
    anzahl: int


def wochenbeginn(tag: date) -> date:
    """Der Montag der Woche, in die der Tag faellt."""
    return tag - timedelta(days=tag.weekday())


def heute_utc() -> date:
    return datetime.now(timezone.utc).date()


def aufbewahrungsgrenze(heute: Optional[date] = None) -> date:
    """Die aelteste Woche, die bleibt; alles davor wird geloescht."""
    return wochenbeginn(heute or heute_utc()) - timedelta(weeks=AUFBEWAHRUNG_WOCHEN - 1)


def alte_wochen_loeschen(
    repository: SuchenOhneTrefferRepository, heute: Optional[date] = None
) -> int:
    """Wochen vor der Aufbewahrungsgrenze loeschen; liefert die Zahl der Zeilen."""
    return repository.loeschen_vor(aufbewahrungsgrenze(heute))


async def loeschen_im_takt(
    repository: SuchenOhneTrefferRepository,
    takt_sekunden: float = LOESCH_TAKT_SEKUNDEN,
) -> None:
    """Hintergrund-Task: loescht sofort und dann taeglich, bis er abgebrochen wird."""
    while True:
        try:
            geloescht = await asyncio.to_thread(alte_wochen_loeschen, repository)
            logger.info(f"Deleted {geloescht} old searches-without-hits weeks")
        except Exception as e:
            logger.error(
                f"Error during searches-without-hits cleanup: {e}", exc_info=True
            )
        await asyncio.sleep(takt_sekunden)


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
        self._repository.zaehlen(statement_id, wochenbeginn(heute or heute_utc()))

    async def haeufigste(
        self,
        wochen: int = WOCHEN_STANDARD,
        limit: int = LIMIT_STANDARD,
        heute: Optional[date] = None,
    ) -> List[SucheOhneTreffer]:
        """
        Die haeufigsten Suchanfragen ohne Treffer der letzten Wochen.

        Der Zeitraum umfasst die laufende Woche und die (wochen - 1) davor. Aussagen,
        die es nicht mehr gibt oder die nicht freigegeben sind, fallen heraus; damit
        die Liste trotzdem bis zu limit Eintraege hat, wird seitenweise nachgeladen.
        """
        seit_woche = wochenbeginn(heute or heute_utc()) - timedelta(weeks=wochen - 1)

        ergebnis: List[SucheOhneTreffer] = []
        offset = 0
        while len(ergebnis) < limit:
            zeilen = self._repository.haeufigste(
                seit_woche, MINDESTANZAHL, limit, offset
            )
            aussagen = await asyncio.gather(
                *(
                    self._freigegebene_aussage(statement_id)
                    for statement_id, _ in zeilen
                )
            )
            for (statement_id, anzahl), aussage in zip(zeilen, aussagen):
                if aussage is not None:
                    ergebnis.append(
                        SucheOhneTreffer(statement_id, aussage.text, anzahl)
                    )
            if len(zeilen) < limit:
                break
            offset += limit
        return ergebnis[:limit]

    async def _freigegebene_aussage(self, statement_id: uuid.UUID):
        try:
            aussage = await self._statement_service.get(statement_id)
        except ValueError:
            return None
        return aussage if aussage.status in FREIGEGEBEN else None
