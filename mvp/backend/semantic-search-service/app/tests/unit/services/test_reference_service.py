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
