"""
Verdichten der Suchereignisse gegen ein echtes PostgreSQL (#289, #495).

Suchereignisse abgeschlossener Tage werden zu Tageszaehlern verdichtet (Tag, Zahl
der Suchen, der Suchen ohne Treffer und der Personen) und die Einzelzeilen samt
Tagespseudonym geloescht; nur der laufende Tag bleibt als Einzelzeilen. Die
Kennzahlen zaehlen die Tageszaehler mit. Datenbank und
Wegwerf-Schema kommen aus ``tests/integration/postgres.py``; dass die Migration
dasselbe Schema anlegt wie create_all, prueft ``test_migrationen.py``.
"""

from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy import text

from infrastructure.database.models import Base, SuchenJeTagZeile
from tests.integration.suchereignis_helfer import suchtracking_repository
from tests.integration.postgres import Datenbank

pytestmark = pytest.mark.integration

# Der laufende Tag; alles davor ist abgeschlossen.
HEUTE = date(2026, 7, 29)
GESTERN = date(2026, 7, 28)
MITTERNACHT = datetime.combine(HEUTE, time.min, tzinfo=timezone.utc)
PERSON_A = "a" * 64
PERSON_B = "b" * 64


@pytest.fixture
def db(suchereignisse_db):
    """Dazu die Tageszaehler (suchen_je_tag)."""
    Base.metadata.create_all(
        suchereignisse_db.engine, tables=[SuchenJeTagZeile.__table__]
    )
    return suchereignisse_db


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


class TestVerdichtenVor:
    def test_verdichten_vor_abgeschlossene_tage_werden_tageszaehler(self, db):
        for actor in (PERSON_A, PERSON_A, PERSON_B, None):
            _suche(db, GESTERN, actor)
        _suche(db, HEUTE, PERSON_A)

        geloescht = suchtracking_repository(db).verdichten_vor(MITTERNACHT)

        assert geloescht == 4
        assert _tageszaehler(db) == [(GESTERN, 4, 2)]
        assert _suchereignis_tage(db) == [HEUTE]

    def test_verdichten_vor_zweiter_lauf_aendert_nichts(self, db):
        _suche(db, GESTERN, PERSON_A)
        repository = suchtracking_repository(db)
        repository.verdichten_vor(MITTERNACHT)

        assert repository.verdichten_vor(MITTERNACHT) == 0
        assert _tageszaehler(db) == [(GESTERN, 1, 1)]

    @pytest.mark.parametrize("zeitzone", ["Pacific/Kiritimati", "Pacific/Pago_Pago"])
    def test_verdichten_vor_unabhaengig_von_der_zeitzone(self, db, zeitzone):
        _suche(db, GESTERN, PERSON_A)
        _suche(db, HEUTE, PERSON_A)

        with db.mit_zeitzone(zeitzone) as in_zone:
            geloescht = suchtracking_repository(in_zone).verdichten_vor(MITTERNACHT)

        assert geloescht == 1
        assert _tageszaehler(db) == [(GESTERN, 1, 1)]
        assert _suchereignis_tage(db) == [HEUTE]

    def test_verdichten_vor_laufender_tag_bleibt_einzelzeilen(self, db):
        _suche(db, HEUTE, PERSON_A)

        assert suchtracking_repository(db).verdichten_vor(MITTERNACHT) == 0
        assert _tageszaehler(db) == []

    def test_verdichten_vor_erster_lauf_verdichtet_alle_aelteren_tage(self, db):
        """Bis #495 blieben Suchereignisse 90 Tage; der erste Lauf holt sie alle."""
        for tag in (date(2026, 5, 1), date(2026, 6, 15), GESTERN):
            _suche(db, tag, PERSON_A)
            _suche(db, tag, PERSON_B)
        _suche(db, HEUTE, PERSON_A)

        geloescht = suchtracking_repository(db).verdichten_vor(MITTERNACHT)

        assert geloescht == 6
        assert _tageszaehler(db) == [
            (date(2026, 5, 1), 2, 2),
            (date(2026, 6, 15), 2, 2),
            (GESTERN, 2, 2),
        ]
        assert _suchereignis_tage(db) == [HEUTE]

    def test_verdichten_vor_kein_pseudonym_eines_abgeschlossenen_tages_bleibt(self, db):
        _suche(db, GESTERN, PERSON_A)
        _suche(db, HEUTE, PERSON_B)

        suchtracking_repository(db).verdichten_vor(MITTERNACHT)

        with db.engine.connect() as c:
            pseudonyme = c.execute(text("SELECT actor_hash FROM search_events")).all()
        assert pseudonyme == [(PERSON_B,)]

    def test_verdichten_vor_nachzuegler_wird_addiert(self, db):
        """Eine Suche von gestern, die erst nach dem Lauf eingeht, geht nicht verloren."""
        _suche(db, GESTERN, PERSON_A)
        repository = suchtracking_repository(db)
        repository.verdichten_vor(MITTERNACHT)
        _suche(db, GESTERN, PERSON_B, treffer=0)

        repository.verdichten_vor(MITTERNACHT)

        assert _tageszaehler(db) == [(GESTERN, 2, 2)]


