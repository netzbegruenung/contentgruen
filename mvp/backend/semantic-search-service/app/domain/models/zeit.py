"""
Zeitstempel der Inhalte: immer UTC mit Zeitzone.

Frueher schrieb das Backend ``datetime.now()`` ohne Zeitzone. Der Container laeuft
in UTC, die Werte sind also UTC - nur sagt das JSON es nicht, und der Browser liest
"2026-09-17T08:06:22" als Ortszeit ("vor 2 Stunden" fuer einen eben gespeicherten
Beitrag). Neue Werte tragen deshalb die Zeitzone, und beim Lesen gelten naive
Altwerte als UTC. Ausgeliefert wird damit immer mit Offset.
"""

import datetime
from typing import Annotated

from pydantic import AfterValidator


def utc_jetzt() -> datetime.datetime:
    """Jetzt, als UTC mit Zeitzone - fuer created, last_modified, updated."""
    return datetime.datetime.now(datetime.timezone.utc)


def als_utc(wert: datetime.datetime) -> datetime.datetime:
    """Naive Werte gelten als UTC (so wurden sie geschrieben); andere nach UTC umrechnen."""
    if wert.tzinfo is None:
        return wert.replace(tzinfo=datetime.timezone.utc)
    return wert.astimezone(datetime.timezone.utc)


# Fuer Modellfelder: liest naive Altwerte als UTC, liefert immer mit Offset aus.
UtcZeit = Annotated[datetime.datetime, AfterValidator(als_utc)]
