"""
Repository fuer die Vormoderation unbeantworteter Suchanfragen (Tabelle
suchanfrage_freigaben). Je geprueftem Eintrag eine Zeile: freigegeben oder
abgelehnt, und wann. Was daraus folgt, steht in services/suchen_ohne_treffer_service.py.
"""

import uuid
from typing import Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from infrastructure.database.connection import get_app_database
from infrastructure.database.models import SuchanfrageFreigabe


class SuchanfrageFreigabeRepository:
    def __init__(self):
        self.db = get_app_database()

    def entscheidungen(self) -> Dict[uuid.UUID, bool]:
        """Alle Entscheidungen: Aussage-ID -> freigegeben (True) oder abgelehnt."""
        abfrage = select(
            SuchanfrageFreigabe.statement_id, SuchanfrageFreigabe.freigegeben
        )
        with self.db.get_session() as session:
            return {
                statement_id: bool(freigegeben)
                for statement_id, freigegeben in session.execute(abfrage).all()
            }

    def entscheiden(self, statement_id: uuid.UUID, freigegeben: bool) -> None:
        """Freigeben oder ablehnen; eine fruehere Entscheidung wird ersetzt."""
        upsert = insert(SuchanfrageFreigabe).values(
            statement_id=statement_id, freigegeben=freigegeben
        )
        upsert = upsert.on_conflict_do_update(
            index_elements=[SuchanfrageFreigabe.statement_id],
            set_={"freigegeben": freigegeben, "entschieden_am": func.now()},
        )
        with self.db.get_session() as session:
            session.execute(upsert)
            session.commit()


_repository: Optional[SuchanfrageFreigabeRepository] = None


def get_suchanfrage_freigabe_repository() -> SuchanfrageFreigabeRepository:
    global _repository
    if _repository is None:
        _repository = SuchanfrageFreigabeRepository()
    return _repository
