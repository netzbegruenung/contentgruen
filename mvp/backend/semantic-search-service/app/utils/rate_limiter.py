"""
Simple in-memory rate limiter for API endpoints.
"""

from datetime import datetime, timedelta
from typing import Dict, Iterable, List
from collections import defaultdict
import asyncio
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Simple in-memory rate limiter.

    Tracks request timestamps per identifier (user_id or session_id).
    Automatically cleans up old entries.
    """

    def __init__(self, max_requests: int, window_minutes: int):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in the time window
            window_minutes: Time window in minutes
        """
        self.max_requests = max_requests
        self.window = timedelta(minutes=window_minutes)
        self._requests: Dict[str, List[datetime]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_rate_limited(self, identifier: str) -> bool:
        """
        Check if identifier is rate limited.

        Args:
            identifier: User ID or session ID to check

        Returns:
            True if rate limited, False otherwise
        """
        async with self._lock:
            now = datetime.utcnow()
            cutoff = now - self.window

            # Get or create request list for this identifier
            requests = self._requests[identifier]

            # Remove old requests outside the window
            requests[:] = [req_time for req_time in requests if req_time > cutoff]

            # Check if limit exceeded BEFORE adding current request
            if len(requests) >= self.max_requests:
                return True

            # Only add timestamp if not rate limited
            requests.append(now)
            return False

    async def get_remaining(self, identifier: str) -> int:
        """
        Get remaining requests for identifier.

        Args:
            identifier: User ID or session ID

        Returns:
            Number of remaining requests in current window
        """
        async with self._lock:
            now = datetime.utcnow()
            cutoff = now - self.window

            requests = self._requests.get(identifier, [])
            requests[:] = [req_time for req_time in requests if req_time > cutoff]

            return max(0, self.max_requests - len(requests))

    async def cleanup(self):
        """Remove all expired entries (for memory management)."""
        async with self._lock:
            now = datetime.utcnow()
            cutoff = now - self.window

            # Clean up old entries
            for identifier in list(self._requests.keys()):
                requests = self._requests[identifier]
                requests[:] = [req_time for req_time in requests if req_time > cutoff]

                # Remove empty lists
                if not requests:
                    del self._requests[identifier]


# Global rate limiters
# 5 reports per user/session per 15 minutes
report_rate_limiter = RateLimiter(max_requests=5, window_minutes=15)

# Aussagen aus Suchanfragen: 60 je Adresse in 10 Minuten. Gezaehlt wird jeder
# Versuch, auch wenn die Aussage schon existiert. Hinter einem gemeinsamen NAT
# (Geschaeftsstelle, Parteitag) teilen sich viele eine Adresse - deshalb deutlich
# ueber dem, was eine Person sucht. Ist die Grenze erreicht, sucht man weiter,
# nur ohne neue Aussage.
search_query_statement_rate_limiter = RateLimiter(max_requests=60, window_minutes=10)


# Feedback: 5 je Adresse in 15 Minuten, wie Meldungen. Die Route ist ohne Anmeldung
# erreichbar; mehr schreibt niemand in einer Viertelstunde an das Team.
feedback_rate_limiter = RateLimiter(max_requests=5, window_minutes=15)

# Einladungen (#429), beide Routen ohne Anmeldung. Ein Gruppenlink wird oft in einem
# Raum hinter einer gemeinsamen Adresse (NAT) eingeloest; die Zahl der Einloesungen
# begrenzt schon die Einladung selbst. Einloesen: 30 je Adresse in 15 Minuten, jeder
# Aufruf kann eine Mail ausloesen. Pruefen: 60, die Seite fragt einmal beim Oeffnen;
# mehr braucht nur, wer Codes durchprobiert (22 Zeichen Zufall, aussichtslos).
einladung_rate_limiter = RateLimiter(max_requests=30, window_minutes=15)
einladung_pruefen_rate_limiter = RateLimiter(max_requests=60, window_minutes=15)

# Gegenlesen beim Schreiben (#358): 300 je Person in 10 Minuten. Das Formular fragt
# etwa eine Sekunde nach jeder Eingabepause nach; das sind beim zuegigen Schreiben
# weniger als 30 in der Minute.
gegenlesen_rate_limiter = RateLimiter(max_requests=300, window_minutes=10)

# So oft raeumt der Hintergrund-Task abgelaufene Schluessel weg. Ein Schluessel
# verschwindet damit spaetestens ein Fenster plus dieser Takt nach seinem letzten
# Aufruf - fuer die Suchaussage zehn plus eine Minute. Die Datenschutzerklaerung
# nennt diese Frist ("Ihre Suchanfragen"); wer Fenster oder Takt aendert, zieht
# sie nach.
AUFRAEUM_TAKT_SEKUNDEN = 60


async def aufraeumen(limiters: Iterable[RateLimiter]) -> None:
    """Einmal alle Limiter aufraeumen; ein Fehler bei einem haelt die anderen nicht auf."""
    for limiter in limiters:
        try:
            await limiter.cleanup()
        except Exception as e:
            logger.error(
                f"Error in rate limiter cleanup: {type(e).__name__}", exc_info=True
            )


async def aufraeumen_im_takt(
    limiters: Iterable[RateLimiter], takt_sekunden: float = AUFRAEUM_TAKT_SEKUNDEN
) -> None:
    """Hintergrund-Task: raeumt die Limiter in festem Takt auf, bis er abgebrochen wird."""
    limiters = list(limiters)
    while True:
        await asyncio.sleep(takt_sekunden)
        await aufraeumen(limiters)
