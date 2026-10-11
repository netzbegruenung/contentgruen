"""
Repository fuer die Tabelle ``users``: Anzeigenamen ablegen und gesammelt lesen.
"""

import logging
from typing import Dict, Iterable, Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from infrastructure.database.connection import get_app_database
from infrastructure.database.models import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Anzeigenamen je Kennung."""

    def __init__(self):
        self.db = get_app_database()

    def anzeigename_speichern(self, user_id: str, anzeigename: str) -> None:
        """INSERT ... ON CONFLICT (user_id) DO UPDATE."""
        with self.db.get_session() as session:
            session.execute(self._upsert(user_id, anzeigename))

    def anzeigenamen(self, user_ids: Iterable[Optional[str]]) -> Dict[str, str]:
        """
        Die Namen zu mehreren Kennungen in einer Abfrage. Kennungen ohne Zeile
        fehlen im Ergebnis; ``None`` und Doppelte werden uebergangen.
        """
        kennungen = {kennung for kennung in user_ids if kennung}
        if not kennungen:
            return {}
        with self.db.get_session() as session:
            zeilen = session.execute(
                select(User.user_id, User.anzeigename).where(
                    User.user_id.in_(kennungen)
                )
            ).all()
            return {zeile.user_id: zeile.anzeigename for zeile in zeilen}

    @staticmethod
    def _upsert(user_id: str, anzeigename: str):
        stmt = insert(User).values(user_id=user_id, anzeigename=anzeigename)
        return stmt.on_conflict_do_update(
            index_elements=[User.user_id],
            set_={
                "anzeigename": stmt.excluded.anzeigename,
                "aktualisiert_am": func.now(),
            },
        )


_user_repository: Optional[UserRepository] = None


def get_user_repository() -> UserRepository:
    """Die globale UserRepository-Instanz holen oder anlegen."""
    global _user_repository
    if _user_repository is None:
        _user_repository = UserRepository()
    return _user_repository
