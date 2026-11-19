"""
Repository fuer die Tabelle ``punkte_einwilligung``: die Einwilligung "Punkte und
Meilensteine" je Kennung (#351, domain/punkte_einwilligung.py).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import func, insert, select

from domain.punkte_einwilligung import GELTENDE_WORTLAUTE
from infrastructure.database.connection import AppDatabase, get_app_database
from infrastructure.database.models import PunkteEinwilligungZeile


@dataclass(frozen=True)
class PunkteEinwilligung:
    eingewilligt: bool
    wortlaut: str
    beantwortet_am: datetime

    @property
    def gilt(self) -> bool:
        """Eingewilligt, und zu einem Wortlaut, der noch gilt."""
        return self.eingewilligt and self.wortlaut in GELTENDE_WORTLAUTE


class PunkteEinwilligungRepository:
    def __init__(self, db: Optional[AppDatabase] = None):
        """``db``: eine AppDatabase; ohne Angabe die globale."""
        self.db = db if db is not None else get_app_database()

    def lesen(self, user_id: str) -> Optional[PunkteEinwilligung]:
        """Die juengste Antwort der Kennung, oder None, wenn sie nie geantwortet hat."""
        with self.db.get_session() as session:
            zeile = session.execute(
                select(
                    PunkteEinwilligungZeile.eingewilligt,
                    PunkteEinwilligungZeile.wortlaut,
                    PunkteEinwilligungZeile.beantwortet_am,
                )
                .where(PunkteEinwilligungZeile.user_id == user_id)
                .order_by(
                    PunkteEinwilligungZeile.beantwortet_am.desc(),
                    PunkteEinwilligungZeile.id.desc(),
                )
                .limit(1)
            ).first()
            if zeile is None:
                return None
            return PunkteEinwilligung(
                eingewilligt=zeile.eingewilligt,
                wortlaut=zeile.wortlaut,
                beantwortet_am=zeile.beantwortet_am,
            )

    def eingewilligt(self, user_id: str) -> bool:
        """Gilt fuer die Kennung eine Einwilligung? Je Aufruf gefragt: Ein Widerruf wirkt sofort."""
        stand = self.lesen(user_id)
        return stand is not None and stand.gilt

    def antworten(self, user_id: str, eingewilligt: bool, wortlaut: str) -> None:
        """
        Eine neue Zeile; fruehere bleiben als Nachweis stehen. Ist die juengste
        Antwort schon dieselbe zum selben Wortlaut, bleibt es bei ihr.
        """
        juengste = self.lesen(user_id)
        if (
            juengste is not None
            and juengste.eingewilligt == eingewilligt
            and juengste.wortlaut == wortlaut
        ):
            return
        with self.db.get_session() as session:
            session.execute(
                insert(PunkteEinwilligungZeile).values(
                    user_id=user_id,
                    eingewilligt=eingewilligt,
                    wortlaut=wortlaut,
                    beantwortet_am=func.now(),
                )
            )


_repository: Optional[PunkteEinwilligungRepository] = None


def get_punkte_einwilligung_repository() -> PunkteEinwilligungRepository:
    """Die globale Instanz holen oder anlegen."""
    global _repository
    if _repository is None:
        _repository = PunkteEinwilligungRepository()
    return _repository
