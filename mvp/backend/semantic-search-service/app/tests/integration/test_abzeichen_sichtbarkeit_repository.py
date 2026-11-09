"""
Die Zustimmung zur Sichtbarkeit der Meilenstein-Abzeichen (#351), gegen ein echtes
PostgreSQL. Wegwerf-Schema aus der Fixture ``datenbank`` von ``test_loeschkommando.py``.
"""

import pytest
from sqlalchemy import text

from repositories.abzeichen_sichtbarkeit_repository import (
    AbzeichenSichtbarkeitRepository,
)
from tests.integration.test_loeschkommando import datenbank  # noqa: F401

pytestmark = pytest.mark.integration


class TestAbzeichenSichtbarkeit:
    def test_nie_gefragt(self, datenbank):  # noqa: F811
        assert AbzeichenSichtbarkeitRepository(datenbank).lesen("kim-1") is None

    def test_es_gilt_die_juengste_antwort(self, datenbank):  # noqa: F811
        repo = AbzeichenSichtbarkeitRepository(datenbank)
        repo.antworten("kim-1", True, "2026-11-09")
        repo.antworten("kim-1", False, "2026-11-09")

        antwort = repo.lesen("kim-1")
        assert antwort.zeigen is False
        assert antwort.wortlaut == "2026-11-09"

    def test_dieselbe_antwort_zweimal_ist_eine_zeile(self, datenbank):  # noqa: F811
        repo = AbzeichenSichtbarkeitRepository(datenbank)
        repo.antworten("kim-1", True, "2026-11-09")
        repo.antworten("kim-1", True, "2026-11-09")

        with datenbank.get_session() as c:
            anzahl = c.execute(
                text(
                    "SELECT count(*) FROM abzeichen_sichtbarkeit"
                    " WHERE user_id = 'kim-1'"
                )
            ).scalar()
        assert anzahl == 1

    def test_zeigende_nur_mit_juengstem_ja(self, datenbank):  # noqa: F811
        repo = AbzeichenSichtbarkeitRepository(datenbank)
        repo.antworten("kim-1", True, "2026-11-09")
        repo.antworten("bo-2", True, "2026-11-09")
        repo.antworten("bo-2", False, "2026-11-09")
        repo.antworten("ali-3", False, "2026-11-09")

        assert repo.zeigende() == ["kim-1"]
