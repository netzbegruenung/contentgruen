"""
Repository fuer die Tabelle ``art9_einwilligungen``: die Art.-9-Einwilligung je
Kennung (#489).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from infrastructure.database.connection import AppDatabase, get_app_database
from infrastructure.database.models import Art9EinwilligungZeile


@dataclass(frozen=True)
class Art9Einwilligung:
    wortlaut: str
    eingewilligt_am: datetime
    widerrufen_am: Optional[datetime]

    @property
    def gilt(self) -> bool:
        return self.widerrufen_am is None


class Art9EinwilligungRepository:
    def __init__(self, db: Optional[AppDatabase] = None):
        """``db``: eine AppDatabase; ohne Angabe die globale."""
        self.db = db if db is not None else get_app_database()

    def lesen(self, user_id: str) -> Optional[Art9Einwilligung]:
        with self.db.get_session() as session:
            zeile = session.execute(
                select(
                    Art9EinwilligungZeile.wortlaut,
                    Art9EinwilligungZeile.eingewilligt_am,
                    Art9EinwilligungZeile.widerrufen_am,
                ).where(Art9EinwilligungZeile.user_id == user_id)
            ).first()
            if zeile is None:
                return None
            return Art9Einwilligung(
                wortlaut=zeile.wortlaut,
                eingewilligt_am=zeile.eingewilligt_am,
                widerrufen_am=zeile.widerrufen_am,
            )

    def einwilligen(self, user_id: str, wortlaut: str) -> None:
        """Neue Einwilligung; eine fruehere oder widerrufene wird ersetzt."""
        stmt = insert(Art9EinwilligungZeile).values(
            user_id=user_id,
            wortlaut=wortlaut,
            eingewilligt_am=func.now(),
            widerrufen_am=None,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[Art9EinwilligungZeile.user_id],
            set_={
                "wortlaut": stmt.excluded.wortlaut,
                "eingewilligt_am": stmt.excluded.eingewilligt_am,
                "widerrufen_am": None,
            },
        )
        with self.db.get_session() as session:
            session.execute(stmt)

    def widerrufen(self, user_id: str) -> None:
        """Setzt den Zeitpunkt des Widerrufs; ohne geltende Einwilligung nichts."""
        with self.db.get_session() as session:
            session.execute(
                update(Art9EinwilligungZeile)
                .where(
                    Art9EinwilligungZeile.user_id == user_id,
                    Art9EinwilligungZeile.widerrufen_am.is_(None),
                )
                .values(widerrufen_am=func.now())
            )


_repository: Optional[Art9EinwilligungRepository] = None


def get_art9_einwilligung_repository() -> Art9EinwilligungRepository:
    """Die globale Instanz holen oder anlegen."""
    global _repository
    if _repository is None:
        _repository = Art9EinwilligungRepository()
    return _repository
