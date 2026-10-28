"""
Unit-Tests fuer Feedback an das Team (#343).

Das Repository ist gemockt. Geprueft werden der Tag beim Senden, die Frist von
AUFBEWAHRUNG_TAGE und der Hintergrund-Task, der nach einem Fehler weiterlaeuft.
"""

import asyncio
import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from services.feedback_service import (
    AUFBEWAHRUNG_TAGE,
    FeedbackEintrag,
    FeedbackService,
    aufbewahrungsgrenze,
    loeschen_im_takt,
)

pytestmark = pytest.mark.unit

HEUTE = date(2026, 10, 27)


@pytest.fixture
def repository():
    return Mock()


class TestSenden:
    def test_senden_speichert_text_kontakt_und_den_utc_tag(self, repository):
        with patch("services.feedback_service.heute_utc", return_value=HEUTE):
            FeedbackService(repository).senden("Hallo", "anna@example.org")

        repository.anlegen.assert_called_once_with("Hallo", "anna@example.org", HEUTE)

    def test_senden_ohne_kontakt_speichert_keinen(self, repository):
        FeedbackService(repository).senden("Hallo", None, heute=HEUTE)

        repository.anlegen.assert_called_once_with("Hallo", None, HEUTE)


class TestNeueste:
    def test_neueste_liefert_eintraege_ohne_zeilenobjekt(self, repository):
        kennung = uuid.uuid4()
        repository.neueste.return_value = [
            SimpleNamespace(id=kennung, text="Gut", kontakt=None, eingegangen_am=HEUTE)
        ]

        eintraege = FeedbackService(repository).neueste(limit=5)

        repository.neueste.assert_called_once_with(5)
        assert eintraege == [FeedbackEintrag(kennung, "Gut", None, HEUTE)]


class TestFrist:
    def test_aufbewahrungsgrenze_behaelt_genau_die_frist(self):
        assert AUFBEWAHRUNG_TAGE == 180
        assert aufbewahrungsgrenze(HEUTE) == date(2026, 4, 30)

    def test_alte_loeschen_loescht_vor_der_aufbewahrungsgrenze(self, repository):
        repository.loeschen_vor.return_value = 3

        assert FeedbackService(repository).alte_loeschen(heute=HEUTE) == 3
        repository.loeschen_vor.assert_called_once_with(date(2026, 4, 30))

    @pytest.mark.asyncio
    async def test_loeschen_im_takt_loescht_sofort_und_laeuft_nach_fehler_weiter(
        self, repository
    ):
        repository.loeschen_vor = Mock(side_effect=[RuntimeError("weg"), 0, 0])

        task = asyncio.create_task(
            loeschen_im_takt(FeedbackService(repository), takt_sekunden=0)
        )
        while repository.loeschen_vor.call_count < 2:
            await asyncio.sleep(0.01)
        task.cancel()

        assert repository.loeschen_vor.call_count >= 2
