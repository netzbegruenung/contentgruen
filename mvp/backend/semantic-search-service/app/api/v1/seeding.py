import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any

from services.seeding.seeding_service import get_seeding_service
from services.seeding.seeding_status import SeedingStatus

router = APIRouter(prefix="/seeding", tags=["seeding"])


@router.get("/status")
async def get_seeding_status(health_check: bool = False) -> Dict[str, Any]:
    """
    Get current seeding status and progress.

    Args:
        health_check: If true, returns simplified health check format that never fails

    Returns:
        Dictionary containing seeding status, progress, and timing information
    """
    try:
        seeding_service = get_seeding_service()
        progress = await seeding_service.get_progress()
        needs_seeding = await seeding_service.needs_seeding()

        # Base information for both modes
        base_result = {
            "status": progress.status.value,
            "progress": {
                "files_processed": progress.files_processed,
                "total_files": progress.total_files,
                "percentage": round(progress.get_progress_percent(), 1),
            },
        }

        # Health check mode: simplified response that never fails
        if health_check:
            return {
                **base_result,
                "seeding_needed": needs_seeding,
                "is_healthy": progress.status
                in [
                    SeedingStatus.COMPLETED,
                    SeedingStatus.NOT_STARTED,
                    SeedingStatus.RUNNING,
                ],
            }

        # Full status mode: detailed information
        result = {
            **base_result,
            "current_file": progress.current_file,
            "seeding_needed": needs_seeding,
            "timestamps": {
                "started_at": (
                    progress.started_at.isoformat() if progress.started_at else None
                ),
                "completed_at": (
                    progress.completed_at.isoformat() if progress.completed_at else None
                ),
                "last_updated": (
                    progress.last_updated.isoformat() if progress.last_updated else None
                ),
            },
        }

        # Add estimated completion time if running
        if progress.is_running():
            estimated_seconds = progress.estimate_time_remaining()
            if estimated_seconds:
                result["estimated_completion_seconds"] = estimated_seconds
                result["estimated_completion_minutes"] = round(
                    estimated_seconds / 60, 1
                )

        # Add error information if failed
        if progress.status == SeedingStatus.FAILED and progress.error_message:
            result["error"] = progress.error_message

        # Add content statistics for idempotent seeding
        result["content_stats"] = {
            "added": getattr(progress, "content_added", 0),
            "skipped": getattr(progress, "content_skipped", 0),
            "processed_fingerprints_count": len(
                getattr(progress, "processed_fingerprints", [])
            ),
        }

        return result

    except Exception as e:
        # Health check mode: never fail, return error status
        if health_check:
            return {
                "status": "error",
                "progress": {"files_processed": 0, "total_files": 0, "percentage": 0},
                "seeding_needed": True,
                "is_healthy": False,
                "error": str(e),
            }
        # Normal mode: raise HTTP exception
        raise HTTPException(
            status_code=500, detail=f"Error getting seeding status: {str(e)}"
        )


@router.get("/health")
async def get_seeding_health() -> Dict[str, Any]:
    """
    Get seeding health status for health checks.

    This is a convenience endpoint that calls /status?health_check=true
    Suitable for automated monitoring systems that need simplified responses.
    """
    return await get_seeding_status(health_check=True)


