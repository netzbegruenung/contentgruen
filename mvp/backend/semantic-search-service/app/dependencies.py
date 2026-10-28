from typing import Optional, TYPE_CHECKING
from fastapi import Depends, Header, HTTPException

if TYPE_CHECKING:
    # Only needed for the type annotation on the lazily-built Post service; imported
    # under TYPE_CHECKING to avoid pulling the registry/service graph at module load.
    from services.content.base_content_service import BaseContentService
from core.config import settings, Settings
from services.orchestration.content_orchestrator import ContentOrchestrator
from services.content.commentary_service import CommentaryService
from services.content.reference_service import ReferenceService
from services.content.statement_service import StatementService
from services.content.generic_text_service import GenericTextService
from services.voting_service import VotingService
from services.anzeigename_service import get_anzeigename_service
from services.beitrag_fuer_aufrufer import Aufrufer
from services.content.beitrag_loeschen_service import BeitragLoeschenService
from repositories.implementations.qdrant.moderation_repository import (
    get_moderation_repository,
)
from services.suchen_ohne_treffer_service import (
    SuchenOhneTrefferService,
    get_personen_des_tages,
)
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from repositories.suchen_ohne_treffer_repository import (
    get_suchen_ohne_treffer_repository,
)
from core.logging import get_logger

logger = get_logger(__name__)


# Global manager instances
statement_service_instance: Optional[StatementService] = None
commentary_service_instance: Optional[CommentaryService] = None
reference_service_instance: Optional[ReferenceService] = None
generic_text_service_instance: Optional[GenericTextService] = None
# Registry-driven content type (Post): a generic BaseContentService built from a spec,
# lazily instantiated on first use (no per-type service subclass / no orchestrator seeding).
post_service_instance: Optional["BaseContentService"] = None
# Registry-driven content type (Image): same pattern as Post.
image_service_instance: Optional["BaseContentService"] = None
caption_suggestion_service_instance: Optional["CaptionSuggestionService"] = None
content_orchestrator_instance: Optional[ContentOrchestrator] = None
voting_service_instance: Optional[VotingService] = None


def get_settings() -> Settings:
    return settings


def initialize_services() -> None:
    """
    Initializes the singleton instances for the content services and orchestrator.

    NOTE: This function now only creates the service instances without blocking data loading.
    Data loading is handled by the SeedingService in the background.
    """
    global content_orchestrator_instance
    if content_orchestrator_instance is not None:
        logger.debug(
            "ContentOrchestrator already initialized. Skipping initialize_services()"
        )
        return

    logger.info("===== Starting Lightweight Content Service Initialization =====")

    settings_instance = get_settings()
    logger.debug("got settings...")

    # Create content service instances (lightweight - no data loading)
    global statement_service_instance
    statement_service_instance = StatementService(settings=settings_instance)

    global commentary_service_instance
    commentary_service_instance = CommentaryService(settings=settings_instance)

    global reference_service_instance
    reference_service_instance = ReferenceService(settings=settings_instance)

    global generic_text_service_instance
    generic_text_service_instance = GenericTextService(settings=settings_instance)

    global voting_service_instance
    voting_service_instance = VotingService()
    logger.debug("created content service instances...")

    # Create the content orchestrator instance (without triggering data load)
    content_orchestrator_instance = ContentOrchestrator(
        settings=settings_instance,
        statement_service=statement_service_instance,
        commentary_service=commentary_service_instance,
        reference_service=reference_service_instance,
        generic_text_service=generic_text_service_instance,
    )
    logger.debug("created content orchestrator instance...")

    # NOTE: Removed blocking initialize_repositories() call
    # Data loading is now handled by SeedingService in background

    logger.info("===== Finished Lightweight Content Service Initialization =====")


# Dependency injection functions


def get_content_orchestrator() -> ContentOrchestrator:
    if content_orchestrator_instance is None:
        raise ValueError("ContentOrchestrator has not been initialized.")
    return content_orchestrator_instance


def get_statement_service() -> StatementService:
    if statement_service_instance is None:
        raise ValueError("StatementService has not been initialized.")
    return statement_service_instance


def get_suchen_ohne_treffer_service(
    statement_service: StatementService = Depends(get_statement_service),
) -> SuchenOhneTrefferService:
    return SuchenOhneTrefferService(
        get_suchen_ohne_treffer_repository(),
        statement_service,
        get_personen_des_tages(),
    )


def get_beitrag_loeschen_service(
    settings: Settings = Depends(get_settings),
) -> BeitragLoeschenService:
    """Ueber das aggregierte Repository: Loeschen gilt fuer jeden Beitragstyp."""
    return BeitragLoeschenService(
        QdrantRepositoryFactory().create_content_repository(settings),
        get_moderation_repository(),
    )


def get_commentary_service() -> CommentaryService:
    if commentary_service_instance is None:
        raise ValueError("CommentaryService has not been initialized.")
    return commentary_service_instance


def get_reference_service() -> ReferenceService:
    if reference_service_instance is None:
        raise ValueError("ReferenceService has not been initialized.")
    return reference_service_instance


def get_generic_text_service() -> GenericTextService:
    if generic_text_service_instance is None:
        raise ValueError("GenericTextService has not been initialized.")
    return generic_text_service_instance


