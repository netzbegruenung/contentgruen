"""
Themen an Aussagen (#363) gegen ein echtes PostgreSQL.

Das Repository bis in die Tabelle: Setzen ersetzt die Themen einer Aussage, Lesen
liefert sie je Aussage, und die Zuordnungen von Hand lassen sich als Testset
abholen. Die Tabelle traegt weder Person noch Zeitpunkt. Dazu laeuft die
Migration auf einer Datenbank ohne die Tabelle.

Jeder Test bekommt ein eigenes Schema und raeumt es wieder ab; Datenbank und
Schema kommen aus ``conftest.py`` (siehe ``postgres.py``).
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import inspect

from infrastructure.database.models import AussageThemaZeile, Base
from repositories.aussage_themen_repository import AussageThemenRepository
from services.aussage_themen_service import VON_HAND
from tests.integration import postgres
from tests.integration.postgres import Datenbank

MIGRATION = postgres.MIGRATIONEN / "2026-10-29-363-aussage-themen.sql"

A = uuid.UUID("11111111-1111-1111-1111-111111111111")
B = uuid.UUID("22222222-2222-2222-2222-222222222222")
C = uuid.UUID("33333333-3333-3333-3333-333333333333")

pytestmark = pytest.mark.integration


@pytest.fixture
def neue_datenbank(postgres_url):
    with postgres.schema(postgres_url, "itest_th") as db:
        Base.metadata.create_all(db.engine, tables=[AussageThemaZeile.__table__])
        yield db


def _repository(db: Datenbank) -> AussageThemenRepository:
    with patch(
        "repositories.aussage_themen_repository.get_app_database",
        return_value=db,
    ):
        return AussageThemenRepository()


def test_tabelle_traegt_weder_person_noch_zeitpunkt(neue_datenbank):
    spalten = {
        s["name"]
        for s in inspect(neue_datenbank.engine).get_columns(
            "aussage_themen", schema=neue_datenbank.schema
        )
    }
    assert spalten == {"statement_id", "thema", "quelle"}


def test_setzen_und_lesen_je_aussage(neue_datenbank):
    repository = _repository(neue_datenbank)
    repository.setzen(A, ["klima", "verkehr"], VON_HAND)
    repository.setzen(B, ["europa"], VON_HAND)

    themen = repository.themen_von([A, B, C])

    assert {k: sorted(v) for k, v in themen.items()} == {
        A: ["klima", "verkehr"],
        B: ["europa"],
    }
    assert repository.themen_von([]) == {}


def test_setzen_ersetzt_und_leer_entfernt(neue_datenbank):
    repository = _repository(neue_datenbank)
    repository.setzen(A, ["klima", "verkehr"], VON_HAND)

    repository.setzen(A, ["europa"], VON_HAND)
    assert repository.themen_von([A]) == {A: ["europa"]}

    repository.setzen(A, [], VON_HAND)
    assert repository.themen_von([A]) == {}


def test_zuordnungen_nur_der_gefragten_quelle(neue_datenbank):
    repository = _repository(neue_datenbank)
    repository.setzen(A, ["klima"], VON_HAND)
    repository.setzen(B, ["verkehr"], "vorschlag")

    assert repository.zuordnungen(VON_HAND) == {A: ["klima"]}


def test_migration_legt_die_tabelle_an_und_darf_zweimal_laufen(postgres_url):
    with postgres.schema(postgres_url, "itest_th") as db:
        postgres.migration(db, MIGRATION)
        postgres.migration(db, MIGRATION)

        repository = _repository(db)
        repository.setzen(A, ["klima"], VON_HAND)

        assert repository.zuordnungen(VON_HAND) == {A: ["klima"]}
