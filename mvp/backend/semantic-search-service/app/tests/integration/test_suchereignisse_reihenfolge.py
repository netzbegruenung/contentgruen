"""
Die id von Suchereignissen (search_events.id) gegen ein echtes PostgreSQL (#275).

Eine Suche kann eine neue Aussage anlegen, deren Anlagezeitpunkt sekundengenau in
Qdrant steht. Traegt das Suchereignis eine fortlaufende Nummer, ergibt sie die
Reihenfolge der Suchen eines Tages; an ruhigen Tagen passt die zur Reihenfolge der
neuen Aussagen und ordnet jeder Aussage ein Tagespseudonym zu. Die id ist
deshalb eine zufaellige UUID: Nach ihr sortiert, stehen die Suchen eines Tages in
keiner Reihenfolge, die etwas ueber ihren Zeitpunkt sagt.
"""

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import text

from infrastructure.database.models import Base, SearchEvent
from repositories.search_tracking_repository import SearchTrackingRepository
from tests.integration import postgres

pytestmark = pytest.mark.integration

REIHENFOLGE = postgres.MIGRATIONEN / "2026-10-27-suchereignisse-reihenfolge.sql"
TAG = date(2026, 10, 27)
ANZAHL = 40

# search_events, wie sie vor #275 aussahen: id aus einer Sequenz.
VOR_275 = Path(__file__).with_name("search_events_vor_275.sql")


def _repository(db) -> SearchTrackingRepository:
    with patch(
        "repositories.search_tracking_repository.get_app_database",
        return_value=db,
    ):
        return SearchTrackingRepository()


def _pseudonym(nummer: int) -> str:
    return f"{nummer:064d}"


def _nach_id(db) -> list:
    with db.engine.connect() as c:
        return list(
            c.execute(
                text("SELECT actor_hash FROM search_events ORDER BY id")
            ).scalars()
        )


def _sequenzen(db) -> list:
    with db.engine.connect() as c:
        return list(
            c.execute(
                text(
                    "SELECT sequence_name FROM information_schema.sequences"
                    " WHERE sequence_schema = current_schema()"
                )
            ).scalars()
        )


@pytest.fixture
def neue_datenbank(wegwerf_schema):
    Base.metadata.create_all(wegwerf_schema.engine, tables=[SearchEvent.__table__])
    return wegwerf_schema


@pytest.fixture
def datenbank_vor_275(wegwerf_schema):
    """search_events mit fortlaufender id und Suchen eines Tages darin."""
    postgres.migration(wegwerf_schema, VOR_275)
    with wegwerf_schema.engine.begin() as c:
        for nummer in range(ANZAHL):
            c.execute(
                text(
                    "INSERT INTO search_events (actor_hash, results_count, timestamp)"
                    " VALUES (:pseudonym, :treffer, :tag)"
                ),
                {"pseudonym": _pseudonym(nummer), "treffer": nummer % 3, "tag": TAG},
            )
    return wegwerf_schema


def test_id_ergibt_keine_reihenfolge_der_suchen(neue_datenbank):
    repository = _repository(neue_datenbank)
    gesucht = [_pseudonym(nummer) for nummer in range(ANZAHL)]
    for pseudonym in gesucht:
        assert repository.track_search(results_count=0, day=TAG, actor_hash=pseudonym)

    nach_id = _nach_id(neue_datenbank)

    assert sorted(nach_id) == gesucht
    # Bei 40 zufaelligen ids ist jede der beiden Reihenfolgen 1 zu 40!.
    assert nach_id != gesucht
    assert nach_id != gesucht[::-1]


def test_neue_datenbank_hat_keine_sequenz(neue_datenbank):
    assert _sequenzen(neue_datenbank) == []


def test_gegenprobe_vor_275_ergibt_die_reihenfolge(datenbank_vor_275):
    """Ohne Migration sortiert id die Suchen genau in ihre Reihenfolge."""
    assert _nach_id(datenbank_vor_275) == [
        _pseudonym(nummer) for nummer in range(ANZAHL)
    ]
    assert _sequenzen(datenbank_vor_275) == ["search_events_id_seq"]


def test_migration_ersetzt_die_fortlaufende_id(datenbank_vor_275):
    postgres.migration(datenbank_vor_275, REIHENFOLGE)
    postgres.migration(datenbank_vor_275, REIHENFOLGE)

    nach_id = _nach_id(datenbank_vor_275)
    gesucht = [_pseudonym(nummer) for nummer in range(ANZAHL)]
    assert sorted(nach_id) == gesucht
    assert nach_id != gesucht
    assert _sequenzen(datenbank_vor_275) == []
    with datenbank_vor_275.engine.connect() as c:
        assert c.execute(
            text(
                "SELECT count(*), sum(results_count), count(DISTINCT timestamp)"
                " FROM search_events"
            )
        ).one() == (ANZAHL, sum(n % 3 for n in range(ANZAHL)), 1)


def test_nach_migration_schreibt_das_repository_weiter(datenbank_vor_275):
    postgres.migration(datenbank_vor_275, REIHENFOLGE)

    assert _repository(datenbank_vor_275).track_search(
        results_count=1, day=TAG, actor_hash=_pseudonym(ANZAHL)
    )

    with datenbank_vor_275.engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM search_events")).scalar() == (
            ANZAHL + 1
        )
