"""
Repository fuer die Kennzahl "Suchen ohne Treffer" (Tabelle suchen_ohne_treffer).

Je (Aussage, Woche) eine Zeile mit einem Zaehler. Was gezaehlt wird und warum
nichts weiter gespeichert wird, steht in services/suchen_ohne_treffer_service.py.
"""

import logging
import uuid
from datetime import date
from typing import List, Optional, Tuple

from sqlalchemy import delete, desc, func, select
from sqlalchemy.dialects.postgresql import insert

from infrastructure.database.connection import get_app_database
from infrastructure.database.models import SucheOhneTreffer

logger = logging.getLogger(__name__)


class SuchenOhneTrefferRepository:
    def __init__(self):
        self.db = get_app_database()

    def zaehlen(self, statement_id: uuid.UUID, woche: date, aelter_als: date) -> None:
        """
        Eine Suche ohne Treffer zur Aussage in der Woche zaehlen und Wochen vor
        aelter_als loeschen.

        Fehler werden geloggt und geschluckt: die Suche darf an der Kennzahl nicht
        scheitern.
        """
        upsert = insert(SucheOhneTreffer).values(
            statement_id=statement_id, woche=woche, anzahl=1
        )
        upsert = upsert.on_conflict_do_update(
            index_elements=[SucheOhneTreffer.statement_id, SucheOhneTreffer.woche],
            set_={"anzahl": SucheOhneTreffer.anzahl + upsert.excluded.anzahl},
        )
        aufraeumen = delete(SucheOhneTreffer).where(SucheOhneTreffer.woche < aelter_als)
        try:
            with self.db.get_session() as session:
                session.execute(upsert)
                session.execute(aufraeumen)
                session.commit()
        except Exception as e:
            logger.error(f"Suche ohne Treffer nicht gezaehlt: {e}", exc_info=True)

    def haeufigste(
        self, seit_woche: date, mindestanzahl: int, limit: int
    ) -> List[Tuple[uuid.UUID, int]]:
        """(Aussage-ID, Anzahl) ab seit_woche, absteigend nach Anzahl."""
        summe = func.sum(SucheOhneTreffer.anzahl)
        abfrage = (
            select(SucheOhneTreffer.statement_id, summe.label("anzahl"))
            .where(SucheOhneTreffer.woche >= seit_woche)
            .group_by(SucheOhneTreffer.statement_id)
            .having(summe >= mindestanzahl)
            .order_by(desc("anzahl"), SucheOhneTreffer.statement_id)
            .limit(limit)
        )
        with self.db.get_session() as session:
            return [
                (statement_id, int(anzahl))
                for statement_id, anzahl in session.execute(abfrage).all()
            ]


_repository: Optional[SuchenOhneTrefferRepository] = None


def get_suchen_ohne_treffer_repository() -> SuchenOhneTrefferRepository:
    global _repository
    if _repository is None:
        _repository = SuchenOhneTrefferRepository()
    return _repository
