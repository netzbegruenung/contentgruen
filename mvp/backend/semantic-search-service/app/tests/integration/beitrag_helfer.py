"""
Gemeinsame Helfer der Integrationstests zu Zustaenden eines Beitrags: ein Post als
Testbeitrag und die Antwortvorschlaege, in denen er auftaucht (Sperren, #250 Loeschen).
"""

import datetime
import uuid

from domain.models.content_origin import ContentOrigin
from domain.models.content_status import ContentStatus
from domain.models.content_type import ContentType
from domain.models.post import PostDbEntry
from dtos.search import PostSearchResult as PostSearchResultWrapper
from services.search.search_orchestrator import (
    ContentTypeSearchSpec,
    SearchOrchestrator,
)
from tests.integration.test_post_type import _FakeReply, _FakeStatement

TEXT = "Tempolimit auf Autobahnen spart sofort CO2"


def post_beitrag(item_id: uuid.UUID) -> PostDbEntry:
    now = datetime.datetime.now()
    return PostDbEntry(
        text=TEXT,
        id=item_id,
        created=now,
        last_modified=now,
        original_author="autor-1",
        last_modified_by="autor-1",
        title="Tempolimit",
        platform="mastodon",
        author="@gruen",
        url="https://social.example/posts/2",
        engagement=1,
        status=ContentStatus.VISIBLE,
        origin=ContentOrigin.MANUALLY_CREATED,
    )


async def antwortvorschlaege(post_service, post_id):
    orchestrator = SearchOrchestrator(
        [
            ContentTypeSearchSpec(
                content_type=ContentType.POST,
                service=post_service,
                result_cls=PostSearchResultWrapper,
                result_field="post_result",
            )
        ],
        reference_service=None,
        usage_service=None,
        voting_service=None,
    )
    aussage = _FakeStatement(
        stmt_id=uuid.uuid4(),
        text="Bringt ein Tempolimit etwas?",
        score=1.0,
        replysuggestions=[_FakeReply(post_id, ContentType.POST, relevance=1.0)],
    )
    await orchestrator.collect_statement_based([aussage], limit=5, polarity_metadata={})
    return [r.post_result.id for r in orchestrator.results_for(ContentType.POST)]
