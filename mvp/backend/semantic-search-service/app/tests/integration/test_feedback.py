"""
Feedback an das Team (#343) gegen ein echtes PostgreSQL.

Service und Repository zusammen bis in die Tabelle: Senden legt eine Zeile ohne
Kennung an, die Admin-Liste zeigt das Neueste zuerst, und die Frist loescht nach
180 Tagen. Dazu laeuft die Migration auf einer Datenbank ohne die Tabelle.

Jeder Test bekommt ein eigenes Schema und raeumt es wieder ab; Datenbank und
Schema kommen aus ``conftest.py`` (siehe ``postgres.py``).
"""

from datetime import date
from unittest.mock import patch

import pytest
from sqlalchemy import inspect, text

from infrastructure.database.models import Base, FeedbackZeile
from repositories.feedback_repository import FeedbackRepository
from services.feedback_service import FeedbackService
from tests.integration import postgres
from tests.integration.postgres import Datenbank

MIGRATION = postgres.MIGRATIONEN / "2026-10-27-feedback.sql"

HEUTE = date(2026, 10, 27)
GESTERN = date(2026, 10, 26)
# 180 Tage vor HEUTE: bleibt noch; der Tag davor geht.
LETZTER_TAG = date(2026, 4, 30)
ZU_ALT = date(2026, 4, 29)

pytestmark = pytest.mark.integration


@pytest.fixture
def neue_datenbank(postgres_url):
    with postgres.schema(postgres_url, "itest_fb") as db:
        Base.metadata.create_all(db.engine, tables=[FeedbackZeile.__table__])
        yield db


def _service(db: Datenbank) -> FeedbackService:
    with patch(
        "repositories.feedback_repository.get_app_database",
        return_value=db,
    ):
        return FeedbackService(FeedbackRepository())


def test_senden_speichert_nur_text_kontakt_und_tag(neue_datenbank):
    _service(neue_datenbank).senden("Suche findet nichts", "anna@x.org", heute=HEUTE)

    spalten = {
        s["name"]
        for s in inspect(neue_datenbank.engine).get_columns(
            "feedback", schema=neue_datenbank.schema
        )
    }
    assert spalten == {"id", "text", "kontakt", "eingegangen_am"}
    with neue_datenbank.engine.connect() as c:
        zeilen = c.execute(
            text("SELECT text, kontakt, eingegangen_am FROM feedback")
        ).all()
    assert zeilen == [("Suche findet nichts", "anna@x.org", HEUTE)]


def test_neueste_zuerst(neue_datenbank):
    service = _service(neue_datenbank)
    service.senden("alt", None, heute=GESTERN)
    service.senden("neu", None, heute=HEUTE)

    assert [e.text for e in service.neueste()] == ["neu", "alt"]
    assert service.neueste(limit=1)[0].eingegangen_am == HEUTE


def test_frist_loescht_nach_180_tagen(neue_datenbank):
    service = _service(neue_datenbank)
    service.senden("zu alt", "anna@x.org", heute=ZU_ALT)
    service.senden("gerade noch", None, heute=LETZTER_TAG)
    service.senden("frisch", None, heute=HEUTE)

    assert service.alte_loeschen(heute=HEUTE) == 1
    assert [e.text for e in service.neueste()] == ["frisch", "gerade noch"]


def test_migration_legt_die_tabelle_an_und_darf_zweimal_laufen(postgres_url):
    with postgres.schema(postgres_url, "itest_fb") as db:
        postgres.migration(db, MIGRATION)
        postgres.migration(db, MIGRATION)

        _service(db).senden("nach der Migration", None, heute=HEUTE)

        assert [e.text for e in _service(db).neueste()] == ["nach der Migration"]