@router.post("/start")
async def start_seeding(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """
    Manually start the seeding process.

    This endpoint allows administrators to manually trigger seeding,
    for example after uploading new JSON files.
    """
    try:
        seeding_service = get_seeding_service()
        progress = await seeding_service.get_progress()

        # Check if already running
        if progress.is_running():
            raise HTTPException(status_code=409, detail="Seeding is already running")

        # Check if seeding is available (has JSON files to process)
        needs_seeding = await seeding_service.needs_seeding()
        if not needs_seeding:
            return {
                "message": "Seeding not needed - no seed files found",
                "status": "skipped",
            }

        # Start seeding in background (Qdrant handles concurrency properly)
        async def run_seeding():
            try:
                await seeding_service.start_seeding()
            except Exception as e:
                print(f"Seeding failed: {e}")
                raise

        background_tasks.add_task(run_seeding)

        return {"message": "Seeding started successfully", "status": "started"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error starting seeding: {str(e)}")


@router.post("/reset")
async def reset_seeding() -> Dict[str, str]:
    """
    Reset seeding status and clear metadata.

    This endpoint allows administrators to reset the seeding state,
    useful for troubleshooting or forcing a re-seed.
    """
    try:
        seeding_service = get_seeding_service()
        await seeding_service.reset_seeding()

        return {"message": "Seeding status reset successfully", "status": "reset"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error resetting seeding: {str(e)}"
        )


@router.get("/needs-seeding")
async def check_needs_seeding() -> Dict[str, Any]:
    """
    Check if seeding is needed without starting it.

    Returns:
        Information about whether seeding is needed and why
    """
    try:
        seeding_service = get_seeding_service()
        needs_seeding = await seeding_service.needs_seeding()

        # Get additional context
        from services.embeddings.qdrant_embeddings_manager import get_embeddings_manager

        embeddings_manager = get_embeddings_manager()
        content_count = (
            embeddings_manager.count() if embeddings_manager.is_started else 0
        )

        return {
            "needs_seeding": needs_seeding,
            "content_count": content_count,
            "reason": (
                "No content found in Qdrant collection"
                if content_count == 0
                else "Content exists"
            ),
        }

    except Exception as e:
        return {
            "needs_seeding": True,
            "content_count": 0,
            "reason": f"Error checking content: {str(e)}",
        }


@router.post("/resume")
async def resume_seeding(background_tasks: BackgroundTasks) -> Dict[str, str]:
    """
    Resume interrupted seeding from last checkpoint.

    This endpoint allows administrators to resume seeding that was
    previously interrupted due to system restart or failure.
    """
    try:
        seeding_service = get_seeding_service()
        progress = await seeding_service.get_progress()

        # Check if there's an interrupted/failed seeding to resume
        if progress.status not in [SeedingStatus.INTERRUPTED, SeedingStatus.FAILED]:
            return {
                "message": f"No interrupted/failed seeding found to resume (current status: {progress.status.value})",
                "status": "not_needed",
            }

        # Check if already running
        if progress.is_running():
            raise HTTPException(status_code=409, detail="Seeding is already running")

        # Resume seeding in background
        background_tasks.add_task(seeding_service.resume_seeding)

        return {"message": "Seeding resumed successfully", "status": "resumed"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resuming seeding: {str(e)}")


@router.post("/stop")
async def stop_seeding() -> Dict[str, str]:
    """
    Gracefully stop the currently running seeding process.

    This endpoint allows administrators to interrupt a running seeding process
    gracefully, allowing it to be resumed later from the last checkpoint.
    """
    try:
        seeding_service = get_seeding_service()
        progress = await seeding_service.get_progress()

        # Check if seeding is currently running
        if not progress.is_running():
            return {
                "message": f"Seeding is not currently running (status: {progress.status.value})",
                "status": "not_running",
            }

        # Request graceful stop
        await seeding_service.request_stop()

        return {
            "message": "Seeding stop requested - process will finish current item and stop gracefully",
            "status": "stop_requested",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error stopping seeding: {str(e)}")


@router.get("/files")
async def get_seeding_files() -> Dict[str, Any]:
    """
    Get detailed information about individual files being processed.

    Returns:
        Dictionary containing file-level processing status and details
    """
    try:
        seeding_service = get_seeding_service()

        # Load file statuses from metadata
        file_statuses = await seeding_service.metadata.load_file_statuses()

        if not file_statuses:
            return {
                "files": [],
                "total_files": 0,
                "summary": "No file processing information available",
            }

        # Convert to API response format
        files_info = []
        for file_status in file_statuses:
            file_info = {
                "file_path": file_status.file_path,
                "file_name": os.path.basename(file_status.file_path),
                "status": file_status.status.value,
                "content_type": file_status.content_type,
                "file_size_bytes": file_status.file_size_bytes,
                "items_processed": file_status.items_processed,
                "processed_at": (
                    file_status.processed_at.isoformat()
                    if file_status.processed_at
                    else None
                ),
                "processing_duration_seconds": file_status.processing_duration_seconds,
                "error_message": file_status.error_message,
                "retry_count": file_status.retry_count,
            }
            files_info.append(file_info)

        # Generate summary statistics
        total_files = len(files_info)
        completed_files = len(
            [f for f in file_statuses if f.status.value == "completed"]
        )
        failed_files = len([f for f in file_statuses if f.status.value == "failed"])
        pending_files = len([f for f in file_statuses if f.status.value == "pending"])

        return {
            "files": files_info,
            "total_files": total_files,
            "summary": {
                "completed": completed_files,
                "failed": failed_files,
                "pending": pending_files,
                "success_rate": (
                    round((completed_files / total_files) * 100, 1)
                    if total_files > 0
                    else 0
                ),
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting file information: {str(e)}"
        )
