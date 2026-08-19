"""
Characterization tests for the /api/v1/search/searchByText ranking behavior.

These tests pin the CURRENT, user-visible ranking behavior of the search endpoint
so it can be refactored safely later (see docs/ROADMAP.md, rung 1). They do not
assert what the ranking *should* be -- they lock in what it *currently is*:

- combined score formula:  statement_score * 0.7 + reply_relevance * 0.3
- inclusion threshold:     combined_score must be STRICTLY > 0.8
- direct-match penalty:    direct hits are weighted * 0.7 (and therefore can never
                           clear the 0.8 threshold, since max cosine is 1.0)
- final ordering:          results sorted by score, descending, then truncated to `limit`

The search router is exercised through a real FastAPI app, but mounted standalone
(not via main.py) so the test needs no running services and stays in the CI unit
suite. Only the injected services (statement/commentary/generictext/reference/voting)
and the internally-constructed helper services (polarity, keyword-overlap, usage,
tracking) are faked, so the test is hermetic (no Qdrant / Postgres) and deterministic.

If a refactor changes the numbers below, that is a real ranking change -- update these
expectations deliberately, do not "fix" them away.
"""

import datetime
import uuid

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.v1.search import router as search_router
from dependencies import (
    get_statement_service,
    get_commentary_service,
    get_generic_text_service,
    get_post_service,
    get_reference_service,
    get_voting_service,
)
from domain.models.content_type import ContentType
from domain.models.content_status import ContentStatus
from domain.models.content_origin import ContentOrigin
from domain.models.content_visibility import ContentVisibility
from domain.models.statement import StatementSearchResult, StatementReplysuggestion
from domain.models.commentary import CommentaryDbEntry
from domain.models.generic_text import GenericTextDbEntry
from domain.models.post import PostDbEntry

SEARCH_URL = "/api/v1/search/searchByText"

# Mount the search router standalone so we never import main.py (which performs heavy
# app initialization and assumes live backing services).
app = FastAPI()
app.include_router(search_router, prefix="/api/v1/search")


# --------------------------------------------------------------------------- #
# Builders for valid domain objects (only the fields the endpoint touches matter)
# --------------------------------------------------------------------------- #


def _base_fields(**overrides):
    now = datetime.datetime.now()
    fields = dict(
        id=uuid.uuid4(),
        created=now,
        last_modified=now,
        original_author="test",
        last_modified_by="test",
        authors=[],
        edit_history=[],
        status=ContentStatus.APPROVED,
        origin=ContentOrigin.INITIAL_DATA,
        report_count=0,
        is_archived=False,
        report_flagged=False,
        visibility=ContentVisibility.INTERNAL,
    )
    fields.update(overrides)
    return fields


def _reply(content_type, relevance, suggestion_id):
    now = datetime.datetime.now()
    return StatementReplysuggestion(
        id=suggestion_id,
        content_type=content_type,
        relevance=relevance,
        created=now,
        updated=now,
        number_of_usages=0,
    )


def _statement_result(score, replysuggestions, text="statement"):
    return StatementSearchResult(
        text=text,
        content_type=ContentType.STATEMENT,
        replysuggestions=replysuggestions,
        replysuggestions_count=len(replysuggestions),
        score=score,
        **_base_fields(),
    )


def _commentary(content_id):
    return CommentaryDbEntry(
        text="commentary body",
        title="Commentary Title",
        content_type=ContentType.COMMENTARY,
        references=[],
        references_count=0,
        **_base_fields(id=content_id),
    )


def _generictext(content_id):
    return GenericTextDbEntry(
        text="generic text body",
        title="Generic Title",
        content_type=ContentType.GENERIC_TEXT,
        references=[],
        references_count=0,
        **_base_fields(id=content_id),
    )


def _post(content_id):
    return PostDbEntry(
        text="post body",
        title="Post Title",
        platform="mastodon",
        author="@gruen",
        url="https://social.example/p/1",
        engagement=0,
        content_type=ContentType.POST,
        **_base_fields(id=content_id),
    )


