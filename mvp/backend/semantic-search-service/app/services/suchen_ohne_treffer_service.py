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
verschiedene Personen ohne Treffer gesucht haben. Eine Person, die am selben Tag
mehrfach dasselbe sucht, bringt die Aussage nicht allein in die Liste: Die Schwelle
misst Bedarf und schuetzt vor Rueckschluessen auf Einzelne. "Person" heisst hier
Tagespseudonym (SearchTrackingService), und das hat Grenzen:

- dieselbe Person an zwei Tagen zaehlt zweimal, denn ein tagesuebergreifendes
  Merkmal gibt es bewusst nicht;
- wer sich am selben Tag anmeldet, zaehlt danach unter der Nutzerkennung als
  weitere Person; Sitzung und Konto zu verbinden waere neuer Personenbezug;
- die Sitzungskennung setzt der Browser. Wer sie wechselt, ist eine neue Person.

Welche Personen eine Aussage heute schon gezaehlt haben, haelt PersonenDesTages
nur im Speicher und nur fuer den laufenden UTC-Tag; um Mitternacht verwirft
loeschen_im_takt die Merkliste. In der Datenbank landet nur die Zahl. Nach einem
Neustart am selben Tag kann eine Person deshalb ein zweites Mal zaehlen; das ist
der Preis dafuer, dass keine Kennung je Person und Aussage gespeichert wird. Die
Merkliste setzt einen uvicorn-Worker voraus (so startet das Dockerfile den Dienst;
erzwungen wird es nicht) und kommt ohne Sperre aus, weil erfassen synchron in der
Event-Loop laeuft. Mehr als MERKLISTE_MAX Paare je Tag merkt sie sich nicht; was
darueber hinaus kommt, zaehlt als Suche, aber nicht als Person, damit die Liste
nicht unbegrenzt waechst und keine Aussage dadurch ueber die Schwelle rutscht.
Nur sichtbare Aussagen erscheinen, gesperrte und geloeschte nicht.
Admins sehen den Text der Aussage, nicht die eingegebene Suchanfrage: aehnliche
Suchanfragen landen auf derselben Aussage.

