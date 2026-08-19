from enum import Enum


class ContentStatus(Enum):
    """
    Enumeration representing the lifecycle and moderation states of content
    within the CMS. Each status is mutually exclusive and provides clarity
    for the current state and next steps of content.
    """

    DRAFT = "draft"
    """Content is being created but has not yet been submitted for review."""

    FLAGGED = "flagged"
    """
    Content has been flagged for review due to user reports,
    similarity detection, or automated checks.
    """

    PENDING_REVIEW = "pending_review"
    """Content has been submitted and is awaiting moderation or approval."""

    APPROVED = "approved"
    """Content has been approved by the moderation team for release."""

    REJECTED = "rejected"
    """
    Content has been reviewed and deemed unsuitable for release.
    May include reasons such as policy violations or low quality.
    """

    BLOCKED = "blocked"
    """
    Content has been restricted due to a violation of community guidelines,
    ongoing investigation, or other serious issues.
    """

    RELEASED_INTERNAL = "released_internal"
    """Content has been published within the organization but not externally."""

    PUBLISHED_EXTERNAL = "published_external"
    """Content has been published to external audiences (e.g., social media)."""

    ARCHIVED = "archived"
    """
    Content is no longer actively used but is retained for historical purposes.
    Typically excluded from active searches unless explicitly requested.
    """

    DUPLICATE = "duplicate"
    """
    Content has been identified as redundant or overly similar to existing content.
    Requires further action to either merge, revise, or reject.
    """

    PENDING_DESCRIPTION = "pending_description"
    """Image stored without a caption; background worker will generate one."""

    DESCRIPTION_FAILED = "description_failed"
    """Background worker failed to generate a caption; human review required."""


NEW_CONTENT_STATUS = ContentStatus.RELEASED_INTERNAL
"""
Status, mit dem neu eingestellte Inhalte angelegt werden - der eine Ort, an dem
diese Entscheidung faellt. Alle Ingestion-Pfade in api/v1 (und der Bild-Worker)
beziehen sich hierauf, statt einen Status selbst zu waehlen.

RELEASED_INTERNAL, weil die Suche PENDING_REVIEW herausfiltert
(repositories/implementations/qdrant/base_repository.py) und selbst eingestellte
Beitraege sonst erst nach einer Moderation auffindbar waeren, die es noch nicht
gibt. Es ist derselbe Status, den Seeding (services/orchestration/
content_orchestrator.py) und Statements (api/v1/search.py) schon verwenden.

Sobald es eine Moderation gibt, wird hier wieder PENDING_REVIEW eingetragen -
der Filter dafuer ist absichtlich unveraendert geblieben.
"""


def is_valid_transition(
    current_status: ContentStatus, new_status: ContentStatus
) -> bool:
    valid_transitions = {
        ContentStatus.DRAFT: [ContentStatus.PENDING_REVIEW, ContentStatus.ARCHIVED],
        ContentStatus.FLAGGED: [ContentStatus.PENDING_REVIEW, ContentStatus.BLOCKED],
        ContentStatus.PENDING_REVIEW: [ContentStatus.APPROVED, ContentStatus.REJECTED],
        ContentStatus.APPROVED: [
            ContentStatus.RELEASED_INTERNAL,
            ContentStatus.PUBLISHED_EXTERNAL,
        ],
        ContentStatus.REJECTED: [ContentStatus.DRAFT],
        ContentStatus.BLOCKED: [],
        ContentStatus.RELEASED_INTERNAL: [ContentStatus.ARCHIVED],
        ContentStatus.PUBLISHED_EXTERNAL: [ContentStatus.ARCHIVED],
        ContentStatus.ARCHIVED: [],
        ContentStatus.DUPLICATE: [ContentStatus.REJECTED],
        ContentStatus.PENDING_DESCRIPTION: [
            ContentStatus.PENDING_REVIEW,
            ContentStatus.DESCRIPTION_FAILED,
        ],
        ContentStatus.DESCRIPTION_FAILED: [
            ContentStatus.PENDING_DESCRIPTION,
        ],
    }
    return new_status in valid_transitions.get(current_status, [])
