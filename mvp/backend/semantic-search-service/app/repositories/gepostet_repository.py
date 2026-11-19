"""
Repository fuer die Rueckmeldung "Gepostet?" (#643): Pruefwerte der laufenden
Kalenderwoche (``gepostet_pruefwerte``) und die Zahl je vergangener Woche
(``gepostet_wochen``). Wie die Pruefwerte entstehen: services/gepostet_service.py.
"""

from datetime import date
from typing import Dict, Optional

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert

from infrastructure.database.connection import AppDatabase, get_app_database
from infrastructure.database.models import GepostetPruefwert, GepostetWoche
from utils.utc_tag import heute_utc, wochenbeginn

# Loeschen und Zaehlen in einer Anweisung: Die Zeilensperren des DELETE verhindern,
# dass zwei gleichzeitige Laeufe dieselbe Woche zweimal hochzaehlen.
_VERDICHTEN = text(
    """
    WITH weg AS (
        DELETE FROM gepostet_pruefwerte WHERE woche < :woche RETURNING woche
    )
    INSERT INTO gepostet_wochen (woche, personen)
    SELECT woche, count(*) FROM weg GROUP BY woche
    ON CONFLICT (woche)
    DO UPDATE SET personen = gepostet_wochen.personen + EXCLUDED.personen
    """
)


class GepostetRepository:
    def __init__(self, db: Optional[AppDatabase] = None):
        """``db``: eine AppDatabase; ohne Angabe die globale."""
        self.db = db if db is not None else get_app_database()

    @staticmethod
    def _verdichten(session, woche: date) -> None:
        """Pruefwerte der Wochen vor ``woche`` zur Zahl je Woche machen und loeschen."""
        session.execute(_VERDICHTEN, {"woche": woche})

    @staticmethod
    def _anzahl(session, woche: date) -> int:
        return session.execute(
            select(func.count())
            .select_from(GepostetPruefwert)
            .where(GepostetPruefwert.woche == woche)
        ).scalar_one()

    def vergangene_wochen_verdichten(self, heute: Optional[date] = None) -> None:
        """Fuer den taeglichen Task (services/entdoppelung.py): alles vor dieser Woche verdichten."""
        with self.db.get_session() as session:
            self._verdichten(session, wochenbeginn(heute or heute_utc()))

    def melden(self, pruefwert: str, woche: date) -> int:
        """
        Den Pruefwert fuer ``woche`` merken (ein zweites Mal aendert nichts) und die
        Zahl der verschiedenen Personen dieser Woche zurueckgeben.
        """
        with self.db.get_session() as session:
            self._verdichten(session, woche)
            session.execute(
                insert(GepostetPruefwert)
                .values(pruefwert=pruefwert, woche=woche)
                .on_conflict_do_nothing(index_elements=["pruefwert"])
            )
            return self._anzahl(session, woche)

    def anzahl(self, woche: date) -> int:
        """Wie viele verschiedene Personen in ``woche`` gemeldet haben (laufende Woche)."""
        with self.db.get_session() as session:
            return self._anzahl(session, woche)

    def wochen(self, von: date, laufende: date) -> Dict[date, int]:
        """
        Die Zahl je Woche von ``von`` bis zur laufenden Woche, nur Wochen mit Meldungen;
        verdichtet vorher, was aus vergangenen Wochen noch als Pruefwert liegt.
        """
        with self.db.get_session() as session:
            self._verdichten(session, laufende)
            zahlen = {
                zeile.woche: zeile.personen
                for zeile in session.execute(
                    select(GepostetWoche.woche, GepostetWoche.personen).where(
                        GepostetWoche.woche >= von
                    )
                )
            }
            laufend = self._anzahl(session, laufende)
            if laufend:
                zahlen[laufende] = laufend
            return zahlen


_repository: Optional[GepostetRepository] = None


def get_gepostet_repository() -> GepostetRepository:
    global _repository
    if _repository is None:
        _repository = GepostetRepository()
    return _repository
