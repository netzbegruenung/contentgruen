"""
"Suchen ohne Treffer" gegen ein echtes PostgreSQL (#243).

Die Unit-Tests pruefen das SQL nur als Text. Hier laeuft die Zaehlung durch
Service und Repository bis in die Tabelle, und die Admin-Liste kommt aus dem
echten HAVING: Eine Aussage erscheint erst ab zwei verschiedenen Personen.
Dazu laufen die beiden Migrationen auf einer Tabelle im alten Schema.

Jeder Test bekommt ein eigenes Schema und raeumt es wieder ab. Ohne erreichbares
PostgreSQL wird das Modul uebersprungen. Ziel ueber
``SUCHEN_OHNE_TREFFER_DATABASE_URL``, sonst der Dev-Stack (Port 5433).
"""

import os
import uuid
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from domain.models.content_status import ContentStatus
from infrastructure.database.models import Base, SucheOhneTrefferZeile
from repositories.suchen_ohne_treffer_repository import SuchenOhneTrefferRepository
from services.suchen_ohne_treffer_service import (
    PersonenDesTages,
    SuchenOhneTrefferService,
)

DATABASE_URL = os.environ.get(
    "SUCHEN_OHNE_TREFFER_DATABASE_URL",
    "postgresql+psycopg2://app_user:changeme@localhost:5433/gutgesagt_app",
)
REPO_WURZEL = next(p for p in Path(__file__).parents if (p / "mvp").is_dir())
MIGRATIONEN = REPO_WURZEL / "mvp" / "backend" / "postgres-app" / "migrations"
TABELLE = MIGRATIONEN / "2026-10-26-suchen-ohne-treffer.sql"
PERSONEN = MIGRATIONEN / "2026-10-26-suchen-ohne-treffer-personen.sql"

AUSSAGE = uuid.UUID("11111111-1111-1111-1111-111111111111")
# Mittwoch und Donnerstag derselben Woche, dazu ein Tag der Vorwoche.
MITTWOCH = date(2026, 10, 28)
DONNERSTAG = date(2026, 10, 29)
VORWOCHE = date(2026, 10, 21)
PERSON_A = "a" * 64
PERSON_B = "b" * 64


def _postgres_erreichbar() -> bool:
    try:
        engine = create_engine(DATABASE_URL, connect_args={"connect_timeout": 2})
        with engine.connect():
            return True
    except OperationalError:
        return False


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _postgres_erreichbar(), reason="PostgreSQL nicht erreichbar"
    ),
]


class _Datenbank:
    """Ein Wegwerf-Schema; ``get_session`` wie bei AppDatabase, fuer das Repository."""

    def __init__(self, schema: str):
        self.engine = create_engine(
            DATABASE_URL,
            poolclass=NullPool,
            connect_args={"options": f"-csearch_path={schema}"},
        )
        self.sessions = sessionmaker(bind=self.engine)

    @contextmanager
    def get_session(self):
        with self.sessions.begin() as session:
            yield session


@contextmanager
def _schema():
    schema = f"itest_sot_{uuid.uuid4().hex[:8]}"
    with create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT").connect() as c:
        c.execute(text(f"CREATE SCHEMA {schema}"))
    db = _Datenbank(schema)
    try:
        yield db
    finally:
        db.engine.dispose()
        with create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT").connect() as c:
            c.execute(text(f"DROP SCHEMA {schema} CASCADE"))


def _migration(db: _Datenbank, skript: Path) -> None:
    """Das Skript wie psql anwenden: BEGIN/COMMIT stehen darin selbst."""
    with db.engine.connect().execution_options(isolation_level="AUTOCOMMIT") as c:
        c.exec_driver_sql(skript.read_text(encoding="utf-8"))


@pytest.fixture
def neue_datenbank():
    """Schema, wie create_all es in einer neuen Datenbank anlegt."""
    with _schema() as db:
        Base.metadata.create_all(db.engine, tables=[SucheOhneTrefferZeile.__table__])
        yield db


@pytest.fixture
def bestehende_datenbank():
    """Tabelle im Schema von #216, mit einer schon gezaehlten Woche."""
    with _schema() as db:
        _migration(db, TABELLE)
        with db.engine.begin() as c:
            c.execute(
                text(
                    "INSERT INTO suchen_ohne_treffer (statement_id, woche, anzahl)"
                    " VALUES (:id, :woche, 5)"
                ),
                {"id": AUSSAGE, "woche": date(2026, 10, 26)},
            )
        yield db


