"""
Repository fuer die Tabellen ``schalter`` und ``schalter_verlauf``: Admin-Werte der
Schalter und jede Aenderung daran (#708, GLOSSARY.md "Schalter").
"""

from typing import Dict, Optional

from sqlalchemy import func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from infrastructure.database.connection import AppDatabase, get_app_database
from infrastructure.database.models import SchalterVerlaufZeile, SchalterZeile


class SchalterRepository:
    def __init__(self, db: Optional[AppDatabase] = None):
        """``db``: eine AppDatabase; ohne Angabe die globale."""
        self.db = db if db is not None else get_app_database()

    def admin_werte(self) -> Dict[str, bool]:
        """Alle gespeicherten Admin-Werte; ein Schalter ohne Zeile fehlt (gilt aus)."""
        with self.db.get_session() as session:
            zeilen = session.execute(select(SchalterZeile.name, SchalterZeile.an)).all()
            return {zeile.name: zeile.an for zeile in zeilen}

    def setzen(self, name: str, an: bool, admin: str) -> None:
        """Admin-Wert setzen und die Aenderung im Verlauf festhalten, in einer Transaktion."""
        with self.db.get_session() as session:
            einfuegen = pg_insert(SchalterZeile).values(
                name=name, an=an, geaendert_am=func.now(), geaendert_von=admin
            )
            session.execute(
                einfuegen.on_conflict_do_update(
                    index_elements=[SchalterZeile.name],
                    set_={
                        "an": einfuegen.excluded.an,
                        "geaendert_am": einfuegen.excluded.geaendert_am,
                        "geaendert_von": einfuegen.excluded.geaendert_von,
                    },
                )
            )
            session.execute(
                insert(SchalterVerlaufZeile).values(
                    name=name, an=an, geaendert_am=func.now(), geaendert_von=admin
                )
            )


_repository: Optional[SchalterRepository] = None


def get_schalter_repository() -> SchalterRepository:
    """Die globale Instanz holen oder anlegen."""
    global _repository
    if _repository is None:
        _repository = SchalterRepository()
    return _repository
