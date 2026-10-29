"""
Repository fuer Einladungen (Tabelle einladungen, #429).

Was gespeichert wird und warum nicht mehr, steht in services/einladung_service.py.
"""

import uuid
from datetime import date
from typing import List, Optional

from sqlalchemy import desc, select, update

from infrastructure.database.connection import get_app_database
from infrastructure.database.models import EinladungZeile


class EinladungRepository:
    # Festgeschrieben wird beim Verlassen von get_session (connection.py), nicht hier.
    def __init__(self):
        self.db = get_app_database()

    def anlegen(
        self,
        code: str,
        notiz: str,
        erlaubte_konten: int,
        gueltig_bis: date,
        angelegt_am: date,
    ) -> EinladungZeile:
        with self.db.get_session() as session:
            zeile = EinladungZeile(
                code=code,
                notiz=notiz,
                erlaubte_konten=erlaubte_konten,
                angelegte_konten=0,
                gueltig_bis=gueltig_bis,
                abgeschaltet=False,
                angelegt_am=angelegt_am,
            )
            session.add(zeile)
            session.flush()
            session.refresh(zeile)
            session.expunge(zeile)
            return zeile

    def alle(self) -> List[EinladungZeile]:
        """Die neuesten zuerst; am selben Tag in fester Reihenfolge."""
        abfrage = select(EinladungZeile).order_by(
            desc(EinladungZeile.angelegt_am), EinladungZeile.id
        )
        with self.db.get_session() as session:
            zeilen = session.execute(abfrage).scalars().all()
            session.expunge_all()
            return list(zeilen)

    def nach_code(self, code: str) -> Optional[EinladungZeile]:
        with self.db.get_session() as session:
            zeile = session.execute(
                select(EinladungZeile).where(EinladungZeile.code == code)
            ).scalar_one_or_none()
            if zeile is not None:
                session.expunge(zeile)
            return zeile

    def abschalten(
        self, einladung_id: uuid.UUID, abgeschaltet: bool
    ) -> Optional[EinladungZeile]:
        with self.db.get_session() as session:
            zeile = session.get(EinladungZeile, einladung_id)
            if zeile is None:
                return None
            zeile.abgeschaltet = abgeschaltet
            session.flush()
            session.refresh(zeile)
            session.expunge(zeile)
            return zeile

    def platz_belegen(self, code: str, heute: date) -> bool:
        """
        Zaehlt ein Konto hoch, wenn die Einladung noch aktiv ist. In einer einzigen
        UPDATE-Anweisung, damit zwei gleichzeitige Anfragen den letzten Platz nicht
        beide bekommen.
        """
        with self.db.get_session() as session:
            ergebnis = session.execute(
                update(EinladungZeile)
                .where(
                    EinladungZeile.code == code,
                    EinladungZeile.abgeschaltet.is_(False),
                    EinladungZeile.gueltig_bis >= heute,
                    EinladungZeile.angelegte_konten < EinladungZeile.erlaubte_konten,
                )
                .values(angelegte_konten=EinladungZeile.angelegte_konten + 1)
            )
            return ergebnis.rowcount == 1

    def platz_freigeben(self, code: str) -> None:
        """Nimmt einen belegten Platz zurueck, wenn kein Konto entstand."""
        with self.db.get_session() as session:
            session.execute(
                update(EinladungZeile)
                .where(
                    EinladungZeile.code == code,
                    EinladungZeile.angelegte_konten > 0,
                )
                .values(angelegte_konten=EinladungZeile.angelegte_konten - 1)
            )


_repository: Optional[EinladungRepository] = None


def get_einladung_repository() -> EinladungRepository:
    global _repository
    if _repository is None:
        _repository = EinladungRepository()
    return _repository
