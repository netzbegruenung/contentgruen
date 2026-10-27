"""
Repository fuer die Tabelle ``gesehene_nutzung``: der Stand fuer die Rueckmeldung beim
Anmelden (#349).
"""

from typing import Optional

from sqlalchemy import select, update
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

        Der Stand sinkt nie. Liegt die Nutzung darunter (ein Beitrag ist gesperrt oder
        geloescht, oder ein langsamerer Aufruf bringt eine aeltere Zahl), ist der
        Zuwachs 0 und der hoehere Stand bleibt. Sonst meldete der naechste Besuch nach
        dem Entsperren alte Nutzung als neu; dafuer bleiben nach einer Loeschung bis zu
        deren Menge neue Nutzungen unerwaehnt.

        Erst die Zeile anlegen, dann sperren: ``FOR UPDATE`` sperrt nur eine Zeile, die
        es gibt. So wartet auch beim ersten Besuch ein zweiter, gleichzeitiger auf den
        ersten, sieht dessen Stand und meldet nichts doppelt.
        """
        with self.db.get_session() as session:
            session.execute(
                insert(GeseheneNutzung)
                .values(user_id=user_id, nutzung=0)
                .on_conflict_do_nothing(index_elements=[GeseheneNutzung.user_id])
            )
            gesehen = session.execute(
                select(GeseheneNutzung.nutzung)
                .where(GeseheneNutzung.user_id == user_id)
                .with_for_update()
            ).scalar_one()
            if nutzung_jetzt <= gesehen:
                return 0
            session.execute(
                update(GeseheneNutzung)
                .where(GeseheneNutzung.user_id == user_id)
                .values(nutzung=nutzung_jetzt)
            )
            return nutzung_jetzt - gesehen


_repository: Optional[GeseheneNutzungRepository] = None


def get_gesehene_nutzung_repository() -> GeseheneNutzungRepository:
    """Die globale Instanz holen oder anlegen."""
    global _repository
    if _repository is None:
        _repository = GeseheneNutzungRepository()
    return _repository
