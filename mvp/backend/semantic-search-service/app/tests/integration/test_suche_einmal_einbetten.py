"""
Wie oft /searchByText einbettet und den Suchindex abfragt (#304), gegen echtes Qdrant.

Gezaehlt werden die Aufrufe des Einbettungsmodells und die Anfragen an den
Qdrant-Client je Suche. Die Suche laeuft durch den echten Router, mit echten
Diensten auf einer Wegwerf-Collection; nur was PostgreSQL braucht (Nutzung,
Bewertungen, Suchereignis), ist ersetzt.

Der Paritaetstest belegt, dass Treffer, Scores und Reihenfolge dieselben sind wie
mit einer Einbettung und einer Abfrage je Beitragstyp - so lief die Suche vor #304.
"""

import datetime
import uuid
from contextlib import nullcontext
from unittest.mock import MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from api.v1.search import router as search_router
from dependencies import (
    get_commentary_service,
    get_generic_text_service,
    get_image_service,
    get_post_service,
    get_reference_service,
    get_statement_service,
    get_voting_service,
)
from domain.content_registry import REGISTRY, create_content_service
from domain.models.commentary import CommentaryDbEntry
from domain.models.content_origin import ContentOrigin
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from domain.models.generic_text import GenericTextDbEntry
from domain.models.post import PostDbEntry
from domain.models.statement import Statement
from services.content.commentary_service import CommentaryService
from services.content.generic_text_service import GenericTextService
from services.content.reference_service import ReferenceService
from services.content.statement_service import StatementService

from tests.fixtures.direktsuche import direktsuche_ueber_dienste
from tests.integration.conftest import requires_qdrant

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]

SEARCH_URL = "/api/v1/search/searchByText"
SUCHANFRAGE = "Lohnen sich Wärmepumpen im Altbau?"


class _ZaehlenderClient:
    """Reicht alles an den Qdrant-Client durch und merkt sich jede Anfrage."""

    def __init__(self, inner):
        self._inner = inner
        self.anfragen: list[str] = []

    def __getattr__(self, name):
        attr = getattr(self._inner, name)
        if not callable(attr):
            return attr

        def gezaehlt(*args, **kwargs):
            self.anfragen.append(name)
            return attr(*args, **kwargs)

        return gezaehlt


def _felder(**extra):
    now = datetime.datetime.now()
    return dict(
        id=uuid.uuid4(),
        created=now,
        last_modified=now,
        original_author="tester",
        last_modified_by="tester",
        status=ContentStatus.VISIBLE,
        origin=ContentOrigin.MANUALLY_CREATED,
        **extra,
    )


@pytest_asyncio.fixture
async def suche(integration_settings, real_repository_factory, real_embeddings_manager):
    """Router mit echten Diensten, Bestand zum Thema Waermepumpe, Zaehler am Manager."""
    factory = real_repository_factory
    statements = StatementService(integration_settings, factory)
    commentaries = CommentaryService(integration_settings, factory)
    generic_texts = GenericTextService(integration_settings, factory)
    references = ReferenceService(integration_settings, factory)
    posts = create_content_service(
        REGISTRY[ContentType.POST], integration_settings, factory
    )
    images = create_content_service(
        REGISTRY[ContentType.IMAGE], integration_settings, factory
    )

    kommentar = CommentaryDbEntry(
        text="Mit Förderung und Flächenheizkörpern rechnet sich die Wärmepumpe "
        "auch in alten Häusern.",
        title="Wärmepumpe lohnt sich auch im Altbau",
        references=[],
        references_count=0,
        **_felder(),
    )
    await commentaries.add(kommentar)
    await commentaries.add(
        CommentaryDbEntry(
            text="Wärmepumpen im Altbau lohnen sich, wenn die Vorlauftemperatur "
            "unter 55 Grad bleibt.",
            title="Wärmepumpen lohnen sich im Altbau",
            references=[],
            references_count=0,
            **_felder(),
        )
    )
    await generic_texts.add(
        GenericTextDbEntry(
            text="Wärmepumpen arbeiten in den meisten Altbauten effizient, "
            "zeigen Feldtests.",
            title="Wärmepumpen im Altbau sind effizient",
            references=[],
            references_count=0,
            **_felder(),
        )
    )
    await posts.add(
        PostDbEntry(
            text="Wärmepumpe im Altbau? Lohnt sich, sagen die Feldtests.",
            title="Wärmepumpe lohnt sich im Altbau",
            platform="mastodon",
            author="@gruen",
            url="https://social.example/posts/1",
            engagement=0,
            **_felder(),
        )
    )
    _, aussage_id, _ = await statements.add_statement(
        Statement(text="Wärmepumpen lohnen sich nicht im Altbau", replysuggestions=[]),
        "tester",
        ContentStatus.VISIBLE,
        ContentOrigin.MANUALLY_CREATED,
    )
    await statements.add_statementreplysuggestion_to_statement(
        aussage_id, kommentar.id, ContentType.COMMENTARY, 0.9
    )

    app = FastAPI()
    app.include_router(search_router, prefix="/api/v1/search")
    app.dependency_overrides.update(
        {
            get_statement_service: lambda: statements,
            get_commentary_service: lambda: commentaries,
            get_generic_text_service: lambda: generic_texts,
            get_post_service: lambda: posts,
            get_image_service: lambda: images,
            get_reference_service: lambda: references,
            get_voting_service: lambda: MagicMock(),
        }
    )

    usage = MagicMock()
    usage.enrich_content_with_usage.side_effect = lambda dicts: dicts

    zaehler = _ZaehlenderClient(real_embeddings_manager._async_client)
    modell = real_embeddings_manager._model
    einbettungen: list[str] = []

    def encode(text, **kwargs):
        einbettungen.append(text)
        return modell.encode(text, **kwargs)

    with (
        patch("api.v1.search.get_usage_service", return_value=usage),
        patch("api.v1.search.get_search_tracking_service", return_value=MagicMock()),
        patch.object(real_embeddings_manager, "_async_client", zaehler),
        patch.object(real_embeddings_manager, "_model", MagicMock(encode=encode)),
    ):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:

            async def suchen(text=SUCHANFRAGE):
                zaehler.anfragen.clear()
                einbettungen.clear()
                antwort = await client.post(
                    SEARCH_URL, json={"query_text": text, "limit": 10}
                )
                assert antwort.status_code == 200, antwort.text
                return antwort.json(), list(einbettungen), list(zaehler.anfragen)

            yield suchen


