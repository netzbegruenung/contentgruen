"""
Vormoderation unbeantworteter Suchanfragen (Entscheidung des Maintainers vom
13.11.2026) gegen ein echtes PostgreSQL: Entscheidungen speichern und ersetzen,
die Auswahl fuer Nicht-Admins aus Schwelle und Freigabe, und dass die Migration
nichts freigibt (auch der Bestand geht durch die Vormoderation).
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import text

from domain.models.content_origin import ContentOrigin
from domain.models.content_status import ContentStatus
from infrastructure.database.models import (
    Base,
    SuchanfrageFreigabe,
    SucheOhneTrefferZeile,
)
from repositories.suchanfrage_freigabe_repository import (
    SuchanfrageFreigabeRepository,
)
from repositories.suchen_ohne_treffer_repository import SuchenOhneTrefferRepository
from services.suchen_ohne_treffer_service import (
    PersonenDesTages,
    SuchenOhneTrefferService,
)
from tests.integration import postgres
from tests.integration.postgres import Datenbank
from utils.utc_tag import heute_utc, wochenbeginn

MIGRATION = postgres.MIGRATIONEN / "2026-11-13-suchanfrage-freigaben.sql"

A, B, C, D = (uuid.UUID(int=n) for n in range(1, 5))
WOCHE = wochenbeginn(heute_utc())

pytestmark = pytest.mark.integration


@pytest.fixture
def db(postgres_url):
    """Schema, wie create_all es anlegt: create_all laeuft vor den Migrationen."""
    with postgres.schema(postgres_url, "itest_vormod") as db:
        Base.metadata.create_all(
            db.engine,
            tables=[SucheOhneTrefferZeile.__table__, SuchanfrageFreigabe.__table__],
        )
        yield db


def _zaehlen(db: Datenbank, statement_id, woche, personen):
    with db.engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO suchen_ohne_treffer (statement_id, woche, anzahl, personen)"
                " VALUES (:id, :woche, :personen, :personen)"
            ),
            {"id": statement_id, "woche": woche, "personen": personen},
        )


def _freigaben(db: Datenbank) -> dict:
    with db.engine.connect() as c:
        return dict(
            c.execute(
                text("SELECT statement_id, freigegeben FROM suchanfrage_freigaben")
            ).all()
        )


def _repositories(db: Datenbank):
    with patch(
        "repositories.suchen_ohne_treffer_repository.get_app_database",
        return_value=db,
    ), patch(
        "repositories.suchanfrage_freigabe_repository.get_app_database",
        return_value=db,
    ):
        return SuchenOhneTrefferRepository(), SuchanfrageFreigabeRepository()


def _service(db: Datenbank) -> SuchenOhneTrefferService:
    zaehler, freigaben = _repositories(db)
    aussagen = Mock()
    aussagen.get = AsyncMock(
        side_effect=lambda statement_id: SimpleNamespace(
            id=statement_id,
            text=f"Suchanfrage {statement_id.int}",
            status=ContentStatus.VISIBLE,
            origin=ContentOrigin.SEARCH_QUERY,
            replysuggestions_count=0,
        )
    )
    return SuchenOhneTrefferService(zaehler, aussagen, PersonenDesTages(), freigaben)


class TestKeinNachtrag:
    def test_bestand_ueber_der_schwelle_bleibt_ungeprueft(self, db):
        _zaehlen(db, A, WOCHE, 2)

        postgres.migration(db, MIGRATION)
        postgres.migration(db, MIGRATION)

        assert _freigaben(db) == {}


@pytest.mark.asyncio
class TestVormoderation:
    async def test_erst_freigegeben_fuer_alle_sichtbar(self, db):
        _zaehlen(db, A, WOCHE, 3)
        _zaehlen(db, B, WOCHE, 2)
        _zaehlen(db, C, WOCHE, 1)
        service = _service(db)

        assert await service.sichtbar_fuer_alle() == set()
        assert [e.statement_id for e in await service.zu_pruefen()] == [A, B]

        await service.entscheiden(A, True)
        await service.entscheiden(B, False)

        assert await service.sichtbar_fuer_alle() == {A}
        assert await service.zu_pruefen() == []

    async def test_spaetere_entscheidung_ersetzt_die_fruehere(self, db):
        _zaehlen(db, A, WOCHE, 2)
        service = _service(db)

        await service.entscheiden(A, False)
        await service.entscheiden(A, True)

        assert _freigaben(db) == {A: True}
        assert await service.sichtbar_fuer_alle() == {A}

    async def test_freigegeben_unter_der_schwelle_bleibt_unsichtbar(self, db):
        _zaehlen(db, A, WOCHE, 1)
        service = _service(db)

        await service.entscheiden(A, True)

        assert await service.sichtbar_fuer_alle() == set()