# --------------------------------------------------------------------------- #
# Fixture: build a TestClient with all services faked and helpers neutralized
# --------------------------------------------------------------------------- #


@pytest.fixture
def search_client():
    """
    Returns a factory that builds a TestClient whose dependencies are overridden
    with deterministic fakes. The internally-constructed helper services
    (polarity / keyword overlap / usage / tracking) are patched to passthrough
    no-ops so they neither filter nor reorder results.
    """
    patches = [
        patch(
            "api.v1.search.get_polarity_filter_service",
            return_value=_passthrough_polarity(),
        ),
        patch(
            "api.v1.search.get_keyword_overlap_service",
            return_value=_passthrough_keyword(),
        ),
        patch(
            "api.v1.search.get_usage_service",
            return_value=_passthrough_usage(),
        ),
        patch(
            "api.v1.search.get_search_tracking_service",
            return_value=MagicMock(),
        ),
    ]
    for p in patches:
        p.start()

    def _build(
        statement_results=None,
        direct_commentaries=None,
        direct_generictexts=None,
        user_votes=None,
    ):
        statement_service = MagicMock()
        statement_service.add_statement = AsyncMock(
            return_value=(True, uuid.uuid4(), "query")
        )
        statement_service.search_statements = AsyncMock(
            return_value=statement_results or []
        )

        commentary_service = MagicMock()
        commentary_service.get = AsyncMock(side_effect=lambda cid: _commentary(cid))
        commentary_service.search = AsyncMock(return_value=direct_commentaries or [])

        generic_text_service = MagicMock()
        generic_text_service.get = AsyncMock(side_effect=lambda gid: _generictext(gid))
        generic_text_service.search = AsyncMock(return_value=direct_generictexts or [])

        reference_service = MagicMock()
        reference_service.get = AsyncMock(return_value=None)

        voting_service = MagicMock()
        voting_service.get_user_votes_for_contents = MagicMock(
            return_value=user_votes or {}
        )

        # Post is wired into /searchByText as a registry-driven type; a neutral fake keeps
        # the ranking assertions (which use no Post fixtures) unaffected.
        post_service = MagicMock()
        post_service.get = AsyncMock(side_effect=lambda pid: _post(pid))
        post_service.search = AsyncMock(return_value=[])

        app.dependency_overrides[get_statement_service] = lambda: statement_service
        app.dependency_overrides[get_commentary_service] = lambda: commentary_service
        app.dependency_overrides[get_generic_text_service] = (
            lambda: generic_text_service
        )
        app.dependency_overrides[get_post_service] = lambda: post_service
        app.dependency_overrides[get_reference_service] = lambda: reference_service
        app.dependency_overrides[get_voting_service] = lambda: voting_service

        return TestClient(app)

    yield _build

    app.dependency_overrides.clear()
    for p in patches:
        p.stop()


def _passthrough_polarity():
    svc = MagicMock()
    svc.analyze_and_filter_statement_results.side_effect = (
        lambda query_text, statement_results, get_text_fn: (statement_results, {})
    )
    return svc


def _passthrough_keyword():
    svc = MagicMock()
    svc.analyze_and_boost_results.side_effect = (
        lambda query_text, results, get_text_fn: (results, {})
    )
    return svc


def _passthrough_usage():
    svc = MagicMock()
    # Endpoint reads enriched.get("usage_count", 0); echoing the dicts back keeps it at default.
    svc.enrich_content_with_usage.side_effect = lambda content_dicts: content_dicts
    return svc


# --------------------------------------------------------------------------- #
# Ranking characterization tests
# --------------------------------------------------------------------------- #


