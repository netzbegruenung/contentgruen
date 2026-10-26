"""
Frist der Suchereignisse gegen ein echtes PostgreSQL (#289).

Suchereignisse vor der Frist werden zu Tageszaehlern verdichtet (Tag, Zahl der
Suchen, Zahl der Personen) und die Einzelzeilen geloescht. Die Kennzahlen zaehlen
die Tageszaehler mit, damit sie ueber die Frist hinaus stimmen. Dazu die Migration:
Sie muss dasselbe Schema anlegen wie create_all.

Jeder Test bekommt ein eigenes Schema und raeumt es wieder ab. Ohne erreichbares
PostgreSQL wird das Modul uebersprungen. Ziel ueber
``SUCHEREIGNISSE_DATABASE_URL``, sonst der Dev-Stack (Port 5433).
"""

import os
import uuid
from contextlib import contextmanager
from datetime import date, datetime, time, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from infrastructure.database.models import Base, SearchEvent, SuchenJeTagZeile
from repositories.search_tracking_repository import SearchTrackingRepository

DATABASE_URL = os.environ.get(
    "SUCHEREIGNISSE_DATABASE_URL",
    "postgresql+psycopg2://app_user:changeme@localhost:5433/gutgesagt_app",
)
REPO_WURZEL = next(p for p in Path(__file__).parents if (p / "mvp").is_dir())
MIGRATION = (
    REPO_WURZEL
    / "mvp"
    / "backend"
    / "postgres-app"
    / "migrations"
    / "2026-10-26-suchereignisse-tageszaehler.sql"
)

HEUTE = date(2026, 10, 27)
# Mit Frist 90 ist der 29.07. der aelteste Tag, der als Einzelzeilen bleibt.
ALT = date(2026, 7, 28)
NOCH_IN_FRIST = date(2026, 7, 29)
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
        session = self.sessions()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


@contextmanager
def _schema():
    schema = f"itest_ste_{uuid.uuid4().hex[:8]}"
    with create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT").connect() as c:
        c.execute(text(f"CREATE SCHEMA {schema}"))
    db = _Datenbank(schema)
    try:
        yield db, schema
    finally:
        db.engine.dispose()
        with create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT").connect() as c:
            c.execute(text(f"DROP SCHEMA {schema} CASCADE"))


@pytest.fixture
def db():
    with _schema() as (datenbank, _):
        Base.metadata.create_all(
            datenbank.engine,
            tables=[SearchEvent.__table__, SuchenJeTagZeile.__table__],
        )
        yield datenbank


def _repository(datenbank: _Datenbank) -> SearchTrackingRepository:
    with patch(
        "repositories.search_tracking_repository.get_app_database",
        return_value=datenbank,
    ):
        return SearchTrackingRepository()


def _suche(datenbank: _Datenbank, tag: date, actor_hash, treffer: int = 3) -> None:
    with datenbank.engine.begin() as c:
        c.execute(
            text(
                "INSERT INTO search_events (actor_hash, results_count, timestamp)"
                " VALUES (:actor, :treffer, :zeit)"
            ),
            {
                "actor": actor_hash,
                "treffer": treffer,
                "zeit": datetime.combine(tag, time.min, tzinfo=timezone.utc),
            },
        )


def _tageszaehler(datenbank: _Datenbank):
    with datenbank.engine.connect() as c:
        return c.execute(
            text("SELECT tag, suchen, personen FROM suchen_je_tag ORDER BY tag")
        ).all()


def _suchereignis_tage(datenbank: _Datenbank):
    with datenbank.engine.connect() as c:
        return sorted(
            r[0].date()
            for r in c.execute(
                text("SELECT timestamp AT TIME ZONE 'UTC' FROM search_events")
            )
        )