class TestKennzahlenMitTageszaehlern:
    """Personen und Suchen eines Zeitraums: Tageszaehler plus Einzelzeilen."""

    def _verdichtet(self, db):
        for actor in (PERSON_A, PERSON_B, PERSON_B):
            _suche(db, GESTERN, actor)
        for actor in (PERSON_A, PERSON_A):
            _suche(db, HEUTE, actor)
        repository = suchtracking_repository(db)
        repository.verdichten_vor(MITTERNACHT)
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


class TestSuchenJePerson:
    """searches-per-user ohne Pseudonyme abgeschlossener Tage (#495)."""

    def test_get_searches_per_user_aus_tageszaehlern_und_laufendem_tag(self, db):
        heute = datetime.now(timezone.utc).date()
        gestern = heute - timedelta(days=1)
        for actor in (PERSON_A, PERSON_B, PERSON_B):
            _suche(db, gestern, actor)
        repository = suchtracking_repository(db)
        repository.verdichten_vor(
            datetime.combine(heute, time.min, tzinfo=timezone.utc)
        )
        for actor in (PERSON_A, PERSON_A, PERSON_A):
            _suche(db, heute, actor)

        assert repository.get_searches_per_user(7) == {
            "average": 2.0,
            "total_users": 3,
            "total_searches": 6,
        }

    def test_get_searches_per_user_ohne_suchen(self, db):
        assert suchtracking_repository(db).get_searches_per_user(7) == {
            "average": 0.0,
            "total_users": 0,
            "total_searches": 0,
        }


def _ohne_treffer_je_tag(datenbank: Datenbank):
    with datenbank.engine.connect() as c:
        return c.execute(
            text("SELECT tag, ohne_treffer FROM suchen_je_tag ORDER BY tag")
        ).all()


class TestSuchenOhneTrefferImTageszaehler:
    """K3 der Bilanz (#467) muss das Verdichten ueberleben."""

    def test_verdichten_vor_zaehlt_suchen_ohne_treffer(self, db):
        _suche(db, GESTERN, PERSON_A, treffer=0)
        _suche(db, GESTERN, PERSON_B, treffer=0)
        _suche(db, GESTERN, PERSON_B, treffer=4)

        suchtracking_repository(db).verdichten_vor(MITTERNACHT)

        assert _ohne_treffer_je_tag(db) == [(GESTERN, 2)]

    def test_verdichten_vor_unbekannte_bleiben_unbekannt(self, db):
        """Ein Tageszaehler von vor #467 hat keinen Wert; addiert wird nicht auf 0."""
        with db.engine.begin() as c:
            c.execute(
                text(
                    "INSERT INTO suchen_je_tag (tag, suchen, personen)"
                    " VALUES (:tag, 5, 2)"
                ),
                {"tag": GESTERN},
            )
        _suche(db, GESTERN, PERSON_A, treffer=0)

        suchtracking_repository(db).verdichten_vor(MITTERNACHT)

        assert _ohne_treffer_je_tag(db) == [(GESTERN, None)]


class TestTageswerte:
    """Tageswerte fuer die Bilanz: Einzelzeilen und Tageszaehler zusammen."""

    def test_get_tageswerte_verbindet_einzelzeilen_und_tageszaehler(self, db):
        for actor, treffer in ((PERSON_A, 0), (PERSON_B, 2), (PERSON_B, 0)):
            _suche(db, GESTERN, actor, treffer=treffer)
        repository = suchtracking_repository(db)
        repository.verdichten_vor(MITTERNACHT)
        for actor, treffer in ((PERSON_A, 1), (PERSON_A, 0)):
            _suche(db, HEUTE, actor, treffer=treffer)

        tage = repository.get_tageswerte(date(2026, 7, 1), date(2026, 8, 1))

        assert [(t.tag, t.suchen, t.personen, t.ohne_treffer) for t in tage] == [
            (GESTERN, 3, 2, 2),
            (HEUTE, 2, 1, 1),
        ]

    def test_get_tageswerte_grenzen_eingeschlossen_ausserhalb_nicht(self, db):
        for tag in (date(2026, 7, 27), GESTERN, HEUTE, date(2026, 7, 30)):
            _suche(db, tag, PERSON_A)

        tage = suchtracking_repository(db).get_tageswerte(GESTERN, HEUTE)

        assert [t.tag for t in tage] == [GESTERN, HEUTE]

    def test_get_tageswerte_unbekannte_ohne_treffer_bleiben_none(self, db):
        with db.engine.begin() as c:
            c.execute(
                text(
                    "INSERT INTO suchen_je_tag (tag, suchen, personen)"
                    " VALUES (:tag, 5, 2)"
                ),
                {"tag": GESTERN},
            )

        (tag,) = suchtracking_repository(db).get_tageswerte(GESTERN, GESTERN)

        assert (tag.suchen, tag.personen, tag.ohne_treffer) == (5, 2, None)

    @pytest.mark.parametrize("zeitzone", ["Pacific/Kiritimati", "Pacific/Pago_Pago"])
    def test_get_tageswerte_unabhaengig_von_der_zeitzone(self, db, zeitzone):
        _suche(db, HEUTE, PERSON_A)

        with db.mit_zeitzone(zeitzone) as in_zone:
            tage = suchtracking_repository(in_zone).get_tageswerte(HEUTE, HEUTE)

        assert [t.tag for t in tage] == [HEUTE]
