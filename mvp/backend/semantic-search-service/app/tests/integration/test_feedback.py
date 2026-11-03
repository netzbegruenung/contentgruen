"""
Feedback an das Team (#343) gegen ein echtes PostgreSQL.

Service und Repository zusammen bis in die Tabelle: Senden legt eine Zeile ohne
Kennung an, die Admin-Liste zeigt das Neueste zuerst, und die Frist loescht nach
180 Tagen. Admins markieren Feedback als erledigt und loeschen es einzeln (#425).
Dazu laufen die Migrationen auf einer Datenbank ohne die Tabelle und auf einer
mit der Tabelle von #343.

Jeder Test bekommt ein eigenes Schema und raeumt es wieder ab; Datenbank und
Schema kommen aus ``conftest.py`` (siehe ``postgres.py``).
"""

import uuid
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
MIGRATION_ERLEDIGT = postgres.MIGRATIONEN / "2026-11-03-425-feedback-erledigt.sql"

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
    _service(neue_datenbank).senden(
        "Suche findet nichts", "anna@example.org", heute=HEUTE
    )

    spalten = {
        s["name"]
        for s in inspect(neue_datenbank.engine).get_columns(
            "feedback", schema=neue_datenbank.schema
        )
    }
    assert spalten == {"id", "text", "kontakt", "eingegangen_am", "erledigt"}
    with neue_datenbank.engine.connect() as c:
        zeilen = c.execute(
            text("SELECT text, kontakt, eingegangen_am FROM feedback")
        ).all()
    assert zeilen == [("Suche findet nichts", "anna@example.org", HEUTE)]


def test_neueste_zuerst(neue_datenbank):
    service = _service(neue_datenbank)
    service.senden("alt", None, heute=GESTERN)
    service.senden("neu", None, heute=HEUTE)

    assert [e.text for e in service.neueste()] == ["neu", "alt"]
    assert service.neueste(limit=1)[0].eingegangen_am == HEUTE


def _id(service: FeedbackService, text_: str) -> uuid.UUID:
    return next(e.id for e in service.neueste() if e.text == text_)


def test_erledigt_setzen_filtert_und_laesst_sich_zuruecknehmen(neue_datenbank):
    service = _service(neue_datenbank)
    service.senden("offen", None, heute=HEUTE)
    service.senden("bearbeitet", None, heute=GESTERN)
    bearbeitet = _id(service, "bearbeitet")

    eintrag = service.erledigt_setzen(bearbeitet, True)

    assert eintrag.erledigt is True
    assert eintrag.eingegangen_am == GESTERN
    assert [e.text for e in service.neueste(erledigt=False)] == ["offen"]
    assert [e.text for e in service.neueste(erledigt=True)] == ["bearbeitet"]
    assert [e.text for e in service.neueste()] == ["offen", "bearbeitet"]

    assert service.erledigt_setzen(bearbeitet, False).erledigt is False
    assert service.neueste(erledigt=True) == []


def test_erledigt_setzen_fuer_unbekanntes_feedback(neue_datenbank):
    assert _service(neue_datenbank).erledigt_setzen(uuid.uuid4(), True) is None


def test_einzeln_loeschen_loescht_nur_diese_zeile(neue_datenbank):
    service = _service(neue_datenbank)
    service.senden("weg damit", "anna@example.org", heute=HEUTE)
    service.senden("bleibt", None, heute=HEUTE)
    weg = _id(service, "weg damit")

    assert service.loeschen(weg) is True

    assert [e.text for e in service.neueste()] == ["bleibt"]
    assert service.loeschen(weg) is False


def test_frist_loescht_auch_erledigtes(neue_datenbank):
    service = _service(neue_datenbank)
    service.senden("zu alt", None, heute=ZU_ALT)
    service.erledigt_setzen(_id(service, "zu alt"), True)

    assert service.alte_loeschen(heute=HEUTE) == 1


def test_frist_loescht_nach_180_tagen(neue_datenbank):
    service = _service(neue_datenbank)
    service.senden("zu alt", "anna@example.org", heute=ZU_ALT)
    service.senden("gerade noch", None, heute=LETZTER_TAG)
    service.senden("frisch", None, heute=HEUTE)

    assert service.alte_loeschen(heute=HEUTE) == 1
    assert [e.text for e in service.neueste()] == ["frisch", "gerade noch"]


def test_migration_erledigt_macht_vorhandenes_feedback_offen(postgres_url):
    with postgres.schema(postgres_url, "itest_fb") as db:
        postgres.migration(db, MIGRATION)
        with db.engine.begin() as c:
            c.execute(
                text(
                    "INSERT INTO feedback (id, text, eingegangen_am) "
                    "VALUES (gen_random_uuid(), 'von vorher', :tag)"
                ),
                {"tag": GESTERN},
            )

        postgres.migration(db, MIGRATION_ERLEDIGT)

        assert [e.text for e in _service(db).neueste(erledigt=False)] == ["von vorher"]


def test_migration_legt_die_tabelle_an_und_darf_zweimal_laufen(postgres_url):
    with postgres.schema(postgres_url, "itest_fb") as db:
        postgres.migration(db, MIGRATION)
        postgres.migration(db, MIGRATION)
        postgres.migration(db, MIGRATION_ERLEDIGT)
        postgres.migration(db, MIGRATION_ERLEDIGT)

        _service(db).senden("nach der Migration", None, heute=HEUTE)

        assert [e.text for e in _service(db).neueste()] == ["nach der Migration"]
