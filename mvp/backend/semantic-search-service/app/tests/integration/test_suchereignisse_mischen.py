"""
Suchereignisse eines abgeschlossenen Tages gemischt neu schreiben, gegen ein
echtes PostgreSQL (#337).

Jede Suche schreibt ihr Suchereignis in einer eigenen Transaktion. Bis der
taegliche Bereinigungsjob den Tag gemischt hat, ergeben deshalb die Systemspalte
``xmin`` (steigt mit jeder Transaktion) und die physische Lage ``ctid`` (folgt
dem Einfuegen, ebenso ``pg_dump``) die Reihenfolge der Suchen eines Tages. Nach
dem Mischen tragen alle Zeilen des Tages dieselbe Transaktion und liegen in
zufaelliger Reihenfolge.
"""

from datetime import date, datetime, time, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import text

from infrastructure.database.models import Base, SearchEvent
from repositories.search_tracking_repository import SearchTrackingRepository

pytestmark = pytest.mark.integration

HEUTE = date(2026, 10, 27)
GESTERN = date(2026, 10, 26)
VORGESTERN = date(2026, 10, 25)
ANZAHL = 40
# Rund 80 Suchereignisse passen auf eine Seite (8 kB) der Tabellendatei.
VIELE = 500


def _repository(db) -> SearchTrackingRepository:
    with patch(
        "repositories.search_tracking_repository.get_app_database",
        return_value=db,
    ):
        return SearchTrackingRepository()


def _pseudonym(tag: date, nummer: int) -> str:
    return f"{tag:%Y%m%d}{nummer:056d}"


def _suche(c, tag: date, pseudonym: str, treffer: int = 0) -> None:
    c.execute(
        text(
            "INSERT INTO search_events (actor_hash, results_count, timestamp)"
            " VALUES (:pseudonym, :treffer, :zeit)"
        ),
        {
            "pseudonym": pseudonym,
            "treffer": treffer,
            "zeit": datetime.combine(tag, time.min, tzinfo=timezone.utc),
        },
    )


def _suchen(db, tag: date, anzahl: int = ANZAHL) -> list:
    """Suchen eines Tages, jede in ihrer eigenen Transaktion wie im Dienst."""
    gesucht = [_pseudonym(tag, nummer) for nummer in range(anzahl)]
    for nummer, pseudonym in enumerate(gesucht):
        with db.engine.begin() as c:
            _suche(c, tag, pseudonym, nummer % 3)
    return gesucht


def _reihenfolge(db, tag: date, nach: str) -> list:
    with db.engine.connect() as c:
        return list(
            c.execute(
                text(
                    "SELECT actor_hash FROM search_events"
                    " WHERE timestamp = :zeit"
                    f" ORDER BY {nach}"
                ),
                {"zeit": datetime.combine(tag, time.min, tzinfo=timezone.utc)},
            ).scalars()
        )


def _nach_xmin(db, tag: date) -> list:
    return _reihenfolge(db, tag, "xmin::text::bigint")


def _nach_ctid(db, tag: date) -> list:
    return _reihenfolge(db, tag, "ctid")


def _transaktionen(db, tag: date) -> int:
    with db.engine.connect() as c:
        return c.execute(
            text(
                "SELECT count(DISTINCT xmin::text) FROM search_events"
                " WHERE timestamp = :zeit"
            ),
            {"zeit": datetime.combine(tag, time.min, tzinfo=timezone.utc)},
        ).scalar()


def _seiten(db) -> int:
    with db.engine.connect() as c:
        return c.execute(
            text("SELECT count(DISTINCT (ctid::text::point)[0]) FROM search_events")
        ).scalar()


def _zeilen(db) -> list:
    with db.engine.connect() as c:
        return sorted(
            c.execute(
                text(
                    "SELECT id, actor_hash, results_count, timestamp FROM search_events"
                )
            ).all()
        )


def _ohne_reihenfolge(reihenfolge: list, gesucht: list) -> bool:
    # Gezaehlt werden Nachbarn, die auch beim Suchen aufeinander folgten (in einer
    # der beiden Richtungen). Gemischt sind das im Mittel zwei; ein Drittel oder
    # mehr ist bei 40 Zeilen zufaellig etwa 1 zu 100 Millionen. So faellt nicht nur
    # die Reihenfolge selbst und ihre Umkehrung auf, sondern auch eine fast
    # sortierte oder nur verschobene.
    platz = {pseudonym: nummer for nummer, pseudonym in enumerate(gesucht)}
    nachbarn = sum(
        abs(platz[a] - platz[b]) == 1 for a, b in zip(reihenfolge, reihenfolge[1:])
    )
    return sorted(reihenfolge) == gesucht and nachbarn < len(gesucht) // 3


