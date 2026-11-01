"""
Der Zeitstempel von Suchereignissen (search_events.timestamp) gegen ein echtes PostgreSQL.

Ein Suchereignis traegt nur den UTC-Tag, als Mitternacht UTC. Der Unit-Test prueft den
Server-Default nur als Text; hier rechnet PostgreSQL ihn aus, auch wenn die Zeitzone
der Sitzung nicht UTC ist. Server (``postgresql.conf``, ``TZ`` beim initdb), Datenbank
und Rolle (``ALTER DATABASE/ROLE ... SET timezone``) und ``PGTZ`` setzen alle nur den
Anfangswert desselben Sitzungswerts ``TimeZone``, und nur von ihm haengt der Default
ab. Der Test setzt ihn deshalb je Sitzung; ``ALTER DATABASE`` traefe bei
``POSTGRES_TEST_DATABASE_URL`` die ganze Datenbank. Kiritimati (UTC+14) und Pago Pago (UTC-11) weichen
ganzjaehrig von UTC ab, ein Default nach der Mitternacht der Sitzung ergaebe dort nie
Mitternacht UTC.
"""

from datetime import date, datetime, time, timezone

import pytest
from sqlalchemy import text

from tests.integration.suchereignis_helfer import suchtracking_repository
from tests.integration import postgres

pytestmark = pytest.mark.integration

ZEITZONEN = ["UTC", "Pacific/Kiritimati", "Pacific/Pago_Pago"]
NUR_TAG = postgres.MIGRATIONEN / "2026-10-26-search-events-nur-tag.sql"


@pytest.fixture
def migrierte_datenbank(suchereignisse_db):
    """search_events mit dem Default vor #256, dann die Migration darauf."""
    with suchereignisse_db.engine.begin() as c:
        c.execute(text(postgres.SUCHEREIGNIS_DEFAULT_VOR_256))
    postgres.migration(suchereignisse_db, NUR_TAG)
    return suchereignisse_db


def _ohne_zeitstempel_einfuegen(db) -> tuple:
    """
    Ein Suchereignis ohne Zeitstempel anlegen. Liefert den gespeicherten Wert und
    den UTC-Zeitpunkt der Transaktion (dasselbe now(), das der Default sieht).
    """
    with db.engine.begin() as c:
        return c.execute(
            text(
                "INSERT INTO search_events (actor_hash, results_count)"
                " VALUES (NULL, 0)"
                " RETURNING timestamp AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC'"
            )
        ).one()


@pytest.mark.parametrize("zeitzone", ZEITZONEN)
@pytest.mark.parametrize("herkunft", ["suchereignisse_db", "migrierte_datenbank"])
def test_default_ist_mitternacht_utc_des_utc_tages(herkunft, zeitzone, request):
    with request.getfixturevalue(herkunft).mit_zeitzone(zeitzone) as db:
        with db.engine.connect() as c:
            assert c.execute(text("SHOW timezone")).scalar() == zeitzone

        gespeichert, jetzt_utc = _ohne_zeitstempel_einfuegen(db)

    assert gespeichert == datetime.combine(jetzt_utc.date(), time.min)


@pytest.mark.parametrize("zeitzone", ZEITZONEN)
def test_repository_speichert_mitternacht_utc(suchereignisse_db, zeitzone):
    with suchereignisse_db.mit_zeitzone(zeitzone) as db:
        repository = suchtracking_repository(db)

        assert repository.track_search(results_count=3, day=date(2026, 10, 28))

        with db.engine.connect() as c:
            gespeichert = c.execute(
                text("SELECT timestamp FROM search_events")
            ).scalar()
    assert gespeichert == datetime(2026, 10, 28, tzinfo=timezone.utc)
