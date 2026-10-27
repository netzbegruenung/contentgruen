"""
"Hier fehlt eine Antwort": die unbeantworteten Aussagen fuer Mitwirkende.

Unbeantwortet ist nach Glossar eine Aussage ohne Kommentar oder eine, nach der
mindestens zwei Personen ohne Treffer gesucht haben. Die zweite Quelle ist dieselbe
wie die Admin-Kennzahl (SuchenOhneTrefferService.haeufigste): dieselbe Schwelle,
nur sichtbare Aussagen, kein Suchtext. Mitwirkende erfahren nicht, wie oft gesucht
wurde, nur dass gesucht wurde.

Sortiert nach Bedarf: zuerst die Aussagen mit Suchen ohne Treffer, absteigend nach
der Zahl der Suchen, dann die uebrigen ohne Kommentar, neueste zuerst. Aussagen aus
Suchanfragen, die die Schwelle nicht erreichen und auf die niemand geantwortet hat,
erscheinen nicht: Sie sind die Suchanfrage einer einzelnen Person
(StatementRepository.ohne_kommentar).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

from services.content.statement_service import StatementService
from services.suchen_ohne_treffer_service import (
    WOCHEN_STANDARD,
    SuchenOhneTrefferService,
)

LIMIT_STANDARD = 50

_FRUEHESTE = datetime.min.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class UnbeantworteteAussage:
    statement_id: uuid.UUID
    text: str
    ohne_treffer_gesucht: bool


def _zeitpunkt(aussage) -> datetime:
    created = getattr(aussage, "created", None)
    if not isinstance(created, datetime):
        return _FRUEHESTE
    return created if created.tzinfo else created.replace(tzinfo=timezone.utc)


class UnbeantworteteAussagenService:
    def __init__(
        self,
        statement_service: StatementService,
        suchen_ohne_treffer: SuchenOhneTrefferService,
    ):
        self._statement_service = statement_service
        self._suchen_ohne_treffer = suchen_ohne_treffer

    async def liste(self, limit: int = LIMIT_STANDARD) -> List[UnbeantworteteAussage]:
        gesucht = await self._suchen_ohne_treffer.haeufigste(
            wochen=WOCHEN_STANDARD, limit=limit
        )
        ergebnis = [
            UnbeantworteteAussage(g.statement_id, g.text, True) for g in gesucht
        ]
        schon_drin = {a.statement_id for a in ergebnis}

        ohne_kommentar = await self._statement_service.ohne_kommentar()
        ohne_kommentar.sort(key=_zeitpunkt, reverse=True)
        for aussage in ohne_kommentar:
            if len(ergebnis) >= limit:
                break
            if aussage.id not in schon_drin:
                ergebnis.append(UnbeantworteteAussage(aussage.id, aussage.text, False))
        return ergebnis[:limit]
