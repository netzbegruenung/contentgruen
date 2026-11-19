"""
"Ohne Einwilligung weiter" am Konto (UX-Review B2, PR #670) gegen ein echtes
PostgreSQL: Merken, Ersetzen, Aufheben durch eine Einwilligung, Widerruf laesst den
Vermerk stehen. Die Migration prueft test_migrationen.py (zweimal, gleich create_all).
"""

import pytest

from infrastructure.database.models import (
    Art9EinwilligungZeile,
    Art9OhneEinwilligungZeile,
    Base,
)
from repositories.art9_einwilligung_repository import Art9EinwilligungRepository
from services.art9_einwilligung_service import Art9EinwilligungService

PERSON = "test-person"

pytestmark = pytest.mark.integration


@pytest.fixture
def repository(wegwerf_schema):
    Base.metadata.create_all(
        wegwerf_schema.engine,
        tables=[Art9EinwilligungZeile.__table__, Art9OhneEinwilligungZeile.__table__],
    )
    return Art9EinwilligungRepository(wegwerf_schema)


def test_ohne_merken_und_lesen(repository):
    assert repository.ohne_lesen(PERSON) is None

    repository.ohne_merken(PERSON, "2026-11-12")
    repository.ohne_merken(PERSON, "2026-11-13")

    assert repository.ohne_lesen(PERSON) == "2026-11-13"
    assert repository.ohne_lesen("andere-person") is None


def test_einwilligung_hebt_den_vermerk_auf_nach_widerruf_wieder_moeglich(repository):
    dienst = Art9EinwilligungService(repository)
    dienst.ohne_merken(PERSON, "2026-11-13")

    dienst.einwilligen(PERSON, "2026-11-13")
    assert dienst.ohne(PERSON) is None

    # Nach dem Widerruf laesst sich "ohne" wieder festhalten
    dienst.widerrufen(PERSON)
    assert dienst.ohne_merken(PERSON, "2026-11-13") is True
    assert dienst.ohne(PERSON) == "2026-11-13"


def test_migration_legt_die_tabelle_an_und_darf_zweimal_laufen(postgres_url):
    from tests.integration import postgres

    with postgres.schema(postgres_url, "itest_art9_ohne") as db:
        # Die Pruefung auf eine geltende Einwilligung braucht deren Tabelle
        postgres.migration(
            db, postgres.MIGRATIONEN / "2026-11-05-art9-einwilligung.sql"
        )
        migration = postgres.MIGRATIONEN / "2026-11-13-art9-ohne-einwilligung.sql"
        postgres.migration(db, migration)
        postgres.migration(db, migration)

        repository = Art9EinwilligungRepository(db)
        repository.ohne_merken(PERSON, "2026-11-13")

        assert repository.ohne_lesen(PERSON) == "2026-11-13"


def test_ohne_nach_einer_einwilligung_bleibt_ohne_wirkung(repository):
    """Review zu #670: Erst Einwilligung (etwa in einem anderen Tab), dann /ohne."""
    dienst = Art9EinwilligungService(repository)
    dienst.einwilligen(PERSON, "2026-11-13")

    assert dienst.ohne_merken(PERSON, "2026-11-13") is False
    assert dienst.ohne(PERSON) is None
    assert dienst.eingewilligt(PERSON)


def test_ohne_nach_einwilligung_zu_frueherem_wortlaut_wirkt(repository):
    """Eine Einwilligung zu einem Wortlaut, der nicht mehr gilt, haelt den Vermerk nicht auf."""
    repository.einwilligen(PERSON, "2026-11-12")

    assert repository.ohne_merken(PERSON, "2026-11-13") is True
    assert repository.ohne_lesen(PERSON) == "2026-11-13"


def test_ohne_wartet_auf_eine_gleichzeitige_einwilligung(repository, wegwerf_schema):
    """
    Review zu #670: Tab A willigt ein, Tab B schickt gleichzeitig "ohne". Unter READ
    COMMITTED saehe B die noch offene Einwilligung nicht; die Advisory-Sperre je Person
    laesst B warten, bis A festgeschrieben ist, und dann schreibt B nichts.
    """
    import threading
    from datetime import datetime, timezone

    from sqlalchemy import text

    from repositories.art9_einwilligung_repository import SPERRE_ART9

    ergebnis = {}

    def ohne():
        try:
            ergebnis["wert"] = repository.ohne_merken(PERSON, "2026-11-13")
        except Exception as e:  # noqa: BLE001 (der Test prueft den Fehler)
            ergebnis["fehler"] = e

    a = wegwerf_schema.sessions()
    try:
        # A wie einwilligen: Sperre nehmen und die Einwilligung schreiben, noch offen
        a.execute(
            text("SELECT pg_advisory_xact_lock(:sperre, hashtext(:kennung))"),
            {"sperre": SPERRE_ART9, "kennung": PERSON},
        )
        a.add(
            Art9EinwilligungZeile(
                user_id=PERSON,
                wortlaut="2026-11-13",
                eingewilligt_am=datetime.now(timezone.utc),
            )
        )
        a.flush()
        faden = threading.Thread(target=ohne, daemon=True)
        faden.start()
        faden.join(timeout=1.5)
        assert faden.is_alive(), "ohne_merken wartet nicht auf die Sperre"
        a.commit()
    finally:
        a.close()
    faden.join(timeout=10)

    assert not faden.is_alive()
    assert "fehler" not in ergebnis
    assert ergebnis["wert"] is False
    assert repository.ohne_lesen(PERSON) is None
