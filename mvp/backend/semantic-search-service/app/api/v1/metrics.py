from fastapi import APIRouter, Depends, HTTPException, Request, Query
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, Field

from dtos.metrics import GetMetricsResponse
from dependencies import (
    get_commentary_service,
    get_reference_service,
    get_statement_service,
    get_settings,
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
    """Response model for searches per user statistics."""

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


# Retrieves the metrics of the system for display
@router.get("/getMetrics", response_model=GetMetricsResponse)
async def get_metrics(
    request: Request,
    statement_service: StatementService = Depends(get_statement_service),
    commentary_service: CommentaryService = Depends(get_commentary_service),
    reference_service: ReferenceService = Depends(get_reference_service),
    settings: Settings = Depends(get_settings),
) -> GetMetricsResponse:
    try:
        print("/getMetrics was called")

        headers = request.headers  # Get all headers
        print("Received headers:")
        for header, value in headers.items():
            print(f"{header}: {value}")

        repository_factory = QdrantRepositoryFactory()
        content_repository = repository_factory.create_content_repository(settings)
        content_count = await content_repository.count()

        metrics = GetMetricsResponse(
            content_count=content_count,
            content_count_last_week=0,
            statement_count=await statement_service.count(),
            statement_count_last_week=0,
            commentary_count=await commentary_service.count(),
            commentary_count_last_week=0,
            reference_count=await reference_service.count(),
            reference_count_last_week=0,
            requested_commentary_count=0,
            active_users_count=0,
        )

        return metrics
    except Exception as e:
        print("Error in getMetrics: ", e)
        raise HTTPException(status_code=500, detail=str(e))


# MVP Metrics Endpoints
@router.get("/mvp-dashboard", response_model=MVPMetricsResponse)
async def get_mvp_dashboard_metrics(settings: Settings = Depends(get_settings)):
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
