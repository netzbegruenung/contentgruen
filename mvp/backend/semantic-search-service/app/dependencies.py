import uuid
from typing import Optional, TYPE_CHECKING
from fastapi import Depends, Header, HTTPException

if TYPE_CHECKING:
    # Only needed for the type annotation on the lazily-built Post service; imported
    # under TYPE_CHECKING to avoid pulling the registry/service graph at module load.
    from services.content.base_content_service import BaseContentService
from core.config import settings, Settings
from utils.rate_limiter import RateLimiter
from services.orchestration.content_orchestrator import ContentOrchestrator
from services.content.commentary_service import CommentaryService
from services.content.reference_service import ReferenceService
from services.content.statement_service import StatementService
from services.content.generic_text_service import GenericTextService
from services.voting_service import VotingService
from services.anzeigename_service import angemeldet, get_anzeigename_service
from services import art9_einwilligung_service
from services.beitrag_fuer_aufrufer import Aufrufer
from services.content.beitrag_aendern_service import BeitragAendernService
from services.content.beitrag_loeschen_service import BeitragLoeschenService
from services.beitrag_laden import BeitragLader, beitrag_laden
from repositories.interfaces.content_repository import IContentRepository
from repositories.implementations.qdrant.moderation_repository import (
    get_moderation_repository,
)
from services.suchen_ohne_treffer_service import (
    SuchenOhneTrefferService,
    get_personen_des_tages,
)
from services.unbeantwortete_aussagen_service import UnbeantworteteAussagenService
from services.aussage_themen_service import AussageThemenService
from repositories.aussage_themen_repository import get_aussage_themen_repository
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from repositories.suchen_ohne_treffer_repository import (
    get_suchen_ohne_treffer_repository,
)
from repositories.feedback_repository import get_feedback_repository
from services.feedback_service import FeedbackService
from repositories.einladung_repository import get_einladung_repository
from services.einladung_service import EinladungService
from infrastructure.keycloak_konten import KeycloakKonten
from services.bilanz_service import BilanzService
from repositories.search_tracking_repository import get_search_tracking_repository
from repositories.usage_tracking_repository import get_usage_repository
from services.gegenlesen.gegenlesen_service import (
    SPRACHWERKZEUGE,
    GegenlesenService,
    lade_statt_sag_liste,
)
from services.kuerzungsvorschlag_service import KuerzungsvorschlagService
from services.loeschfristen_service import LoeschfristenService
from services.muster_hinweise_service import MusterHinweiseService
from services.punkte_service import PunkteService
from services.spracherkennung.spracherkennung import SPRACHERKENNUNG, Spracherkennung
from services.moderation_service import ModerationService
from repositories.content_report_repository import get_content_report_repository
from repositories.einwurf_repository import get_einwurf_repository
from repositories.sperre_repository import get_sperre_repository
from core.fehler import INTERNER_FEHLER
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
    # NLI-Stufe (#387): das Modell im Hintergrund laden, damit die erste Suche nicht
    # darauf wartet. Ohne Modell gilt die Schwelle, der Start scheitert nicht daran.
    statement_service_instance.nli_vorladen()

    global commentary_service_instance
    commentary_service_instance = CommentaryService(settings=settings_instance)

    global reference_service_instance
    reference_service_instance = ReferenceService(settings=settings_instance)

    global generic_text_service_instance
    generic_text_service_instance = GenericTextService(settings=settings_instance)

    global voting_service_instance
    voting_service_instance = VotingService(settings_instance.startkonto_kennungen())
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


def get_bilanz_service(
    settings: Settings = Depends(get_settings),
) -> BilanzService:
    # Ohne Bereinigungsjob bleiben die Nutzungsereignisse, eine Frist gilt dann nicht.
    return BilanzService(
        get_search_tracking_repository(),
        get_usage_repository(),
        settings.usage_retention_days if settings.enable_bereinigungsjob else None,
    )


def get_aussage_themen_service(
    statement_service: StatementService = Depends(get_statement_service),
) -> AussageThemenService:
    return AussageThemenService(get_aussage_themen_repository(), statement_service)


