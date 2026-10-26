"""
Unit-Tests fuer das SearchTrackingRepository.

Die Datenbanksitzung ist gemockt; geprueft wird, was als Suchereignis gespeichert
wuerde: Trefferzahl, Tagespseudonym und als Zeitstempel nur der Tag (Mitternacht
UTC), keine Uhrzeit.
"""

import logging
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from infrastructure.database.models import SearchEvent
from repositories.search_tracking_repository import SearchTrackingRepository

pytestmark = pytest.mark.unit


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
        "repositories.search_tracking_repository.get_app_database",
        return_value=db,
    ):
        yield SearchTrackingRepository()


def _gespeichertes_ereignis(session) -> SearchEvent:
    (ereignis,), _ = session.add.call_args
    return ereignis


class TestTrackSearch:
    def test_track_search_speichert_nur_den_tag_als_zeitstempel(
        self, repository, session
    ):
        assert repository.track_search(
            results_count=0, actor_hash="a" * 64, day=date(2026, 10, 26)
        )

        ereignis = _gespeichertes_ereignis(session)
        assert ereignis.timestamp == datetime(2026, 10, 26, tzinfo=timezone.utc)
        assert ereignis.results_count == 0
        assert ereignis.actor_hash == "a" * 64

    def test_track_search_zwei_suchen_am_selben_tag_gleicher_zeitstempel(
        self, repository, session
    ):
        """Zwei Suchen eines Tages tragen denselben Zeitstempel; eine Aussage, die
        eine von ihnen angelegt hat, laesst sich ueber die Uhrzeit keiner zuordnen."""
        repository.track_search(results_count=0, day=date(2026, 10, 26))
        frueh = _gespeichertes_ereignis(session).timestamp
        repository.track_search(results_count=3, day=date(2026, 10, 26))
        spaet = _gespeichertes_ereignis(session).timestamp

        assert frueh == spaet

    def test_timestamp_server_default_ist_nur_der_tag(self):
        """Wer ohne Zeitstempel schreibt, bekommt von PostgreSQL auch nur den Tag."""
        default = str(SearchEvent.__table__.c.timestamp.server_default.arg)

        assert "date_trunc('day'" in default
        assert "UTC" in default

    def test_track_search_protokolliert_nichts(self, repository, caplog):
        """Eine Logzeile je Suche traegt die Uhrzeit und liesse sich ueber die
        Reihenfolge den Suchereignissen des Tages zuordnen."""
        with caplog.at_level(logging.DEBUG):
            repository.track_search(results_count=0, day=date(2026, 10, 26))

        assert caplog.records == []
