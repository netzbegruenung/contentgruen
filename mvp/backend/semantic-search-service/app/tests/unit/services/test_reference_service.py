"""
Unit tests for ReferenceService
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from services.content.reference_service import ReferenceService
from domain.models.reference import Reference, ReferenceDbEntry, ReferenceSearchResult
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin
from core.config import Settings


@pytest.fixture
def mock_settings():
    """Create mock settings"""
    settings = Mock(spec=Settings)
    return settings


@pytest.fixture
def mock_repository_factory():
    """Create mock repository factory"""
    factory = Mock()
    factory.create_reference_repository = Mock()
    factory.create_content_repository = Mock()
    return factory


@pytest.fixture
def reference_service(mock_settings, mock_repository_factory):
    """Create ReferenceService instance with mocked dependencies"""
    service = ReferenceService(mock_settings, mock_repository_factory)
    return service


class TestReferenceService:
    """Test suite for ReferenceService"""


@pytest.mark.asyncio
class TestHerkunftErgaenzen:
    """Link und Beschreibung an den Herkuenften eines Beitrags, fuer die Karte."""

    def _beitrag(self, *refs):
        from types import SimpleNamespace

        return SimpleNamespace(references=list(refs))

    def _ref(self, description=None):
        from types import SimpleNamespace

        return SimpleNamespace(
            reference_id=uuid4(),
            description=description,
            reference_text=None,
            reference_description=None,
        )

    async def test_herkunft_ergaenzen_notiz_vor_globalem_text(self, reference_service):
        mit_notiz, ohne_notiz = self._ref("Seite 12"), self._ref()
        reference_service.get = MagicMock(
            side_effect=lambda _id: _async(
                Mock(reference_string="https://beispiel.de/studie", text="Die Studie")
            )
        )

        await reference_service.herkunft_ergaenzen(self._beitrag(mit_notiz, ohne_notiz))

        assert mit_notiz.reference_text == "https://beispiel.de/studie"
        assert mit_notiz.reference_description == "Seite 12"
        assert ohne_notiz.reference_description == "Die Studie"

    async def test_herkunft_ergaenzen_fehler_laesst_die_naechste_nicht_aus(
        self, reference_service
    ):
        kaputt, heil = self._ref(), self._ref()
        antworten = iter([ValueError("weg"), Mock(reference_string="u", text="t")])

        async def get(_id):
            antwort = next(antworten)
            if isinstance(antwort, Exception):
                raise antwort
            return antwort

        reference_service.get = get

        await reference_service.herkunft_ergaenzen(self._beitrag(kaputt, heil))

        assert kaputt.reference_text is None
        assert heil.reference_text == "u"

    async def test_herkunft_ergaenzen_ohne_herkuenfte_fragt_nichts(
        self, reference_service
    ):
        from types import SimpleNamespace

        reference_service.get = MagicMock()

        await reference_service.herkunft_ergaenzen(SimpleNamespace(references=None))

        reference_service.get.assert_not_called()


async def _async(wert):
    return wert