@pytest.mark.api
class TestSearchRanking:
    def test_combined_score_formula_and_descending_sort(self, search_client):
        """statement*0.7 + relevance*0.3, sorted descending, sub-threshold dropped."""
        sugg_a, sugg_b, sugg_c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        # Intentionally returned out of score order (C, A, B) to prove the endpoint sorts.
        statements = [
            # C: 0.85*0.7 + 0.20*0.3 = 0.655  -> below 0.8, filtered out
            _statement_result(
                0.85, [_reply(ContentType.COMMENTARY, 0.20, sugg_c)], "C"
            ),
            # A: 1.00*0.7 + 1.00*0.3 = 1.000  -> kept
            _statement_result(
                1.00, [_reply(ContentType.COMMENTARY, 1.00, sugg_a)], "A"
            ),
            # B: 0.95*0.7 + 0.80*0.3 = 0.905  -> kept
            _statement_result(
                0.95, [_reply(ContentType.COMMENTARY, 0.80, sugg_b)], "B"
            ),
        ]
        client = search_client(statement_results=statements)

        resp = client.post(SEARCH_URL, json={"query_text": "klimaschutz", "limit": 10})

        assert resp.status_code == 200
        data = resp.json()
        results = data["commentary_search_results"]

        assert data["commentary_search_results_count"] == 2
        assert [r["score"] for r in results] == [
            pytest.approx(1.000),
            pytest.approx(0.905),
        ]
        # Highest combined score first; the orphaned low-score statement is excluded.
        assert [r["commentary_result"]["id"] for r in results] == [
            str(sugg_a),
            str(sugg_b),
        ]

    def test_single_statement_populates_both_result_types(self, search_client):
        """
        A statement carrying both a commentary and a generic-text reply suggestion
        populates both result lists independently, each with its own combined score.
        This pins the commentary/generictext branch interaction that the planned
        SearchOrchestrator will collapse into one loop.
        """
        sugg_c, sugg_g = uuid.uuid4(), uuid.uuid4()
        statements = [
            _statement_result(
                1.00,
                [
                    # commentary:   1.00*0.7 + 1.00*0.3 = 1.000
                    _reply(ContentType.COMMENTARY, 1.00, sugg_c),
                    # generic_text: 1.00*0.7 + 0.90*0.3 = 0.970
                    _reply(ContentType.GENERIC_TEXT, 0.90, sugg_g),
                ],
                "mixed",
            )
        ]
        client = search_client(statement_results=statements)

        resp = client.post(SEARCH_URL, json={"query_text": "klimaschutz", "limit": 10})

        assert resp.status_code == 200
        data = resp.json()

        assert data["commentary_search_results_count"] == 1
        assert data["generictext_search_results_count"] == 1

        commentary = data["commentary_search_results"][0]
        generictext = data["generictext_search_results"][0]
        assert commentary["commentary_result"]["id"] == str(sugg_c)
        assert commentary["score"] == pytest.approx(1.000)
        assert generictext["generictext_result"]["id"] == str(sugg_g)
        assert generictext["score"] == pytest.approx(0.970)

    def test_authenticated_user_votes_are_attached(self, search_client):
        """
        For an authenticated request, each result carries the user's existing vote,
        fetched in one batch from the voting service. Anonymous requests skip this
        branch entirely (default user_vote is null). This pins lines 563-592 of the
        handler, an otherwise untested code path.
        """
        sugg = uuid.uuid4()
        statements = [
            _statement_result(
                1.00, [_reply(ContentType.COMMENTARY, 1.00, sugg)], "voted"
            )
        ]
        client = search_client(
            statement_results=statements,
            user_votes={str(sugg): "like"},
        )

        # require_auth would normally validate against the auth backend; bypass it so
        # the test targets the vote-enrichment branch, not authentication itself.
        with patch(
            "api.v1.search.require_auth",
            side_effect=lambda user, operation=None: user,
        ):
            resp = client.post(
                SEARCH_URL,
                json={"query_text": "klimaschutz", "limit": 10},
                headers={"X-User": "testuser"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["commentary_search_results_count"] == 1
        assert data["commentary_search_results"][0]["user_vote"] == "like"

    def test_anonymous_requests_have_no_user_vote(self, search_client):
        """Counterpart to the above: without an X-User header, user_vote stays null."""
        sugg = uuid.uuid4()
        statements = [
            _statement_result(
                1.00, [_reply(ContentType.COMMENTARY, 1.00, sugg)], "anon"
            )
        ]
        client = search_client(
            statement_results=statements,
            user_votes={
                str(sugg): "like"
            },  # present but must be ignored when anonymous
        )

        resp = client.post(SEARCH_URL, json={"query_text": "klimaschutz", "limit": 10})

        assert resp.status_code == 200
        data = resp.json()
        assert data["commentary_search_results"][0]["user_vote"] is None

    def test_threshold_is_strictly_greater_than_080(self, search_client):
        """A combined score of exactly 0.8 is excluded (filter is `> 0.8`, not `>=`)."""
        sugg = uuid.uuid4()
        # 0.80*0.7 + 0.80*0.3 = 0.80 exactly -> excluded
        statements = [
            _statement_result(
                0.80, [_reply(ContentType.COMMENTARY, 0.80, sugg)], "edge"
            )
        ]
        client = search_client(statement_results=statements)

        resp = client.post(SEARCH_URL, json={"query_text": "edge", "limit": 10})

        assert resp.status_code == 200
        assert resp.json()["commentary_search_results_count"] == 0

    def test_generictext_uses_same_formula(self, search_client):
        """Generic-text reply suggestions are scored and surfaced identically."""
        sugg = uuid.uuid4()
        # 0.95*0.7 + 0.90*0.3 = 0.935 -> kept
        statements = [
            _statement_result(0.95, [_reply(ContentType.GENERIC_TEXT, 0.90, sugg)], "G")
        ]
        client = search_client(statement_results=statements)

        resp = client.post(SEARCH_URL, json={"query_text": "energie", "limit": 10})

        assert resp.status_code == 200
        data = resp.json()
        results = data["generictext_search_results"]
        assert data["generictext_search_results_count"] == 1
        assert results[0]["score"] == pytest.approx(0.935)
        assert results[0]["generictext_result"]["id"] == str(sugg)

    def test_direct_match_above_threshold_is_kept(self, search_client):
        """
        Der Schwellwert prueft den Rohscore, nicht den mit DIRECT_MATCH_PENALTY
        gedaempften Wert. Vorher wurde 0.9 * 0.7 = 0.63 gegen 0.8 geprueft und der
        Treffer verworfen; da die Penalty konstant 0.7 ist, haette der Rohscore
        ueber 1.143 liegen muessen - fuer eine Kosinus-Aehnlichkeit unerreichbar.
        Der Zweig konnte dadurch nie etwas liefern.
        """
        hit = _commentary_search_hit(score=0.90)
        client = search_client(statement_results=[], direct_commentaries=[hit])

        resp = client.post(SEARCH_URL, json={"query_text": "klimaschutz", "limit": 10})

        assert resp.status_code == 200
        data = resp.json()
        assert data["commentary_search_results_count"] == 1
        # Die Penalty wirkt weiterhin auf das Ranking: 0.90 * 0.7 = 0.63.
        assert data["commentary_search_results"][0]["score"] == pytest.approx(0.63)

    def test_direct_match_at_threshold_is_dropped(self, search_client):
        """Der Vergleich bleibt strikt: ein Rohscore von genau 0.8 faellt heraus."""
        edge = _commentary_search_hit(score=0.80)
        client = search_client(statement_results=[], direct_commentaries=[edge])

        resp = client.post(SEARCH_URL, json={"query_text": "klimaschutz", "limit": 10})

        assert resp.status_code == 200
        assert resp.json()["commentary_search_results_count"] == 0

    def test_statement_based_outranks_direct_at_equal_raw_score(self, search_client):
        """
        Bei gleichem Rohscore steht der statement-basierte Treffer vorn - genau
        dafuer ist die Penalty da. Statement: 0.9*0.7 + 0.9*0.3 = 0.9;
        direkt: 0.9 * 0.7 = 0.63.
        """
        sugg = uuid.uuid4()
        statements = [
            _statement_result(0.90, [_reply(ContentType.COMMENTARY, 0.90, sugg)], "S")
        ]
        direct = _commentary_search_hit(score=0.90)
        client = search_client(
            statement_results=statements, direct_commentaries=[direct]
        )

        resp = client.post(SEARCH_URL, json={"query_text": "klimaschutz", "limit": 10})

        assert resp.status_code == 200
        data = resp.json()
        assert data["commentary_search_results_count"] == 2
        scores = [r["score"] for r in data["commentary_search_results"]]
        assert scores == sorted(scores, reverse=True)
        assert data["commentary_search_results"][0]["commentary_result"]["id"] == str(
            sugg
        )
        assert scores[0] == pytest.approx(0.90)
        assert scores[1] == pytest.approx(0.63)

    def test_results_sorted_and_truncated_to_limit(self, search_client):
        """With more passing results than `limit`, only the top-scoring `limit` remain."""
        sugg_a, sugg_b, sugg_c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        statements = [
            _statement_result(
                1.00, [_reply(ContentType.COMMENTARY, 1.00, sugg_a)], "A"
            ),  # 1.000
            _statement_result(
                1.00, [_reply(ContentType.COMMENTARY, 0.90, sugg_b)], "B"
            ),  # 0.970
            _statement_result(
                1.00, [_reply(ContentType.COMMENTARY, 0.85, sugg_c)], "C"
            ),  # 0.955
        ]
        client = search_client(statement_results=statements)

        resp = client.post(SEARCH_URL, json={"query_text": "klimaschutz", "limit": 2})

        assert resp.status_code == 200
        data = resp.json()
        results = data["commentary_search_results"]
        assert data["commentary_search_results_count"] == 2
        assert [r["commentary_result"]["id"] for r in results] == [
            str(sugg_a),
            str(sugg_b),
        ]


@pytest.mark.api
class TestSearchValidation:
    """Pin the request-validation contract (DTO bounds vs. handler bounds)."""

    def test_empty_query_is_rejected(self, search_client):
        client = search_client()
        resp = client.post(SEARCH_URL, json={"query_text": "", "limit": 10})
        assert resp.status_code == 422  # DTO min_length=1

    def test_missing_query_is_rejected(self, search_client):
        client = search_client()
        resp = client.post(SEARCH_URL, json={"limit": 10})
        assert resp.status_code == 422

    def test_limit_zero_is_rejected_by_dto(self, search_client):
        client = search_client()
        resp = client.post(SEARCH_URL, json={"query_text": "x", "limit": 0})
        assert resp.status_code == 422  # DTO ge=1

    def test_limit_above_20_is_rejected_with_400(self, search_client):
        """
        The DTO permits limit up to 100, but the handler enforces a stricter max of
        20 and rejects with a 400.

        Previously this surfaced as a 500: the handler's `raise HTTPException(400)`
        was swallowed by its broad `except Exception`, which re-wrapped it as
        `HTTPException(500, str(e))`. The handler now re-raises HTTPException
        untouched, so the intended client error reaches the caller.
        """
        client = search_client()
        resp = client.post(SEARCH_URL, json={"query_text": "x", "limit": 25})
        assert resp.status_code == 400


def _commentary_search_hit(score):
    """A CommentarySearchResult (db entry + score) for the direct-search path."""
    from domain.models.commentary import CommentarySearchResult

    return CommentarySearchResult(
        text="direct hit body",
        title="Direct Hit",
        content_type=ContentType.COMMENTARY,
        references=[],
        references_count=0,
        score=score,
        **_base_fields(),
    )
