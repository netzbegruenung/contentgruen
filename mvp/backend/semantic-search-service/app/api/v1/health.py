"""
Health check and statistics endpoints for monitoring Gut gesagt.
"""

import os
import psutil
import shutil
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from core.config import settings
from core.logging import get_logger
from infrastructure.database.connection import get_app_database
from services.embeddings.qdrant_embeddings_manager import get_embeddings_manager

logger = get_logger(__name__)

router = APIRouter()


class HealthStatus(BaseModel):
    """Health check response model."""

    status: str
    timestamp: str
    checks: Dict[str, Any]


class StatsResponse(BaseModel):
    """Statistics response model."""

    timestamp: str
    users: Dict[str, int]
    content: Dict[str, Any]
    system: Dict[str, Any]


async def check_database_connection() -> Dict[str, Any]:
    """Check PostgreSQL database connectivity."""
    try:
        db = get_app_database()
        with db.get_session() as session:
            # Simple query to verify connection
            session.execute(text("SELECT 1"))
        return {"status": "healthy", "message": "Database connection successful"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "message": "Database connection failed"}


async def check_qdrant_connection() -> Dict[str, Any]:
    """Check Qdrant vector database connectivity."""
    try:
        manager = get_embeddings_manager()
        # Get health check info from manager
        health_info = await manager.health_check()
        if health_info.get("status") == "healthy":
            return {
                "status": "healthy",
                "message": "Qdrant connection successful",
                "vectors_count": health_info.get("vectors_count") or 0,
            }
        else:
            return {"status": "unhealthy", "message": "Qdrant connection failed"}
    except Exception as e:
        # Log without stack trace - already logged in health_check method
        logger.warning(f"Qdrant health check failed: {e}")
        return {"status": "unhealthy", "message": "Qdrant connection failed"}


def check_disk_space() -> Dict[str, Any]:
    """Check available disk space."""
    try:
        # Check disk space for metadata path
        usage = shutil.disk_usage(settings.metadata_path)
        total_gb = usage.total / (1024**3)
        used_gb = usage.used / (1024**3)
        free_gb = usage.free / (1024**3)
        percent_used = (usage.used / usage.total) * 100

        status = "healthy"
        if percent_used > 90:
            status = "critical"
        elif percent_used > 80:
            status = "warning"

        return {
            "status": status,
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "free_gb": round(free_gb, 2),
            "percent_used": round(percent_used, 2),
        }
    except Exception as e:
        logger.error(f"Disk space check failed: {e}")
        return {"status": "unhealthy", "message": "Disk space check failed"}


def check_memory_usage() -> Dict[str, Any]:
    """Check system memory usage."""
    try:
        memory = psutil.virtual_memory()
        total_gb = memory.total / (1024**3)
        used_gb = memory.used / (1024**3)
        available_gb = memory.available / (1024**3)
        percent_used = memory.percent

        status = "healthy"
        if percent_used > 90:
            status = "critical"
        elif percent_used > 80:
            status = "warning"

        return {
            "status": status,
            "total_gb": round(total_gb, 2),
            "used_gb": round(used_gb, 2),
            "available_gb": round(available_gb, 2),
            "percent_used": round(percent_used, 2),
        }
    except Exception as e:
        logger.error(f"Memory usage check failed: {e}")
        return {"status": "unhealthy", "message": "Memory usage check failed"}


