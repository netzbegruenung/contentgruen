"""
Admin-Werte der Schalter und ihr Verlauf (#708), gegen ein echtes PostgreSQL.
Wegwerf-Schema aus der Fixture ``datenbank`` von ``test_loeschkommando.py``.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from repositories.schalter_repository import SchalterRepository
from tests.integration.test_loeschkommando import datenbank  # noqa: F401

pytestmark = pytest.mark.integration


def _zahl(datenbank, tabelle):  # noqa: F811
    with datenbank.get_session() as s:
        return s.execute(text(f"SELECT count(*) FROM {tabelle}")).scalar()


class TestSchalterRepository:
    def test_ohne_zeile_kein_admin_wert(self, datenbank):  # noqa: F811
        assert SchalterRepository(datenbank).admin_werte() == {}

    def test_zweimal_setzen_eine_zeile_zwei_im_verlauf(self, datenbank):  # noqa: F811
        repo = SchalterRepository(datenbank)
        repo.setzen("punkte", True, "admin-1")
        repo.setzen("punkte", False, "admin-2")

        assert repo.admin_werte() == {"punkte": False}
        assert _zahl(datenbank, "schalter") == 1
        with datenbank.get_session() as s:
            von = s.execute(text("SELECT geaendert_von FROM schalter")).scalar()
            verlauf = s.execute(
                text("SELECT an, geaendert_von FROM schalter_verlauf ORDER BY an DESC")
            ).all()
        assert von == "admin-2"
        assert [tuple(z) for z in verlauf] == [(True, "admin-1"), (False, "admin-2")]

    def test_mehrere_schalter_getrennt(self, datenbank):  # noqa: F811
        repo = SchalterRepository(datenbank)
        repo.setzen("punkte", True, "admin-1")
        repo.setzen("gepostet", False, "admin-1")

        assert repo.admin_werte() == {"punkte": True, "gepostet": False}

    def test_verlauf_vor_der_grenze_geht_stand_bleibt(self, datenbank):  # noqa: F811
        repo = SchalterRepository(datenbank)
        repo.setzen("punkte", True, "admin-1")
        repo.setzen("punkte", False, "admin-1")
        with datenbank.get_session() as s:
            s.execute(
                text("UPDATE schalter_verlauf SET geaendert_am = :alt WHERE an"),
                {"alt": datetime.now(timezone.utc) - timedelta(days=400)},
            )

        grenze = datetime.now(timezone.utc) - timedelta(days=365)
        assert repo.verlauf_loeschen_vor(grenze) == 1

        assert _zahl(datenbank, "schalter_verlauf") == 1
        assert repo.admin_werte() == {"punkte": False}
