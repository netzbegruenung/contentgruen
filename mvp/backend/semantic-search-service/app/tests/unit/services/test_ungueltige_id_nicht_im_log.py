"""
Eine ungueltige ID steht nicht in der Fehlerzeile (#422).

content_id und report_id kommen als freier Text aus Pfad oder Rumpf; ist der Wert
keine UUID, ist er beliebige Eingabe und gehoert nicht ins Log.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from repositories.content_report_repository import ContentReportRepository
from repositories.interfaces.moderation_repository import IModerationRepository
from services.moderation_service import ModerationService
from services.usage_tracking_service import UsageTrackingService

EINGABE = "Waermepumpe-im-Altbau-422"


@pytest.fixture
def nutzung():
    with patch(
        "services.usage_tracking_service.get_usage_repository",
        return_value=MagicMock(),
    ):
        return UsageTrackingService()


@pytest.fixture
def moderation():
    report_repo = MagicMock(spec=ContentReportRepository)
    report_repo.has_report_from_user = MagicMock(return_value=False)
    return ModerationService(
        report_repo=report_repo, moderation_repo=MagicMock(spec=IModerationRepository)
    )


@pytest.mark.unit
class TestNutzungMitUngueltigerId:
    def test_track_content_usage_ungueltige_id_nicht_im_log(self, nutzung, caplog):
        caplog.set_level(logging.DEBUG)

        assert nutzung.track_content_usage(content_id=EINGABE) is False

        assert "Invalid content ID format" in caplog.text
        assert EINGABE not in caplog.text

    def test_get_content_usage_ungueltige_id_nicht_im_log(self, nutzung, caplog):
        caplog.set_level(logging.DEBUG)

        assert nutzung.get_content_usage(EINGABE) == 0

        assert "Invalid content ID format" in caplog.text
        assert EINGABE not in caplog.text


@pytest.mark.unit
@pytest.mark.asyncio
class TestModerationMitUngueltigerId:
    async def test_report_content_ungueltige_id_nicht_im_log(self, moderation, caplog):
        caplog.set_level(logging.DEBUG)

        assert not await moderation.report_content(
            EINGABE, "commentary", "spam", user_id="person-1"
        )

        assert "Invalid content_id format" in caplog.text
        assert EINGABE not in caplog.text

    async def test_dismiss_report_ungueltige_id_nicht_im_log(self, moderation, caplog):
        caplog.set_level(logging.DEBUG)

        assert not await moderation.dismiss_report(EINGABE, "admin-1")

        assert "Invalid report_id format" in caplog.text
        assert EINGABE not in caplog.text