def get_post_service():
    """
    Dependency for the Post content service.

    Post is a registry-driven type: instead of a hand-written PostService, a generic
    BaseContentService is built from REGISTRY[POST] on first use. Lazy init keeps it out
    of the orchestrator's seeding path (registry types are not seeded from JSON).
    """
    global post_service_instance
    if post_service_instance is None:
        from domain.content_registry import REGISTRY, create_content_service
        from domain.models.content_type import ContentType
        from repositories.implementations.qdrant.qdrant_repository_factory import (
            QdrantRepositoryFactory,
        )
        from services.embeddings.qdrant_embeddings_manager import (
            get_embeddings_manager,
        )

        # QdrantEmbeddingsManager is a process-wide singleton (see its __new__): the
        # QdrantRepositoryFactory below resolves that same shared instance the rest of
        # the app started during lifespan, so Post search/ingest uses the same started
        # manager as every other content type. Resolve it explicitly here so that, if
        # this lazy dependency is ever exercised before startup has completed, we fail
        # loudly with a clear error instead of silently building a repository on an
        # unstarted manager.
        get_embeddings_manager()  # raises if the shared manager is not yet initialized
        post_service_instance = create_content_service(
            REGISTRY[ContentType.POST], get_settings(), QdrantRepositoryFactory()
        )
    return post_service_instance


def get_image_service():
    """
    Dependency for the Image content service.

    Returns None if the embeddings manager is not yet initialized (e.g. in unit
    tests without Qdrant). Callers must guard against None before use.
    """
    global image_service_instance
    if image_service_instance is None:
        from domain.content_registry import REGISTRY, create_content_service
        from domain.models.content_type import ContentType
        from repositories.implementations.qdrant.qdrant_repository_factory import (
            QdrantRepositoryFactory,
        )
        from services.embeddings.qdrant_embeddings_manager import (
            get_embeddings_manager,
        )

        try:
            get_embeddings_manager()
        except RuntimeError:
            return None
        image_service_instance = create_content_service(
            REGISTRY[ContentType.IMAGE], get_settings(), QdrantRepositoryFactory()
        )
    return image_service_instance


def get_caption_suggestion_service():
    """
    Dependency for the CaptionSuggestionService (singleton).

    Raises ValueError if OPENAI_API_KEY / SEMANTIC_SEARCH_OPENAI_API_KEY is unset,
    so misconfiguration is caught at the first request rather than at startup.
    The singleton avoids creating a new AsyncOpenAI connection pool per request.
    """
    global caption_suggestion_service_instance
    if caption_suggestion_service_instance is None:
        from services.vision.caption_suggestion_service import CaptionSuggestionService

        s = get_settings()
        if not s.openai_api_key:
            raise ValueError(
                "openai_api_key is not configured. "
                "Set OPENAI_API_KEY or SEMANTIC_SEARCH_OPENAI_API_KEY."
            )
        caption_suggestion_service_instance = CaptionSuggestionService(
            api_key=s.openai_api_key,
            model=s.openai_vision_model,
        )
    return caption_suggestion_service_instance


def get_voting_service() -> VotingService:
    if voting_service_instance is None:
        raise ValueError("VotingService has not been initialized.")
    return voting_service_instance


def get_current_user_optional(
    x_user_id: Optional[str] = Header(None, alias="X-User"),
) -> Optional[str]:
    """
    Optional authentication dependency.
    Returns the user ID from the X-User header if present, None otherwise.
    Used for tracking anonymous vs authenticated usage.

    Der Alias ist zwingend: ohne ihn leitet FastAPI den Header-Namen aus dem
    Parameternamen ab (x_user_id -> X-User-Id). Das BFF setzt aber X-User, also
    kam hier fuer jeden echten Request None an -- und /usage-stats hat den
    Eigentuemer seiner eigenen Daten mit 403 abgewiesen. Siehe require_admin
    unten, das denselben Header schon immer korrekt liest.
    """
    return x_user_id


def anzeigename_merken(
    x_user: Optional[str] = Header(None, alias="X-User"),
    x_user_display_name: Optional[str] = Header(None, alias="X-User-Display-Name"),
) -> None:
    """
    App-weite Dependency (main.py): den Anzeigenamen aus dem BFF-Header ablegen.

    Synchron, damit FastAPI sie im Threadpool ausfuehrt - der seltene Schreibzugriff
    blockiert so nicht die Event-Loop. Ohne Header passiert nichts, auch kein
    Datenbankzugriff.
    """
    if x_user_display_name:
        get_anzeigename_service().merken(x_user, x_user_display_name)


def ist_admin_kopf(x_is_admin: Optional[str]) -> bool:
    """
    X-Is-Admin auswerten. Den Header setzt allein das BFF aus den Claims; aus
    Client-Anfragen entfernt es ihn vorher.
    """
    return (x_is_admin or "").lower() == "true"


def get_aufrufer(
    x_user: Optional[str] = Header(None, alias="X-User"),
    x_is_admin: Optional[str] = Header(None, alias="X-Is-Admin"),
) -> Aufrufer:
    """Wer eine Beitragsantwort bekommt (services/beitrag_fuer_aufrufer.py, #333)."""
    return Aufrufer(kennung=x_user, admin_kopf=ist_admin_kopf(x_is_admin))


def require_user(
    x_user_id: Optional[str] = Header(None, alias="X-User"),
) -> str:
    """
    Die Kennung der angemeldeten Person aus ``X-User``, sonst 401.

    "anonymous" setzt das BFF fuer oeffentliche Endpunkte; es ist keine Kennung.
    """
    if not x_user_id or x_user_id == "anonymous":
        raise HTTPException(status_code=401, detail="Authentication required")
    return x_user_id


def require_admin(
    x_user_id: Optional[str] = Header(None, alias="X-User"),
    x_is_admin: Optional[str] = Header(None, alias="X-Is-Admin"),
) -> str:
    """
    Require admin authentication dependency.
    Raises HTTPException if user is not authenticated or not admin.
    Returns the user ID if admin.
    """
    require_user(x_user_id)

    if not ist_admin_kopf(x_is_admin):
        raise HTTPException(status_code=403, detail="Admin privileges required")

    return x_user_id
