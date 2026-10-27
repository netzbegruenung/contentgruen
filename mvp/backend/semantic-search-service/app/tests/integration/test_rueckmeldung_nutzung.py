"""
Rueckmeldung zur Nutzung (#349) gegen ein echtes PostgreSQL.

Zwei Zahlen fuer Autoren: der Zuwachs je Beitrag in den letzten 7 Tagen (aus
``usage_events``) und wie oft ihre Beitraege seit dem letzten Besuch genutzt wurden
(gegen den zuletzt gezeigten Stand in ``gesehene_nutzung``). Wegwerf-Schema aus der
Fixture ``datenbank`` von ``test_loeschkommando.py``.
"""

import uuid
from datetime import datetime, timedelta, timezone

import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import text, update
from sqlalchemy.dialects.postgresql import insert

from infrastructure.database.models import GeseheneNutzung, UsageEvent, UsageTracking
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


def _warten_bis_blockiert(datenbank, sekunden: float = 10) -> None:  # noqa: F811
    """Bis eine andere Verbindung auf eine Sperre wartet."""
    ende = time.monotonic() + sekunden
    while time.monotonic() < ende:
        with datenbank.engine.connect() as c:
            wartend = c.execute(
                text(
                    "SELECT count(*) FROM pg_stat_activity"
                    " WHERE wait_event_type = 'Lock' AND datname = current_database()"
                )
            ).scalar()
        if wartend:
            return
        time.sleep(0.05)
    raise AssertionError("Der zweite Besuch wartet nicht auf den ersten")


class TestZuwachsLetzte7Tage:
    def test_get_nutzung_letzte_7_tage_batch_nur_die_letzten_7_tage(
        self, datenbank
    ):  # noqa: F811
        beitrag = uuid.uuid4()
        _nutzungen(datenbank, beitrag, [0, 3, 6.9, 7.1, 30])

        zuwachs = UsageTrackingRepository(datenbank).get_nutzung_letzte_7_tage_batch(
            [beitrag]
        )

        assert zuwachs == {str(beitrag): 3}

    def test_get_nutzung_letzte_7_tage_batch_ohne_nutzung_null(
        self, datenbank
    ):  # noqa: F811
        alt, ungenutzt = uuid.uuid4(), uuid.uuid4()
        _nutzungen(datenbank, alt, [10])

        zuwachs = UsageTrackingRepository(datenbank).get_nutzung_letzte_7_tage_batch(
            [alt, ungenutzt]
        )

        assert zuwachs == {str(alt): 0, str(ungenutzt): 0}

    def test_get_nutzung_letzte_7_tage_batch_leere_liste(self, datenbank):  # noqa: F811
        assert (
            UsageTrackingRepository(datenbank).get_nutzung_letzte_7_tage_batch([]) == {}
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

    def test_neu_seit_letztem_besuch_stand_sinkt_nie(self, datenbank):  # noqa: F811
        """
        Ein gesperrter Beitrag faellt aus der Summe und kommt beim Entsperren
        zurueck: Seine alte Nutzung ist dann nicht neu.
        """
        repo = GeseheneNutzungRepository(datenbank)
        repo.neu_seit_letztem_besuch(AUTORIN, nutzung_jetzt=8)

        assert repo.neu_seit_letztem_besuch(AUTORIN, nutzung_jetzt=6) == 0
        assert repo.neu_seit_letztem_besuch(AUTORIN, nutzung_jetzt=8) == 0
        assert repo.neu_seit_letztem_besuch(AUTORIN, nutzung_jetzt=9) == 1

    def test_neu_seit_letztem_besuch_gleichzeitig_beim_ersten_besuch_einmal(
        self, datenbank
    ):  # noqa: F811
        """
        Zwei Tabs oeffnen die App zugleich, bevor es eine Zeile gibt: Nur einer
        meldet die Nutzung. Der erste haelt seine Transaktion offen, bis der zweite
        nachweislich auf ihn wartet.
        """
        repo = GeseheneNutzungRepository(datenbank)
        with datenbank.get_session() as erster:
            erster.execute(
                insert(GeseheneNutzung)
                .values(user_id=AUTORIN, nutzung=0)
                .on_conflict_do_nothing(index_elements=[GeseheneNutzung.user_id])
            )
            with ThreadPoolExecutor(max_workers=1) as pool:
                zweiter = pool.submit(
                    repo.neu_seit_letztem_besuch, AUTORIN, nutzung_jetzt=5
                )
                _warten_bis_blockiert(datenbank)
                erster.execute(
                    update(GeseheneNutzung)
                    .where(GeseheneNutzung.user_id == AUTORIN)
                    .values(nutzung=5)
                )
                erster.commit()
                assert zweiter.result(timeout=10) == 0

    def test_neu_seit_letztem_besuch_je_person_getrennt(self, datenbank):  # noqa: F811
        repo = GeseheneNutzungRepository(datenbank)
        repo.neu_seit_letztem_besuch(AUTORIN, nutzung_jetzt=5)

        assert repo.neu_seit_letztem_besuch("andere", nutzung_jetzt=2) == 2
