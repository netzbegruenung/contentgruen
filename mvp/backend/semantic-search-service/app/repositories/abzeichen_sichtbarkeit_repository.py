"""
Repository fuer die Tabelle ``abzeichen_sichtbarkeit``: die Zustimmung zur
Sichtbarkeit der Meilenstein-Abzeichen je Kennung (#351).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, insert, select

from infrastructure.database.connection import AppDatabase, get_app_database
from infrastructure.database.models import AbzeichenSichtbarkeitZeile


@dataclass(frozen=True)
class Sichtbarkeit:
    zeigen: bool
    wortlaut: str
    beantwortet_am: datetime


class AbzeichenSichtbarkeitRepository:
    def __init__(self, db: Optional[AppDatabase] = None):
        """``db``: eine AppDatabase; ohne Angabe die globale."""
        self.db = db if db is not None else get_app_database()

    def lesen(self, user_id: str) -> Optional[Sichtbarkeit]:
        """Die juengste Antwort der Kennung, oder None, wenn sie nie gefragt wurde."""
        with self.db.get_session() as session:
            zeile = session.execute(
                select(
                    AbzeichenSichtbarkeitZeile.zeigen,
                    AbzeichenSichtbarkeitZeile.wortlaut,
                    AbzeichenSichtbarkeitZeile.beantwortet_am,
                )
                .where(AbzeichenSichtbarkeitZeile.user_id == user_id)
                .order_by(
                    AbzeichenSichtbarkeitZeile.beantwortet_am.desc(),
                    AbzeichenSichtbarkeitZeile.id.desc(),
                )
                .limit(1)
            ).first()
            if zeile is None:
                return None
            return Sichtbarkeit(
                zeigen=zeile.zeigen,
                wortlaut=zeile.wortlaut,
                beantwortet_am=zeile.beantwortet_am,
            )

    def antworten(self, user_id: str, zeigen: bool, wortlaut: str) -> None:
        """
        Eine neue Zeile; fruehere bleiben als Nachweis stehen. Ist die juengste
        Antwort schon dieselbe zum selben Wortlaut, bleibt es bei ihr.
        """
        juengste = self.lesen(user_id)
        if (
            juengste is not None
            and juengste.zeigen == zeigen
            and juengste.wortlaut == wortlaut
        ):
            return
        with self.db.get_session() as session:
            session.execute(
                insert(AbzeichenSichtbarkeitZeile).values(
                    user_id=user_id,
                    zeigen=zeigen,
                    wortlaut=wortlaut,
                    beantwortet_am=func.now(),
                )
            )

    def zeigende(self) -> List[str]:
        """Alle Kennungen, deren juengste Antwort "zeigen" ist."""
        juengste = (
            select(
                AbzeichenSichtbarkeitZeile.user_id,
                AbzeichenSichtbarkeitZeile.zeigen,
                func.row_number()
                .over(
                    partition_by=AbzeichenSichtbarkeitZeile.user_id,
                    # Bei gleichem Zeitpunkt wie in lesen(): beide Abfragen einig.
                    order_by=(
                        AbzeichenSichtbarkeitZeile.beantwortet_am.desc(),
                        AbzeichenSichtbarkeitZeile.id.desc(),
                    ),
                )
                .label("rang"),
            )
        ).subquery()
        abfrage = select(juengste.c.user_id).where(
            juengste.c.rang == 1, juengste.c.zeigen.is_(True)
        )
        with self.db.get_session() as session:
            return [kennung for (kennung,) in session.execute(abfrage)]


_repository: Optional[AbzeichenSichtbarkeitRepository] = None


def get_abzeichen_sichtbarkeit_repository() -> AbzeichenSichtbarkeitRepository:
    """Die globale Instanz holen oder anlegen."""
    global _repository
    if _repository is None:
        _repository = AbzeichenSichtbarkeitRepository()
    return _repository