def get_unbeantwortete_aussagen_service(
    statement_service: StatementService = Depends(get_statement_service),
    suchen_ohne_treffer: SuchenOhneTrefferService = Depends(
        get_suchen_ohne_treffer_service
    ),
    themen: AussageThemenService = Depends(get_aussage_themen_service),
) -> UnbeantworteteAussagenService:
    return UnbeantworteteAussagenService(statement_service, suchen_ohne_treffer, themen)


def get_feedback_service() -> FeedbackService:
    return FeedbackService(get_feedback_repository())


def get_punkte_service(
    settings: Settings = Depends(get_settings),
) -> PunkteService:
    from domain.content_registry import BEITRAGSTYPEN_WERTE
    from repositories.aggregated.content_repository import ContentRepository
    from repositories.punkte_repository import get_punkte_repository
    from repositories.usage_tracking_repository import get_usage_repository

    async def sichtbare_beitraege(user_id: str):
        # get_by_author laesst gesperrte und geloeschte Beitraege aus: Sie verlieren
        # ihre Punkte (#352).
        return await ContentRepository(settings).get_by_author(
            # Alle Beitraege der Person, wie get_user_statistics.
            user_id,
            limit=10000,
            offset=0,
            content_types=BEITRAGSTYPEN_WERTE,
        )

    return PunkteService(
        sichtbare_beitraege, get_usage_repository(), get_punkte_repository(), settings
    )


def get_muster_hinweise_service() -> MusterHinweiseService:
    from repositories.muster_hinweis_repository import get_muster_hinweis_repository

    return MusterHinweiseService(get_muster_hinweis_repository())


def _keycloak_konten() -> Optional[KeycloakKonten]:
    """Ohne Zugang zur Keycloak-Admin-Schnittstelle None; so laeuft es im Dev-Stack."""
    if not (
        settings.keycloak_url
        and settings.keycloak_admin_client_id
        and settings.keycloak_admin_client_secret
    ):
        return None
    return KeycloakKonten(
        basis_url=settings.keycloak_url,
        realm=settings.keycloak_realm,
        client_id=settings.keycloak_admin_client_id,
        client_secret=settings.keycloak_admin_client_secret,
        app_client_id=settings.keycloak_app_client_id,
        app_url=settings.app_url,
    )


def get_einladung_service() -> EinladungService:
    """
    Ohne Zugang zur Keycloak-Admin-Schnittstelle lassen sich Einladungen verwalten,
    aber nicht einloesen (503).
    """
    return EinladungService(get_einladung_repository(), _keycloak_konten())


_gegenlesen_service: Optional[GegenlesenService] = None


_nutzung_rate_limiter: Optional[RateLimiter] = None


def get_nutzung_rate_limiter() -> RateLimiter:
    """Das Rate-Limit am Zaehl-Endpunkt (#352), Werte aus der Konfiguration."""
    global _nutzung_rate_limiter
    if _nutzung_rate_limiter is None:
        _nutzung_rate_limiter = RateLimiter(
            max_requests=settings.nutzung_rate_limit_anfragen,
            window_minutes=settings.nutzung_rate_limit_minuten,
        )
    return _nutzung_rate_limiter


def get_gegenlesen_service() -> GegenlesenService:
    """Einmal je Prozess: die Liste "statt X sag Y" wird beim ersten Aufruf gelesen."""
    global _gegenlesen_service
    if _gegenlesen_service is None:
        _gegenlesen_service = GegenlesenService(
            statt_sag=lade_statt_sag_liste(), werkzeuge=SPRACHWERKZEUGE
        )
    return _gegenlesen_service


def get_spracherkennung() -> Spracherkennung:
    """Eine Instanz je Prozess; der Start lädt Lingua vor (main.py)."""
    return SPRACHERKENNUNG


_kuerzungsvorschlag_service: Optional[KuerzungsvorschlagService] = None


