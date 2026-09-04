import asyncio
import time

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field

from dtos.metrics import GetMetricsResponse
from dependencies import (
    get_commentary_service,
    get_reference_service,
    get_statement_service,
    get_settings,
    require_admin,
)
from services.content.commentary_service import CommentaryService
from repositories.implementations.qdrant.qdrant_repository_factory import (
    QdrantRepositoryFactory,
)
from services.content.reference_service import ReferenceService
from services.content.statement_service import StatementService
from services.metrics_service import get_metrics_service
from core.config import Settings
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# /getMetrics ist anonym erreichbar und loest vier count-Abfragen gegen Qdrant aus.
# Die RateLimitMiddleware greift hier nicht -- sie limitiert ausschliesslich POSTs auf
# einer Namensliste (/addStatement und Geschwister). Ohne Cache laesst sich der
# Endpunkt also unbegrenzt oft abrufen und multipliziert dabei die Qdrant-Last.
#
# Bestandszaehler aendern sich langsam; 60 Sekunden Verzoegerung ist fuer die Anzeige
# auf der Startseite nicht wahrnehmbar. Der Cache liegt im Prozess (ein Container, ein
# Wert) und braucht deshalb kein Redis.
_METRICS_CACHE_TTL_SECONDS = 60
_metrics_cache: Optional[tuple[float, GetMetricsResponse]] = None
# Ohne Lock wuerden bei abgelaufenem Cache alle gleichzeitig wartenden Requests die
# Zaehlung parallel ausloesen -- genau die Spitze, die der Cache verhindern soll.
_metrics_cache_lock = asyncio.Lock()


# Response Models for MVP Metrics
class MVPMetricsResponse(BaseModel):
    """Response model for MVP dashboard metrics."""

    timestamp: str
    period_days: int
    daily_active_users: int
    daily_active_users_goal: int
    daily_active_users_met: bool
    searches_per_user: float
    searches_per_user_goal: float
    searches_per_user_met: bool
    content_created_this_week: int
    content_created_goal: int
    content_created_met: bool
    usage_counter_total: int
    usage_counter_current_week: int
    usage_counter_previous_week: int
    usage_counter_trend: str
    usage_counter_met: bool
    helpful_rate: float
    helpful_rate_goal: float
    helpful_rate_met: bool
    helpful_like_count: int
    helpful_dislike_count: int
    helpful_total_votes: int


class DailyActiveUsersResponse(BaseModel):
    """Response model for daily active users."""

    date: str
    active_users: int


class SearchesPerUserResponse(BaseModel):
    """Response model for searches per user statistics.

    total_users counts active user-days, not distinct people: search events carry a
    pseudonym that rotates daily, so nobody can be followed across the window.
    """

    period_days: int
    average: float
    median: int
    total_users: int
    total_searches: int


class ContentCreatedResponse(BaseModel):
    """Response model for content creation statistics."""

    weeks_analyzed: int
    weekly_stats: list


class UsageTrendResponse(BaseModel):
    """Response model for usage trend statistics."""

    weeks_analyzed: int
    weekly_stats: list
    trend_direction: str


class HelpfulRateResponse(BaseModel):
    """Response model for helpful rate statistics."""

    period_days: int
    like_count: int
    dislike_count: int
    total_votes: int
    helpful_rate: float