@pytest.fixture
def db(wegwerf_schema):
    Base.metadata.create_all(wegwerf_schema.engine, tables=[SearchEvent.__table__])
    return wegwerf_schema


def test_gegenprobe_ungemischt_ergeben_xmin_und_ctid_die_reihenfolge(db):
    gesucht = _suchen(db, GESTERN)

    assert _nach_xmin(db, GESTERN) == gesucht
    assert _nach_ctid(db, GESTERN) == gesucht


def test_mische_abgeschlossene_tage_xmin_und_ctid_ergeben_keine_reihenfolge(db):
    gesucht = _suchen(db, GESTERN)

    gemischt = _repository(db).mische_abgeschlossene_tage(heute=HEUTE)

    assert gemischt == ANZAHL
    assert _transaktionen(db, GESTERN) == 1
    assert _ohne_reihenfolge(_nach_ctid(db, GESTERN), gesucht)


def test_mische_abgeschlossene_tage_behaelt_die_zeilen(db):
    _suchen(db, VORGESTERN)
    _suchen(db, GESTERN)
    vorher = _zeilen(db)

    _repository(db).mische_abgeschlossene_tage(heute=HEUTE)

    assert _zeilen(db) == vorher


def test_mische_abgeschlossene_tage_laesst_den_laufenden_tag(db):
    gesucht = _suchen(db, HEUTE)

    assert _repository(db).mische_abgeschlossene_tage(heute=HEUTE) == 0

    assert _nach_ctid(db, HEUTE) == gesucht
    assert _transaktionen(db, HEUTE) == ANZAHL


def test_mische_abgeschlossene_tage_ueber_mehrere_seiten(db):
    """Mehr Zeilen, als auf eine Seite der Tabellendatei passen."""
    gesucht = _suchen(db, GESTERN, anzahl=VIELE)
    assert _seiten(db) > 1

    _repository(db).mische_abgeschlossene_tage(heute=HEUTE)

    assert _transaktionen(db, GESTERN) == 1
    assert _ohne_reihenfolge(_nach_ctid(db, GESTERN), gesucht)


def test_mische_abgeschlossene_tage_auch_mit_einer_transaktion(db):
    """Ein Tag, dessen Zeilen schon eine Transaktion tragen, aber in der
    Reihenfolge ihres Einfuegens liegen: nach dem Neuschreiben der Tabelle in
    2026-10-27-suchereignisse-reihenfolge.sql oder nach dem Einspielen eines
    Dumps, den pg_dump vor dem Mischen geschrieben hat."""
    gesucht = _suchen(db, GESTERN)
    with db.engine.begin() as c:
        c.execute(text("UPDATE search_events SET results_count = results_count"))
    assert _transaktionen(db, GESTERN) == 1
    assert _nach_ctid(db, GESTERN) == gesucht
    vorher = _zeilen(db)

    _repository(db).mische_abgeschlossene_tage(heute=HEUTE)

    assert _zeilen(db) == vorher
    assert _ohne_reihenfolge(_nach_ctid(db, GESTERN), gesucht)


def test_mische_abgeschlossene_tage_zweiter_lauf_behaelt_die_zeilen(db):
    _suchen(db, VORGESTERN)
    _suchen(db, GESTERN)
    vorher = _zeilen(db)
    repository = _repository(db)

    assert repository.mische_abgeschlossene_tage(heute=HEUTE) == 2 * ANZAHL
    assert repository.mische_abgeschlossene_tage(heute=HEUTE) == 2 * ANZAHL

    assert _zeilen(db) == vorher
    assert _transaktionen(db, GESTERN) == 1


def test_mische_abgeschlossene_tage_suche_waehrend_des_laufs(db):
    """Eine Suche kurz vor Mitternacht, deren Suchereignis erst eingeht, waehrend
    der Lauf mischt: Der Lauf wartet nicht auf sie, sie geht nicht verloren, und
    der naechste Lauf mischt sie mit."""
    gesucht = _suchen(db, GESTERN)
    nachzuegler = _pseudonym(GESTERN, ANZAHL)
    repository = _repository(db)

    with db.engine.connect() as suche:
        with suche.begin():
            _suche(suche, GESTERN, nachzuegler)
            assert repository.mische_abgeschlossene_tage(heute=HEUTE) == ANZAHL

    assert nachzuegler in _nach_ctid(db, GESTERN)
    assert _transaktionen(db, GESTERN) == 2

    assert repository.mische_abgeschlossene_tage(heute=HEUTE) == ANZAHL + 1

    assert _transaktionen(db, GESTERN) == 1
    assert _ohne_reihenfolge(_nach_ctid(db, GESTERN), gesucht + [nachzuegler])