def _treffer(antwort):
    """Was die Nutzenden sehen: je Beitragstyp IDs, Scores und Reihenfolge."""
    return {
        feld: [
            (
                next(v for k, v in eintrag.items() if k.endswith("_result"))["id"],
                eintrag["score"],
            )
            for eintrag in antwort[feld]
        ]
        for feld in (
            "commentary_search_results",
            "generictext_search_results",
            "post_search_results",
            "image_search_results",
        )
    }


async def test_neue_suchanfrage_einmal_eingebettet(suche):
    """Neue Aussage: Dublettenpruefung, Speichern, Aussagen- und Direktsuche.

    Vor #304: 8 Einbettungen, 10 Anfragen (scroll, search, 2x upsert, search,
    retrieve, 4x search - eine Direktsuche je Beitragstyp).
    """
    antwort, einbettungen, anfragen = await suche()

    assert antwort["query_was_newly_added_as_statement"] is True
    assert antwort["commentary_search_results_count"] >= 1
    assert einbettungen == [f"query: {SUCHANFRAGE}"]
    assert sorted(anfragen) == sorted(
        ["scroll", "search", "upsert", "upsert", "search", "retrieve", "search_batch"]
    )


async def test_vorhandene_suchanfrage_einmal_eingebettet(suche):
    """Die Aussage gibt es schon (normalisiert gleich): keine Dublettensuche.

    Vor #304: 5 Einbettungen, 7 Anfragen.
    """
    await suche()
    antwort, einbettungen, anfragen = await suche()

    assert antwort["query_was_newly_added_as_statement"] is False
    assert einbettungen == [f"query: {SUCHANFRAGE}"]
    assert sorted(anfragen) == sorted(["scroll", "search", "retrieve", "search_batch"])


async def test_suchanfrage_mit_apostroph_zweimal_eingebettet(suche):
    """Die Suche ersetzt ' und ; vor dem Einbetten, die Aussage behaelt den Text.

    Zwei verschiedene Texte, also zwei Einbettungen - bewusst so gelassen, damit
    sich Treffer nicht aendern (siehe PR zu #304, Offene Punkte).
    """
    text = "Wärmepumpen lohnen sich im Altbau, sagt's die Studie"
    _, einbettungen, _ = await suche(text)

    assert sorted(einbettungen) == sorted(
        [f"query: {text}", f"query: {text.replace(chr(39), chr(34))}"]
    )


async def test_treffer_wie_mit_einbettung_je_abfrage(suche):
    """Paritaet: Treffer, Scores und Reihenfolge wie vor #304."""
    await suche()  # Aussage anlegen, damit beide Laeufe dieselbe Lage sehen
    neu, _, _ = await suche()

    with (
        patch("api.v1.search.einbettungen_teilen", nullcontext),
        direktsuche_ueber_dienste(),
    ):
        alt, einbettungen_alt, _ = await suche()

    assert len(einbettungen_alt) == 5  # wirklich der alte Weg
    assert _treffer(neu) == _treffer(alt)
    assert sum(len(t) for t in _treffer(neu).values()) >= 3
