"""
Frist der Suchereignisse gegen ein echtes PostgreSQL (#289).

Suchereignisse vor der Frist werden zu Tageszaehlern verdichtet (Tag, Zahl der
Suchen, Zahl der Personen) und die Einzelzeilen geloescht. Die Kennzahlen zaehlen
die Tageszaehler mit, damit sie ueber die Frist hinaus stimmen. Datenbank und
Wegwerf-Schema kommen aus ``tests/integration/postgres.py``; dass die Migration
dasselbe Schema anlegt wie create_all, prueft ``test_migrationen.py``.
"""

from datetime import date, datetime, time, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import text

from infrastructure.database.models import Base, SearchEvent, SuchenJeTagZeile
from repositories.search_tracking_repository import SearchTrackingRepository
from tests.integration.postgres import Datenbank

pytestmark = pytest.mark.integration

HEUTE = date(2026, 10, 27)
# Mit Frist 90 ist der 29.07. der aelteste Tag, der als Einzelzeilen bleibt.
ALT = date(2026, 7, 28)
NOCH_IN_FRIST = date(2026, 7, 29)
PERSON_A = "a" * 64
PERSON_B = "b" * 64


@pytest.fixture
def db(wegwerf_schema):
    Base.metadata.create_all(
        wegwerf_schema.engine,
        tables=[SearchEvent.__table__, SuchenJeTagZeile.__table__],
    )
    return wegwerf_schema


def _repository(datenbank: Datenbank) -> SearchTrackingRepository:
    with patch(
        "repositories.search_tracking_repository.get_app_database",
        return_value=datenbank,
    ):
        return SearchTrackingRepository()


def _suche(datenbank: Datenbank, tag: date, actor_hash, treffer: int = 3) -> None:
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


def _tageszaehler(datenbank: Datenbank):
    with datenbank.engine.connect() as c:
        return c.execute(
            text("SELECT tag, suchen, personen FROM suchen_je_tag ORDER BY tag")
        ).all()


def _suchereignis_tage(datenbank: Datenbank):
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

    @pytest.mark.parametrize("zeitzone", ["Pacific/Kiritimati", "Pacific/Pago_Pago"])
    def test_verdichte_alte_suchereignisse_unabhaengig_von_der_zeitzone(
        self, db, zeitzone
    ):
        _suche(db, ALT, PERSON_A)
        _suche(db, NOCH_IN_FRIST, PERSON_A)

        with db.mit_zeitzone(zeitzone) as in_zone:
            geloescht = _repository(in_zone).verdichte_alte_suchereignisse(
                90, heute=HEUTE
            )

        assert geloescht == 1
        assert _tageszaehler(db) == [(ALT, 1, 1)]
        assert _suchereignis_tage(db) == [NOCH_IN_FRIST]

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