def _service(db: _Datenbank) -> SuchenOhneTrefferService:
    with patch(
        "repositories.suchen_ohne_treffer_repository.get_app_database",
        return_value=db,
    ):
        repository = SuchenOhneTrefferRepository()
    aussagen = Mock()
    aussagen.get = AsyncMock(
        return_value=SimpleNamespace(
            id=AUSSAGE,
            text="Lohnt sich eine Waermepumpe im Altbau?",
            status=ContentStatus.RELEASED_INTERNAL,
        )
    )
    return SuchenOhneTrefferService(repository, aussagen, PersonenDesTages())


async def _liste(service: SuchenOhneTrefferService):
    return [
        (e.statement_id, e.anzahl)
        for e in await service.haeufigste(wochen=4, heute=DONNERSTAG)
    ]


@pytest.mark.asyncio
class TestMindestanzahlZaehltPersonen:
    async def test_eine_person_mehrfach_am_selben_tag_erscheint_nicht(
        self, neue_datenbank
    ):
        service = _service(neue_datenbank)

        for _ in range(3):
            service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)

        assert await _liste(service) == []

    async def test_zwei_personen_erscheinen_mit_der_zahl_der_suchen(
        self, neue_datenbank
    ):
        service = _service(neue_datenbank)

        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, PERSON_B, heute=MITTWOCH)

        assert await _liste(service) == [(AUSSAGE, 3)]

    async def test_ohne_pseudonym_zaehlt_keine_person(self, neue_datenbank):
        service = _service(neue_datenbank)

        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, None, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, None, heute=MITTWOCH)

        assert await _liste(service) == []

    async def test_personen_verschiedener_wochen_werden_summiert(self, neue_datenbank):
        """Zwei Wochen mit je einer Person ergeben zwei Personen im Zeitraum."""
        service = _service(neue_datenbank)

        service.erfassen(AUSSAGE, 0, PERSON_A, heute=VORWOCHE)
        service.erfassen(AUSSAGE, 0, PERSON_B, heute=MITTWOCH)

        assert await _liste(service) == [(AUSSAGE, 2)]

    async def test_dieselbe_person_an_zwei_tagen_zaehlt_zweimal(self, neue_datenbank):
        """
        Der benannte Restfall: Die Merkliste beginnt jeden Tag neu (und das echte
        Tagespseudonym wechselt mit dem Datum ohnehin).
        """
        service = _service(neue_datenbank)

        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, PERSON_A, heute=DONNERSTAG)

        assert await _liste(service) == [(AUSSAGE, 2)]


@pytest.mark.asyncio
class TestMigration:
    async def test_bestehende_zeilen_bekommen_null_personen(self, bestehende_datenbank):
        _migration(bestehende_datenbank, PERSONEN)
        service = _service(bestehende_datenbank)

        assert await _liste(service) == []
        service.erfassen(AUSSAGE, 0, PERSON_A, heute=MITTWOCH)
        service.erfassen(AUSSAGE, 0, PERSON_B, heute=MITTWOCH)
        assert await _liste(service) == [(AUSSAGE, 7)]

    def test_migration_darf_mehrfach_laufen(self, bestehende_datenbank):
        _migration(bestehende_datenbank, PERSONEN)
        _migration(bestehende_datenbank, PERSONEN)

        with bestehende_datenbank.engine.connect() as c:
            assert c.execute(
                text("SELECT anzahl, personen FROM suchen_ohne_treffer")
            ).all() == [(5, 0)]

    def test_migration_ergibt_dasselbe_schema_wie_create_all(
        self, bestehende_datenbank, neue_datenbank
    ):
        _migration(bestehende_datenbank, PERSONEN)
        abfrage = text(
            "SELECT column_name, data_type, is_nullable, column_default"
            " FROM information_schema.columns"
            " WHERE table_schema = current_schema()"
            " AND table_name = 'suchen_ohne_treffer' ORDER BY column_name"
        )

        with bestehende_datenbank.engine.connect() as alt:
            spalten_alt = alt.execute(abfrage).all()
        with neue_datenbank.engine.connect() as neu:
            spalten_neu = neu.execute(abfrage).all()

        assert spalten_alt == spalten_neu
