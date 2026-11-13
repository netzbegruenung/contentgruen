"""
Unit-Tests fuer das SuchanfrageFreigabeRepository (Vormoderation). Die Sitzung ist
gemockt; geprueft wird das SQL, das PostgreSQL bekaeme.
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.dialects import postgresql

from repositories.suchanfrage_freigabe_repository import (
    SuchanfrageFreigabeRepository,
)

pytestmark = pytest.mark.unit

AUSSAGE = uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def repository(app_datenbank):
    with patch(
        "repositories.suchanfrage_freigabe_repository.get_app_database",
        return_value=app_datenbank,
    ):
        yield SuchanfrageFreigabeRepository()


@pytest.mark.parametrize("freigegeben", [True, False])
def test_entscheiden_ersetzt_eine_fruehere_entscheidung(
    repository, session, freigegeben
):
    repository.entscheiden(AUSSAGE, freigegeben)

    upsert = session.execute.call_args.args[0]
    kompiliert = upsert.compile(dialect=postgresql.dialect())
    sql = " ".join(str(kompiliert).split())
    assert sql.startswith("INSERT INTO suchanfrage_freigaben")
    assert "ON CONFLICT (statement_id) DO UPDATE" in sql
    assert "entschieden_am = now()" in sql
    assert kompiliert.params["statement_id"] == AUSSAGE
    assert kompiliert.params["freigegeben"] is freigegeben
    session.commit.assert_called_once()


def test_entscheidungen_als_zuordnung(repository, session):
    andere = uuid.UUID(int=2)
    session.execute.return_value.all.return_value = [(AUSSAGE, True), (andere, False)]

    assert repository.entscheidungen() == {AUSSAGE: True, andere: False}
