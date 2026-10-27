"""
Eine Einbettung und eine Anfrage an den Suchindex je Suche (#304).

- einbettungen_teilen(): gleicher Text wird im Block nur einmal eingebettet.
- QdrantEmbeddingsManager.search_batch(): mehrere Suchen, ein Vektor, eine Anfrage.
- QdrantBaseRepository.search_batch() / BaseContentService.search_batch(): je
  Repository bzw. Dienst dasselbe wie dessen search().
- SearchOrchestrator.collect_direct(): dieselben Treffer wie mit einer Suche je Typ.

Ohne Qdrant und ohne Modell: Client und Modell sind ersetzt.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import inspect
import numpy as np
import pytest
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import FieldCondition, MatchValue

from domain.models.commentary import CommentarySearchResult
from domain.models.generic_text import GenericTextSearchResult
from domain.interfaces.embeddings_manager import Suchparameter
from domain.models.content_type import ContentType
from dtos.search import CommentarySearchResult as CommentaryWrapper
from dtos.search import GenericTextSearchResult as GenericTextWrapper
from repositories.implementations.qdrant.base_repository import (
    QdrantBaseRepository,
    nur_sichtbar_bedingungen,
)
from services.content.base_content_service import BaseContentService
from services.content.commentary_service import CommentaryService
from services.content.generic_text_service import GenericTextService
from services.search.search_orchestrator import (
    ContentTypeSearchSpec,
    SearchOrchestrator,
)
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from services.embeddings.qdrant_embeddings_manager import (
    QdrantEmbeddingsManager,
    einbettungen_geteilt,
    einbettungen_teilen,
)
from tests.fixtures.direktsuche import direktsuche_ueber_dienste
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
        "status": "visible",
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

    @pytest.mark.asyncio
    async def test_einbettungen_geteilt_endpunkt_teilt_je_aufruf(self, manager):
        @einbettungen_geteilt
        async def endpunkt(text: str):
            manager.encode_text(text)
            manager.encode_text(text)

        await endpunkt("Tempolimit jetzt")
        await endpunkt("Tempolimit jetzt")

        assert manager._model.encode.call_count == 2  # je Aufruf einmal
        manager.encode_text("Tempolimit jetzt")
        assert manager._model.encode.call_count == 3  # danach nicht mehr geteilt

    def test_einbettungen_geteilt_signatur_bleibt_fuer_fastapi(self):
        async def endpunkt(text: str, limit: int = 5):
            pass

        assert inspect.signature(einbettungen_geteilt(endpunkt)) == inspect.signature(
            endpunkt
        )


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
                Suchparameter("commentary", {"must_not": must_not}, 5),
                Suchparameter("generic_text", {"must_not": must_not}, 5),
                Suchparameter("post", None, 3),
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
    async def test_search_batch_anfragen_wie_search_je_suche(self, manager):
        """Was an Qdrant geht: je Suche derselbe Vektor, Filter und dasselbe Limit."""
        punkte = [[_punkt(0.9, text="a"), _punkt(0.8, text="b")], [_punkt(0.7)], []]
        manager._async_client.search = AsyncMock(side_effect=punkte)
        manager._async_client.search_batch = AsyncMock(return_value=punkte)
        sichtbar = {"must": nur_sichtbar_bedingungen()}
        suchen = [
            Suchparameter("commentary", sichtbar, 10),
            Suchparameter("generic_text", sichtbar, 1),
            Suchparameter("statement", None, 3),
        ]

        einzeln = [
            await manager.search(
                "Tempolimit jetzt",
                content_type=suche.content_type,
                limit=suche.limit,
                filter_dict=suche.filter_dict,
            )
            for suche in suchen
        ]
        gebuendelt = await manager.search_batch("Tempolimit jetzt", suchen)

        assert gebuendelt == einzeln
        anfragen = manager._async_client.search_batch.call_args.kwargs["requests"]
        for anfrage, aufruf in zip(
            anfragen, manager._async_client.search.call_args_list
        ):
            assert anfrage.vector == aufruf.kwargs["query_vector"]
            assert anfrage.filter == aufruf.kwargs["query_filter"]
            assert anfrage.limit == aufruf.kwargs["limit"]
            assert anfrage.with_payload == aufruf.kwargs["with_payload"]
            assert anfrage.with_vector == aufruf.kwargs["with_vectors"]
        assert anfragen[0].filter.must[0] == FieldCondition(
            key="content_type", match=MatchValue(value="commentary")
        )

    @pytest.mark.asyncio
    async def test_search_batch_qdrant_fehler_als_runtime_error(self, manager):
        manager._async_client.search_batch = AsyncMock(
            side_effect=UnexpectedResponse(500, "Server Error", b"", httpx.Headers())
        )

        with pytest.raises(RuntimeError, match="Vector database search failed"):
            await manager.search_batch(
                "Tempolimit jetzt", [Suchparameter("commentary", None, 5)]
            )

    @pytest.mark.asyncio
    async def test_search_batch_ohne_suchen_fragt_nicht_an(self, manager):
        manager._async_client.search_batch = AsyncMock()

        assert await manager.search_batch("Tempolimit jetzt", []) == []
        manager._async_client.search_batch.assert_not_called()
        manager._model.encode.assert_not_called()


class TestRepositoriesSearchBatch:
    """Gegen den TestEmbeddingsManager, dessen search_batch() je Eintrag search()
    ruft: belegt die Verdrahtung (Parameter, Ergebnismodell). Was an Qdrant geht,
    vergleicht TestManagerSearchBatch."""

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
        gebuendelt = await QdrantBaseRepository.search_batch(
            repositories, "tempolimit", 5
        )
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
            await QdrantBaseRepository.search_batch(
                [*repositories, fremd], "tempolimit", 5
            )


class TestDiensteSearchBatch:
    """Die Ebene, die der SearchOrchestrator ruft - ohne die Router-Fakes."""

    @pytest.fixture
    def dienste(self, test_settings, repository_factory, test_embeddings_manager):
        test_embeddings_manager.add_test_data(
            "commentary",
            [
                _payload("commentary", "Tempolimit rettet Leben"),
                _payload("commentary", "Ohne Tempolimit mehr Unfaelle"),
            ],
        )
        test_embeddings_manager.add_test_data(
            "generic_text", [_payload("generic_text", "Tempolimit senkt CO2")]
        )
        return [
            CommentaryService(test_settings, repository_factory),
            GenericTextService(test_settings, repository_factory),
        ]

    @pytest.mark.asyncio
    async def test_search_batch_liefert_je_dienst_dessen_search(self, dienste):
        gebuendelt = await BaseContentService.search_batch(dienste, "tempolimit", 5)
        einzeln = [await d.search("tempolimit", 5) for d in dienste]

        assert gebuendelt == einzeln
        assert [len(t) for t in gebuendelt] == [2, 1]

    @pytest.mark.asyncio
    async def test_search_batch_ohne_dienste_leer(self):
        assert await BaseContentService.search_batch([], "tempolimit", 5) == []

    @pytest.mark.asyncio
    async def test_collect_direct_wie_eine_suche_je_typ(self, dienste):
        def orchestrator():
            return SearchOrchestrator(
                [
                    ContentTypeSearchSpec(
                        ContentType.COMMENTARY,
                        dienste[0],
                        CommentaryWrapper,
                        "commentary_result",
                    ),
                    ContentTypeSearchSpec(
                        ContentType.GENERIC_TEXT,
                        dienste[1],
                        GenericTextWrapper,
                        "generictext_result",
                    ),
                ],
                reference_service=MagicMock(),
                usage_service=MagicMock(),
                voting_service=MagicMock(),
            )

        neu = orchestrator()
        await neu.collect_direct("tempolimit", 5)
        alt = orchestrator()
        with direktsuche_ueber_dienste():
            await alt.collect_direct("tempolimit", 5)

        for typ in (ContentType.COMMENTARY, ContentType.GENERIC_TEXT):
            assert neu.results_for(typ) == alt.results_for(typ)
        assert len(neu.results_for(ContentType.COMMENTARY)) == 2
