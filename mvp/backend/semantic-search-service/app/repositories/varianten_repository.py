"""
Repository fuer Varianten (Tabelle varianten, #356): welcher Beitrag auf welchem
beruht. Was eine Variante ist, steht am Modell (infrastructure/database/models.py,
``VarianteZeile``); wie sie entsteht und gezaehlt wird, in services/varianten.py.
"""

from typing import Dict, List, Optional, Sequence
from uuid import UUID

from sqlalchemy import delete, exists, func, select
from sqlalchemy.dialects.postgresql import insert

from infrastructure.database.connection import AppDatabase, get_app_database
from infrastructure.database.models import Sperre, VarianteZeile


class VariantenRepository:
    """Jede Methode ist eine Transaktion; get_session schreibt beim Verlassen fest."""

    def __init__(self, db: Optional[AppDatabase] = None):
        """``db``: eine AppDatabase; ohne Angabe die globale, erst beim ersten Zugriff.
        So kostet die Dependency an den Formular-Endpunkten nichts, solange niemand
        einen Beitrag als Vorlage nimmt."""
        self._db = db

    @property
    def db(self) -> AppDatabase:
        if self._db is None:
            self._db = get_app_database()
        return self._db

    def festhalten(self, variante_id: UUID, original_id: UUID) -> None:
        """Die Variante beruht auf dem Original. Eine Variante hat genau ein Original;
        ein zweiter Aufruf fuer dieselbe Variante aendert nichts."""
        with self.db.get_session() as session:
            session.execute(
                insert(VarianteZeile)
                .values(variante_id=variante_id, original_id=original_id)
                .on_conflict_do_nothing(index_elements=["variante_id"])
            )

    def anzahl_je_original(self, original_ids: Sequence[UUID]) -> Dict[UUID, int]:
        """
        Wie viele sichtbare Varianten jedes Original hat; Originale ohne fehlen.
        Gesperrte zaehlen nicht (aktive Sperre in ``sperren``), damit die Zahl an der
        Karte zur Liste passt; geloeschte haben keine Zeile mehr.
        """
        if not original_ids:
            return {}
        gesperrt = exists().where(
            Sperre.content_id == VarianteZeile.variante_id,
            Sperre.aufgehoben_am.is_(None),
        )
        abfrage = (
            select(VarianteZeile.original_id, func.count())
            .where(VarianteZeile.original_id.in_(list(original_ids)), ~gesperrt)
            .group_by(VarianteZeile.original_id)
        )
        with self.db.get_session() as session:
            return {
                original_id: int(anzahl)
                for original_id, anzahl in session.execute(abfrage).all()
            }

    def varianten_von(self, original_id: UUID) -> List[UUID]:
        """Die IDs der Varianten des Originals, in fester Reihenfolge."""
        abfrage = (
            select(VarianteZeile.variante_id)
            .where(VarianteZeile.original_id == original_id)
            .order_by(VarianteZeile.variante_id)
        )
        with self.db.get_session() as session:
            return list(session.execute(abfrage).scalars().all())

    def variante_entfernen(self, variante_id: UUID) -> None:
        """Die Verknuepfung der Variante loesen, etwa wenn ihr Autor sie loescht."""
        with self.db.get_session() as session:
            session.execute(
                delete(VarianteZeile).where(VarianteZeile.variante_id == variante_id)
            )


_repository: Optional[VariantenRepository] = None


def get_varianten_repository() -> VariantenRepository:
    """Fuer Depends; die Verbindung kommt aus der globalen AppDatabase."""
    global _repository
    if _repository is None:
        _repository = VariantenRepository()
    return _repository
