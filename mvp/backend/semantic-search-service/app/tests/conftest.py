"""
Test configuration using the new dependency injection architecture.

This module provides clean test fixtures that use dependency injection
instead of complex mocking, making tests simpler and more maintainable.
"""

import datetime
import json
import os
import pytest
import uuid
import threading
from typing import Optional
from unittest.mock import MagicMock, patch

# Set test environment before any imports
os.environ["TESTING"] = "true"
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Patch logging before imports to prevent initialization errors
import logging


def mock_get_logger(name):
    """Mock logger that doesn't require initialization."""
    return logging.getLogger(name)


# Apply the patch globally before importing any modules
patch("core.logging.get_logger", mock_get_logger).start()

# Now import the rest
from core.config import Settings
from domain.models.content_type import ContentType
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin
from domain.interfaces.embeddings_manager import IEmbeddingsManager
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from tests.fixtures.embeddings_manager import TestEmbeddingsManager


@pytest.fixture(scope="session")
def test_settings():
    """Test settings fixture."""
    return Settings(
        data_path="/tmp/test_data",
        metadata_path="/tmp/test_metadata",
        index_initial_data_path="/tmp/test_initial_data",
        qdrant_url="http://localhost:6333",
        qdrant_collection="test_collection",
        initial_data_author="test_system",
    )


@pytest.fixture
def test_embeddings_manager():
    """
    Create a test embeddings manager for each test.
    This ensures complete test isolation without singleton issues.
    """
    return TestEmbeddingsManager()


@pytest.fixture
def repository_factory(test_embeddings_manager):
    """
    Create a repository factory with injected test embeddings manager.
    """
    return QdrantRepositoryFactory(embeddings_manager=test_embeddings_manager)


@pytest.fixture(autouse=True)
def clean_singleton_state():
    """
    Clean up singleton state before and after each test.
    This ensures tests don't interfere with each other.
    """
    # Clear singleton before test
    from services.embeddings.qdrant_embeddings_manager import QdrantEmbeddingsManager

    QdrantEmbeddingsManager._instance = None
    QdrantEmbeddingsManager._lock = threading.Lock()

    yield

    # Clear singleton after test
    QdrantEmbeddingsManager._instance = None
    QdrantEmbeddingsManager._lock = threading.Lock()


@pytest.fixture(autouse=True)
def anzeigenamen_ohne_datenbank(monkeypatch):
    """
    Der AnzeigenameService haengt an jeder angemeldeten Antwort. Ohne diesen Ersatz
    baute der erste Aufruf das echte UserRepository, und get_app_database() verbaende
    sich mit dem PostgreSQL aus den Settings - auf der Dev-VM ist das der laufende
    Dev-Stack. Der Ersatz kennt keine Namen; Tests, die welche brauchen, stellen sie
    ueber ``anzeigenamen_ohne_datenbank.anzeigenamen.return_value`` ein.
    """
    import services.anzeigename_service as modul

    repository = MagicMock()
    repository.anzeigenamen.return_value = {}
    monkeypatch.setattr(
        modul, "_anzeigename_service", modul.AnzeigenameService(repository)
    )
    yield repository


@pytest.fixture(autouse=True)
def suchen_ohne_treffer_ohne_datenbank(monkeypatch):
    """
    Jede Suche meldet sich bei der Kennzahl "Suchen ohne Treffer", und ein
    Hintergrund-Task loescht alte Wochen. Ohne diesen Ersatz baute der erste
    Aufruf das echte Repository und verbaende sich mit dem PostgreSQL aus den
    Settings (siehe anzeigenamen_ohne_datenbank).
    """
    import repositories.suchen_ohne_treffer_repository as modul

    repository = MagicMock()
    repository.haeufigste.return_value = []
    monkeypatch.setattr(modul, "_repository", repository)
    yield repository


@pytest.fixture(autouse=True)
def aussage_themen_ohne_datenbank(monkeypatch):
    """
    Die Suche haengt die Themen an ihre Aussagen (``get_aussage_themen_service``).
    Ohne diesen Ersatz baute der erste Aufruf das echte Repository und verbaende
    sich mit dem PostgreSQL aus den Settings (siehe anzeigenamen_ohne_datenbank);
    in der CI gibt es dort keins (#460). Der Ersatz kennt keine Themen.
    """
    import repositories.aussage_themen_repository as modul

    repository = MagicMock()
    repository.themen_von.return_value = {}
    repository.zuordnungen.return_value = {}
    monkeypatch.setattr(modul, "_repository", repository)
    yield repository


# Sperrgrund und Begruendung fuer Tests, die nur sperren muessen (#448).
GRUND_FUER_SPERRE = {"sperrgrund": "ohne_bezug", "begruendung": "Kein Bezug zum Zweck."}


def create_base_content_fields(**overrides):
    """
    Create base content fields with all required attributes.

    This is a helper function, not a fixture, so it can accept parameters.
    """
    now = datetime.datetime.now()
    base_fields = {
        "created": now,
        "last_modified": now,
        "updated": now,  # Some models expect this field
        "original_author": "test_user",
        "last_modified_by": "test_user",
        "authors": [],
        "edit_history": [],
        "status": ContentStatus.VISIBLE,
        "origin": ContentOrigin.INITIAL_DATA,
        "most_similar_similarity_score": None,
        "most_similar_content_id": None,
        "report_count": 0,
        "is_archived": False,
        "report_flagged": False,
        "rejection_reason": None,
        "block_reason": None,
    }
    base_fields.update(overrides)
    return base_fields


def add_aussage_mit_verweis(speicher, beitrag_id: str) -> str:
    """
    Eine Aussage im TestEmbeddingsManager anlegen, deren einziger Antwortvorschlag
    beitrag_id ist; gibt ihre Kennung zurueck.
    """
    aussage_id = str(uuid.uuid4())
    speicher.add_test_data(
        "statement",
        [
            {
                **create_base_content_fields(),
                "id": aussage_id,
                "replysuggestions": json.dumps([{"id": beitrag_id}]),
                "replysuggestions_count": 1,
            }
        ],
    )
    return aussage_id


# Test data factories for common content types
def create_statement_data(**overrides):
    """Create test data for a statement."""
    data = {
        "text": "Climate change requires immediate action",
        "title": "Climate Action Statement",
        "party": "Green Party",
        "author": "Test Author",
        "references": [],
        "sources": [],
        "replySuggestions": [],
        "replysuggestions": [],  # Alternative spelling
        "replysuggestions_count": 0,
    }
    data.update(overrides)
    return data


def create_commentary_data(**overrides):
    """Create test data for a commentary."""
    data = {
        "text": "This is a comprehensive analysis of the climate situation",
        "title": "Climate Analysis",
        "short_text": "Climate analysis",
        "long_text": "This is a comprehensive analysis of the climate situation",
        "references": [],
        "references_count": 0,
    }
    data.update(overrides)
    return data


def create_reference_data(**overrides):
    """Create test data for a reference."""
    data = {
        "text": "Scientific study on climate change impacts",
        "reference_string": "https://example.com/study",
    }
    data.update(overrides)
    return data


def create_generic_text_data(**overrides):
    """Create test data for generic text."""
    data = {
        "text": "General information about environmental policies",
        "title": "Environmental Policy Info",
        "references": [],
        "references_count": 0,
    }
    data.update(overrides)
    return data


def create_image_data(**overrides):
    """Create test data for an image."""
    data = {
        "title": "Test Image Title",
        "image_url": "https://example.com/test-image.jpg",
        "text": "Protesters holding signs at a climate rally",
        "description_model": None,
    }
    data.update(overrides)
    return data
