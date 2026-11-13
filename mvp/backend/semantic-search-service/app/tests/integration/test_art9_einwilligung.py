"""
Art.-9-Einwilligung (#489) gegen ein echtes PostgreSQL: Repository und Dienst bis
in die Tabelle. Einwilligen speichert Zeitpunkt und Wortlaut, Widerrufen laesst
die Zeile mit dem Zeitpunkt des Widerrufs stehen, erneutes Einwilligen ersetzt
sie. Dazu laeuft die Migration auf einer Datenbank ohne die Tabelle.
"""

import uuid

import pytest
from sqlalchemy import text

from domain.art9_einwilligung import AKTUELLER_WORTLAUT
from infrastructure.database.models import Art9EinwilligungZeile, Base
from repositories.art9_einwilligung_repository import Art9EinwilligungRepository
from repositories.vote_repository import VoteRepository
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

        dienst.einwilligen(PERSON, AKTUELLER_WORTLAUT)
        assert dienst.eingewilligt(PERSON)

        dienst.widerrufen(PERSON)
        assert not dienst.eingewilligt(PERSON)

    def test_widerruf_loescht_die_stimmen_der_person_und_nur_ihre(
        self, repository, datenbank
    ):
        stimmen = VoteRepository(datenbank)
        stimmen.create_votes_table()
        beitrag = str(uuid.uuid4())
        with datenbank.engine.begin() as c:
            for person, inhalt, art in [
                (PERSON, beitrag, "like"),
                (PERSON, str(uuid.uuid4()), "dislike"),
                ("andere-person", beitrag, "like"),
            ]:
                c.execute(
                    text(
                        "INSERT INTO votes (user_id, content_id, vote_type)"
                        " VALUES (:p, :i, :a)"
                    ),
                    {"p": person, "i": inhalt, "a": art},
                )
        dienst = Art9EinwilligungService(repository, stimmen)
        dienst.einwilligen(PERSON, AKTUELLER_WORTLAUT)

        dienst.widerrufen(PERSON)

        with datenbank.engine.connect() as c:
            uebrig = c.execute(text("SELECT user_id FROM votes")).scalars().all()
        assert uebrig == ["andere-person"]
        assert not dienst.eingewilligt(PERSON)

    def test_bei_loeschfehler_kein_vermerk(self, repository, datenbank):
        """Eine Transaktion: Scheitert das Loeschen, gilt die Einwilligung weiter."""
        from unittest.mock import MagicMock

        stimmen = MagicMock()
        stimmen.loeschen_fuer_person.side_effect = RuntimeError("Datenbank weg")
        dienst = Art9EinwilligungService(repository, stimmen)
        dienst.einwilligen(PERSON, AKTUELLER_WORTLAUT)

        with pytest.raises(RuntimeError):
            dienst.widerrufen(PERSON)

        assert dienst.eingewilligt(PERSON)
        assert repository.lesen(PERSON).widerrufen_am is None

    def test_frueherer_wortlaut_zaehlt_nicht_bis_zur_neuen_einwilligung(
        self, repository
    ):
        """2026-11-13: Wer einem frueheren Wortlaut zugestimmt hat, wird neu gefragt."""
        dienst = Art9EinwilligungService(repository)
        repository.einwilligen(PERSON, "2026-11-12")
        assert not dienst.eingewilligt(PERSON)
        assert repository.lesen(PERSON).gilt

        dienst.einwilligen(PERSON, AKTUELLER_WORTLAUT)

        assert dienst.eingewilligt(PERSON)
        assert _zeilen(repository.db) == [
            ("2026-11-12", False),
            (AKTUELLER_WORTLAUT, False),
        ]

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
