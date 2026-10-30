"""
Der UTC-Tag fuer Daten, die statt eines Zeitpunkts nur den Tag tragen, und fuer
Hintergrund-Tasks, die um Mitternacht (UTC) loeschen.

Gerechnet wird in UTC wie bei search_events. Genutzt von den Suchen ohne Treffer,
vom Feedback und von der Bilanz.
"""

from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Tuple


def heute_utc() -> date:
    return datetime.now(timezone.utc).date()


def sekunden_bis_mitternacht(jetzt: Optional[datetime] = None) -> float:
    """Sekunden bis zum Beginn des naechsten UTC-Tages."""
    jetzt = jetzt or datetime.now(timezone.utc)
    morgen = datetime.combine(
        jetzt.date() + timedelta(days=1), datetime.min.time(), timezone.utc
    )
    return (morgen - jetzt).total_seconds()


def wochenbeginn(tag: date) -> date:
    """Der Montag der Woche, in die der Tag faellt."""
    return tag - timedelta(days=tag.weekday())


def utc_zeitraum(erster: date, letzter: date) -> Tuple[datetime, datetime]:
    """Die UTC-Tage erster bis letzter (beide eingeschlossen) als [von, bis)."""
    return (
        datetime.combine(erster, time.min, tzinfo=timezone.utc),
        datetime.combine(letzter + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )
