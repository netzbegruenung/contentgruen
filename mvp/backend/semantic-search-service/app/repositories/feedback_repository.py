"""
Repository fuer Feedback an das Team (Tabelle feedback).

Was gespeichert wird und warum nicht mehr, steht in services/feedback_service.py.
"""

import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy import delete, desc, select

from infrastructure.database.connection import get_app_database
from infrastructure.database.models import FeedbackZeile


class FeedbackRepository:
    def __init__(self):
        self.db = get_app_database()

    def anlegen(self, text: str, kontakt: Optional[str], tag: date) -> None:
        with self.db.get_session() as session:
            session.add(FeedbackZeile(text=text, kontakt=kontakt, eingegangen_am=tag))
            session.commit()

    def neueste(
        self, limit: int, erledigt: Optional[bool] = None
    ) -> List[FeedbackZeile]:
        """
        Das neueste Feedback zuerst; am selben Tag in fester Reihenfolge. Mit
        erledigt nur das offene (False) oder das erledigte (True).
        """
        abfrage = select(FeedbackZeile)
        if erledigt is not None:
            abfrage = abfrage.where(FeedbackZeile.erledigt.is_(erledigt))
        abfrage = abfrage.order_by(
            desc(FeedbackZeile.eingegangen_am), FeedbackZeile.id
        ).limit(limit)
        with self.db.get_session() as session:
            zeilen = session.execute(abfrage).scalars().all()
            session.expunge_all()
            return list(zeilen)

    def erledigt_setzen(
        self, feedback_id: uuid.UUID, erledigt: bool
    ) -> Optional[FeedbackZeile]:
        """Setzt oder nimmt erledigt zurueck; None, wenn es die Zeile nicht gibt."""
        with self.db.get_session() as session:
            zeile = session.get(FeedbackZeile, feedback_id)
            if zeile is None:
                return None
            zeile.erledigt = erledigt
            session.flush()
            session.refresh(zeile)
            session.expunge(zeile)
            return zeile

    def loeschen(self, feedback_id: uuid.UUID) -> bool:
        """Loescht eine Zeile ganz, Kontakt eingeschlossen; False, wenn es sie nicht gibt."""
        with self.db.get_session() as session:
            ergebnis = session.execute(
                delete(FeedbackZeile).where(FeedbackZeile.id == feedback_id)
            )
            session.commit()
            return ergebnis.rowcount > 0

    def loeschen_vor(self, tag: date) -> int:
        """Alles Feedback vor dem Tag loeschen; liefert die Zahl der Zeilen."""
        with self.db.get_session() as session:
            ergebnis = session.execute(
                delete(FeedbackZeile).where(FeedbackZeile.eingegangen_am < tag)
            )
            session.commit()
            return ergebnis.rowcount


_repository: Optional[FeedbackRepository] = None


def get_feedback_repository() -> FeedbackRepository:
    global _repository
    if _repository is None:
        _repository = FeedbackRepository()
    return _repository
