"""
Art.-9-Einwilligung (#489) gegen ein echtes PostgreSQL: Repository und Dienst bis
in die Tabelle. Einwilligen speichert Zeitpunkt und Wortlaut, Widerrufen laesst
die Zeile mit dem Zeitpunkt des Widerrufs stehen, erneutes Einwilligen ersetzt
sie. Dazu laeuft die Migration auf einer Datenbank ohne die Tabelle.
"""

import pytest
from sqlalchemy import text

from infrastructure.database.models import Art9EinwilligungZeile, Base
from repositories.art9_einwilligung_repository import Art9EinwilligungRepository
from services.art9_einwilligung_service import (
    Art9EinwilligungService,
    UnbekannterWortlaut,
)
from tests.integration import postgres

MIGRATION = postgres.MIGRATIONEN / "2026-11-05-art9-einwilligung.sql"
PERSON = "person-mit-einwilligung"

pytestmark = pytest.mark.integration


@pytest.fixture
def datenbank(wegwerf_schema):
    Base.metadata.create_all(
        wegwerf_schema.engine, tables=[Art9EinwilligungZeile.__table__]
    )
    return wegwerf_schema


@pytest.fixture
def repository(datenbank):
    return Art9EinwilligungRepository(datenbank)


class TestRepository:
    def test_ohne_zeile_keine_einwilligung(self, repository):
        assert repository.lesen(PERSON) is None

    def test_einwilligen_speichert_zeitpunkt_und_wortlaut(self, repository):
        repository.einwilligen(PERSON, "2026-11-05")

        einwilligung = repository.lesen(PERSON)
        assert einwilligung.wortlaut == "2026-11-05"
        assert einwilligung.eingewilligt_am is not None
        assert einwilligung.gilt

    def test_widerruf_laesst_zeile_mit_zeitpunkt(self, repository):
        repository.einwilligen(PERSON, "2026-11-05")

        repository.widerrufen(PERSON)

        einwilligung = repository.lesen(PERSON)
        assert einwilligung.widerrufen_am >= einwilligung.eingewilligt_am
        assert not einwilligung.gilt

    def test_zweiter_widerruf_aendert_den_zeitpunkt_nicht(self, repository, datenbank):
        repository.einwilligen(PERSON, "2026-11-05")
        repository.widerrufen(PERSON)
        erster = repository.lesen(PERSON).widerrufen_am

        repository.widerrufen(PERSON)

        assert repository.lesen(PERSON).widerrufen_am == erster

    def test_widerruf_ohne_einwilligung_legt_nichts_an(self, repository):
        repository.widerrufen(PERSON)

        assert repository.lesen(PERSON) is None

    def test_erneut_einwilligen_neue_zeile_der_widerruf_bleibt_belegt(
        self, repository, datenbank
    ):
        repository.einwilligen(PERSON, "2026-11-05")
        repository.widerrufen(PERSON)

        repository.einwilligen(PERSON, "2026-11-05")

        einwilligung = repository.lesen(PERSON)
        assert einwilligung.gilt
        assert einwilligung.widerrufen_am is None
        assert _zeilen(datenbank) == [("2026-11-05", True), ("2026-11-05", False)]

    def test_doppelt_absenden_legt_keine_zweite_zeile_an(self, repository, datenbank):
        repository.einwilligen(PERSON, "2026-11-05")
        repository.einwilligen(PERSON, "2026-11-05")

        assert _zeilen(datenbank) == [("2026-11-05", False)]


def _zeilen(datenbank):
    """(Wortlaut, widerrufen) je Zeile der Person, die aelteste zuerst."""
    with datenbank.engine.connect() as c:
        return [
            (wortlaut, widerrufen)
            for wortlaut, widerrufen in c.execute(
                text(
                    "SELECT wortlaut, widerrufen_am IS NOT NULL"
                    " FROM art9_einwilligungen WHERE user_id = :k"
                    " ORDER BY eingewilligt_am"
                ),
                {"k": PERSON},
            )
        ]


class TestDienst:
    def test_einwilligen_widerrufen_pruefen(self, repository):
        dienst = Art9EinwilligungService(repository)
        assert not dienst.eingewilligt(PERSON)

        dienst.einwilligen(PERSON, "2026-11-05")
        assert dienst.eingewilligt(PERSON)

        dienst.widerrufen(PERSON)
        assert not dienst.eingewilligt(PERSON)

    def test_unbekannter_wortlaut_speichert_nichts(self, repository):
        dienst = Art9EinwilligungService(repository)

        with pytest.raises(UnbekannterWortlaut):
            dienst.einwilligen(PERSON, "2099-01-01")

        assert repository.lesen(PERSON) is None


def test_migration_legt_die_tabelle_an_und_darf_zweimal_laufen(postgres_url):
    with postgres.schema(postgres_url, "itest_art9") as db:
        postgres.migration(db, MIGRATION)
        postgres.migration(db, MIGRATION)

        repository = Art9EinwilligungRepository(db)
        repository.einwilligen(PERSON, "2026-11-05")
        repository.widerrufen(PERSON)

        assert not repository.lesen(PERSON).gilt
