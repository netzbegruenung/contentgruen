"""
Meldegrund „Erfunden oder sachlich falsch“ (#423) gegen ein echtes PostgreSQL.

Service und Repository zusammen bis in die Tabelle: Eine Meldung mit dem neuen
Grund wird gespeichert und steht in der Admin-Liste; Meldungen mit den bisherigen
Gruenden bleiben, wie sie sind. Die Spalte ist ein freier Text, eine Migration
braucht der neue Grund nicht.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

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
    # Die echte AppDatabase auf dem Wegwerf-Schema: Das Repository committet
    # selbst, was die Test-Sitzungen aus postgres.py (sessions.begin) nicht vertragen.
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


async def test_erfunden_oder_sachlich_falsch_steht_in_der_admin_liste(service):
    beitrag = str(uuid.uuid4())

    assert await service.report_content(
        beitrag,
        "commentary",
        "fabricated_or_false",
        user_id="person-1",
        description="Die Zahl im zweiten Satz stimmt nicht",
    )

    [meldung] = await service.get_pending_reports()
    assert meldung["content_id"] == beitrag
    assert meldung["reason"] == "fabricated_or_false"
    assert meldung["description"] == "Die Zahl im zweiten Satz stimmt nicht"


async def test_bestehende_meldungen_bleiben_unveraendert(service, datenbank):
    with datenbank.get_session() as s:
        for grund in ("spam", "inappropriate", "duplicate", "other"):
            s.add(
                ContentReport(
                    content_id=uuid.uuid4(),
                    content_type="commentary",
                    reported_by_session_id="sitzung",
                    reason=grund,
                )
            )

    await service.report_content(
        str(uuid.uuid4()), "commentary", "fabricated_or_false", user_id="person-1"
    )

    gruende = sorted(m["reason"] for m in await service.get_pending_reports())
    assert gruende == sorted(
        ["spam", "inappropriate", "duplicate", "other", "fabricated_or_false"]
    )
