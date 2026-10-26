"""
ContentReportRepository.update_reports_by_content_id: Fehler nicht verschlucken.

Sperren setzt alle Meldungen zum Beitrag auf bearbeitet. Lieferte das Repository
bei einem Datenbankfehler still 0, meldete Sperren Erfolg, waehrend die Meldungen
offen blieben.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from repositories.content_report_repository import ContentReportRepository


@pytest.mark.unit
class TestUpdateReportsByContentId:
    def test_datenbankfehler_wird_weitergereicht(self):
        datenbank = MagicMock()
        datenbank.get_session.side_effect = RuntimeError("PostgreSQL weg")
        with patch(
            "repositories.content_report_repository.get_app_database",
            return_value=datenbank,
        ):
            repository = ContentReportRepository()

        with pytest.raises(RuntimeError):
            repository.update_reports_by_content_id(
                content_id=uuid.uuid4(), status="reviewed", reviewed_by="admin-1"
            )
