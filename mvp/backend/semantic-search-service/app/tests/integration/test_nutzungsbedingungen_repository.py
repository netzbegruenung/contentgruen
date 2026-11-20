"""
Zustimmung zu den Nutzungsbedingungen in der App, gegen ein echtes PostgreSQL.
Wegwerf-Schema aus der Fixture ``datenbank`` von ``test_loeschkommando.py``.
"""

import pytest
from sqlalchemy import text

from domain.nutzungsbedingungen import AKTUELLER_STAND
from repositories.nutzungsbedingungen_repository import NutzungsbedingungenRepository
from services.nutzungsbedingungen_service import NutzungsbedingungenService
from tests.integration.test_loeschkommando import datenbank  # noqa: F401

pytestmark = pytest.mark.integration


def _zeilen(datenbank, kennung="kim-1"):  # noqa: F811
    with datenbank.get_session() as c:
        return c.execute(
            text(
                "SELECT count(*) FROM nutzungsbedingungen_zustimmungen"
                " WHERE user_id = :k"
            ),
            {"k": kennung},
        ).scalar_one()


class TestNutzungsbedingungen:
    def test_nie_gefragt_hat_nicht_zugestimmt(self, datenbank):  # noqa: F811
        dienst = NutzungsbedingungenService(NutzungsbedingungenRepository(datenbank))

        assert dienst.stand("kim-1") is None
        assert dienst.zugestimmt("kim-1") is False

    def test_zustimmen_wirkt_sofort_mit_stand_und_zeitpunkt(
        self, datenbank  # noqa: F811
    ):
        dienst = NutzungsbedingungenService(NutzungsbedingungenRepository(datenbank))

        dienst.zustimmen("kim-1", AKTUELLER_STAND)

        assert dienst.zugestimmt("kim-1") is True
        zustimmung = dienst.stand("kim-1")
        assert zustimmung.stand == AKTUELLER_STAND
        assert zustimmung.zugestimmt_am.tzinfo is not None
        assert dienst.zugestimmt("andere") is False

    def test_doppelt_absenden_ist_eine_zeile(self, datenbank):  # noqa: F811
        repo = NutzungsbedingungenRepository(datenbank)

        repo.zustimmen("kim-1", AKTUELLER_STAND)
        repo.zustimmen("kim-1", AKTUELLER_STAND)

        assert _zeilen(datenbank) == 1

    def test_neuer_stand_ist_eine_neue_zeile_und_gilt(self, datenbank):  # noqa: F811
        repo = NutzungsbedingungenRepository(datenbank)
        repo.zustimmen("kim-1", "2026-11-02")

        repo.zustimmen("kim-1", AKTUELLER_STAND)

        assert _zeilen(datenbank) == 2
        assert repo.lesen("kim-1").stand == AKTUELLER_STAND
