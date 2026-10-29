"""
Der UTC-Tag fuer Daten, die statt eines Zeitpunkts nur den Tag tragen, und fuer
Hintergrund-Tasks, die um Mitternacht (UTC) loeschen.

Gerechnet wird in UTC wie bei search_events. Genutzt von den Suchen ohne Treffer
und vom Feedback.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Optional


def heute_utc() -> date:
    return datetime.now(timezone.utc).date()


def sekunden_bis_mitternacht(jetzt: Optional[datetime] = None) -> float:
    """Sekunden bis zum Beginn des naechsten UTC-Tages."""
    jetzt = jetzt or datetime.now(timezone.utc)
    morgen = datetime.combine(
        jetzt.date() + timedelta(days=1), datetime.min.time(), timezone.utc
    )
    return (morgen - jetzt).total_seconds()
