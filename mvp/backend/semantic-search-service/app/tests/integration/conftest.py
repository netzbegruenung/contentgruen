"""
Integration-test harness that exercises the REAL Qdrant wiring.

Unlike the mocked unit suite (which injects ``TestEmbeddingsManager`` and therefore
passes real-wiring bugs straight through), these fixtures boot the actual
``QdrantEmbeddingsManager`` against a live Qdrant instance. They are the honest gate
for the content-registry work (registry refactor + Post/Image types); see
``docs/CONTENT_MODEL.md``.

The whole module self-skips when Qdrant is not reachable, so a Docker-less CI/unit
run stays green. Point at a different instance with ``QDRANT_URL``. In the strict mode
of ``scripts/check.sh --integration`` a missing stack aborts the run instead (``stack.py``).

PostgreSQL: ``postgres_url`` and ``wegwerf_schema`` below, helpers in ``postgres.py``.
"""

import os
import uuid

import pytest
import pytest_asyncio
import torch
from sentence_transformers import SentenceTransformer

from core.config import EMBEDDING_MODELL, Settings
from tests.integration import postgres, stack
from services.embeddings import qdrant_embeddings_manager
from services.embeddings.qdrant_embeddings_manager import QdrantEmbeddingsManager
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)

QDRANT_URL = stack.QDRANT_URL
EINBETTUNG_THREADS = 2


def pytest_configure(config):
    """Register the ``integration`` marker so ``-m integration`` and strict-markers work."""
    config.addinivalue_line(
        "markers",
        "integration: test requires a live backing stack (Qdrant/PostgreSQL).",
    )


def pytest_sessionstart(session):
    """Im Pflichtmodus vor dem ersten Test abbrechen, wenn der Stack fehlt."""
    if not stack.pflicht():
        return
    fehlend = stack.fehlende_dienste()
    if fehlend:
        pytest.exit(
            "Integrationssuite abgebrochen, Stack fehlt:\n- " + "\n- ".join(fehlend),
            returncode=pytest.ExitCode.USAGE_ERROR,
        )


# Module-level guard: skip every integration test when there is no backing stack.
requires_qdrant = pytest.mark.skipif(
    not stack.qdrant_erreichbar(),
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


@pytest.fixture(scope="session")
def einbettungsmodell():
    """Das echte Einbettungsmodell, einmal je Lauf geladen (#459).

    Jeder neue Manager laedt es sonst in ``start()`` neu; das kostete je Test Sekunden.
    Das Modell haelt keinen Zustand zwischen Aufrufen, geteilt bettet es dasselbe ein.
    Zwei Threads: Mit einem je Kern bremsen sie sich auf einem ausgelasteten Rechner
    gegenseitig aus, eine kurze Einbettung dauerte dann Sekunden statt Zehntelsekunden.
    Die Zahl gilt fuer den ganzen Testprozess; die Integrationssuite laeuft allein in ihm.
    """
    torch.set_num_threads(EINBETTUNG_THREADS)
    return SentenceTransformer(EMBEDDING_MODELL)


@pytest_asyncio.fixture
async def real_embeddings_manager(integration_settings, einbettungsmodell, monkeypatch):
    """A started, real ``QdrantEmbeddingsManager`` bound to a clean collection.

    Resets the process-wide singleton on the way in and out (the manager is a
    singleton; the autouse ``clean_singleton_state`` in the parent conftest also
    nulls ``_instance`` between tests, so we hold the object reference directly and
    drive it via the injected factory rather than the global getter). The model
    comes from ``einbettungsmodell``.
    """
    # Der Manager laedt das Modell in start() ueber diesen Importnamen, eine andere
    # Naht hat er nicht. Benennt jemand den Import um, schlaegt die Pruefung unten fehl,
    # statt dass jeder Test das Modell still neu laedt.
    monkeypatch.setattr(
        qdrant_embeddings_manager,
        "SentenceTransformer",
        lambda *_, **__: einbettungsmodell,
    )
    QdrantEmbeddingsManager._instance = None
    manager = QdrantEmbeddingsManager(integration_settings)
    await manager.start()
    try:
        assert (
            manager.model is einbettungsmodell
        ), "Modell nicht geteilt: laedt QdrantEmbeddingsManager.start() es anders?"
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


@pytest.fixture(scope="session")
def postgres_url():
    """URL eines echten PostgreSQL fuer den ganzen Lauf, siehe ``postgres.py``.

    Ist ``POSTGRES_TEST_DATABASE_URL`` gesetzt, muss die Datenbank erreichbar sein;
    sonst ein Wegwerf-Container; ohne Docker werden die Tests uebersprungen,
    in der CI und im Pflichtmodus (``stack.py``) schlagen sie fehl.
    """
    url = os.environ.get(postgres.URL_VARIABLE)
    grund = stack.postgres_fehlt()
    if grund:
        # Eine gesetzte URL muss gehen; in der CI waere Ueberspringen ein falsches Gruen.
        if url or os.environ.get("CI") or stack.pflicht():
            pytest.fail(grund)
        pytest.skip(grund)
    if url:
        yield url
        return
    with postgres.wegwerf_container() as url:
        yield url


@pytest.fixture
def wegwerf_schema(postgres_url):
    """Ein leeres Schema je Test; wird danach mit allem Inhalt geloescht."""
    with postgres.schema(postgres_url) as db:
        yield db
