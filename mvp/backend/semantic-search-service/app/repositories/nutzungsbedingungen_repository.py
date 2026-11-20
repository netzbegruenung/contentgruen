"""
Repository fuer die Tabelle ``nutzungsbedingungen_zustimmungen``: die Zustimmung zu den
Nutzungsbedingungen je Kennung (domain/nutzungsbedingungen.py).
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import func, insert, select, text

from domain.nutzungsbedingungen import geltender_stand
from infrastructure.database.connection import AppDatabase, get_app_database
from infrastructure.database.models import NutzungsbedingungenZustimmungZeile

# Schluessel der Advisory-Sperre je Person (eigener Raum neben SPERRE_ART9 = 489):
# Zwei Tabs, die gleichzeitig zustimmen, schreiben sonst zwei Zeilen.
SPERRE_NUTZUNGSBEDINGUNGEN = 305


@dataclass(frozen=True)
class NbZustimmung:
    stand: str
    zugestimmt_am: datetime

    @property
    def zaehlt(self) -> bool:
        """Zu einem Stand, dessen Zustimmung heute zaehlt (GELTENDE_STAENDE)."""
        return geltender_stand(self.stand)


class NutzungsbedingungenRepository:
    def __init__(self, db: Optional[AppDatabase] = None):
        """``db``: eine AppDatabase; ohne Angabe die globale."""
        self.db = db if db is not None else get_app_database()

    def lesen(self, user_id: str) -> Optional[NbZustimmung]:
        """Die juengste Zustimmung der Kennung, sonst None."""
        with self.db.get_session() as session:
            zeile = session.execute(
                select(
                    NutzungsbedingungenZustimmungZeile.stand,
                    NutzungsbedingungenZustimmungZeile.zugestimmt_am,
                )
                .where(NutzungsbedingungenZustimmungZeile.user_id == user_id)
                .order_by(NutzungsbedingungenZustimmungZeile.zugestimmt_am.desc())
                .limit(1)
            ).first()
            if zeile is None:
                return None
            return NbZustimmung(stand=zeile.stand, zugestimmt_am=zeile.zugestimmt_am)

    def zustimmen(self, user_id: str, stand: str) -> None:
        """
        Eine neue Zeile; fruehere bleiben als Nachweis. Ist die juengste schon eine
        Zustimmung zu diesem Stand, bleibt es bei ihr (doppeltes Absenden, zweiter Tab).
        """
        with self.db.get_session() as session:
            session.execute(
                text("SELECT pg_advisory_xact_lock(:sperre, hashtext(:kennung))"),
                {"sperre": SPERRE_NUTZUNGSBEDINGUNGEN, "kennung": user_id},
            )
            juengster = session.execute(
                select(NutzungsbedingungenZustimmungZeile.stand)
                .where(NutzungsbedingungenZustimmungZeile.user_id == user_id)
                .order_by(NutzungsbedingungenZustimmungZeile.zugestimmt_am.desc())
                .limit(1)
            ).scalar_one_or_none()
            if juengster == stand:
                return
            session.execute(
                insert(NutzungsbedingungenZustimmungZeile).values(
                    user_id=user_id, stand=stand, zugestimmt_am=func.now()
                )
            )


_repository: Optional[NutzungsbedingungenRepository] = None


def get_nutzungsbedingungen_repository() -> NutzungsbedingungenRepository:
    """Die globale Instanz holen oder anlegen."""
    global _repository
    if _repository is None:
        _repository = NutzungsbedingungenRepository()
    return _repository
