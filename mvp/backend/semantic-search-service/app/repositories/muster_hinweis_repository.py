"""
Repository fuer Muster-Hinweise (Tabelle muster_hinweise, #352).

Was ein Muster-Hinweis ist und wie lange er bleibt, steht in
services/muster_hinweise_service.py.
"""

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from sqlalchemy import delete, desc, exists, func, select
from sqlalchemy.dialects.postgresql import insert

from infrastructure.database.connection import AppDatabase, get_app_database
from infrastructure.database.models import MusterHinweisZeile, NutzungHeute


@dataclass(frozen=True)
class MusterHinweis:
    konto_a: str
    konto_b: str
    tage: int
    erster_tag: date
    letzter_tag: date


class MusterHinweisRepository:
    def __init__(self, db: Optional[AppDatabase] = None):
        """``db``: eine AppDatabase; ohne Angabe die globale."""
        self.db = db if db is not None else get_app_database()

    def nutzung_merken(
        self, hin: str, rueck: str, nutzende: str, autor: str, tag: date
    ) -> bool:
        """
        Merkt sich fuer den Tag den Pruefwert ``hin`` (``nutzende`` hat einen Beitrag
        von ``autor`` genutzt). Steht ``rueck`` schon da, haben sich beide heute
        gegenseitig genutzt: Dann zaehlt der Hinweis zum Paar diesen Tag, hoechstens
        einmal. Liefert, ob das Paar heute gegenseitig war.
        """
        konto_a, konto_b = sorted([nutzende, autor])
        with self.db.get_session() as session:
            # Je Paar nacheinander: Kaemen A->B und B->A gleichzeitig, saehe sonst
            # keine der beiden Transaktionen den noch nicht festgeschriebenen
            # Pruefwert der anderen, und der Tag ginge verloren.
            session.execute(
                select(
                    func.pg_advisory_xact_lock(func.hashtext(f"{konto_a}|{konto_b}"))
                )
            )
            session.execute(
                insert(NutzungHeute)
                .values(pruefwert=hin, tag=tag)
                .on_conflict_do_nothing(index_elements=["pruefwert"])
            )
            gegenseitig = session.execute(
                select(exists().where(NutzungHeute.pruefwert == rueck))
            ).scalar()
            if not gegenseitig:
                return False
            neuer_tag = MusterHinweisZeile.letzter_tag < tag
            session.execute(
                insert(MusterHinweisZeile)
                .values(
                    konto_a=konto_a,
                    konto_b=konto_b,
                    tage=1,
                    erster_tag=tag,
                    letzter_tag=tag,
                )
                .on_conflict_do_update(
                    index_elements=["konto_a", "konto_b"],
                    set_={"tage": MusterHinweisZeile.tage + 1, "letzter_tag": tag},
                    where=neuer_tag,
                )
            )
            return True

    def hinweise(self, limit: int) -> List[MusterHinweis]:
        """Die zuletzt aufgefallenen zuerst, bei gleichem Tag die mit mehr Tagen."""
        abfrage = (
            select(MusterHinweisZeile)
            .order_by(
                desc(MusterHinweisZeile.letzter_tag),
                desc(MusterHinweisZeile.tage),
                MusterHinweisZeile.konto_a,
                MusterHinweisZeile.konto_b,
            )
            .limit(limit)
        )
        with self.db.get_session() as session:
            return [
                MusterHinweis(z.konto_a, z.konto_b, z.tage, z.erster_tag, z.letzter_tag)
                for z in session.execute(abfrage).scalars()
            ]

    def loeschen_vor(self, tag: date) -> int:
        """Hinweise, deren letzter Tag vor ``tag`` liegt, loeschen."""
        with self.db.get_session() as session:
            return session.execute(
                delete(MusterHinweisZeile).where(MusterHinweisZeile.letzter_tag < tag)
            ).rowcount


_repository: Optional[MusterHinweisRepository] = None


def get_muster_hinweis_repository() -> MusterHinweisRepository:
    global _repository
    if _repository is None:
        _repository = MusterHinweisRepository()
    return _repository
