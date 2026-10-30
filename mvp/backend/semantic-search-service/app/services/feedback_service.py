"""
Feedback an das Team (#343): ein Freitext und optional eine Kontaktangabe, die
Admins im Admin-Dashboard lesen. Keine Mail, kein externer Dienst.

Gespeichert wird nur, was die Person selbst eingibt, und der Tag:

- keine Kennung und keine Sitzung, auch nicht bei angemeldeten Personen. Wer eine
  Antwort will, schreibt einen Kontakt dazu; sonst bleibt das Feedback anonym;
- kein Zeitpunkt, nur der UTC-Tag. Ein genauer Zeitpunkt liesse sich mit
  Anwendungsprotokollen oder Suchereignissen derselben Minute verbinden.

Nach AUFBEWAHRUNG_TAGE loescht loeschen_im_takt, ein eigener Hintergrund-Task aus
main.py, die ganze Zeile, Kontakt eingeschlossen, taeglich und zusaetzlich um
Mitternacht (UTC). Wie bei den Suchen ohne Treffer haengt er nicht am abschaltbaren
Usage-Cleanup: Die Frist steht im Loeschkonzept ohne Bedingung.
"""

import asyncio
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

from core.logging import get_logger
from repositories.feedback_repository import FeedbackRepository
from utils.utc_tag import heute_utc, sekunden_bis_mitternacht

logger = get_logger(__name__)

AUFBEWAHRUNG_TAGE = 180
TEXT_MAX = 2000
KONTAKT_MAX = 200
LIMIT_STANDARD = 100
LOESCH_TAKT_SEKUNDEN = 24 * 60 * 60


@dataclass(frozen=True)
class FeedbackEintrag:
    id: uuid.UUID
    text: str
    kontakt: Optional[str]
    eingegangen_am: date


def aufbewahrungsgrenze(heute: Optional[date] = None) -> date:
    """Der aelteste Tag, der bleibt; alles davor wird geloescht."""
    return (heute or heute_utc()) - timedelta(days=AUFBEWAHRUNG_TAGE)


class FeedbackService:
    def __init__(self, repository: FeedbackRepository):
        self._repository = repository

    def senden(
        self, text: str, kontakt: Optional[str], heute: Optional[date] = None
    ) -> None:
        self._repository.anlegen(text, kontakt, heute or heute_utc())

    def neueste(self, limit: int = LIMIT_STANDARD) -> List[FeedbackEintrag]:
        return [
            FeedbackEintrag(z.id, z.text, z.kontakt, z.eingegangen_am)
            for z in self._repository.neueste(limit)
        ]

    def alte_loeschen(self, heute: Optional[date] = None) -> int:
        """Feedback vor der Aufbewahrungsgrenze loeschen; liefert die Zahl der Zeilen."""
        return self._repository.loeschen_vor(aufbewahrungsgrenze(heute))


async def loeschen_im_takt(
    service: FeedbackService, takt_sekunden: float = LOESCH_TAKT_SEKUNDEN
) -> None:
    """
    Hintergrund-Task: loescht altes Feedback sofort und dann taeglich, spaetestens
    aber um Mitternacht (UTC), bis er abgebrochen wird.
    """
    while True:
        try:
            geloescht = await asyncio.to_thread(service.alte_loeschen)
            logger.info(f"Deleted {geloescht} old feedback entries")
        except Exception as e:
            logger.error(
                f"Error during feedback cleanup: {type(e).__name__}", exc_info=True
            )
        await asyncio.sleep(min(takt_sekunden, sekunden_bis_mitternacht() + 1))