class TestVerdichteAlteSuchereignisse:
    def test_verdichte_alte_suchereignisse_tage_vor_der_frist_werden_tageszaehler(
        self, db
    ):
        for actor in (PERSON_A, PERSON_A, PERSON_B, None):
            _suche(db, ALT, actor)
        _suche(db, NOCH_IN_FRIST, PERSON_A)

        geloescht = _repository(db).verdichte_alte_suchereignisse(90, heute=HEUTE)

        assert geloescht == 4
        assert _tageszaehler(db) == [(ALT, 4, 2)]
        assert _suchereignis_tage(db) == [NOCH_IN_FRIST]

    def test_verdichte_alte_suchereignisse_zweiter_lauf_aendert_nichts(self, db):
        _suche(db, ALT, PERSON_A)
        repository = _repository(db)
        repository.verdichte_alte_suchereignisse(90, heute=HEUTE)

        assert repository.verdichte_alte_suchereignisse(90, heute=HEUTE) == 0
        assert _tageszaehler(db) == [(ALT, 1, 1)]

    def test_verdichte_alte_suchereignisse_ohne_alte_kein_tageszaehler(self, db):
        _suche(db, NOCH_IN_FRIST, PERSON_A)

        assert _repository(db).verdichte_alte_suchereignisse(90, heute=HEUTE) == 0
        assert _tageszaehler(db) == []


class TestKennzahlenUeberDieFrist:
    """Personen und Suchen eines Zeitraums: Tageszaehler plus Einzelzeilen."""

    def _verdichtet(self, db):
        for actor in (PERSON_A, PERSON_B, PERSON_B):
            _suche(db, ALT, actor)
        for actor in (PERSON_A, PERSON_A):
            _suche(db, NOCH_IN_FRIST, actor)
        repository = _repository(db)
        repository.verdichte_alte_suchereignisse(90, heute=HEUTE)
        return repository

    def test_get_unique_active_users_zaehlt_tageszaehler_mit(self, db):
        repository = self._verdichtet(db)

        personen = repository.get_unique_active_users(
            datetime(2026, 7, 1), datetime(2026, 8, 1)
        )

        assert personen == 2 + 1

    def test_get_search_count_by_period_zaehlt_tageszaehler_mit(self, db):
        repository = self._verdichtet(db)

        suchen = repository.get_search_count_by_period(
            datetime(2026, 7, 1), datetime(2026, 8, 1)
        )

        assert suchen == 3 + 2

    def test_get_unique_active_users_tageszaehler_ausserhalb_zaehlt_nicht(self, db):
        repository = self._verdichtet(db)

        assert (
            repository.get_unique_active_users(
                datetime(2026, 7, 29), datetime(2026, 7, 29, 23, 59, 59)
            )
            == 1
        )

    def test_get_search_count_by_period_tageszaehler_ausserhalb_zaehlt_nicht(self, db):
        repository = self._verdichtet(db)

        assert (
            repository.get_search_count_by_period(
                datetime(2026, 7, 28, 12), datetime(2026, 8, 1)
            )
            == 2
        )


def _spalten(datenbank: _Datenbank, schema: str):
    with datenbank.engine.connect() as c:
        return c.execute(
            text(
                "SELECT column_name, data_type, is_nullable, column_default"
                " FROM information_schema.columns"
                " WHERE table_schema = :s AND table_name = 'suchen_je_tag'"
                " ORDER BY column_name"
            ),
            {"s": schema},
        ).all()


def _primaerschluessel(datenbank: _Datenbank, schema: str):
    with datenbank.engine.connect() as c:
        return c.execute(
            text(
                "SELECT kcu.column_name FROM information_schema.table_constraints tc"
                " JOIN information_schema.key_column_usage kcu"
                "   ON tc.constraint_name = kcu.constraint_name"
                "  AND tc.table_schema = kcu.table_schema"
                " WHERE tc.table_schema = :s AND tc.table_name = 'suchen_je_tag'"
                "   AND tc.constraint_type = 'PRIMARY KEY'"
            ),
            {"s": schema},
        ).all()


def test_migration_legt_dasselbe_schema_an_wie_create_all():
    with _schema() as (neu, schema_neu), _schema() as (migriert, schema_migriert):
        Base.metadata.create_all(neu.engine, tables=[SuchenJeTagZeile.__table__])
        for _ in range(2):  # idempotent
            with migriert.engine.connect().execution_options(
                isolation_level="AUTOCOMMIT"
            ) as c:
                c.exec_driver_sql(MIGRATION.read_text(encoding="utf-8"))

        assert _spalten(migriert, schema_migriert) == _spalten(neu, schema_neu)
        assert _primaerschluessel(migriert, schema_migriert) == _primaerschluessel(
            neu, schema_neu
        )
