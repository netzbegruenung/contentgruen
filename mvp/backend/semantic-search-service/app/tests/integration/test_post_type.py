"""
Step 6 gate: the Post content type, proven end-to-end against REAL Qdrant.

This is the rung-1 proof that adding a content type costs only *a spec + a model*
(no new service/repository clone, no new search branch):

* test 6 -- a Post written and read back purely through the generic, registry-built
  ``BaseContentService`` (``create_content_service`` over ``REGISTRY[POST]``), with the
  Post-specific fields (platform/author/url/engagement) surviving the round-trip and the
  post being semantically searchable.
* test 7 -- the same registry-built Post service plugged into the type-agnostic
  ``SearchOrchestrator`` via a single ``ContentTypeSearchSpec``, showing a Post reply
  suggestion is retrieved and assembled by the orchestrator with no Post-specific code
  path. The statement-based phase is used because it yields a deterministic combined
  score (0.7*statement + 0.3*relevance) above ``MINIMUM_SCORE_THRESHOLD``; the
  direct-search phase applies ``DIRECT_MATCH_PENALTY`` and is score-magnitude sensitive.

See ``docs/RUNG_1_PLAN.md`` Step 6 and ``docs/CONTENT_MODEL.md``.
"""

import datetime
import uuid

import pytest

from domain.models.content_type import ContentType
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin
from domain.models.post import PostDbEntry
from domain.content_registry import REGISTRY, create_content_service
from dtos.search import PostSearchResult as PostSearchResultWrapper
from services.search.search_orchestrator import (
    SearchOrchestrator,
    ContentTypeSearchSpec,
)

from tests.integration.conftest import requires_qdrant

pytestmark = [pytest.mark.integration, requires_qdrant, pytest.mark.asyncio]


def _make_post_db_entry(
    item_id: uuid.UUID,
    text: str,
    *,
    title: str = "Klimapost",
    platform: str = "mastodon",
    author: str = "@gruen",
    url: str = "https://social.example/posts/1",
    engagement: int = 42,
) -> PostDbEntry:
    now = datetime.datetime.now()
    return PostDbEntry(
        text=text,
        id=item_id,
        created=now,
        last_modified=now,
        original_author="tester",
        last_modified_by="tester",
        title=title,
        platform=platform,
        author=author,
        url=url,
        engagement=engagement,
        status=ContentStatus.APPROVED,
        origin=ContentOrigin.MANUALLY_CREATED,
    )


async def test_post_roundtrip_via_registry(
    integration_settings, real_repository_factory
):
    """Post stored & retrieved purely through the registry-built generic service."""
    spec = REGISTRY[ContentType.POST]
    service = create_content_service(spec, integration_settings, real_repository_factory)

    item_id = uuid.uuid4()
    entry = _make_post_db_entry(
        item_id, "Verkehrswende und Klimaschutz gehören zusammen"
    )
    stored_id = await service._upsert(entry)
    assert stored_id == item_id

    fetched = await service.get(item_id)
    assert fetched.id == item_id
    assert fetched.content_type == ContentType.POST
    assert fetched.title == "Klimapost"
    # Post-specific fields must survive the round-trip unchanged.
    assert fetched.platform == "mastodon"
    assert fetched.author == "@gruen"
    assert fetched.url == "https://social.example/posts/1"
    assert fetched.engagement == 42

    hits = await service.search("Klimaschutz Verkehr", limit=5)
    assert any(h.id == item_id for h in hits)


class _FakeReply:
    """Minimal stand-in for a statement's reply suggestion (attribute access only)."""

    def __init__(self, post_id: uuid.UUID, content_type: ContentType, relevance: float):
        self.id = post_id
        self.content_type = content_type
        self.relevance = relevance


class _FakeStatement:
    """Minimal stand-in for a StatementSearchResult (attribute access only)."""

    def __init__(self, stmt_id, text, score, replysuggestions):
        self.id = stmt_id
        self.text = text
        self.score = score
        self.replysuggestions = replysuggestions


async def test_post_search_parity_via_orchestrator(
    integration_settings, real_repository_factory
):
    """A Post flows through the type-agnostic SearchOrchestrator via only a spec."""
    spec = REGISTRY[ContentType.POST]
    service = create_content_service(spec, integration_settings, real_repository_factory)

    post_id = uuid.uuid4()
    await service._upsert(
        _make_post_db_entry(post_id, "Erneuerbare Energien konsequent ausbauen")
    )

    search_spec = ContentTypeSearchSpec(
        content_type=ContentType.POST,
        service=service,
        result_cls=PostSearchResultWrapper,
        result_field="post_result",
    )
    orchestrator = SearchOrchestrator(
        [search_spec],
        reference_service=None,
        usage_service=None,
        voting_service=None,
    )

    fake_statement = _FakeStatement(
        stmt_id=uuid.uuid4(),
        text="Wie stehen wir zu erneuerbaren Energien?",
        score=1.0,
        replysuggestions=[_FakeReply(post_id, ContentType.POST, relevance=1.0)],
    )

    await orchestrator.collect_statement_based(
        [fake_statement], limit=5, polarity_metadata={}
    )
    orchestrator.sort_and_truncate(5)

    results = orchestrator.results_for(ContentType.POST)
    assert any(r.post_result.id == post_id for r in results)
    # Combined score = 0.7 * 1.0 + 0.3 * 1.0 = 1.0, comfortably above threshold.
    assert results[0].score == pytest.approx(1.0)
