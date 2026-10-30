"""
Muster-Hinweise fuer Admins (#352) gegen ein echtes PostgreSQL: zwei Konten, die
innerhalb von sieben Tagen jeweils einen Beitrag des anderen nutzen. Wegwerf-Schema aus der
Fixture ``datenbank`` von ``test_loeschkommando.py``.
"""

import threading
from datetime import date, datetime, time, timedelta, timezone

import pytest

from repositories.muster_hinweis_repository import MusterHinweisRepository
from repositories.usage_tracking_repository import UsageTrackingRepository
from services.muster_hinweise_service import (
    MUSTER_FENSTER_TAGE,
    MUSTER_FRIST_TAGE,
    MusterHinweiseService,
)
from tests.integration.test_loeschkommando import datenbank  # noqa: F401

pytestmark = pytest.mark.integration

MONTAG = date(2026, 10, 26)


def _um(tag: date) -> datetime:
    return datetime.combine(tag, time(12), timezone.utc)


@pytest.fixture
def dienst(datenbank):  # noqa: F811
    return MusterHinweiseService(
        MusterHinweisRepository(datenbank),
        UsageTrackingRepository(datenbank),
    )


class TestMusterHinweise:
    def test_nutzung_melden_gegenseitig_am_selben_tag_wird_hinweis(self, dienst):
        dienst.nutzung_melden("kim-1", "bo-2", _um(MONTAG))
        assert dienst.hinweise() == []

        dienst.nutzung_melden("bo-2", "kim-1", _um(MONTAG))

        [hinweis] = dienst.hinweise()
        assert (hinweis.konto_a, hinweis.konto_b) == ("bo-2", "kim-1")
        assert (hinweis.tage, hinweis.erster_tag, hinweis.letzter_tag) == (
            1,
            MONTAG,
            MONTAG,
        )

    def test_nutzung_melden_einseitig_kein_hinweis(self, dienst):
        for _ in range(3):
            dienst.nutzung_melden("kim-1", "bo-2", _um(MONTAG))

        assert dienst.hinweise() == []

    def test_nutzung_melden_gegenseitig_innerhalb_des_fensters_wird_hinweis(
        self, dienst
    ):
        spaeter = MONTAG + timedelta(MUSTER_FENSTER_TAGE - 1)
        dienst.nutzung_melden("kim-1", "bo-2", _um(MONTAG))
        dienst.nutzung_melden("bo-2", "kim-1", _um(spaeter))

        [hinweis] = dienst.hinweise()
        assert (hinweis.tage, hinweis.erster_tag, hinweis.letzter_tag) == (
            1,
            spaeter,
            spaeter,
        )

    def test_nutzung_melden_nach_dem_fenster_kein_hinweis(self, dienst):
        dienst.nutzung_melden("kim-1", "bo-2", _um(MONTAG))
        dienst.nutzung_melden(
            "bo-2", "kim-1", _um(MONTAG + timedelta(MUSTER_FENSTER_TAGE))
        )

        assert dienst.hinweise() == []

    def test_fristen_anwenden_verwirft_paar_pruefwerte_nach_dem_fenster(self, dienst):
        """Nach dem Lauf ist die alte Richtung weg, auch wenn noch jemand fragt."""
        dienst.nutzung_melden("kim-1", "bo-2", _um(MONTAG))

        dienst.fristen_anwenden(MONTAG + timedelta(MUSTER_FENSTER_TAGE))
        # Ein Nachzuegler mit altem Zeitstempel, noch im Fenster des ersten Tages.
        dienst.nutzung_melden("bo-2", "kim-1", _um(MONTAG + timedelta(1)))

        assert dienst.hinweise() == []

    def test_nutzung_melden_zaehlt_tage_nicht_nutzungen(self, dienst):
        for tag in [MONTAG, MONTAG + timedelta(2)]:
            for _ in range(2):
                dienst.nutzung_melden("kim-1", "bo-2", _um(tag))
                dienst.nutzung_melden("bo-2", "kim-1", _um(tag))

        [hinweis] = dienst.hinweise()
        assert (hinweis.tage, hinweis.erster_tag, hinweis.letzter_tag) == (
            2,
            MONTAG,
            MONTAG + timedelta(2),
        )

    def test_nutzung_melden_gleichzeitig_verliert_keinen_tag(self, dienst):
        """A nutzt B und B nutzt A im selben Augenblick: Der Tag zaehlt trotzdem."""
        for runde in range(10):
            a, b = f"a-{runde}", f"b-{runde}"
            start = threading.Barrier(2)

            def melden(von, an):
                start.wait()
                dienst.nutzung_melden(von, an, _um(MONTAG))

            faeden = [
                threading.Thread(target=melden, args=paar) for paar in [(a, b), (b, a)]
            ]
            for faden in faeden:
                faden.start()
            for faden in faeden:
                faden.join()

        assert len(dienst.hinweise()) == 10

    def test_nutzung_melden_eigene_und_anonyme_zaehlen_nicht(self, dienst):
        dienst.nutzung_melden("kim-1", "kim-1", _um(MONTAG))
        dienst.nutzung_melden(None, "kim-1", _um(MONTAG))
        dienst.nutzung_melden("anonymous", "kim-1", _um(MONTAG))
        dienst.nutzung_melden("kim-1", None, _um(MONTAG))

        assert dienst.hinweise() == []

    def test_fristen_anwenden_loescht_alte_hinweise(self, dienst):
        alt = MONTAG - timedelta(MUSTER_FRIST_TAGE + 1)
        for tag in [alt, MONTAG]:
            dienst.nutzung_melden(f"a-{tag}", f"b-{tag}", _um(tag))
            dienst.nutzung_melden(f"b-{tag}", f"a-{tag}", _um(tag))

        dienst.fristen_anwenden(MONTAG + timedelta(1))

        assert [h.letzter_tag for h in dienst.hinweise()] == [MONTAG]
