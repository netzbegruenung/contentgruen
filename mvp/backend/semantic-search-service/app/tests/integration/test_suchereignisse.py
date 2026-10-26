"""
Der Zeitstempel von Suchereignissen (search_events.timestamp) gegen ein echtes PostgreSQL.

Ein Suchereignis traegt nur den UTC-Tag, als Mitternacht UTC. Der Unit-Test prueft den
Server-Default nur als Text; hier rechnet PostgreSQL ihn aus, auch wenn die Zeitzone
der Sitzung nicht UTC ist. Jede Sitzung erbt die Server-Zeitzone (``timezone``), hier
wird sie je Sitzung gesetzt: Kiritimati (UTC+14) und Pago Pago (UTC-11) liegen fast
immer auf einem anderen Kalendertag als UTC.
"""

from datetime import date, datetime, time, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import text

from infrastructure.database.models import Base, SearchEvent
from repositories.search_tracking_repository import SearchTrackingRepository
from tests.integration import postgres

pytestmark = pytest.mark.integration

ZEITZONEN = ["UTC", "Pacific/Kiritimati", "Pacific/Pago_Pago"]
NUR_TAG = postgres.MIGRATIONEN / "2026-10-26-search-events-nur-tag.sql"


@pytest.fixture
def neue_datenbank(wegwerf_schema):
    """search_events, wie create_all es anlegt."""
    Base.metadata.create_all(wegwerf_schema.engine, tables=[SearchEvent.__table__])
    return wegwerf_schema


@pytest.fixture
def migrierte_datenbank(wegwerf_schema):
    """search_events mit dem Default vor #256, dann die Migration darauf."""
    Base.metadata.create_all(wegwerf_schema.engine, tables=[SearchEvent.__table__])
    with wegwerf_schema.engine.begin() as c:
        c.execute(
            text("ALTER TABLE search_events ALTER COLUMN timestamp SET DEFAULT now()")
        )
    postgres.migration(wegwerf_schema, NUR_TAG)
    return wegwerf_schema


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
@pytest.mark.parametrize("herkunft", ["neue_datenbank", "migrierte_datenbank"])
def test_default_ist_mitternacht_utc_des_utc_tages(herkunft, zeitzone, request):
    db = request.getfixturevalue(herkunft).mit_zeitzone(zeitzone)
    with db.engine.connect() as c:
        assert c.execute(text("SHOW timezone")).scalar() == zeitzone

    gespeichert, jetzt_utc = _ohne_zeitstempel_einfuegen(db)

    assert gespeichert == datetime.combine(jetzt_utc.date(), time.min)


@pytest.mark.parametrize("zeitzone", ZEITZONEN)
def test_repository_speichert_mitternacht_utc(neue_datenbank, zeitzone):
    db = neue_datenbank.mit_zeitzone(zeitzone)
    with patch(
        "repositories.search_tracking_repository.get_app_database", return_value=db
    ):
        repository = SearchTrackingRepository()

    assert repository.track_search(results_count=3, day=date(2026, 10, 28))

    with db.engine.connect() as c:
        gespeichert = c.execute(text("SELECT timestamp FROM search_events")).scalar()
    assert gespeichert == datetime(2026, 10, 28, tzinfo=timezone.utc)
