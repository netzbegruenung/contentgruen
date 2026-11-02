"""
Meldungen einer Person finden und ihre Angaben loeschen (#494), gegen ein echtes
PostgreSQL.

Wer ohne Konto meldet, ist nur ueber Name und E-Mail-Adresse an der Meldung zu
finden (seit #438). Auskunft (Art. 15 DSGVO) heisst: alle Meldungen mit diesen
Angaben zeigen. Loeschung (Art. 17 DSGVO) heisst: bearbeitete und abgewiesene
Meldungen gehen ganz; offene bleiben als Arbeit fuer die Moderation stehen
(Art. 16 DSA), verlieren aber Name und E-Mail-Adresse.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.orm import sessionmaker

from infrastructure.database.connection import AppDatabase
from infrastructure.database.models import Base, ContentReport
from repositories.content_report_repository import ContentReportRepository
from services.moderation_service import ModerationService

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.fixture
def datenbank(wegwerf_schema):
    Base.metadata.create_all(wegwerf_schema.engine, tables=[ContentReport.__table__])
    return wegwerf_schema


@pytest.fixture
def service(datenbank):
    app_db = AppDatabase(datenbank.url)
    app_db.engine = datenbank.engine
    app_db.SessionLocal = sessionmaker(autoflush=False, bind=datenbank.engine)
    with patch(
        "repositories.content_report_repository.get_app_database",
        return_value=app_db,
    ):
        yield ModerationService(
            report_repo=ContentReportRepository(), moderation_repo=AsyncMock()
        )


def _meldung(datenbank, *, status="pending", name=None, email=None, text=None):
    kennung = uuid.uuid4()
    with datenbank.get_session() as s:
        s.add(
            ContentReport(
                id=kennung,
                content_id=uuid.uuid4(),
                content_type="commentary",
                reported_by_session_id=(
                    "anon:x" if status != "pending" else "besucher:y"
                ),
                reason="other",
                description=text,
                status=status,
                reviewed_at=None if status == "pending" else datetime.now(timezone.utc),
                melder_name=name,
                melder_email=email,
                guter_glaube=True,
            )
        )
    return str(kennung)


def _alle(datenbank):
    with datenbank.get_session() as s:
        return {
            str(m.id): (m.status, m.melder_name, m.melder_email, m.description)
            for m in s.query(ContentReport).all()
        }


async def test_meldungen_einer_person_findet_die_adresse_ohne_gross_und_kleinschreibung(
    service, datenbank
):
    eigene = _meldung(datenbank, email="Anna.B@example.org", text="erste")
    erledigte = _meldung(
        datenbank, status="dismissed", email="anna.b@example.org", text="zweite"
    )
    _meldung(datenbank, email="bert@example.org")
    _meldung(datenbank, name="Anna B.")

    gefunden = await service.meldungen_einer_person(email="ANNA.B@example.org")

    assert {m["id"] for m in gefunden} == {eigene, erledigte}
    assert {m["description"] for m in gefunden} == {"erste", "zweite"}


async def test_meldungen_einer_person_sucht_nur_ganze_angaben(service, datenbank):
    """Kein Teiltreffer: Eine Auskunft darf keine Meldungen anderer zeigen."""
    _meldung(datenbank, email="anna@example.org", name="Anna Beispiel")
    _meldung(datenbank, email="hanna@example.org", name="Hanna")

    assert await service.meldungen_einer_person(email="anna@example.org")
    assert len(await service.meldungen_einer_person(email="anna@example.org")) == 1
    assert await service.meldungen_einer_person(name="anna") == []
    assert await service.meldungen_einer_person(email="%@example.org") == []
    assert await service.meldungen_einer_person(name="_nna") == []


async def test_meldungen_einer_person_name_und_adresse_muessen_beide_passen(
    service, datenbank
):
    beide = _meldung(datenbank, email="anna@example.org", name="Anna Beispiel")
    _meldung(datenbank, email="anna@example.org")
    _meldung(datenbank, name="Anna Beispiel", email="andere@example.org")

    gefunden = await service.meldungen_einer_person(
        email="anna@example.org", name="  anna beispiel "
    )

    assert [m["id"] for m in gefunden] == [beide]


async def test_meldungen_einer_person_ohne_angabe_ist_ein_fehler(service):
    with pytest.raises(ValueError):
        await service.meldungen_einer_person()
    with pytest.raises(ValueError):
        await service.meldungen_einer_person(email="  ", name="")


async def test_angaben_loeschen_entfernt_erledigte_und_leert_offene(service, datenbank):
    offen = _meldung(datenbank, email="anna@example.org", name="Anna", text="Grund")
    bearbeitet = _meldung(datenbank, status="reviewed", email="Anna@example.org")
    abgewiesen = _meldung(datenbank, status="dismissed", email="anna@example.org")
    fremd = _meldung(datenbank, status="reviewed", email="bert@example.org")

    ergebnis = await service.angaben_der_person_loeschen(email="anna@example.org")

    assert ergebnis.geloescht == 2
    assert ergebnis.angaben_entfernt == 1
    alle = _alle(datenbank)
    assert bearbeitet not in alle and abgewiesen not in alle
    # Die offene Meldung bleibt Arbeit fuer die Moderation, ohne Personenbezug.
    assert alle[offen] == ("pending", None, None, "Grund")
    assert alle[fremd] == ("reviewed", None, "bert@example.org", None)
    assert await service.meldungen_einer_person(email="anna@example.org") == []


async def test_angaben_loeschen_ohne_treffer_aendert_nichts(service, datenbank):
    fremd = _meldung(datenbank, email="bert@example.org")

    ergebnis = await service.angaben_der_person_loeschen(name="Niemand")

    assert (ergebnis.geloescht, ergebnis.angaben_entfernt) == (0, 0)
    assert fremd in _alle(datenbank)


async def test_angaben_loeschen_ohne_angabe_ist_ein_fehler(service, datenbank):
    _meldung(datenbank, email="bert@example.org")

    with pytest.raises(ValueError):
        await service.angaben_der_person_loeschen()
    assert len(_alle(datenbank)) == 1
