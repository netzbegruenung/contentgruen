"""
Kennzahl "Suchen ohne Treffer": welche Suchanfragen keinen Beitrag finden.

Jede Suche legt ihren Text ohnehin als Aussage an (Herkunft SEARCH_QUERY,
Systemautor, siehe services/search/search_query_statement.py). Findet sie keinen
Beitrag ueber der Schwelle des SearchOrchestrators, zaehlt dieser Service das an
der Aussage, je Kalenderwoche. Gespeichert wird nur (Aussage, Woche, Anzahl der
Suchen, Anzahl der Personen):

- kein Pseudonym, keine Sitzung, kein Bezug zur Zeile in search_events;
- kein Zeitpunkt, nur der Montag der Woche. Ein genauer Zeitpunkt liesse sich mit
  search_events (Zeitpunkt, results_count = 0, actor_hash) verbinden und koppelte
  so die Aussage an das Tagespseudonym der suchenden Person;
- kein zweiter Suchtext: der Text steht an der Aussage, und aehnliche
  Suchanfragen landen dort schon auf derselben Aussage.

Admins sehen nur Aussagen, zu denen im Zeitraum mindestens MINDESTANZAHL
verschiedene Personen ohne Treffer gesucht haben. Eine Person, die dasselbe
mehrfach sucht, bringt die Aussage nicht allein in die Liste: Die Schwelle misst
Bedarf und schuetzt vor Rueckschluessen auf Einzelne. "Person" heisst hier
Tagespseudonym (SearchTrackingService): dieselbe Person an zwei Tagen zaehlt
zweimal, denn ein tagesuebergreifendes Merkmal gibt es bewusst nicht.

Welche Personen eine Aussage heute schon gezaehlt haben, haelt PersonenDesTages
nur im Speicher und nur fuer den laufenden UTC-Tag; um Mitternacht verwirft
loeschen_im_takt die Merkliste. In der Datenbank landet nur die Zahl. Nach einem
Neustart am selben Tag kann eine Person deshalb ein zweites Mal zaehlen; das ist
der Preis dafuer, dass keine Kennung je Person und Aussage gespeichert wird. Der
Dienst laeuft mit einem uvicorn-Worker.
Aussagen, die nicht freigegeben sind (Status BLOCKED, DUPLICATE), erscheinen nicht.
Admins sehen den Text der Aussage, nicht die eingegebene Suchanfrage: aehnliche
Suchanfragen landen auf derselben Aussage.

Wochen vor der Aufbewahrungsgrenze loescht loeschen_im_takt, ein eigener
Hintergrund-Task aus main.py, taeglich und zusaetzlich um Mitternacht (UTC). Er haengt bewusst nicht am Usage-Cleanup, der sich
abschalten laesst: Die Datenschutzerklaerung sagt die Loeschung nach acht Wochen
ohne Bedingung zu. Gerechnet wird in UTC wie bei search_events.
"""

import asyncio
import hashlib
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Set

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


def sekunden_bis_mitternacht(jetzt: Optional[datetime] = None) -> float:
    """Sekunden bis zum Beginn des naechsten UTC-Tages."""
    jetzt = jetzt or datetime.now(timezone.utc)
    morgen = datetime.combine(
        jetzt.date() + timedelta(days=1), datetime.min.time(), timezone.utc
    )
    return (morgen - jetzt).total_seconds()


async def loeschen_im_takt(
    repository: SuchenOhneTrefferRepository,
    personen: "PersonenDesTages",
    takt_sekunden: float = LOESCH_TAKT_SEKUNDEN,
) -> None:
    """
    Hintergrund-Task: loescht alte Wochen und verwirft die Personen der Vortage,
    sofort und dann taeglich, spaetestens aber um Mitternacht (UTC), bis er
    abgebrochen wird.
    """
    while True:
        personen.verwerfen_vor(heute_utc())
        try:
            geloescht = await asyncio.to_thread(alte_wochen_loeschen, repository)
            logger.info(f"Deleted {geloescht} old searches-without-hits weeks")
        except Exception as e:
            logger.error(
                f"Error during searches-without-hits cleanup: {e}", exc_info=True
            )
        # Eine Sekunde Puffer, damit der Lauf sicher im neuen Tag liegt.
        await asyncio.sleep(min(takt_sekunden, sekunden_bis_mitternacht() + 1))


class PersonenDesTages:
    """
    Merkt sich fuer den laufenden UTC-Tag, welche Personen zu welcher Aussage schon
    gezaehlt sind, als SHA-256 ueber (Tagespseudonym, Aussage). Der Hash haelt nur
    Pseudonym und Aussage-ID aus Logs und Fehlermeldungen heraus; wer den Speicher
    des Prozesses auslesen kann, kann ihn mit search_events abgleichen. Der Schutz
    liegt darin, dass nichts davon gespeichert wird und die Liste mit dem Tag
    verfaellt.
    """

    def __init__(self):
        self._tag: Optional[date] = None
        self._gezaehlt: Set[bytes] = set()

    def neu(self, pseudonym: str, statement_id: uuid.UUID, tag: date) -> bool:
        """True, wenn die Person die Aussage an diesem Tag noch nicht gezaehlt hat."""
        if tag != self._tag:
            self._tag = tag
            self._gezaehlt = set()
        kennung = hashlib.sha256(f"{pseudonym}|{statement_id}".encode("utf-8")).digest()
        if kennung in self._gezaehlt:
            return False
        self._gezaehlt.add(kennung)
        return True

    def verwerfen_vor(self, tag: date) -> None:
        """Die Merkliste vergessen, wenn sie zu einem frueheren Tag gehoert."""
        if self._tag is not None and self._tag < tag:
            self._tag = None
            self._gezaehlt = set()

    def anzahl(self) -> int:
        """Wie viele (Person, Aussage)-Paare gerade gemerkt sind."""
        return len(self._gezaehlt)


_personen_des_tages = PersonenDesTages()


def get_personen_des_tages() -> PersonenDesTages:
    """Prozessweit eine Merkliste: der Service entsteht je Anfrage neu."""
    return _personen_des_tages


class SuchenOhneTrefferService:
    def __init__(
        self,
        repository: SuchenOhneTrefferRepository,
        statement_service: StatementService,
        personen: PersonenDesTages,
    ):
        self._repository = repository
        self._statement_service = statement_service
        self._personen = personen

    def erfassen(
        self,
        statement_id: Optional[uuid.UUID],
        treffer: int,
        pseudonym: Optional[str],
        heute: Optional[date] = None,
    ) -> None:
        """
        Eine Suche zaehlen, wenn sie keinen Beitrag fand, und die suchende Person,
        wenn sie die Aussage heute noch nicht gezaehlt hat.

        pseudonym ist das Tagespseudonym aus SearchTrackingService. Ohne Pseudonym
        (weder Nutzer- noch Sitzungskennung) zaehlt die Suche, aber keine Person.
        Ohne Aussage (das Rate-Limit hat das Anlegen ausgelassen) gibt es nichts,
        woran sich zaehlen liesse; die Suche faellt dann aus der Kennzahl.
        Datenbankfehler gehen an den Aufrufer.
        """
        if treffer > 0 or statement_id is None:
            return
        tag = heute or heute_utc()
        neue_person = pseudonym is not None and self._personen.neu(
            pseudonym, statement_id, tag
        )
        self._repository.zaehlen(statement_id, wochenbeginn(tag), neue_person)

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