def get_last_backup_time() -> Optional[str]:
    """Get the timestamp of the last backup."""
    try:
        backup_base_path = "/opt/contentgruen-backups"
        latest_daily = os.path.join(backup_base_path, "daily", "latest")
        latest_weekly = os.path.join(backup_base_path, "weekly", "latest")

        # Check for latest daily backup
        if os.path.exists(latest_daily) and os.path.islink(latest_daily):
            target = os.readlink(latest_daily)
            backup_path = os.path.join(backup_base_path, "daily", target)
            if os.path.exists(backup_path):
                mtime = os.path.getmtime(backup_path)
                return datetime.fromtimestamp(mtime).isoformat()

        # Check for latest weekly backup
        if os.path.exists(latest_weekly) and os.path.islink(latest_weekly):
            target = os.readlink(latest_weekly)
            backup_path = os.path.join(backup_base_path, "weekly", target)
            if os.path.exists(backup_path):
                mtime = os.path.getmtime(backup_path)
                return datetime.fromtimestamp(mtime).isoformat()

        return None
    except Exception as e:
        logger.error(f"Failed to get last backup time: {e}")
        return None


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Comprehensive health check endpoint.

    Checks:
    - Database connection (PostgreSQL)
    - Semantic search service (Qdrant)
    - Disk space availability
    - Memory usage

    Returns:
        HealthStatus: Overall health status and individual check results
    """
    logger.debug("Running health check")

    # Run all health checks
    database_check = await check_database_connection()
    qdrant_check = await check_qdrant_connection()
    disk_check = check_disk_space()
    memory_check = check_memory_usage()

    # Determine overall status
    checks = {
        "database": database_check,
        "qdrant": qdrant_check,
        "disk": disk_check,
        "memory": memory_check,
    }

    # Overall status is unhealthy if any critical check fails
    overall_status = "healthy"
    for check_name, check_result in checks.items():
        if check_result.get("status") == "unhealthy":
            overall_status = "unhealthy"
            break
        elif check_result.get("status") == "critical":
            overall_status = "degraded"

    # Log health check results
    if overall_status == "healthy":
        logger.info(
            f"✅ Health check passed - DB: {database_check['status']}, "
            f"Qdrant: {qdrant_check['status']} ({qdrant_check.get('vectors_count', 0)} vectors), "
            f"Disk: {disk_check['status']} ({disk_check.get('percent_used', 0)}%), "
            f"Memory: {memory_check['status']} ({memory_check.get('percent_used', 0)}%)"
        )
    elif overall_status == "degraded":
        logger.warning(
            f"⚠️ Health check degraded - DB: {database_check['status']}, "
            f"Qdrant: {qdrant_check['status']}, "
            f"Disk: {disk_check['status']}, "
            f"Memory: {memory_check['status']}"
        )
    else:
        logger.error(
            f"❌ Health check failed - DB: {database_check['status']}, "
            f"Qdrant: {qdrant_check['status']}, "
            f"Disk: {disk_check['status']}, "
            f"Memory: {memory_check['status']}"
        )

    return HealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        checks=checks,
    )


@router.get("/stats", response_model=StatsResponse)
async def get_statistics():
    """
    Get system statistics.

    Returns:
        StatsResponse: Statistics about users, content, and system resources
    """
    logger.debug("Fetching system statistics")

    try:
        # Get database statistics
        db = get_app_database()
        with db.get_session() as session:
            # Count unique users from votes table
            result = session.execute(text("SELECT COUNT(DISTINCT user_id) FROM votes"))
            unique_voters = result.scalar() or 0

        # Get Qdrant statistics
        manager = get_embeddings_manager()
        health_info = await manager.health_check()

        # Get disk and memory info
        disk_usage = shutil.disk_usage(settings.metadata_path)
        memory = psutil.virtual_memory()

        # Get last backup time
        last_backup = get_last_backup_time()

        # Calculate percentages for logging
        disk_percent = round((disk_usage.used / disk_usage.total) * 100, 2)
        memory_percent = round(memory.percent, 2)
        total_vectors = health_info.get("vectors_count", 0)

        logger.info(
            f"📊 Statistics retrieved - Users: {unique_voters}, "
            f"Vectors: {total_vectors}, "
            f"Disk: {disk_percent}%, "
            f"Memory: {memory_percent}%, "
            f"Last backup: {last_backup or 'none'}"
        )

        return StatsResponse(
            timestamp=datetime.utcnow().isoformat(),
            users={
                "total_voters": unique_voters,
            },
            content={
                "total_vectors": total_vectors,
                "collection_name": settings.qdrant_collection,
                "qdrant_url": settings.qdrant_url,
            },
            system={
                "disk": {
                    "total_gb": round(disk_usage.total / (1024**3), 2),
                    "used_gb": round(disk_usage.used / (1024**3), 2),
                    "free_gb": round(disk_usage.free / (1024**3), 2),
                    "percent_used": disk_percent,
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "percent_used": memory_percent,
                },
                "last_backup": last_backup,
            },
        )

    except Exception as e:
        logger.error(f"Failed to fetch statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch statistics: {e}")
