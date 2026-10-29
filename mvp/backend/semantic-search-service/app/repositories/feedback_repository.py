"""
Repository fuer Feedback an das Team (Tabelle feedback).

Was gespeichert wird und warum nicht mehr, steht in services/feedback_service.py.
"""

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

    def neueste(self, limit: int) -> List[FeedbackZeile]:
        """Das neueste Feedback zuerst; am selben Tag in fester Reihenfolge."""
        abfrage = (
            select(FeedbackZeile)
            .order_by(desc(FeedbackZeile.eingegangen_am), FeedbackZeile.id)
            .limit(limit)
        )
        with self.db.get_session() as session:
            zeilen = session.execute(abfrage).scalars().all()
            session.expunge_all()
            return list(zeilen)

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
