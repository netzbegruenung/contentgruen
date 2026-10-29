"""
"Hier fehlt eine Antwort": die unbeantworteten Aussagen fuer Mitwirkende.

Unbeantwortet ist nach Glossar eine Aussage ohne Kommentar oder eine, nach der
mindestens zwei Personen ohne Treffer gesucht haben. Die zweite Quelle ist dieselbe
wie die Admin-Kennzahl (SuchenOhneTrefferService.haeufigste): dieselbe Schwelle,
nur sichtbare Aussagen. Stammt eine davon aus einer Suchanfrage, ist ihr Text der
Suchtext der ersten suchenden Person (wie in der Admin-Kennzahl). Mitwirkende sehen
dazu, wie viele Personen ohne Treffer danach gesucht haben, gezaehlt wie in der
Kennzahl (Tagespseudonyme, ueber die Wochen summiert), damit Hotspots sichtbar
werden; die Zahl der Suchen sehen nur Admins.

Sortiert nach Bedarf: zuerst die Aussagen mit Suchen ohne Treffer, absteigend nach
der Zahl der Personen (bei gleicher Zahl wie in der Kennzahl), dann die uebrigen
ohne Kommentar, neueste zuerst. Nach Personen statt nach Suchen, damit die
Reihenfolge zur gezeigten Zahl passt und die Zahl der Suchen nicht verraet. Aussagen aus
Suchanfragen, die die Schwelle nicht erreichen und auf die niemand geantwortet hat,
erscheinen nicht: Sie sind die Suchanfrage einer einzelnen Person
(StatementRepository.ohne_kommentar).

Jede Aussage traegt ihre Themen (AussageThemenService). Mit einem Thema als Filter
bleiben nur die Aussagen mit diesem Thema, in derselben Reihenfolge; gefiltert wird
vor der Begrenzung, damit die Liste nicht durch Aussagen anderer Themen leer bleibt.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from domain.models.statement import StatementDbEntry
from services.aussage_themen_service import AussageThemenService
from services.content.statement_service import StatementService
from services.suchen_ohne_treffer_service import (
    WOCHEN_STANDARD,
    SuchenOhneTrefferService,
)

LIMIT_STANDARD = 50

# Wie viele Aussagen mit Suchen ohne Treffer gelesen werden, wenn nach einem Thema
# gefiltert wird: Der Filter laeuft danach, und mit nur LIMIT_STANDARD fehlten
# Aussagen des Themas, die weiter hinten stehen.
KANDIDATEN_MIT_FILTER = 500

_FRUEHESTE = datetime.min.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class UnbeantworteteAussage:
    statement_id: uuid.UUID
    text: str
    # Personen, die im Zeitraum ohne Treffer danach gesucht haben; 0 bei einer
    # Aussage, die nur wegen des fehlenden Kommentars auf der Liste steht.
    personen_ohne_treffer: int
    # Schluessel aus domain/themen.py, in der Reihenfolge der Liste.
    themen: Tuple[str, ...] = ()


def _zeitpunkt(aussage: StatementDbEntry) -> datetime:
    created = aussage.created
    if not isinstance(created, datetime):
        return _FRUEHESTE
    return created if created.tzinfo else created.replace(tzinfo=timezone.utc)


class UnbeantworteteAussagenService:
    def __init__(
        self,
        statement_service: StatementService,
        suchen_ohne_treffer: SuchenOhneTrefferService,
        themen: AussageThemenService,
    ):
        self._statement_service = statement_service
        self._suchen_ohne_treffer = suchen_ohne_treffer
        self._themen = themen

    async def liste(
        self, limit: int = LIMIT_STANDARD, thema: Optional[str] = None
    ) -> List[UnbeantworteteAussage]:
        gesucht = await self._suchen_ohne_treffer.haeufigste(
            wochen=WOCHEN_STANDARD,
            limit=KANDIDATEN_MIT_FILTER if thema else limit,
        )
        gesucht = sorted(gesucht, key=lambda g: g.personen, reverse=True)
        kandidaten = [(g.statement_id, g.text, g.personen) for g in gesucht]
        schon_drin = {statement_id for statement_id, _, _ in kandidaten}

        ohne_kommentar = await self._statement_service.ohne_kommentar()
        ohne_kommentar.sort(key=_zeitpunkt, reverse=True)
        kandidaten += [
            (aussage.id, aussage.text, 0)
            for aussage in ohne_kommentar
            if aussage.id not in schon_drin
        ]

        themen = self._themen.themen_von([s for s, _, _ in kandidaten])
        ergebnis = [
            UnbeantworteteAussage(
                statement_id, text, personen, tuple(themen.get(statement_id, ()))
            )
            for statement_id, text, personen in kandidaten
            if thema is None or thema in themen.get(statement_id, ())
        ]
        return ergebnis[:limit]
