import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks

# Import configuration first
from core.config import settings

# Initialize logging with dependency injection
from core.logging import initialize_logging, get_logger

initialize_logging(settings.get_logging_config())
logger = get_logger(__name__)

logger.info("📚 Importing FastAPI app dependencies")
logger.debug(f"📁 Current directory: {os.getcwd()}")

from dependencies import initialize_services
from services.embeddings.qdrant_embeddings_manager import (
    get_qdrant_embeddings_manager,
    get_embeddings_manager,
)
from services.seeding.seeding_service import get_seeding_service
from infrastructure.database.connection import get_app_database, close_app_database
from api.v1.candidate import router as candidates_router
from api.v1.commentary import router as commentary_router
from api.v1.content import router as content_router
from api.v1.contribution import router as contribution_router
from api.v1.metrics import router as metrics_router
from api.v1.reference import router as reference_router

# from api.v1.scores import router as scores_router
from api.v1.search import router as search_router
from api.v1.statement import router as statement_router
from api.v1.test import router as test_router

from api.v1.generic_text import router as generic_text_router
from api.v1.post import router as post_router
from api.v1.image import router as image_router
from api.v1.raw_input import router as raw_input_router
from api.v1.seeding import router as seeding_router
from api.v1.usage import router as usage_router
from api.v1.voting import router as voting_router
from api.v1.moderation import router as moderation_router
from api.v1.health import router as health_router
from services.cleanup.usage_cleanup_service import start_cleanup_scheduler
from services.vision.image_description_worker import start_description_worker
from utils.rate_limiter import report_rate_limiter
import asyncio

# This is a workaround for a dependency issue: "OMP: Error #15: Initializing libomp140.x86_64.dll, but found libomp140.x86_64.dll already initialized.""
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


async def rate_limiter_cleanup():
    """Background task to periodically clean up expired rate limiter entries."""
    while True:
        try:
            await asyncio.sleep(3600)  # Run every hour
            logger.debug("Running rate limiter cleanup...")
            report_rate_limiter.cleanup()
            logger.debug("Rate limiter cleanup completed")
        except Exception as e:
            logger.error(f"Error in rate limiter cleanup: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager that handles QdrantEmbeddingsManager startup/shutdown
    and non-blocking seeding initialization.
    """
    # Startup
    try:
        logger.info("🚀 Starting ContentGrün Semantic Search Service v1.0.0")

        # Initialize QdrantEmbeddingsManager with settings (fast)
        shared_manager = get_qdrant_embeddings_manager(settings)
        await shared_manager.start()
        logger.info("✅ QdrantEmbeddingsManager started")

        # Initialize application database
        logger.info("Initializing application database")
        app_db = get_app_database()
        app_db.create_tables()
        logger.info("✅ Application database initialized")

        # Initialize seeding service with metadata path
        seeding_service = get_seeding_service(
            settings, shared_manager, settings.metadata_path
        )
        logger.info("✅ SeedingService initialized")

        # Store seeding service for manual API access (no automatic seeding)
        logger.info("Seeding available via /api/v1/seeding/start endpoint")

        # Initialize lightweight content services (without blocking data load)
        logger.info("Initializing content services...")
        initialize_services()
        logger.info("✅ Content services initialized")

        # Start cleanup scheduler for usage data retention
        logger.info("Starting usage data cleanup scheduler...")
        start_cleanup_scheduler()
        logger.info("✅ Cleanup scheduler started")

        # Start image description worker (processes PENDING_DESCRIPTION images async)
        logger.info("Starting image description worker...")
        from dependencies import get_image_service
        from domain.content_registry import REGISTRY
        from domain.models.content_type import ContentType

        try:
            _image_svc = get_image_service()
            if _image_svc is None:
                logger.warning(
                    "⚠️ Image description worker not started: embeddings manager unavailable"
                )
            else:
                start_description_worker(
                    _image_svc, REGISTRY[ContentType.IMAGE].ingestion
                )
                logger.info("✅ Image description worker started")
        except Exception as e:
            logger.warning(f"⚠️ Image description worker could not start: {e}")

        # Start rate limiter cleanup task
        logger.info("Starting rate limiter cleanup task...")
        asyncio.create_task(rate_limiter_cleanup())
        logger.info("✅ Rate limiter cleanup task started")

        logger.info(
            "✅ Application startup complete - server ready to accept connections"
        )

        # Store seeding service for API access
        app.state.seeding_service = seeding_service

        yield  # Server is now ready to accept connections

    finally:
        # Shutdown
        try:
            logger.info("Shutting down ContentGrün Semantic Search Service")
            manager = get_embeddings_manager()
            await manager.shutdown()
            close_app_database()
            logger.info("✅ Application shutdown complete")
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}", exc_info=True)


logger.info("🔧 Initializing FastAPI app")

# Initialize FastAPI app with lifespan management
app = FastAPI(
    title="Gut gesagt API",
    description="Semantic search API with unified embeddings",
    version="1.0.0",
    lifespan=lifespan,
)

# Add rate limiting middleware for content creation endpoints
from middleware.rate_limit import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=10,  # Max 10 requests per minute per user
    requests_per_hour=100,  # Max 100 requests per hour per user
)

app.include_router(candidates_router, prefix="/api/v1/candidates", tags=["candidates"])
app.include_router(commentary_router, prefix="/api/v1/commentary", tags=["commentary"])
app.include_router(content_router, prefix="/api/v1/content", tags=["content"])
app.include_router(
    contribution_router, prefix="/api/v1/contribution", tags=["contribution"]
)
app.include_router(metrics_router, prefix="/api/v1/metrics", tags=["metrics"])
app.include_router(reference_router, prefix="/api/v1/reference", tags=["reference"])
# app.include_router(scores_router, prefix="/api/v1/scores", tags=["scores"])
app.include_router(search_router, prefix="/api/v1/search", tags=["search"])
app.include_router(statement_router, prefix="/api/v1/statement", tags=["statement"])
app.include_router(test_router, prefix="/api/v1/test", tags=["test"])
app.include_router(
    generic_text_router, prefix="/api/v1/generic_text", tags=["generic_text"]
)
app.include_router(post_router, prefix="/api/v1/post", tags=["post"])
app.include_router(image_router, prefix="/api/v1/image", tags=["image"])
app.include_router(raw_input_router, prefix="/api/v1/rawinput", tags=["rawinput"])
app.include_router(seeding_router, prefix="/api/v1", tags=["seeding"])
app.include_router(usage_router, prefix="/api/v1/usage", tags=["usage"])
app.include_router(voting_router, prefix="/api/v1/voting", tags=["voting"])
app.include_router(moderation_router, prefix="/api/v1/moderation", tags=["moderation"])
app.include_router(health_router, prefix="/api/v1", tags=["monitoring"])


if __name__ == "__main__":
    import uvicorn

    logger.info("🚀 Starting FastAPI server")

    uvicorn.run(app, host="0.0.0.0")
