"""
Unit-Tests fuer das RawInputRepository.

Die Datenbanksitzung ist gemockt; gepruefte Sache ist, *was* das Repository in
die Zeile schreibt und in welcher Reihenfolge es liest - nicht, ob PostgreSQL
funktioniert.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from domain.models.raw_input import RawInputSource, RawInputStatus
from repositories.raw_input_repository import RawInputRepository


def _zeile(**overrides):
    """Eine gelesene raw_inputs-Zeile nachbilden."""
    zeile = MagicMock()
    zeile.id = overrides.get("id", uuid.uuid4())
    zeile.content = overrides.get("content", "ein Satz")
    zeile.url = overrides.get("url", None)
    zeile.image_url = overrides.get("image_url", None)
    zeile.submitted_by = overrides.get("submitted_by", "testuser")
    zeile.source_channel = overrides.get("source_channel", RawInputSource.WEB.value)
    zeile.status = overrides.get("status", RawInputStatus.OPEN.value)
    zeile.created_at = overrides.get(
        "created_at", datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)
    )
    return zeile


@pytest.fixture
def session():
    """Eine gemockte SQLAlchemy-Session als Context-Manager."""
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    return session


@pytest.fixture
def repository(session):
    datenbank = MagicMock()
    datenbank.get_session.return_value = session
    with patch(
        "repositories.raw_input_repository.get_app_database", return_value=datenbank
    ):
        return RawInputRepository()


@pytest.mark.unit
class TestCreate:
    def test_create_legt_einwurf_mit_status_open_an(self, repository, session):
        """Der Eingang setzt genau einen Zustand: offen."""
        repository.create(content="ein Satz", submitted_by="testuser")

        angelegt = session.add.call_args[0][0]
        assert angelegt.status == RawInputStatus.OPEN.value
        assert angelegt.source_channel == RawInputSource.WEB.value
        assert angelegt.content == "ein Satz"
        assert angelegt.submitted_by == "testuser"
        session.commit.assert_called_once()

    def test_create_ohne_person_speichert_null(self, repository, session):
        """submitted_by ist nullable - der Share-Eingang kommt ohne Sitzung."""
        repository.create(url="https://example.org/post", submitted_by=None)

        angelegt = session.add.call_args[0][0]
        assert angelegt.submitted_by is None
        assert angelegt.url == "https://example.org/post"

    def test_create_gibt_dict_statt_orm_objekt_zurueck(self, repository, session):
        """Nach dem Schliessen der Session waere ein ORM-Objekt nicht mehr lesbar."""
        session.refresh.side_effect = lambda obj: None
        with patch.object(
            RawInputRepository, "_to_dict", return_value={"id": "abc"}
        ) as to_dict:
            ergebnis = repository.create(content="x")

        assert ergebnis == {"id": "abc"}
        to_dict.assert_called_once()


@pytest.mark.unit
class TestGetAll:
    def _query_kette(self, session, zeilen):
        query = MagicMock()
        session.query.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.limit.return_value = query
        query.offset.return_value = query
        query.all.return_value = zeilen
        query.count.return_value = len(zeilen)
        return query

    def test_get_all_liefert_dicts(self, repository, session):
        self._query_kette(session, [_zeile(content="a"), _zeile(content="b")])

        ergebnis = repository.get_all(limit=10, offset=0)

        assert [e["content"] for e in ergebnis] == ["a", "b"]
        assert ergebnis[0]["status"] == RawInputStatus.OPEN.value

    def test_get_all_paginiert(self, repository, session):
        query = self._query_kette(session, [])

        repository.get_all(limit=5, offset=10)

        query.limit.assert_called_once_with(5)
        query.offset.assert_called_once_with(10)

    def test_get_all_filtert_nicht_ohne_status(self, repository, session):
        """Ohne Statusangabe kommt der ganze Fangkorb - auch Verarbeitetes."""
        query = self._query_kette(session, [])

        repository.get_all()

        query.filter.assert_not_called()

    def test_get_all_filtert_mit_status(self, repository, session):
        query = self._query_kette(session, [])

        repository.get_all(status=RawInputStatus.OPEN.value)

        query.filter.assert_called_once()

    def test_count_zaehlt_alles(self, repository, session):
        query = self._query_kette(session, [_zeile(), _zeile(), _zeile()])

        assert repository.count() == 3
        query.filter.assert_not_called()
