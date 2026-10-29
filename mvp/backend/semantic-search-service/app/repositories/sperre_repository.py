"""
Repository fuer Sperren (Tabelle sperren, #448).

Was eine Sperre traegt und warum, steht am Modell (infrastructure/database/models.py,
``Sperre``); die Regeln dazu in services/moderation_service.py.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError

from domain.models.widerspruch import (
    PRUEFERGEBNIS_ENTSPERRT,
    PRUEFERGEBNIS_SPERRE_BLEIBT,
    Widerspruchsergebnis,
)
from infrastructure.database.connection import get_app_database
from infrastructure.database.models import Sperre


class SperreRepository:
    """Jede Methode ist eine Transaktion; get_session schreibt beim Verlassen fest."""

    def __init__(self):
        self.db = get_app_database()

    def anlegen(
        self,
        content_id: UUID,
        sperrgrund: str,
        begruendung: str,
        gesperrt_von: Optional[str],
        autor: Optional[str],
    ) -> Optional[Sperre]:
        """
        Eine Sperre anlegen. Gibt es schon eine aktive, bleibt sie, und es kommt None
        zurueck; auch wenn eine gleichzeitige Anfrage sie eben angelegt hat: Der
        eindeutige Index laesst nur eine zu.
        """
        with self.db.get_session() as session:
            if session.execute(self._aktiv(content_id)).scalar_one_or_none():
                return None
            sperre = Sperre(
                content_id=content_id,
                sperrgrund=sperrgrund,
                begruendung=begruendung,
                gesperrt_von=gesperrt_von,
                autor=autor,
            )
            try:
                with session.begin_nested():
                    session.add(sperre)
            except IntegrityError:
                return None
            session.refresh(sperre)
            session.expunge(sperre)
            return sperre

    def aktive(self, content_id: UUID) -> Optional[Sperre]:
        with self.db.get_session() as session:
            sperre = session.execute(self._aktiv(content_id)).scalar_one_or_none()
            if sperre is not None:
                session.expunge(sperre)
            return sperre

    def aktive_je_beitrag(self) -> Dict[UUID, Sperre]:
        """Alle aktiven Sperren, nach Beitrag."""
        abfrage = select(Sperre).where(Sperre.aufgehoben_am.is_(None))
        with self.db.get_session() as session:
            zeilen = session.execute(abfrage).scalars().all()
            session.expunge_all()
            return {z.content_id: z for z in zeilen}

    def fuer_autor(self, autor: str) -> List[Sperre]:
        """
        Die Sperren, von denen eine Person erfaehrt, die neueste zuerst: aktive und
        solche, die nach ihrem Widerspruch aufgehoben wurden. Die zweiten bleiben, bis
        ihre Frist sie loescht, damit sie das Ergebnis der Pruefung sieht.
        """
        abfrage = (
            select(Sperre)
            .where(
                Sperre.autor == autor,
                or_(
                    Sperre.aufgehoben_am.is_(None),
                    Sperre.pruefergebnis == PRUEFERGEBNIS_ENTSPERRT,
                ),
            )
            .order_by(Sperre.gesperrt_am.desc(), Sperre.id)
        )
        with self.db.get_session() as session:
            zeilen = session.execute(abfrage).scalars().all()
            session.expunge_all()
            return list(zeilen)

    def aufheben(
        self,
        content_id: UUID,
        von: Optional[str],
        jetzt: datetime,
        entsperrt: bool = True,
    ) -> bool:
        """
        Die aktive Sperre eines Beitrags aufheben. Beim Entsperren gilt ein offener
        Widerspruch damit als geprueft, mit dem Ergebnis "entsperrt"; wird der
        Beitrag endgueltig entfernt (entsperrt=False), bleibt er ohne Ergebnis.

        Returns:
            bool: False, wenn es keine aktive Sperre gab
        """
        with self.db.get_session() as session:
            sperre = session.execute(
                self._aktiv(content_id).with_for_update()
            ).scalar_one_or_none()
            if sperre is None:
                return False
            sperre.aufgehoben_am = jetzt
            if (
                entsperrt
                and sperre.widerspruch_am is not None
                and sperre.pruefergebnis is None
            ):
                sperre.pruefergebnis = PRUEFERGEBNIS_ENTSPERRT
                sperre.geprueft_von = von
                sperre.geprueft_am = jetzt
            return True

    def widersprechen(
        self, sperre_id: UUID, autor: str, text: Optional[str], jetzt: datetime
    ) -> Widerspruchsergebnis:
        """Einen Widerspruch gegen eine aktive Sperre eintragen; je Sperre einer."""
        abfrage = (
            select(Sperre)
            .where(
                Sperre.id == sperre_id,
                Sperre.autor == autor,
                Sperre.aufgehoben_am.is_(None),
            )
            .with_for_update()
        )
        with self.db.get_session() as session:
            sperre = session.execute(abfrage).scalar_one_or_none()
            if sperre is None:
                return Widerspruchsergebnis.NICHT_GEFUNDEN
            if sperre.widerspruch_am is not None:
                return Widerspruchsergebnis.SCHON_WIDERSPROCHEN
            sperre.widerspruch = text
            sperre.widerspruch_am = jetzt
            return Widerspruchsergebnis.ANGENOMMEN

    def sperre_bestaetigen(
        self, sperre_id: UUID, von: Optional[str], begruendung: str, jetzt: datetime
    ) -> bool:
        """
        Nach erneuter Pruefung bleibt die Sperre. Geht nur bei einem offenen
        Widerspruch gegen eine aktive Sperre.
        """
        with self.db.get_session() as session:
            ergebnis = session.execute(
                update(Sperre)
                .where(
                    Sperre.id == sperre_id,
                    Sperre.aufgehoben_am.is_(None),
                    Sperre.widerspruch_am.is_not(None),
                    Sperre.pruefergebnis.is_(None),
                )
                .values(
                    pruefergebnis=PRUEFERGEBNIS_SPERRE_BLEIBT,
                    pruefung_begruendung=begruendung,
                    geprueft_von=von,
                    geprueft_am=jetzt,
                )
            )
            return ergebnis.rowcount == 1

    def aufgehobene_loeschen_vor(self, grenze: datetime) -> int:
        """Sperren loeschen, die vor der Grenze aufgehoben wurden."""
        with self.db.get_session() as session:
            ergebnis = session.execute(
                delete(Sperre).where(Sperre.aufgehoben_am < grenze)
            )
            return ergebnis.rowcount

    @staticmethod
    def _aktiv(content_id: UUID):
        return select(Sperre).where(
            Sperre.content_id == content_id, Sperre.aufgehoben_am.is_(None)
        )


_repository: Optional[SperreRepository] = None


def get_sperre_repository() -> SperreRepository:
    global _repository
    if _repository is None:
        _repository = SperreRepository()
    return _repository
