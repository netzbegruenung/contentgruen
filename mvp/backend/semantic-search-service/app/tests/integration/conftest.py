"""
Integration-test harness that exercises the REAL Qdrant wiring.

Unlike the mocked unit suite (which injects ``TestEmbeddingsManager`` and therefore
passes real-wiring bugs straight through), these fixtures boot the actual
``QdrantEmbeddingsManager`` against a live Qdrant instance. They are the honest gate
required for the rung-1 Steps 5-6 work (registry refactor + Post type); see
``docs/RUNG_1_PLAN.md`` "Verification requirements for Steps 5-6".

The whole module self-skips when Qdrant is not reachable, so a Docker-less CI/unit
run stays green. Point at a different instance with ``QDRANT_URL``.
"""

import os
import uuid

import pytest
import pytest_asyncio
import requests

from core.config import Settings
from services.embeddings.qdrant_embeddings_manager import QdrantEmbeddingsManager
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)

QDRANT_URL = os.environ.get("QDRANT_URL", "http://localhost:6333")


def pytest_configure(config):
    """Register the ``integration`` marker so ``-m integration`` and strict-markers work."""
    config.addinivalue_line(
        "markers",
        "integration: test requires a live backing stack (Qdrant/PostgreSQL).",
    )


def _qdrant_reachable() -> bool:
    """Return True if a Qdrant instance answers /healthz at QDRANT_URL."""
    try:
        resp = requests.get(f"{QDRANT_URL}/healthz", timeout=2)
        return resp.status_code == 200
    except requests.RequestException:
        return False


# Module-level guard: skip every integration test when there is no backing stack.
requires_qdrant = pytest.mark.skipif(
    not _qdrant_reachable(),
    reason=f"Qdrant not reachable at {QDRANT_URL} (start docker-compose.local-dbs.yml)",
)


@pytest.fixture(scope="session")
def integration_settings() -> Settings:
    """Real settings pointed at the live Qdrant, with a unique throwaway collection.

    The per-run collection name keeps integration runs from colliding with dev data
    or with each other, and lets teardown drop it cleanly.
    """
    return Settings(
        data_path="/tmp/test_data",
        metadata_path="/tmp/test_metadata",
        index_initial_data_path="/tmp/test_initial_data",
        qdrant_url=QDRANT_URL,
        qdrant_collection=f"itest_{uuid.uuid4().hex[:12]}",
        initial_data_author="integration_test",
    )


@pytest_asyncio.fixture
async def real_embeddings_manager(integration_settings):
    """A started, real ``QdrantEmbeddingsManager`` bound to a clean collection.

    Resets the process-wide singleton on the way in and out (the manager is a
    singleton; the autouse ``clean_singleton_state`` in the parent conftest also
    nulls ``_instance`` between tests, so we hold the object reference directly and
    drive it via the injected factory rather than the global getter).
    """
    QdrantEmbeddingsManager._instance = None
    manager = QdrantEmbeddingsManager(integration_settings)
    await manager.start()
    try:
        yield manager
    finally:
        try:
            manager.client.delete_collection(integration_settings.qdrant_collection)
        except Exception:
            pass
        QdrantEmbeddingsManager._instance = None


@pytest.fixture
def real_repository_factory(real_embeddings_manager):
    """Repository factory wired to the real embeddings manager (real Qdrant)."""
    return QdrantRepositoryFactory(embeddings_manager=real_embeddings_manager)
