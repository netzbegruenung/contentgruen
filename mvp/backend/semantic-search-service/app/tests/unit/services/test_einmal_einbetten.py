"""
Eine Einbettung und eine Anfrage an den Suchindex je Suche (#304).

- einbettungen_teilen(): gleicher Text wird im Block nur einmal eingebettet.
- QdrantEmbeddingsManager.search_batch(): mehrere Suchen, ein Vektor, eine Anfrage.
- base_repository.search_batch(): je Repository dasselbe wie dessen search().

Ohne Qdrant und ohne Modell: Client und Modell sind ersetzt.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from qdrant_client.models import FieldCondition, MatchValue

from domain.models.commentary import CommentarySearchResult
from domain.models.generic_text import GenericTextSearchResult
from repositories.implementations.qdrant.base_repository import search_batch
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from services.embeddings.qdrant_embeddings_manager import (
    QdrantEmbeddingsManager,
    einbettungen_teilen,
)
from tests.fixtures.embeddings_manager import TestEmbeddingsManager


@pytest.fixture
def manager(test_settings):
    """Gestarteter Manager mit gezaehltem Modell und gefaktem Qdrant-Client."""
    manager = QdrantEmbeddingsManager(test_settings)
    manager._model = MagicMock()
    manager._model.encode.side_effect = lambda text, **_: np.array([0.1, 0.2])
    manager._async_client = MagicMock()
    manager._is_started = True
    return manager


def _payload(content_type, text):
    jetzt = "2026-10-26T12:00:00"
    return {
        "id": str(uuid.uuid4()),
        "text": text,
        "title": text,
        "content_type": content_type,
        "created": jetzt,
        "last_modified": jetzt,
        "original_author": "tester",
        "last_modified_by": "tester",
        "status": "approved",
        "origin": "manually_created",
        "references": [],
        "references_count": 0,
    }


def _punkt(score, **payload):
    return SimpleNamespace(id=uuid.uuid4(), score=score, payload=payload)


class TestEinbettungenTeilen:
    def test_encode_text_gleicher_text_im_block_einmal(self, manager):
        with einbettungen_teilen():
            erste = manager.encode_text("Tempolimit jetzt", content_type="statement")
            zweite = manager.encode_text("Tempolimit jetzt", content_type="statement")

        assert manager._model.encode.call_count == 1
        assert erste == zweite == [0.1, 0.2]

    def test_encode_text_anderer_praefix_wird_eigens_eingebettet(self, manager):
        with einbettungen_teilen():
            manager.encode_text("Tempolimit jetzt", content_type="statement")
            manager.encode_text("Tempolimit jetzt", content_type="passage")

        assert manager._model.encode.call_count == 2

    def test_encode_text_ausserhalb_des_blocks_jedes_mal(self, manager):
        with einbettungen_teilen():
            manager.encode_text("Tempolimit jetzt")
        manager.encode_text("Tempolimit jetzt")
        manager.encode_text("Tempolimit jetzt")

        assert manager._model.encode.call_count == 3

    def test_encode_text_geteilter_vektor_bleibt_unveraendert(self, manager):
        with einbettungen_teilen():
            manager.encode_text("Tempolimit jetzt").append(9.9)
            assert manager.encode_text("Tempolimit jetzt") == [0.1, 0.2]


class TestManagerSearchBatch:
    @pytest.mark.asyncio
    async def test_search_batch_ein_vektor_eine_anfrage(self, manager):
        must_not = [FieldCondition(key="status", match=MatchValue(value="blocked"))]
        manager._async_client.search_batch = AsyncMock(
            return_value=[[_punkt(0.9, text="a")], [], [_punkt(0.85, text="c")]]
        )

        treffer = await manager.search_batch(
            "Tempolimit jetzt",
            [
                ("commentary", {"must_not": must_not}, 5),
                ("generic_text", {"must_not": must_not}, 5),
                ("post", None, 3),
            ],
        )

        assert manager._model.encode.call_count == 1
        manager._async_client.search_batch.assert_awaited_once()
        anfragen = manager._async_client.search_batch.call_args.kwargs["requests"]
        assert [a.limit for a in anfragen] == [5, 5, 3]
        assert anfragen[0].filter == manager._suchfilter(
            "commentary", {"must_not": must_not}
        )
        assert anfragen[2].filter == manager._suchfilter("post", None)
        assert [[t["text"] for t in liste] for liste in treffer] == [["a"], [], ["c"]]
        assert treffer[0][0]["score"] == 0.9

    @pytest.mark.asyncio
    async def test_search_batch_ohne_suchen_fragt_nicht_an(self, manager):
        manager._async_client.search_batch = AsyncMock()

        assert await manager.search_batch("Tempolimit jetzt", []) == []
        manager._async_client.search_batch.assert_not_called()
        manager._model.encode.assert_not_called()


class TestRepositoriesSearchBatch:
    @pytest.fixture
    def repositories(self, test_settings, test_embeddings_manager):
        test_embeddings_manager.add_test_data(
            "commentary", [_payload("commentary", "Tempolimit rettet Leben")]
        )
        test_embeddings_manager.add_test_data(
            "generic_text", [_payload("generic_text", "Tempolimit senkt CO2")]
        )
        factory = QdrantRepositoryFactory(embeddings_manager=test_embeddings_manager)
        return [
            factory.create_commentary_repository(test_settings),
            factory.create_generic_text_repository(test_settings),
        ]

    @pytest.mark.asyncio
    async def test_search_batch_liefert_je_repository_dessen_search(self, repositories):
        gebuendelt = await search_batch(repositories, "tempolimit", 5)
        einzeln = [await r.search("tempolimit", 5) for r in repositories]

        assert gebuendelt == einzeln
        assert isinstance(gebuendelt[0][0], CommentarySearchResult)
        assert isinstance(gebuendelt[1][0], GenericTextSearchResult)

    @pytest.mark.asyncio
    async def test_search_batch_verschiedene_manager_abgelehnt(
        self, test_settings, repositories
    ):
        fremd = QdrantRepositoryFactory(
            embeddings_manager=TestEmbeddingsManager()
        ).create_commentary_repository(test_settings)

        with pytest.raises(ValueError):
            await search_batch([*repositories, fremd], "tempolimit", 5)
