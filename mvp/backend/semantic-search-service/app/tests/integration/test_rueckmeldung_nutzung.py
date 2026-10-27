"""
Rueckmeldung zur Nutzung (#349) gegen ein echtes PostgreSQL.

Zwei Zahlen fuer Autoren: der Zuwachs je Beitrag in den letzten 7 Tagen (aus
``usage_events``) und wie oft ihre Beitraege seit dem letzten Besuch genutzt wurden
(gegen den zuletzt gezeigten Stand in ``gesehene_nutzung``). Wegwerf-Schema aus der
Fixture ``datenbank`` von ``test_loeschkommando.py``.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest

from infrastructure.database.models import UsageEvent, UsageTracking
from repositories.gesehene_nutzung_repository import GeseheneNutzungRepository
from repositories.usage_tracking_repository import UsageTrackingRepository
from tests.integration.test_loeschkommando import datenbank  # noqa: F401

pytestmark = pytest.mark.integration

AUTORIN = "autorin"


def _nutzungen(datenbank, beitrag: uuid.UUID, vor_tagen: list) -> None:  # noqa: F811
    jetzt = datetime.now(timezone.utc)
    with datenbank.get_session() as s:
        s.add(UsageTracking(content_id=beitrag, usage_count=len(vor_tagen)))
        s.flush()
        for tage in vor_tagen:
            s.add(
                UsageEvent(content_id=beitrag, timestamp=jetzt - timedelta(days=tage))
            )


class TestZuwachsLetzte7Tage:
    def test_get_recent_usage_counts_batch_nur_die_letzten_7_tage(
        self, datenbank
    ):  # noqa: F811
        beitrag = uuid.uuid4()
        _nutzungen(datenbank, beitrag, [0, 3, 6.9, 7.1, 30])

        zuwachs = UsageTrackingRepository(datenbank).get_recent_usage_counts_batch(
            [beitrag]
        )

        assert zuwachs == {str(beitrag): 3}

    def test_get_recent_usage_counts_batch_ohne_nutzung_null(
        self, datenbank
    ):  # noqa: F811
        alt, ungenutzt = uuid.uuid4(), uuid.uuid4()
        _nutzungen(datenbank, alt, [10])

        zuwachs = UsageTrackingRepository(datenbank).get_recent_usage_counts_batch(
            [alt, ungenutzt]
        )

        assert zuwachs == {str(alt): 0, str(ungenutzt): 0}

    def test_get_recent_usage_counts_batch_leere_liste(self, datenbank):  # noqa: F811
        assert (
            UsageTrackingRepository(datenbank).get_recent_usage_counts_batch([]) == {}
        )


class TestSeitLetztemBesuch:
    def test_neu_seit_letztem_besuch_erster_besuch_zeigt_alles_bisherige(
        self, datenbank
    ):  # noqa: F811
        repo = GeseheneNutzungRepository(datenbank)

        assert repo.neu_seit_letztem_besuch(AUTORIN, nutzung_jetzt=5) == 5

    def test_neu_seit_letztem_besuch_danach_nur_den_zuwachs(
        self, datenbank
    ):  # noqa: F811
        repo = GeseheneNutzungRepository(datenbank)
        repo.neu_seit_letztem_besuch(AUTORIN, nutzung_jetzt=5)

        assert repo.neu_seit_letztem_besuch(AUTORIN, nutzung_jetzt=8) == 3
        assert repo.neu_seit_letztem_besuch(AUTORIN, nutzung_jetzt=8) == 0

    def test_neu_seit_letztem_besuch_weniger_als_gesehen_ist_null(
        self, datenbank
    ):  # noqa: F811
        """Ein geloeschter Beitrag nimmt seine Nutzung aus der Summe mit."""
        repo = GeseheneNutzungRepository(datenbank)
        repo.neu_seit_letztem_besuch(AUTORIN, nutzung_jetzt=8)

        assert repo.neu_seit_letztem_besuch(AUTORIN, nutzung_jetzt=6) == 0
        assert repo.neu_seit_letztem_besuch(AUTORIN, nutzung_jetzt=7) == 1

    def test_neu_seit_letztem_besuch_je_person_getrennt(self, datenbank):  # noqa: F811
        repo = GeseheneNutzungRepository(datenbank)
        repo.neu_seit_letztem_besuch(AUTORIN, nutzung_jetzt=5)

        assert repo.neu_seit_letztem_besuch("andere", nutzung_jetzt=2) == 2
