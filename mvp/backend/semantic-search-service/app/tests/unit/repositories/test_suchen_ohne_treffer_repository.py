"""
Unit-Tests fuer das SuchenOhneTrefferRepository.

Die Datenbanksitzung ist gemockt; geprueft wird das SQL, das PostgreSQL bekaeme:
Hochzaehlen per Upsert je (Aussage, Woche), Aufraeumen alter Wochen und die
Rangliste mit Mindestanzahl.
"""

import uuid
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.dialects import postgresql

from repositories.suchen_ohne_treffer_repository import SuchenOhneTrefferRepository

pytestmark = pytest.mark.unit

AUSSAGE = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _sql(statement) -> str:
    return " ".join(str(statement.compile(dialect=postgresql.dialect())).split())


def _params(statement) -> dict:
    return statement.compile(dialect=postgresql.dialect()).params


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
    with patch(
        "repositories.suchen_ohne_treffer_repository.get_app_database",
        return_value=db,
    ):
        yield SuchenOhneTrefferRepository()


class TestZaehlen:
    def test_zaehlen_erhoeht_die_anzahl_je_aussage_und_woche(self, repository, session):
        repository.zaehlen(AUSSAGE, date(2026, 10, 26))

        upsert = session.execute.call_args.args[0]
        sql = _sql(upsert)
        assert sql.startswith("INSERT INTO suchen_ohne_treffer")
        assert "ON CONFLICT (statement_id, woche) DO UPDATE" in sql
        assert "anzahl = (suchen_ohne_treffer.anzahl + " in sql
        params = _params(upsert)
        assert params["statement_id"] == AUSSAGE
        assert params["woche"] == date(2026, 10, 26)
        assert params["anzahl"] == 1
        session.commit.assert_called_once()

    def test_zaehlen_gibt_datenbankfehler_an_den_aufrufer(self, repository, session):
        """Abgefangen wird im Suchpfad, nicht hier."""
        session.execute.side_effect = RuntimeError("weg")

        with pytest.raises(RuntimeError):
            repository.zaehlen(AUSSAGE, date(2026, 10, 26))


class TestLoeschenVor:
    def test_loeschen_vor_entfernt_aeltere_wochen(self, repository, session):
        session.execute.return_value.rowcount = 3

        geloescht = repository.loeschen_vor(date(2026, 9, 7))

        loeschen = session.execute.call_args.args[0]
        sql = _sql(loeschen)
        assert sql.startswith("DELETE FROM suchen_ohne_treffer")
        assert "suchen_ohne_treffer.woche <" in sql
        assert date(2026, 9, 7) in _params(loeschen).values()
        assert geloescht == 3


class TestHaeufigste:
    def test_haeufigste_summiert_ab_woche_mit_mindestanzahl(self, repository, session):
        session.execute.return_value.all.return_value = [(AUSSAGE, 5)]

        zeilen = repository.haeufigste(date(2026, 10, 5), 2, 20)

        abfrage = session.execute.call_args.args[0]
        sql = _sql(abfrage)
        assert "sum(suchen_ohne_treffer.anzahl)" in sql
        assert "WHERE suchen_ohne_treffer.woche >=" in sql
        assert "GROUP BY suchen_ohne_treffer.statement_id" in sql
        assert "HAVING sum(suchen_ohne_treffer.anzahl) >=" in sql
        assert "ORDER BY" in sql and "DESC" in sql
        assert "LIMIT" in sql
        params = _params(abfrage)
        assert date(2026, 10, 5) in params.values()
        assert 2 in params.values()
        assert 20 in params.values()
        assert zeilen == [(AUSSAGE, 5)]
