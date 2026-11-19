"""
Die Einwilligung "Punkte und Meilensteine" (#351), gegen ein echtes PostgreSQL.
Wegwerf-Schema aus der Fixture ``datenbank`` von ``test_loeschkommando.py``.
"""

import pytest
from sqlalchemy import text

from domain.punkte_einwilligung import AKTUELLER_WORTLAUT
from repositories.punkte_einwilligung_repository import PunkteEinwilligungRepository
from tests.integration.test_loeschkommando import datenbank  # noqa: F401

pytestmark = pytest.mark.integration


class TestPunkteEinwilligung:
    def test_nie_gefragt_ist_nicht_eingewilligt(self, datenbank):  # noqa: F811
        repo = PunkteEinwilligungRepository(datenbank)

        assert repo.lesen("kim-1") is None
        assert repo.eingewilligt("kim-1") is False

    def test_widerruf_ist_eine_neue_zeile_und_wirkt_sofort(
        self, datenbank  # noqa: F811
    ):
        repo = PunkteEinwilligungRepository(datenbank)
        repo.antworten("kim-1", True, AKTUELLER_WORTLAUT)
        assert repo.eingewilligt("kim-1") is True

        repo.antworten("kim-1", False, AKTUELLER_WORTLAUT)

        assert repo.eingewilligt("kim-1") is False
        with datenbank.get_session() as c:
            anzahl = c.execute(
                text("SELECT count(*) FROM punkte_einwilligung WHERE user_id = 'kim-1'")
            ).scalar_one()
        assert anzahl == 2

    def test_dieselbe_antwort_zweimal_ist_eine_zeile(self, datenbank):  # noqa: F811
        repo = PunkteEinwilligungRepository(datenbank)
        repo.antworten("kim-1", True, AKTUELLER_WORTLAUT)
        repo.antworten("kim-1", True, AKTUELLER_WORTLAUT)

        with datenbank.get_session() as c:
            anzahl = c.execute(
                text("SELECT count(*) FROM punkte_einwilligung WHERE user_id = 'kim-1'")
            ).scalar_one()
        assert anzahl == 1

    def test_alter_wortlaut_gilt_nicht(self, datenbank):  # noqa: F811
        repo = PunkteEinwilligungRepository(datenbank)
        repo.antworten("kim-1", True, "2000-01-01")

        assert repo.eingewilligt("kim-1") is False

    def test_je_kennung_getrennt(self, datenbank):  # noqa: F811
        repo = PunkteEinwilligungRepository(datenbank)
        repo.antworten("kim-1", True, AKTUELLER_WORTLAUT)

        assert repo.eingewilligt("bo-2") is False