Wochen vor der Aufbewahrungsgrenze loescht loeschen_im_takt, ein eigener
Hintergrund-Task aus main.py, taeglich und zusaetzlich um Mitternacht (UTC). Er
haengt bewusst nicht am Usage-Cleanup, der sich abschalten laesst: Die
Datenschutzerklaerung sagt die Loeschung nach acht Wochen ohne Bedingung zu. Gerechnet wird in UTC wie bei search_events.
"""

import asyncio
import hashlib
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import FrozenSet, List, Optional, Set

from core.logging import get_logger
from domain.models.content_status import ContentStatus
from repositories.suchen_ohne_treffer_repository import SuchenOhneTrefferRepository
from services.content.statement_service import StatementService
from utils.utc_tag import heute_utc, sekunden_bis_mitternacht

logger = get_logger(__name__)

# Wochen, die gespeichert bleiben, die laufende eingeschlossen. Zugleich der
# laengste Zeitraum, den Admins abfragen koennen.
AUFBEWAHRUNG_WOCHEN = 8
WOCHEN_STANDARD = 4
WOCHEN_MAX = AUFBEWAHRUNG_WOCHEN
MINDESTANZAHL = 2
LIMIT_STANDARD = 20
LOESCH_TAKT_SEKUNDEN = 24 * 60 * 60
# Obergrenze der Merkliste: (Person, Aussage)-Paare je Tag, je Eintrag 32 Bytes
# plus Verwaltung des Sets, zusammen gut 10 MB.
MERKLISTE_MAX = 100_000


@dataclass(frozen=True)
class SucheOhneTreffer:
    """
    Eine Aussage, zu der Suchen keinen Beitrag fanden, mit der Anzahl der Suchen
    und der Personen (Tagespseudonyme, ueber die Wochen summiert).
    """

    statement_id: uuid.UUID
    text: str
    anzahl: int
    personen: int


def wochenbeginn(tag: date) -> date:
    """Der Montag der Woche, in die der Tag faellt."""
    return tag - timedelta(days=tag.weekday())


def _seit_woche(wochen: int, heute: Optional[date] = None) -> date:
    """Montag der ersten Woche im Zeitraum: die laufende und die (wochen - 1) davor."""
    return wochenbeginn(heute or heute_utc()) - timedelta(weeks=wochen - 1)


def aufbewahrungsgrenze(heute: Optional[date] = None) -> date:
    """Die aelteste Woche, die bleibt; alles davor wird geloescht."""
    return _seit_woche(AUFBEWAHRUNG_WOCHEN, heute)


def alte_wochen_loeschen(
    repository: SuchenOhneTrefferRepository, heute: Optional[date] = None
) -> int:
    """Wochen vor der Aufbewahrungsgrenze loeschen; liefert die Zahl der Zeilen."""
    return repository.loeschen_vor(aufbewahrungsgrenze(heute))


def _kennung(pseudonym: str, statement_id: uuid.UUID) -> bytes:
    return hashlib.sha256(f"{pseudonym}|{statement_id}".encode("utf-8")).digest()


class PersonenDesTages:
    """
    Merkt sich fuer den laufenden UTC-Tag, welche Personen zu welcher Aussage schon
    gezaehlt sind, als SHA-256 ueber (Tagespseudonym, Aussage). Der Hash haelt nur
    Pseudonym und Aussage-ID aus Logs und Fehlermeldungen heraus; wer den Speicher
    des Prozesses auslesen kann, kann ihn mit search_events abgleichen. Der Schutz
    liegt darin, dass nichts davon gespeichert wird und die Liste mit dem Tag
    verfaellt.
    """

    def __init__(self, obergrenze: int = MERKLISTE_MAX):
        self._tag: Optional[date] = None
        self._gezaehlt: Set[bytes] = set()
        self._obergrenze = obergrenze

    def neu(self, pseudonym: str, statement_id: uuid.UUID, tag: date) -> bool:
        """
        True, wenn die Person die Aussage an diesem Tag noch nicht gezaehlt hat.
        Ist die Merkliste voll, False: lieber eine Person zu wenig als eine zu viel.
        """
        if tag != self._tag:
            self._tag = tag
            self._gezaehlt = set()
        kennung = _kennung(pseudonym, statement_id)
        if kennung in self._gezaehlt or len(self._gezaehlt) >= self._obergrenze:
            return False
        self._gezaehlt.add(kennung)
        return True

    def vergessen(self, pseudonym: str, statement_id: uuid.UUID) -> None:
        """Eine Person wieder streichen, deren Zaehlung nicht geschrieben wurde."""
        self._gezaehlt.discard(_kennung(pseudonym, statement_id))

    def verwerfen_vor(self, tag: date) -> None:
        """Die Merkliste vergessen, wenn sie zu einem frueheren Tag gehoert."""
        if self._tag is not None and self._tag < tag:
            self._tag = None
            self._gezaehlt = set()

    def anzahl(self) -> int:
        """Wie viele (Person, Aussage)-Paare gerade gemerkt sind."""
        return len(self._gezaehlt)


async def loeschen_im_takt(
    repository: SuchenOhneTrefferRepository,
    personen: PersonenDesTages,
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

        pseudonym ist das Tagespseudonym aus SearchTrackingService und heute der
        Tag, zu dem es gehoert. Ohne Pseudonym (weder Nutzer- noch
        Sitzungskennung) zaehlt die Suche, aber keine Person.
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
        try:
            self._repository.zaehlen(statement_id, wochenbeginn(tag), neue_person)
        except Exception:
            # Nicht geschrieben, also auch nicht gezaehlt: die naechste Suche der
            # Person soll sie nachtragen koennen.
            if neue_person:
                self._personen.vergessen(pseudonym, statement_id)
            raise

    async def haeufigste(
        self,
        wochen: int = WOCHEN_STANDARD,
        limit: int = LIMIT_STANDARD,
        heute: Optional[date] = None,
    ) -> List[SucheOhneTreffer]:
        """
        Die haeufigsten Suchanfragen ohne Treffer der letzten Wochen.

        Der Zeitraum umfasst die laufende Woche und die (wochen - 1) davor. Aussagen,
        die es nicht mehr gibt oder die nicht sichtbar sind, fallen heraus; damit
        die Liste trotzdem bis zu limit Eintraege hat, wird seitenweise nachgeladen.
        """
        seit_woche = _seit_woche(wochen, heute)

        ergebnis: List[SucheOhneTreffer] = []
        offset = 0
        while len(ergebnis) < limit:
            zeilen = self._repository.haeufigste(
                seit_woche, MINDESTANZAHL, limit, offset
            )
            aussagen = await asyncio.gather(
                *(self._sichtbare_aussage(statement_id) for statement_id, *_ in zeilen)
            )
            for (statement_id, anzahl, personen), aussage in zip(zeilen, aussagen):
                if aussage is not None:
                    ergebnis.append(
                        SucheOhneTreffer(statement_id, aussage.text, anzahl, personen)
                    )
            if len(zeilen) < limit:
                break
            offset += limit
        return ergebnis[:limit]

    async def ueber_der_schwelle(
        self, wochen: int = WOCHEN_STANDARD, heute: Optional[date] = None
    ) -> FrozenSet[uuid.UUID]:
        """
        Alle Aussagen, nach denen im Zeitraum mindestens MINDESTANZAHL Personen ohne
        Treffer gesucht haben, ohne Limit und ohne Blick auf den Zustand: Fuer
        Nicht-Admins zaehlen sie wie kuratierte Aussagen (api/v1/statement.py, #436),
        nur sichtbare filtert dort Qdrant.

        Ohne Limit, weil Zeitraum und Mindestanzahl die Menge begrenzen: es sind
        hoechstens die Aussagen, nach denen im Zeitraum mindestens MINDESTANZAHL
        Personen ohne Treffer gesucht haben. Die IDs gehen als eine Bedingung in jeden
        Qdrant-Filter fuer Nicht-Admins.

        Die Abfrage ist synchron (SQLAlchemy) und laeuft deshalb in einem Thread:
        Sie kommt bei jedem Aufruf von Nicht-Admins und soll den Event-Loop nicht
        blockieren.
        """
        seit_woche = _seit_woche(wochen, heute)
        ids = await asyncio.to_thread(
            self._repository.ueber_der_schwelle, seit_woche, MINDESTANZAHL
        )
        return frozenset(ids)

    async def _sichtbare_aussage(self, statement_id: uuid.UUID):
        try:
            aussage = await self._statement_service.get(statement_id)
        except ValueError:
            return None
        return aussage if aussage.status == ContentStatus.VISIBLE else None
