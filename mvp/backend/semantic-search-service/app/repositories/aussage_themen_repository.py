"""
Repository fuer die Themen an Aussagen (Tabelle aussage_themen).

Je (Aussage, Thema) eine Zeile mit der Zuordnungsart der Zuordnung. Was gespeichert wird
und warum nichts weiter: services/aussage_themen_service.py.
"""

import uuid
from collections import defaultdict
from typing import Dict, Iterable, List, Optional

from sqlalchemy import delete, select, text
from sqlalchemy.dialects.postgresql import insert

from infrastructure.database.connection import get_app_database
from domain.themen import Zuordnungsart
from infrastructure.database.models import AussageThemaZeile

# Erster Schluessel der Advisory-Sperre je Aussage. Die Form mit zwei Schluesseln
# hat einen eigenen Schluesselraum, getrennt von der Migrationssperre
# (infrastructure/database/migrationen.py, SPERRE).
SPERRE_THEMEN = 363


class AussageThemenRepository:
    def __init__(self):
        self.db = get_app_database()

    def setzen(
        self, statement_id: uuid.UUID, themen: List[str], zuordnungsart: Zuordnungsart
    ) -> None:
        """
        Die Themen einer Aussage ersetzen, in einer Transaktion. Eine Sperre je
        Aussage haelt zwei gleichzeitige Zuordnungen auseinander; sonst blieben
        die Themen beider stehen, mehr als zwei.
        """
        with self.db.get_session() as session:
            self._sperren(session, statement_id)
            session.execute(
                delete(AussageThemaZeile).where(
                    AussageThemaZeile.statement_id == statement_id
                )
            )
            self._einfuegen(session, statement_id, themen, zuordnungsart)
            session.commit()

    def ergaenzen(
        self, statement_id: uuid.UUID, themen: List[str], zuordnungsart: Zuordnungsart
    ) -> List[str]:
        """
        Die Themen einer Aussage setzen, nur wenn sie noch keine hat; liefert die,
        die sie danach hat. Pruefen und Setzen in einer Transaktion unter derselben
        Sperre wie `setzen`: Legen zwei Personen dieselbe Aussage gleichzeitig mit
        verschiedenen Themen an, bekommt sie die der ersten, und die zweite erfaehrt
        sie, statt sie zu ersetzen.
        """
        with self.db.get_session() as session:
            self._sperren(session, statement_id)
            bisher = list(
                session.execute(
                    select(AussageThemaZeile.thema).where(
                        AussageThemaZeile.statement_id == statement_id
                    )
                ).scalars()
            )
            if bisher:
                session.rollback()
                return bisher
            self._einfuegen(session, statement_id, themen, zuordnungsart)
            session.commit()
            return list(themen)

    @staticmethod
    def _sperren(session, statement_id: uuid.UUID) -> None:
        session.execute(
            text("SELECT pg_advisory_xact_lock(:sperre, hashtext(:id))"),
            {"sperre": SPERRE_THEMEN, "id": str(statement_id)},
        )

    @staticmethod
    def _einfuegen(
        session,
        statement_id: uuid.UUID,
        themen: List[str],
        zuordnungsart: Zuordnungsart,
    ) -> None:
        if themen:
            session.execute(
                insert(AussageThemaZeile).values(
                    [
                        {
                            "statement_id": statement_id,
                            "thema": t,
                            "zuordnungsart": str(zuordnungsart),
                        }
                        for t in themen
                    ]
                )
            )

    def themen_von(
        self, statement_ids: Iterable[uuid.UUID]
    ) -> Dict[uuid.UUID, List[str]]:
        """Die Themen je Aussage; Aussagen ohne Thema fehlen im Ergebnis."""
        ids = list(statement_ids)
        if not ids:
            return {}
        abfrage = select(AussageThemaZeile.statement_id, AussageThemaZeile.thema).where(
            AussageThemaZeile.statement_id.in_(ids)
        )
        return self._gruppiert(abfrage)

    def zuordnungen(self, zuordnungsart: Zuordnungsart) -> Dict[uuid.UUID, List[str]]:
        """Alle Zuordnungen einer Zuordnungsart, je Aussage."""
        abfrage = select(AussageThemaZeile.statement_id, AussageThemaZeile.thema).where(
            AussageThemaZeile.zuordnungsart == str(zuordnungsart)
        )
        return self._gruppiert(abfrage)

    def _gruppiert(self, abfrage) -> Dict[uuid.UUID, List[str]]:
        ergebnis: Dict[uuid.UUID, List[str]] = defaultdict(list)
        with self.db.get_session() as session:
            for statement_id, thema in session.execute(
                abfrage.order_by(
                    AussageThemaZeile.statement_id, AussageThemaZeile.thema
                )
            ).all():
                ergebnis[statement_id].append(thema)
        return dict(ergebnis)


_repository: Optional[AussageThemenRepository] = None


def get_aussage_themen_repository() -> AussageThemenRepository:
    global _repository
    if _repository is None:
        _repository = AussageThemenRepository()
    return _repository