def get_kuerzungsvorschlag_service() -> KuerzungsvorschlagService:
    """Einmal je Prozess; teilt sich das Sprachmodell mit dem Gegenlesen (#403)."""
    global _kuerzungsvorschlag_service
    if _kuerzungsvorschlag_service is None:
        _kuerzungsvorschlag_service = KuerzungsvorschlagService(
            werkzeuge=SPRACHWERKZEUGE
        )
    return _kuerzungsvorschlag_service


def get_moderation_service() -> ModerationService:
    """
    Der Moderationsdienst ueber die Repository-Singletons. Die Repositories, die erst
    das endgueltige Entfernen braucht (Stimmen, Einwuerfe, Sperren), holt der Dienst
    selbst, wenn es so weit ist; vorher oeffnet er keine Verbindung dafuer.
    """
    return ModerationService(
        report_repo=get_content_report_repository(),
        moderation_repo=get_moderation_repository(),
    )


def get_loeschfristen_service() -> LoeschfristenService:
    return LoeschfristenService(
        get_content_report_repository(),
        get_einwurf_repository(),
        get_moderation_repository(),
        get_moderation_service(),
        get_sperre_repository(),
        # Ohne Zugang zur Keycloak-Admin-Schnittstelle bleiben Konten im Realm unberuehrt.
        _keycloak_konten(),
    )


def get_content_repository(
    settings: Settings = Depends(get_settings),
) -> IContentRepository:
    """Das aggregierte Content-Repository: liest und loescht jeden Beitragstyp."""
    return QdrantRepositoryFactory().create_content_repository(settings)


def get_beitrag_laden(settings: Settings = Depends(get_settings)) -> BeitragLader:
    """
    ``beitrag_laden`` ueber das aggregierte Repository, fuer Nutzung und Stimmen.

    Das Repository entsteht erst beim Laden, nicht beim Aufloesen der Dependency:
    Scheitert es, faengt das ``try`` des Endpunkts den Fehler wie einen Ausfall des
    Suchindex (die Stimme zaehlt trotzdem, die Nutzung antwortet mit ihrem 500).
    """

    async def laden(content_id: uuid.UUID):
        return await beitrag_laden(content_id, get_content_repository(settings))

    return laden


def get_beitrag_loeschen_service(
    repository: IContentRepository = Depends(get_content_repository),
) -> BeitragLoeschenService:
    """Ueber das aggregierte Repository: Loeschen gilt fuer jeden Beitragstyp."""
    return BeitragLoeschenService(repository, get_moderation_repository())


def get_beitrag_aendern_service(
    repository: IContentRepository = Depends(get_content_repository),
) -> BeitragAendernService:
    """Ueber das aggregierte Repository, wie das Loeschen (#299)."""
    return BeitragAendernService(
        repository,
        get_reference_service().herkunft_id,
        get_content_report_repository().hat_offene_meldung,
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
    """Wer eine Antwort mit Personenbezug bekommt (services/beitrag_fuer_aufrufer.py, #333, #385)."""
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


# Antworttext, an dem das Frontend erkennt, dass die Art.-9-Einwilligung fehlt
# (auth.interceptor.ts), und dann auf /einwilligung fuehrt.
ART9_EINWILLIGUNG_FEHLT = "art9_einwilligung_fehlt"


def require_art9_einwilligung(
    x_user: Optional[str] = Header(None, alias="X-User"),
) -> None:
    """
    Sperrt einen Endpunkt fuer angemeldete Personen ohne geltende
    Art.-9-Einwilligung (#489) mit 403. Ob jemand angemeldet sein muss,
    entscheidet der Endpunkt selbst; ohne Anmeldung laesst diese Pruefung durch.

    Synchron, damit FastAPI sie im Threadpool ausfuehrt: Sie fragt die Datenbank.
    """
    if not angemeldet(x_user):
        return
    try:
        eingewilligt = (
            art9_einwilligung_service.get_art9_einwilligung_service().eingewilligt(
                x_user
            )
        )
    except Exception as e:
        logger.error(
            f"Art.-9-Einwilligung nicht lesbar: {type(e).__name__}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)
    if not eingewilligt:
        raise HTTPException(status_code=403, detail=ART9_EINWILLIGUNG_FEHLT)


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
