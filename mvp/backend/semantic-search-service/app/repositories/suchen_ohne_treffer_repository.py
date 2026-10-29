"""
Repository fuer die Kennzahl "Suchen ohne Treffer" (Tabelle suchen_ohne_treffer).

Je (Aussage, Woche) eine Zeile mit zwei Zaehlern: Suchen und Personen. Was
gezaehlt wird und warum nichts weiter gespeichert wird, steht in
services/suchen_ohne_treffer_service.py.
"""

import uuid
from datetime import date
from typing import List, Optional, Tuple

from sqlalchemy import delete, desc, func, select
from sqlalchemy.dialects.postgresql import insert

from infrastructure.database.connection import get_app_database
from infrastructure.database.models import SucheOhneTrefferZeile


# Personen im Zeitraum: die Summe ueber die Wochen (Tagespseudonyme verschiedener
# Tage sind immer verschieden).
_PERSONEN = func.sum(SucheOhneTrefferZeile.personen)


def _ab_mindestanzahl(abfrage, seit_woche: date, mindestanzahl: int):
    """Je Aussage ab seit_woche, nur mit mindestens mindestanzahl Personen."""
    return (
        abfrage.where(SucheOhneTrefferZeile.woche >= seit_woche)
        .group_by(SucheOhneTrefferZeile.statement_id)
        .having(_PERSONEN >= mindestanzahl)
    )


class SuchenOhneTrefferRepository:
    def __init__(self):
        self.db = get_app_database()

    def zaehlen(self, statement_id: uuid.UUID, woche: date, neue_person: bool) -> None:
        """
        Eine Suche ohne Treffer zur Aussage in der Woche zaehlen, und eine Person
        dazu, wenn neue_person gesetzt ist.
        """
        upsert = insert(SucheOhneTrefferZeile).values(
            statement_id=statement_id,
            woche=woche,
            anzahl=1,
            personen=1 if neue_person else 0,
        )
        upsert = upsert.on_conflict_do_update(
            index_elements=[
                SucheOhneTrefferZeile.statement_id,
                SucheOhneTrefferZeile.woche,
            ],
            set_={
                "anzahl": SucheOhneTrefferZeile.anzahl + upsert.excluded.anzahl,
                "personen": SucheOhneTrefferZeile.personen + upsert.excluded.personen,
            },
        )
        with self.db.get_session() as session:
            session.execute(upsert)
            session.commit()

    def loeschen_vor(self, woche: date) -> int:
        """Alle Wochen vor der angegebenen loeschen; liefert die Zahl der Zeilen."""
        with self.db.get_session() as session:
            ergebnis = session.execute(
                delete(SucheOhneTrefferZeile).where(SucheOhneTrefferZeile.woche < woche)
            )
            session.commit()
            return ergebnis.rowcount

    def haeufigste(
        self, seit_woche: date, mindestanzahl: int, limit: int, offset: int = 0
    ) -> List[Tuple[uuid.UUID, int, int]]:
        """
        (Aussage-ID, Anzahl der Suchen, Anzahl der Personen) ab seit_woche,
        absteigend nach Anzahl der Suchen, seitenweise; nur Aussagen mit mindestens
        mindestanzahl Personen. Die
        Personen der Wochen duerfen summiert werden: Tagespseudonyme verschiedener
        Tage sind immer verschieden.
        """
        summe = func.sum(SucheOhneTrefferZeile.anzahl)
        abfrage = (
            _ab_mindestanzahl(
                select(
                    SucheOhneTrefferZeile.statement_id,
                    summe.label("anzahl"),
                    _PERSONEN.label("personen"),
                ),
                seit_woche,
                mindestanzahl,
            )
            .order_by(desc("anzahl"), SucheOhneTrefferZeile.statement_id)
            .limit(limit)
            .offset(offset)
        )
        with self.db.get_session() as session:
            return [
                (statement_id, int(anzahl), int(personen))
                for statement_id, anzahl, personen in session.execute(abfrage).all()
            ]

    def ueber_der_schwelle(
        self, seit_woche: date, mindestanzahl: int
    ) -> List[uuid.UUID]:
        """
        Alle Aussage-IDs ab seit_woche mit mindestens mindestanzahl Personen,
        ungeordnet und ohne Limit; dieselbe Schwelle wie haeufigste.
        """
        abfrage = _ab_mindestanzahl(
            select(SucheOhneTrefferZeile.statement_id), seit_woche, mindestanzahl
        )
        with self.db.get_session() as session:
            return list(session.execute(abfrage).scalars().all())


_repository: Optional[SuchenOhneTrefferRepository] = None


def get_suchen_ohne_treffer_repository() -> SuchenOhneTrefferRepository:
    global _repository
    if _repository is None:
        _repository = SuchenOhneTrefferRepository()
    return _repository
