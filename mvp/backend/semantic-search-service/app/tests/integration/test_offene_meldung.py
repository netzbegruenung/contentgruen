"""
ContentReportRepository.hat_offene_meldung gegen ein echtes PostgreSQL (#299).

Solange eine Meldung offen ist, laesst sich der Beitrag nicht aendern: Der Admin
soll den gemeldeten Wortlaut sehen. Bearbeitete und abgewiesene Meldungen halten
das Aendern nicht auf.
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.orm import sessionmaker

from domain.models.meldung import MelderAngaben
from infrastructure.database.connection import AppDatabase
from infrastructure.database.models import Base, ContentReport
from repositories.content_report_repository import ContentReportRepository

pytestmark = [pytest.mark.integration]


@pytest.fixture
def meldungen(wegwerf_schema):
    Base.metadata.create_all(wegwerf_schema.engine, tables=[ContentReport.__table__])
    app_db = AppDatabase(wegwerf_schema.url)
    app_db.engine = wegwerf_schema.engine
    app_db.SessionLocal = sessionmaker(autoflush=False, bind=wegwerf_schema.engine)
    with patch(
        "repositories.content_report_repository.get_app_database",
        return_value=app_db,
    ):
        yield ContentReportRepository()


def _melden(meldungen, beitrag_id) -> None:
    meldungen.create_report(
        beitrag_id,
        "commentary",
        "spam",
        melder=MelderAngaben(guter_glaube=True),
        reported_by_user_id="person-1",
    )


def test_hat_offene_meldung_nur_solange_sie_offen_ist(meldungen):
    beitrag_id = uuid.uuid4()
    _melden(meldungen, beitrag_id)

    assert meldungen.hat_offene_meldung(beitrag_id) is True
    assert meldungen.hat_offene_meldung(uuid.uuid4()) is False

    meldungen.update_reports_by_content_id(
        content_id=beitrag_id, status="dismissed", reviewed_by="admin-1"
    )

    assert meldungen.hat_offene_meldung(beitrag_id) is False
