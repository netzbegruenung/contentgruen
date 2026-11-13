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
