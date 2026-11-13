"""
Repository fuer die Tabelle ``art9_einwilligungen``: die Art.-9-Einwilligung je
Kennung (#489).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import func, insert, select, update
from sqlalchemy.orm import Session

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
        """Die juengste Einwilligung der Kennung, auch wenn sie widerrufen ist."""
        with self.db.get_session() as session:
            zeile = self._juengste(session, user_id)
            if zeile is None:
                return None
            return Art9Einwilligung(
                wortlaut=zeile.wortlaut,
                eingewilligt_am=zeile.eingewilligt_am,
                widerrufen_am=zeile.widerrufen_am,
            )

    def einwilligen(self, user_id: str, wortlaut: str) -> None:
        """
        Eine neue Zeile; fruehere bleiben als Nachweis stehen. Gilt schon eine
        Einwilligung zu diesem Wortlaut, bleibt es bei ihr (doppeltes Absenden).
        """
        with self.db.get_session() as session:
            juengste = self._juengste(session, user_id)
            if (
                juengste is not None
                and juengste.widerrufen_am is None
                and juengste.wortlaut == wortlaut
            ):
                return
            session.execute(
                insert(Art9EinwilligungZeile).values(
                    user_id=user_id, wortlaut=wortlaut, eingewilligt_am=func.now()
                )
            )

    def widerrufen(
        self,
        user_id: str,
        im_selben_zug: Optional[Callable[[Session, bool], None]] = None,
    ) -> None:
        """
        Setzt den Zeitpunkt des Widerrufs an jeder noch geltenden Zeile.

        ``im_selben_zug`` laeuft danach in derselben Transaktion (das Loeschen der
        Stimmen und der Loeschauftrag, Art9EinwilligungService.widerrufen): Scheitert
        es, gilt auch der Widerruf nicht, und die Person kann ihn wiederholen. Es
        bekommt die Sitzung und ob eben eine geltende Einwilligung widerrufen wurde.
        """
        with self.db.get_session() as session:
            geaendert = session.execute(
                update(Art9EinwilligungZeile)
                .where(
                    Art9EinwilligungZeile.user_id == user_id,
                    Art9EinwilligungZeile.widerrufen_am.is_(None),
                )
                .values(widerrufen_am=func.now())
            ).rowcount
            if im_selben_zug is not None:
                im_selben_zug(session, geaendert > 0)

    @staticmethod
    def _juengste(session, user_id: str):
        return session.execute(
            select(
                Art9EinwilligungZeile.wortlaut,
                Art9EinwilligungZeile.eingewilligt_am,
                Art9EinwilligungZeile.widerrufen_am,
            )
            .where(Art9EinwilligungZeile.user_id == user_id)
            .order_by(Art9EinwilligungZeile.eingewilligt_am.desc())
            .limit(1)
        ).first()


_repository: Optional[Art9EinwilligungRepository] = None


def get_art9_einwilligung_repository() -> Art9EinwilligungRepository:
    """Die globale Instanz holen oder anlegen."""
    global _repository
    if _repository is None:
        _repository = Art9EinwilligungRepository()
    return _repository
