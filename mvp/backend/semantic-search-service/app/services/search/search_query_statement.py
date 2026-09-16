"""
Die Aussage, die beim Suchen nebenbei entsteht.

Jede Suche legt ihren Text als Statement an (Herkunft SEARCH_QUERY, Systemautor).
Das geschieht allein hier im Suchpfad: Die Suche ist ohne Anmeldung erreichbar,
die Statement-Endpunkte sind es nicht. Frueher legte das Frontend die Aussage
zusaetzlich ueber /statement/addStatement an - fuer Anonyme endete das mit 401
und einem Sprung auf /login.

Zwei Dinge regelt diese Klasse, bevor StatementService.add_statement laeuft:

- Rate-Limit je Aufrufer: Eine offene Route, die dauerhaft schreibt, braucht eine
  Grenze. Ist sie erreicht, entfaellt nur das Anlegen - die Suche selbst laeuft
  weiter. Der Schluessel ist derselbe fluechtige Adress-Hash wie bei den
  anonymen Meldungen (utils/client_identity.py). Abgelaufene Schluessel raeumt
  der Hintergrund-Task in main.py im Minutentakt weg (utils/rate_limiter.py).
- Serialisierung gleicher Texte: add_statement prueft erst auf Aehnlichkeit und
  schreibt dann mit neuer UUID. Zwei gleichzeitige Suchen nach demselben Text
  bestehen beide die Pruefung und legen zwei Punkte an. Eine Sperre je
  normalisiertem Text laesst die zweite erst pruefen, wenn die erste
  geschrieben hat. Die Sperre lebt im Prozess; das genuegt, weil der Dienst mit
  einem uvicorn-Worker laeuft.
"""

import asyncio
import hashlib
import uuid
from typing import Dict, Optional, Tuple

from core.logging import get_logger
from domain.models.content_origin import ContentOrigin, SEARCH_QUERY_AUTHOR
from domain.models.content_status import ContentStatus
from domain.models.statement import Statement
from utils.rate_limiter import RateLimiter, search_query_statement_rate_limiter

logger = get_logger(__name__)


def _sperrschluessel(text: str) -> str:
    """Gross/klein und Leerraum spielen fuer "derselbe Text" keine Rolle."""
    normalisiert = " ".join(text.split()).casefold()
    return hashlib.sha256(normalisiert.encode("utf-8")).hexdigest()


class SearchQueryStatementRecorder:
    def __init__(self, limiter: RateLimiter):
        self._limiter = limiter
        self._sperren: Dict[str, asyncio.Lock] = {}
        self._belegt: Dict[str, int] = {}

    async def anlegen(
        self, statement_service, text: str, client_key: str
    ) -> Tuple[bool, Optional[uuid.UUID], str]:
        """
        Aussage zum Suchtext anlegen oder die vorhandene finden.

        Returns:
            (neu angelegt, ID oder None, Text) - wie add_statement. None, wenn das
            Limit erreicht ist; die Suche kommt dann ohne Aussage aus.

        Fehler von add_statement gehen an den Aufrufer, der sie wie bisher
        abfaengt.
        """
        if await self._limiter.is_rate_limited(client_key):
            # Kein Suchtext und kein Schluessel im Log.
            logger.info("Suchanfrage-Aussage entfaellt: Rate-Limit erreicht")
            return False, None, text

        schluessel = _sperrschluessel(text)
        sperre = self._sperren.setdefault(schluessel, asyncio.Lock())
        self._belegt[schluessel] = self._belegt.get(schluessel, 0) + 1
        try:
            async with sperre:
                return await statement_service.add_statement(
                    Statement(text=text, replysuggestions=[]),
                    SEARCH_QUERY_AUTHOR,
                    ContentStatus.RELEASED_INTERNAL,
                    ContentOrigin.SEARCH_QUERY,
                )
        finally:
            self._belegt[schluessel] -= 1
            if self._belegt[schluessel] == 0:
                del self._belegt[schluessel]
                del self._sperren[schluessel]


_recorder = SearchQueryStatementRecorder(search_query_statement_rate_limiter)


def get_search_query_statement_recorder() -> SearchQueryStatementRecorder:
    return _recorder
