"""
Abfragen fuer die Punkte (#352) und die Meilensteine (#351): Zustimmung anderer zu
Beitraegen und ausformulierte Einwuerfe. Was daraus wird, steht in
services/punkte_service.py und services/meilensteine_service.py.
"""

import uuid
from datetime import date, datetime
from typing import Dict, List, Optional, Set

from sqlalchemy import bindparam, func, select

from infrastructure.database.connection import AppDatabase, get_app_database
from domain.models.einwurf import EinwurfStatus
from infrastructure.database.models import Einwurf, AusformuliertIn, Sperre
from repositories.vote_repository import OHNE_AUSGENOMMENE, ohne_ausgenommene


class PunkteRepository:
    def __init__(self, db: Optional[AppDatabase] = None):
        """``db``: eine AppDatabase; ohne Angabe die globale."""
        self.db = db if db is not None else get_app_database()

    def zustimmungen(self, content_ids: List[uuid.UUID], ausgenommen: Set[str]) -> int:
        """Zustimmungen zu diesen Beitraegen, ohne Stimmen der ausgenommenen Kennungen."""
        if not content_ids:
            return 0
        # votes legt vote_repository.py per Hand an; content_id ist dort UUID.
        abfrage, werte = ohne_ausgenommene(
            "SELECT count(*) FROM votes WHERE vote_type = 'like'"
            f" AND content_id IN :ids AND {OHNE_AUSGENOMMENE}",
            ausgenommen,
            ids=[str(i) for i in content_ids],
        )
        abfrage = abfrage.bindparams(bindparam("ids", expanding=True))
        with self.db.get_session() as session:
            return session.execute(abfrage, werte).scalar_one()

    def einwuerfe_ausformuliert_je_tag(
        self, user_id: str, bis: datetime
    ) -> Dict[date, int]:
        """
        Die Einwuerfe der Person, die in einem sichtbaren Beitrag ausformuliert sind,
        gezaehlt je UTC-Tag ihrer ersten Verknuepfung, die spaetestens ``bis``
        entstand (die Wartezeit wie beim Beitrag, services/punkte_service.py).

        Eine Verknuepfung mit einem gesperrten Beitrag zaehlt nicht; ein entfernter
        Beitrag nimmt seine Verknuepfung mit (ModerationService.delete_content).
        Ob ein verknuepfter Beitrag vom Autor geloescht ist, steht nur in Qdrant;
        bis zu seiner endgueltigen Entfernung zaehlt er hier mit.
        """
        gesperrt = (
            select(Sperre.content_id)
            .where(
                Sperre.content_id == AusformuliertIn.content_id,
                Sperre.aufgehoben_am.is_(None),
            )
            .exists()
        )
        erste = (
            select(
                func.min(AusformuliertIn.created_at)
                .op("AT TIME ZONE")("UTC")
                .label("am")
            )
            .join(Einwurf, Einwurf.id == AusformuliertIn.raw_input_id)
            .where(Einwurf.submitted_by == user_id, ~gesperrt)
            .group_by(AusformuliertIn.raw_input_id)
            .having(func.min(AusformuliertIn.created_at) <= bis)
            .subquery()
        )
        tag = func.date(erste.c.am)
        abfrage = select(tag, func.count()).group_by(tag)
        with self.db.get_session() as session:
            return {t: n for t, n in session.execute(abfrage)}

    def einwuerfe_ausformuliert_von(self, user_id: str, ausgenommen: Set[str]) -> int:
        """
        Wie viele Einwuerfe anderer die Person als Ausformulierer mit einem nicht
        gesperrten Beitrag verknuepft hat, je Einwurf einmal (Meilensteine, #351).
        Eigene Einwuerfe und die der ausgenommenen Kennungen (Startkonten) zaehlen
        nicht: Sonst liesse sich der Meilenstein mit selbst eingeworfenen Einwuerfen
        und einer Verknuepfung mit irgendeinem vorhandenen Beitrag erklicken.
        """
        bedingungen = [
            AusformuliertIn.created_by == user_id,
            Einwurf.submitted_by != user_id,
            ~self._gesperrt(),
        ]
        if ausgenommen:
            bedingungen.append(Einwurf.submitted_by.notin_(sorted(ausgenommen)))
        abfrage = (
            select(func.count(func.distinct(AusformuliertIn.raw_input_id)))
            .join(Einwurf, Einwurf.id == AusformuliertIn.raw_input_id)
            .where(*bedingungen)
        )
        with self.db.get_session() as session:
            return session.execute(abfrage).scalar_one()

    def eigene_einwuerfe_von_anderen_ausformuliert(
        self, user_id: str, ausgenommen: Set[str]
    ) -> int:
        """
        Wie viele Einwuerfe der Person jemand anderes mit einem nicht gesperrten
        Beitrag verknuepft hat (Meilensteine, #351). Verknuepfungen der Person selbst
        und der ausgenommenen Kennungen (Startkonten) zaehlen nicht.
        """
        bedingungen = [
            Einwurf.submitted_by == user_id,
            AusformuliertIn.created_by != user_id,
            ~self._gesperrt(),
        ]
        if ausgenommen:
            bedingungen.append(AusformuliertIn.created_by.notin_(sorted(ausgenommen)))
        abfrage = (
            select(func.count(func.distinct(AusformuliertIn.raw_input_id)))
            .join(Einwurf, Einwurf.id == AusformuliertIn.raw_input_id)
            .where(*bedingungen)
        )
        with self.db.get_session() as session:
            return session.execute(abfrage).scalar_one()

    def eigene_einwuerfe(self, user_id: str) -> int:
        """
        Wie viele Einwuerfe die Person eingeworfen hat, ohne verworfene (Wegmarke
        "Erster Einwurf", #351). Ein geloeschter Einwurf faellt mit seiner Zeile weg.
        """
        abfrage = select(func.count()).where(
            Einwurf.submitted_by == user_id,
            Einwurf.status != EinwurfStatus.DISCARDED.value,
        )
        with self.db.get_session() as session:
            return session.execute(abfrage).scalar_one()

    @staticmethod
    def _gesperrt():
        """Der verknuepfte Beitrag hat eine Sperre, die nicht aufgehoben ist."""
        return (
            select(Sperre.content_id)
            .where(
                Sperre.content_id == AusformuliertIn.content_id,
                Sperre.aufgehoben_am.is_(None),
            )
            .exists()
        )


_repository: Optional[PunkteRepository] = None


def get_punkte_repository() -> PunkteRepository:
    global _repository
    if _repository is None:
        _repository = PunkteRepository()
    return _repository
