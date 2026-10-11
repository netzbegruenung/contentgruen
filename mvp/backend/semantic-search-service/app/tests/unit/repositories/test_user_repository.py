"""
Die Tabelle users und ihr Repository.

Schema festnageln (create_all legt die Tabelle nur an, wenn sie am selben Base
haengt) und das SQL pruefen, das das Repository schickt - die Session ist
gemockt wie in test_raw_input_repository.py.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from infrastructure.database.models import Base, User
from repositories.user_repository import UserRepository


def _sql(statement) -> str:
    return " ".join(str(statement.compile(dialect=postgresql.dialect())).split())


@pytest.fixture
def session():
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return session


@pytest.fixture
def repository(session):
    db = MagicMock()
    db.get_session.return_value = session
    with patch("repositories.user_repository.get_app_database", return_value=db):
        yield UserRepository()


@pytest.mark.unit
class TestUserSchema:
    def test_tabelle_haengt_am_base_den_create_all_anlegt(self):
        assert Base.metadata.tables["users"] is User.__table__

    def test_felder_stehen_fest(self):
        assert set(User.__table__.columns.keys()) == {
            "user_id",
            "anzeigename",
            "aktualisiert_am",
        }
        assert User.__table__.columns["user_id"].primary_key is True
        assert User.__table__.columns["anzeigename"].nullable is False


@pytest.mark.unit
class TestUserRepository:
    def test_speichern_ist_ein_upsert_auf_die_kennung(self, repository, session):
        repository.anzeigename_speichern("kennung-1", "Anna B.")

        sql = _sql(session.execute.call_args.args[0])
        assert sql.startswith("INSERT INTO users")
        assert "ON CONFLICT (user_id) DO UPDATE" in sql
        assert "aktualisiert_am = now()" in sql

    def test_namen_in_einer_abfrage(self, repository, session):
        session.execute.return_value.all.return_value = [
            SimpleNamespace(user_id="a", anzeigename="Anna B."),
        ]

        namen = repository.anzeigenamen(["a", "b", "a", None])

        assert namen == {"a": "Anna B."}
        assert session.execute.call_count == 1
        sql = _sql(session.execute.call_args.args[0])
        assert "WHERE users.user_id IN" in sql

    def test_ohne_kennungen_keine_abfrage(self, repository, session):
        assert repository.anzeigenamen([None, ""]) == {}
        session.execute.assert_not_called()
