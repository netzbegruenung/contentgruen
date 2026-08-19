"""
Type-agnostic search orchestration.

Collapses the previously per-content-type duplicated phases of the search handler
(statement-based reply retrieval, direct-search fallback, usage enrichment, user-vote
enrichment, sort/truncate) into one set of helpers driven by a list of
``ContentTypeSearchSpec`` entries. Adding a content type to search becomes adding a
spec, not copying a branch (see docs/CONTENT_MODEL.md, "the search handler becomes
type-agnostic").

Behavior is intentionally identical to the prior hand-rolled branches; the search
characterization test (tests/unit/api/test_search_ranking.py) pins it.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Type

from core.logging import get_logger
from domain.models.content_type import ContentType

logger = get_logger(__name__)

# Search scoring constants (single source of truth; re-exported by api/v1/search.py).
MINIMUM_SCORE_THRESHOLD = 0.8  # Minimum score for results to be included
DIRECT_MATCH_PENALTY = 0.7  # Penalty multiplier for direct content matches
STATEMENT_WEIGHT = 0.7  # Weight for statement similarity score in combined score
RELEVANCE_WEIGHT = 0.3  # Weight for reply relevance score in combined score


def compute_combined_score(statement_score: float, reply_relevance: float) -> float:
    """Weighted combination: statement match 70%, reply relevance 30%."""
    return statement_score * STATEMENT_WEIGHT + reply_relevance * RELEVANCE_WEIGHT


@dataclass(frozen=True)
class ContentTypeSearchSpec:
    """Ties a content type to the pieces search needs to handle it uniformly."""

    content_type: ContentType
    service: object  # BaseContentService-like: async get(id) / async search(query, limit)
    result_cls: Type  # the per-type search-result wrapper DTO
    result_field: str  # name of the nested content field on the wrapper (e.g. "commentary_result")


class SearchOrchestrator:
    """Runs the shared search pipeline across all registered content-type specs."""

    def __init__(
        self,
        specs: List[ContentTypeSearchSpec],
        reference_service,
        usage_service,
        voting_service,
    ):
        self._specs: Dict[ContentType, ContentTypeSearchSpec] = {
            spec.content_type: spec for spec in specs
        }
        self._reference_service = reference_service
        self._usage_service = usage_service
        self._voting_service = voting_service
        # Per-type result buckets, preserving spec order.
        self._results: Dict[ContentType, List] = {
            spec.content_type: [] for spec in specs
        }

    def results_for(self, content_type: ContentType) -> List:
        return self._results.get(content_type, [])

    # ------------------------------------------------------------------ #
    # Result construction & enrichment helpers
    # ------------------------------------------------------------------ #

    def _build_result(
        self,
        spec: ContentTypeSearchSpec,
        *,
        score: float,
        statement_text: str,
        statement_similarity_score: float,
        reply_relevance: float,
        content_result,
        polarity_info=None,
    ):
        kwargs = {
            "score": score,
            "statement_text": statement_text,
            "statement_similarity_score": statement_similarity_score,
            "reply_relevance": reply_relevance,
            spec.result_field: content_result,
        }
        if polarity_info is not None:
            kwargs["polarity_mismatch_detected"] = polarity_info.polarity_mismatch_detected
            kwargs["original_score"] = polarity_info.original_score
        return spec.result_cls(**kwargs)

    async def _enrich_references(self, content_result) -> None:
        """Populate each reference's URL/description from the reference service.

        Die Notiz dieses Beitrags hat Vorrang vor dem Text der Referenz: sie
        gilt nur hier, waehrend der Referenztext global ist.
        """
        if not content_result or not getattr(content_result, "references", None):
            return
        for ref in content_result.references:
            try:
                reference_data = await self._reference_service.get(ref.reference_id)
                if reference_data:
                    ref.reference_text = reference_data.reference_string
                    ref.reference_description = (
                        getattr(ref, "description", None) or reference_data.text
                    )
            except Exception as e:
                logger.warning(f"Failed to fetch reference {ref.reference_id}: {e}")

    # ------------------------------------------------------------------ #
    # Phase 1: statement-based reply-suggestion retrieval
    # ------------------------------------------------------------------ #

    async def collect_statement_based(
        self,
        statement_index_results: List,
        limit: int,
        polarity_metadata: dict,
    ) -> None:
        for statement_result in statement_index_results:
            for replysuggestion in statement_result.replysuggestions:
                spec = self._specs.get(replysuggestion.content_type)
                combined_score = (
                    compute_combined_score(
                        statement_result.score, replysuggestion.relevance
                    )
                    if spec is not None
                    else 0.0
                )

                # Filter sub-threshold (and unknown content types) before any retrieval.
                if combined_score <= MINIMUM_SCORE_THRESHOLD:
                    logger.info(
                        f"❌ FILTERED OUT: statement='{statement_result.text[:50]}...' | "
                        f"combined_score={combined_score:.3f} ≤ threshold={MINIMUM_SCORE_THRESHOLD} | "
                        f"statement_score={statement_result.score:.3f}, "
                        f"reply_relevance={replysuggestion.relevance}, "
                        f"type={replysuggestion.content_type.value}"
                    )
                    continue

                try:
                    content_result = await spec.service.get(replysuggestion.id)
                except ValueError as e:
                    # Orphaned reply suggestion (referenced content missing): skip it.
                    logger.warning(
                        f"⚠️ Skipping orphaned reply suggestion: {spec.content_type.value} "
                        f"{replysuggestion.id} not found (referenced by statement "
                        f"{statement_result.id}). Error: {e}"
                    )
                    continue

                await self._enrich_references(content_result)

                self._results[spec.content_type].append(
                    self._build_result(
                        spec,
                        score=combined_score,
                        statement_text=statement_result.text,
                        statement_similarity_score=statement_result.score,
                        reply_relevance=replysuggestion.relevance,
                        content_result=content_result,
                        polarity_info=polarity_metadata.get(statement_result.id),
                    )
                )

                if len(self._results[spec.content_type]) >= limit:
                    break

    # ------------------------------------------------------------------ #
    # Phase 2: direct content search fallback (deduplicated against phase 1)
    # ------------------------------------------------------------------ #

    async def collect_direct(self, query_text: str, limit: int) -> None:
        # Content already surfaced via statement-based search must not be duplicated.
        # NOTE: this dedup set pools ids across all content types into one set, while the
        # intent ("don't re-add the same *content* surfaced in phase 1") is per-content.
        # That is correct only because content ids are UUIDs and therefore globally unique
        # across types; if ids ever become type-scoped (e.g. per-type sequential ints), key
        # this set by (content_type, id) instead.
        statement_based_ids = {
            getattr(result, spec.result_field).id
            for spec in self._specs.values()
            for result in self._results[spec.content_type]
            if getattr(result, spec.result_field)
        }

        for spec in self._specs.values():
            direct_results = await spec.service.search(query_text, limit=limit)
            for content_result in direct_results:
                if content_result.id in statement_based_ids:
                    continue

                # Der Schwellwert entscheidet ueber die Aufnahme und prueft deshalb
                # den Rohscore. Frueher lief der Vergleich gegen den bereits mit
                # DIRECT_MATCH_PENALTY gedaempften Wert - bei einer Penalty von 0.7
                # und einer Schwelle von 0.8 haette der Rohscore ueber 1.143 liegen
                # muessen, was eine Kosinus-Aehnlichkeit nie erreicht. Der Zweig
                # konnte dadurch nie etwas liefern.
                if content_result.score <= MINIMUM_SCORE_THRESHOLD:
                    continue

                # Die Penalty bleibt und wirkt weiter auf das Ranking: ein direkter
                # Treffer steht hinter einem statement-basierten mit gleichem Score.
                direct_score = content_result.score * DIRECT_MATCH_PENALTY

                await self._enrich_references(content_result)

                self._results[spec.content_type].append(
                    self._build_result(
                        spec,
                        score=direct_score,
                        statement_text="",  # No statement association for direct matches
                        statement_similarity_score=0.0,
                        reply_relevance=0.0,
                        content_result=content_result,
                    )
                )

    # ------------------------------------------------------------------ #
    # Phase 3: sort, truncate, enrich
    # ------------------------------------------------------------------ #

    def sort_and_truncate(self, limit: int) -> None:
        for content_type, results in self._results.items():
            results.sort(key=lambda x: x.score, reverse=True)
            self._results[content_type] = results[:limit]

    def enrich_with_usage(self) -> None:
        for spec in self._specs.values():
            results = self._results[spec.content_type]
            if not results:
                continue
            # Keep the concrete content objects alongside the dicts handed to the usage
            # service so the enriched counts are written back to the exact same objects.
            # Re-indexing the enriched list by position into `results` would misalign if
            # any result had a falsy content field (filtered out here but not there).
            content_objs = [
                getattr(r, spec.result_field)
                for r in results
                if getattr(r, spec.result_field)
            ]
            content_dicts = [obj.model_dump() for obj in content_objs]
            enriched = self._usage_service.enrich_content_with_usage(content_dicts)
            for content_obj, enriched_item in zip(content_objs, enriched):
                content_obj.usage_count = enriched_item.get("usage_count", 0)

    def apply_user_votes(self, user: str) -> None:
        all_content_ids = [
            getattr(result, spec.result_field).id
            for spec in self._specs.values()
            for result in self._results[spec.content_type]
            if getattr(result, spec.result_field)
        ]
        if not all_content_ids:
            return

        user_votes = self._voting_service.get_user_votes_for_contents(
            user, all_content_ids
        )
        for spec in self._specs.values():
            for result in self._results[spec.content_type]:
                content_result = getattr(result, spec.result_field)
                if content_result:
                    result.user_vote = user_votes.get(str(content_result.id))
