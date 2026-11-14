"""
Angaben nach Art. 16 Abs. 2 DSA an einer Meldung (#438) gegen ein echtes PostgreSQL.

Service und Repository zusammen bis in die Tabelle: Name, E-Mail-Adresse und die
Erklaerung guten Glaubens werden gespeichert und stehen in der Admin-Liste, denn
nur die Admins koennen der meldenden Person die Entscheidung mitteilen. Meldungen
von vor #438 haben keine dieser Angaben.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from sqlalchemy.orm import sessionmaker

from domain.models.meldung import MelderAngaben
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


async def test_report_content_name_und_email_stehen_in_der_admin_liste(service):
    beitrag = str(uuid.uuid4())

    assert await service.report_content(
        beitrag,
        "commentary",
        "other",
        session_id="sitzung",
        description="Der Beitrag nennt meine Adresse",
        melder=MelderAngaben(
            guter_glaube=True,
            name="Anna Beispiel",
            email="anna@example.org",
        ),
    )

    [meldung] = await service.get_pending_reports()
    assert meldung["content_id"] == beitrag
    assert meldung["melder_name"] == "Anna Beispiel"
    assert meldung["melder_email"] == "anna@example.org"
    assert meldung["guter_glaube"] is True


async def test_report_content_ohne_name_und_email(service):
    assert await service.report_content(
        str(uuid.uuid4()),
        "commentary",
        "spam",
        user_id="person-1",
        melder=MelderAngaben(guter_glaube=True),
    )

    [meldung] = await service.get_pending_reports()
    assert meldung["melder_name"] is None
    assert meldung["melder_email"] is None
    assert meldung["guter_glaube"] is True


async def test_get_pending_reports_meldung_von_vor_438_hat_keine_angaben(
    service, datenbank
):
    with datenbank.get_session() as s:
        s.add(
            ContentReport(
                content_id=uuid.uuid4(),
                content_type="commentary",
                reported_by_session_id="sitzung",
                reason="spam",
                status="pending",
            )
        )
        s.commit()

    [meldung] = await service.get_pending_reports()
    assert meldung["melder_name"] is None
    assert meldung["melder_email"] is None
    assert meldung["guter_glaube"] is None


@pytest.mark.parametrize(
    "haekchen, gespeichert", [(True, "test.user@example.com"), (False, None)]
)
async def test_melde_route_nimmt_fuer_angemeldete_die_kontoadresse(
    service, haekchen, gespeichert
):
    """
    UX-Review B17: Angemeldete geben keine Adresse ein. Mit Haekchen landet die Adresse
    des Kontos (X-User-Email vom BFF) an der Meldung, eine im Koerper nie; ohne Haekchen
    keine.
    """
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import Mock

    from api.v1 import moderation as moderation_module
    from dependencies import get_moderation_service, get_settings
    from utils.rate_limiter import RateLimiter

    app = FastAPI()
    app.include_router(moderation_module.router, prefix="/api/v1/moderation")
    app.dependency_overrides[get_settings] = lambda: Mock()
    app.dependency_overrides[get_moderation_service] = lambda: service
    service.content_exists = AsyncMock(return_value=True)

    with patch.object(
        moderation_module,
        "report_rate_limiter",
        RateLimiter(max_requests=5, window_minutes=15),
    ):
        antwort = TestClient(app).post(
            "/api/v1/moderation/report",
            json={
                "content_id": str(uuid.uuid4()),
                "content_type": "commentary",
                "reason": "spam",
                "guter_glaube": True,
                "melder_email": "fremd@example.com",
                "bestaetigung_an_konto": haekchen,
            },
            headers={"X-User": "person-1", "X-User-Email": "test.user%40example.com"},
        )

    assert antwort.status_code == 200
    [meldung] = await service.get_pending_reports()
    assert meldung["melder_email"] == gespeichert
