"""
Der taegliche Bereinigungsjob (Loeschkonzept): loescht Nutzungsereignisse nach
ihrer Frist.

Derselbe Job verdichtet Suchereignisse nach ihrer eigenen Frist zu
Tageszaehlern der Suchen ohne Tagespseudonym (#289, siehe SearchTrackingRepository)
und schreibt die Suchereignisse abgeschlossener Tage gemischt neu (#337).
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import schedule
import threading
import time

from repositories.search_tracking_repository import get_search_tracking_repository
from services.usage_tracking_service import get_usage_service
from core.config import settings

logger = logging.getLogger(__name__)


class Bereinigungsjob:
    """
    Der taegliche Bereinigungsjob: Fristen der Nutzungs- und der Suchereignisse und
    das Mischen abgeschlossener Tage. Ein Schalter fuer alles:
    ``enable_bereinigungsjob`` (core/config.py).
    """

    def __init__(self, retention_days: int = 90, search_event_retention_days: int = 90):
        """
        Initialize cleanup service.

        Args:
            retention_days: Number of days of usage data to retain (default 90)
            search_event_retention_days: Number of days of search events to keep as
                single rows before they become day counters (default 90)
        """
        self.retention_days = retention_days
        self.search_event_retention_days = search_event_retention_days
        self.usage_service = get_usage_service()
        self.search_repository = get_search_tracking_repository()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.last_cleanup: Optional[datetime] = None
        self.last_cleanup_count = 0

    def cleanup_old_data(self) -> int:
        """
        Perform cleanup of old usage events, compact old search events and
        rewrite the search events of closed days in random order.

        Returns:
            Number of usage event records deleted
        """
        self._verdichte_suchereignisse()
        self._mische_suchereignisse()

        logger.info(
            f"Starting usage data cleanup (retention: {self.retention_days} days)"
        )

        try:
            # Call the cleanup method in usage service
            deleted_count = self.usage_service.cleanup_old_events(self.retention_days)

            # Update stats
            self.last_cleanup = datetime.utcnow()
            self.last_cleanup_count = deleted_count

            if deleted_count > 0:
                logger.info(
                    f"Successfully deleted {deleted_count} old usage event records"
                )
            else:
                logger.info("No old usage events to delete")

            return deleted_count

        except Exception as e:
            logger.error(
                f"Error during usage data cleanup: {type(e).__name__}", exc_info=True
            )
            return 0

    def _verdichte_suchereignisse(self) -> None:
        """Suchereignisse vor der Frist zu Tageszaehlern verdichten.

        Ein Fehler hier haelt die Bereinigung der Nutzungsereignisse nicht auf.
        """
        try:
            self.search_repository.verdichte_alte_suchereignisse(
                self.search_event_retention_days
            )
        except Exception as e:
            logger.error(
                f"Error compacting old search events: {type(e).__name__}", exc_info=True
            )

    def _mische_suchereignisse(self) -> None:
        """Suchereignisse abgeschlossener Tage gemischt neu schreiben.

        Nach dem Verdichten, damit verdichtete Tage nicht erst gemischt werden.
        Ein Fehler hier haelt die Bereinigung der Nutzungsereignisse nicht auf.
        """
        try:
            self.search_repository.mische_abgeschlossene_tage()
        except Exception as e:
            logger.error(
                f"Error rewriting search events of closed days: {type(e).__name__}",
                exc_info=True,
            )

    def _run_scheduled_jobs(self):
        """
        Run scheduled cleanup jobs in a loop.
        """
        while self._running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

    def start_scheduled_cleanup(self, hour: int = 2, minute: int = 0):
        """
        Start scheduled daily cleanup at specified time.

        Args:
            hour: Hour to run cleanup (0-23, default 2 AM)
            minute: Minute to run cleanup (0-59, default 0)
        """
        if self._running:
            logger.warning("Cleanup service is already running")
            return

        # Schedule daily cleanup
        schedule_time = f"{hour:02d}:{minute:02d}"
        schedule.every().day.at(schedule_time).do(self.cleanup_old_data)

        logger.info(f"Scheduled daily usage cleanup at {schedule_time}")

        # Also run an immediate cleanup on startup
        logger.info("Running initial cleanup on service start")
        self.cleanup_old_data()

        # Start the scheduler thread
        self._running = True
        self._thread = threading.Thread(target=self._run_scheduled_jobs, daemon=True)
        self._thread.start()

        logger.info("Usage cleanup service started")

    def stop_scheduled_cleanup(self):
        """
        Stop the scheduled cleanup service.
        """
        if not self._running:
            return

        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

        schedule.clear()
        logger.info("Usage cleanup service stopped")

    def get_status(self) -> dict:
        """
        Get the current status of the cleanup service.

        Returns:
            Dictionary with service status information
        """
        return {
            "running": self._running,
            "retention_days": self.retention_days,
            "search_event_retention_days": self.search_event_retention_days,
            "last_cleanup": (
                self.last_cleanup.isoformat() if self.last_cleanup else None
            ),
            "last_cleanup_count": self.last_cleanup_count,
            "next_cleanup": self._get_next_cleanup_time(),
        }

    def _get_next_cleanup_time(self) -> Optional[str]:
        """
        Get the next scheduled cleanup time.

        Returns:
            ISO format string of next cleanup time or None
        """
        jobs = schedule.get_jobs()
        if not jobs:
            return None

        # Get the next run time from the first job
        next_run = jobs[0].next_run
        return next_run.isoformat() if next_run else None


# Global cleanup service instance
_bereinigungsjob: Optional[Bereinigungsjob] = None


def get_bereinigungsjob(retention_days: Optional[int] = None) -> Bereinigungsjob:
    """
    Get or create the global cleanup service instance.

    Args:
        retention_days: Days of data to retain (uses settings if not specified)

    Returns:
        Bereinigungsjob instance
    """
    global _bereinigungsjob

    if _bereinigungsjob is None:
        days = retention_days or settings.usage_retention_days
        _bereinigungsjob = Bereinigungsjob(
            retention_days=days,
            search_event_retention_days=settings.search_event_retention_days,
        )

    return _bereinigungsjob


def bereinigungsjob_starten():
    """
    Start the cleanup scheduler with default settings.
    Should be called during application startup.
    """
    # Check if cleanup is enabled
    if not settings.enable_bereinigungsjob:
        logger.info("Bereinigungsjob is disabled in settings")
        return

    # Get configuration from settings
    cleanup_hour = settings.cleanup_hour
    cleanup_minute = settings.cleanup_minute

    # Start the service
    service = get_bereinigungsjob()
    service.start_scheduled_cleanup(hour=cleanup_hour, minute=cleanup_minute)
