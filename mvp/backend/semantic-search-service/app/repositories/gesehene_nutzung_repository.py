"""
Repository fuer die Tabelle ``gesehene_nutzung``: der Stand fuer die Rueckmeldung beim
Anmelden (#349).
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from infrastructure.database.connection import AppDatabase, get_app_database
from infrastructure.database.models import GeseheneNutzung


class GeseheneNutzungRepository:
    """Zuletzt gezeigte Nutzung je Kennung."""

    def __init__(self, db: Optional[AppDatabase] = None):
        """``db``: eine AppDatabase; ohne Angabe die globale."""
        self.db = db if db is not None else get_app_database()

    def neu_seit_letztem_besuch(self, user_id: str, nutzung_jetzt: int) -> int:
        """
        Wie viele Nutzungen seit dem zuletzt gezeigten Stand dazugekommen sind;
        danach gilt ``nutzung_jetzt`` als gezeigt.

        Ohne Zeile ist der Stand 0: Alles bisher war noch nie Thema einer Rueckmeldung.
        Liegt die Nutzung unter dem Stand (ein Beitrag wurde geloescht), ist der
        Zuwachs 0 und der niedrigere Stand gilt.

        ``FOR UPDATE`` haelt zwei gleichzeitige Besuche auseinander: Der zweite
        sieht den Stand des ersten und meldet nichts doppelt.
        """
        with self.db.get_session() as session:
            gesehen = session.execute(
                select(GeseheneNutzung.nutzung)
                .where(GeseheneNutzung.user_id == user_id)
                .with_for_update()
            ).scalar()
            stmt = insert(GeseheneNutzung).values(
                user_id=user_id, nutzung=nutzung_jetzt
            )
            session.execute(
                stmt.on_conflict_do_update(
                    index_elements=[GeseheneNutzung.user_id],
                    set_={"nutzung": stmt.excluded.nutzung},
                )
            )
            return max(0, nutzung_jetzt - (gesehen or 0))


_repository: Optional[GeseheneNutzungRepository] = None


def get_gesehene_nutzung_repository() -> GeseheneNutzungRepository:
    """Die globale Instanz holen oder anlegen."""
    global _repository
    if _repository is None:
        _repository = GeseheneNutzungRepository()
    return _repository