# Bewusst oeffentlich: /getMetrics liefert nur aggregierte Bestandszaehler
# (content_count, statement_count, commentary_count, reference_count -- die
# uebrigen Felder sind im Code hart 0) und wird von der Startseite aufgerufen,
# die ueber den PublicGuard auch anonym erreichbar ist. Die Betriebskennzahlen
# stehen in den Endpunkten darunter, die admin-only sind.
@router.get("/getMetrics", response_model=GetMetricsResponse)
async def get_metrics(
    statement_service: StatementService = Depends(get_statement_service),
    commentary_service: CommentaryService = Depends(get_commentary_service),
    reference_service: ReferenceService = Depends(get_reference_service),
    settings: Settings = Depends(get_settings),
) -> GetMetricsResponse:
    global _metrics_cache

    try:
        # Der frueher hier stehende Dump saemtlicher eingehender Header ist ersatzlos
        # entfernt: er schrieb bei jedem Aufruf das Session-Cookie im Klartext in die
        # Container-Logs.
        logger.debug("/getMetrics was called")

        cached = _metrics_cache
        if (
            cached is not None
            and time.monotonic() - cached[0] < _METRICS_CACHE_TTL_SECONDS
        ):
            return cached[1]

        async with _metrics_cache_lock:
            # Erneut pruefen: waehrend des Wartens auf den Lock kann ein anderer
            # Request den Cache bereits gefuellt haben.
            cached = _metrics_cache
            if (
                cached is not None
                and time.monotonic() - cached[0] < _METRICS_CACHE_TTL_SECONDS
            ):
                return cached[1]

            repository_factory = QdrantRepositoryFactory()
            content_repository = repository_factory.create_content_repository(settings)
            content_count = await content_repository.count()

            metrics = GetMetricsResponse(
                content_count=content_count,
                content_count_last_week=0,
                statement_count=await statement_service.count_curated(),
                statement_count_last_week=0,
                commentary_count=await commentary_service.count(),
                commentary_count_last_week=0,
                reference_count=await reference_service.count(),
                reference_count_last_week=0,
                requested_commentary_count=0,
                active_users_count=0,
            )

            _metrics_cache = (time.monotonic(), metrics)
            return metrics
    except Exception as e:
        logger.error(f"Error in getMetrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# MVP Metrics Endpoints -- alle admin-only.
#
# Sie liefern Betriebskennzahlen: taegliche aktive Nutzer, Suchvolumen pro
# Nutzer, Content-Zuwachs und Vote-Verhaeltnisse. Bis hierher waren sie ohne
# jede Auth-Dependency erreichbar.
#
# require_admin prueft X-Is-Admin, das der IdentityHeaderTransform aus den
# Claims setzt -- dieselbe Grundlage wie der AdminGuard im Frontend. Es braucht
# dafuer kein SEMANTIC_SEARCH_ADMIN_USERS; diese Variable gilt nur fuer die
# Cleanup-Endpunkte in api/v1/usage.py, die mit settings.is_admin_user() gegen
# eine Namensliste pruefen.
@router.get("/mvp-dashboard", response_model=MVPMetricsResponse)
async def get_mvp_dashboard_metrics(
    settings: Settings = Depends(get_settings),
    admin_user: str = Depends(require_admin),
):
    """
    Get comprehensive MVP dashboard metrics.

    Returns all 5 key metrics for MVP goals:
    1. Daily Active Users (Goal: 10)
    2. Searches per User (Goal: >3)
    3. Content Created per Week (Goal: 20)
    4. Usage Counter Sum (must be increasing weekly)
    5. "War hilfreich" Rate (Goal: >60%)
    """
    try:
        logger.info("Fetching MVP dashboard metrics")
        metrics_service = get_metrics_service()
        metrics = metrics_service.get_mvp_dashboard_metrics()
        return MVPMetricsResponse(**metrics)
    except Exception as e:
        logger.error(f"Error fetching MVP dashboard metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch MVP metrics: {e}")


@router.get("/daily-active-users", response_model=DailyActiveUsersResponse)
async def get_daily_active_users(
    target_date: Optional[date] = Query(None, description="Date to check (YYYY-MM-DD)"),
    settings: Settings = Depends(get_settings),
    admin_user: str = Depends(require_admin),
):
    """
    Get count of unique active users for a specific day.

    Args:
        target_date: Date to check (defaults to today)

    Returns:
        DailyActiveUsersResponse with count of unique users/sessions
    """
    try:
        metrics_service = get_metrics_service()
        dau = metrics_service.get_daily_active_users(target_date)

        return DailyActiveUsersResponse(
            date=(target_date or date.today()).isoformat(), active_users=dau
        )
    except Exception as e:
        logger.error(f"Error fetching daily active users: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch daily active users: {e}"
        )


@router.get("/searches-per-user", response_model=SearchesPerUserResponse)
async def get_searches_per_user(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    settings: Settings = Depends(get_settings),
    admin_user: str = Depends(require_admin),
):
    """
    Get search statistics per user/session.

    Args:
        days: Number of days to analyze (default: 7)

    Returns:
        SearchesPerUserResponse with average, median, and distribution stats
    """
    try:
        metrics_service = get_metrics_service()
        stats = metrics_service.get_searches_per_user(days)

        return SearchesPerUserResponse(period_days=days, **stats)
    except Exception as e:
        logger.error(f"Error fetching searches per user: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch searches per user: {e}"
        )


@router.get("/content-created", response_model=ContentCreatedResponse)
async def get_content_created(
    weeks: int = Query(4, ge=1, le=12, description="Number of weeks to analyze"),
    settings: Settings = Depends(get_settings),
    admin_user: str = Depends(require_admin),
):
    """
    Get content creation statistics by week.

    Args:
        weeks: Number of weeks to analyze (default: 4)

    Returns:
        ContentCreatedResponse with weekly content creation stats
    """
    try:
        metrics_service = get_metrics_service()
        weekly_stats = metrics_service.get_content_created_per_week(weeks)

        return ContentCreatedResponse(weeks_analyzed=weeks, weekly_stats=weekly_stats)
    except Exception as e:
        logger.error(f"Error fetching content created: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch content created: {e}"
        )


@router.get("/usage-trend", response_model=UsageTrendResponse)
async def get_usage_trend(
    weeks: int = Query(4, ge=2, le=12, description="Number of weeks to analyze"),
    settings: Settings = Depends(get_settings),
    admin_user: str = Depends(require_admin),
):
    """
    Get usage counter trend by week.

    Args:
        weeks: Number of weeks to analyze (default: 4)

    Returns:
        UsageTrendResponse with weekly usage stats and trend direction
    """
    try:
        metrics_service = get_metrics_service()
        weekly_stats = metrics_service.get_usage_counter_trend(weeks)

        # Determine trend direction
        trend_direction = "stable"
        if len(weekly_stats) >= 2:
            current = weekly_stats[0]["usage_count"]
            previous = weekly_stats[1]["usage_count"]
            if current > previous * 1.1:
                trend_direction = "increasing"
            elif current < previous * 0.9:
                trend_direction = "decreasing"

        return UsageTrendResponse(
            weeks_analyzed=weeks,
            weekly_stats=weekly_stats,
            trend_direction=trend_direction,
        )
    except Exception as e:
        logger.error(f"Error fetching usage trend: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch usage trend: {e}")


@router.get("/helpful-rate", response_model=HelpfulRateResponse)
async def get_helpful_rate(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    settings: Settings = Depends(get_settings),
    admin_user: str = Depends(require_admin),
):
    """
    Get the "War hilfreich" rate (percentage of likes vs total votes).

    Args:
        days: Number of days to analyze (default: 7)

    Returns:
        HelpfulRateResponse with like/dislike counts and helpful rate percentage
    """
    try:
        metrics_service = get_metrics_service()
        stats = metrics_service.get_helpful_rate(days)

        return HelpfulRateResponse(period_days=days, **stats)
    except Exception as e:
        logger.error(f"Error fetching helpful rate: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch helpful rate: {e}"
        )
