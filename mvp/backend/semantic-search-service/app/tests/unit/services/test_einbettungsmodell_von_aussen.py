"""
Einbettungsmodell und Thread-Zahl des QdrantEmbeddingsManager von aussen (#480).

- Ein uebergebenes Modell nutzt start(), ohne ein zweites zu laden.
- Ohne Angabe laedt start() wie bisher EMBEDDING_MODELL.
- embedding_threads setzt die Thread-Zahl von Torch beim Start; ohne bleibt sie.

Ohne Qdrant und ohne Modell: Clients, Sammlung und Modell-Klasse sind ersetzt.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.config import EMBEDDING_MODELL, Settings
from services.embeddings import qdrant_embeddings_manager
from services.embeddings.qdrant_embeddings_manager import QdrantEmbeddingsManager


@pytest.fixture
def ohne_qdrant(monkeypatch):
    """Kein Qdrant noetig: Clients und Sammlungs-Pruefung sind ersetzt."""
    monkeypatch.setattr(qdrant_embeddings_manager, "QdrantClient", MagicMock())
    monkeypatch.setattr(qdrant_embeddings_manager, "AsyncQdrantClient", MagicMock())
    monkeypatch.setattr(QdrantEmbeddingsManager, "_ensure_collection", AsyncMock())


@pytest.fixture
def modell_klasse(monkeypatch):
    """Die Modell-Klasse, ueber die start() ohne Angabe laedt, gezaehlt."""
    klasse = MagicMock(name="SentenceTransformer")
    monkeypatch.setattr(qdrant_embeddings_manager, "SentenceTransformer", klasse)
    return klasse


@pytest.fixture
def threads_setzen(monkeypatch):
    """torch.set_num_threads, gezaehlt statt prozessweit wirksam."""
    setzen = MagicMock(name="set_num_threads")
    monkeypatch.setattr(qdrant_embeddings_manager.torch, "set_num_threads", setzen)
    return setzen


def _settings(**mehr) -> Settings:
    return Settings(
        data_path="/tmp/test_data",
        metadata_path="/tmp/test_metadata",
        qdrant_url="http://localhost:6333",
        qdrant_collection="test_collection",
        **mehr,
    )


class TestEinbettungsmodell:
    @pytest.mark.asyncio
    async def test_start_uebergebenes_modell_genutzt_kein_zweites_geladen(
        self, ohne_qdrant, modell_klasse
    ):
        modell = MagicMock(name="einbettungsmodell")
        manager = QdrantEmbeddingsManager(_settings(), einbettungsmodell=modell)

        await manager.start()

        assert manager.model is modell
        modell_klasse.assert_not_called()

    @pytest.mark.asyncio
    async def test_start_ohne_modell_laedt_embedding_modell(
        self, ohne_qdrant, modell_klasse
    ):
        manager = QdrantEmbeddingsManager(_settings())

        await manager.start()

        modell_klasse.assert_called_once_with(EMBEDDING_MODELL)
        assert manager.model is modell_klasse.return_value


class TestEinbettungThreads:
    @pytest.mark.asyncio
    async def test_start_mit_embedding_threads_setzt_torch_threads(
        self, ohne_qdrant, modell_klasse, threads_setzen
    ):
        manager = QdrantEmbeddingsManager(_settings(embedding_threads=2))

        await manager.start()

        threads_setzen.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_start_ohne_embedding_threads_laesst_torch_threads(
        self, ohne_qdrant, modell_klasse, threads_setzen
    ):
        manager = QdrantEmbeddingsManager(_settings())

        await manager.start()

        threads_setzen.assert_not_called()

    def test_settings_embedding_threads_unter_eins_abgelehnt(self):
        with pytest.raises(ValueError):
            _settings(embedding_threads=0)

    def test_settings_embedding_threads_aus_umgebung(self, monkeypatch):
        monkeypatch.setenv("SEMANTIC_SEARCH_EMBEDDING_THREADS", "3")

        assert _settings().embedding_threads == 3
