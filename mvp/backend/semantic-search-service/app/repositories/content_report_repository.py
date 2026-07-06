"""
Repository for managing content reports.
Handles database operations for content moderation.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import desc

from infrastructure.database.connection import get_app_database
from infrastructure.database.models import ContentReport

logger = logging.getLogger(__name__)


class ContentReportRepository:
    """Repository for managing content report data."""

    def __init__(self):
        self.db = get_app_database()

    def create_report(
        self,
        content_id: UUID,
        content_type: str,
        reason: str,
        reported_by_user_id: Optional[str] = None,
        reported_by_session_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ContentReport:
        """
        Create a new content report.

        Args:
            content_id: UUID of the reported content
            content_type: Type of content (commentary, generictext, etc.)
            reason: Report reason (spam, inappropriate, duplicate, other)
            reported_by_user_id: Optional user ID of reporter
            reported_by_session_id: Optional session ID of reporter
            description: Optional detailed description

        Returns:
            ContentReport: Created report object
        """
        try:
            with self.db.get_session() as session:
                report = ContentReport(
                    content_id=content_id,
                    content_type=content_type,
                    reason=reason,
                    reported_by_user_id=reported_by_user_id,
                    reported_by_session_id=reported_by_session_id,
                    description=description,
                    status="pending",
                )
                session.add(report)
                session.commit()
                session.refresh(report)
                logger.info(
                    f"Created report {report.id} for content {content_id} by {reported_by_user_id or reported_by_session_id}"
                )
                return report
        except Exception as e:
            logger.error(f"Error creating content report: {e}", exc_info=True)
            raise

    def get_pending_reports(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get pending content reports (backwards compatibility).

        Args:
            limit: Maximum number of reports to return
            offset: Number of reports to skip

        Returns:
            List[Dict[str, Any]]: List of pending reports as dictionaries
        """
        return self.get_reports(status="pending", limit=limit, offset=offset)

    def get_reports(
        self, status: str = "pending", limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get content reports filtered by status.

        Args:
            status: Filter by status (pending, reviewed, dismissed, or all)
            limit: Maximum number of reports to return
            offset: Number of reports to skip

        Returns:
            List[Dict[str, Any]]: List of reports as dictionaries
        """
        try:
            with self.db.get_session() as session:
                query = session.query(ContentReport)

                # Filter by status unless "all" is requested
                if status != "all":
                    query = query.filter(ContentReport.status == status)

                reports = (
                    query.order_by(desc(ContentReport.created))
                    .limit(limit)
                    .offset(offset)
                    .all()
                )

                # Convert to dictionaries while still in session
                return [
                    {
                        "id": str(report.id),
                        "content_id": str(report.content_id),
                        "content_type": report.content_type,
                        "reason": report.reason,
                        "description": report.description,
                        "reported_by_user_id": report.reported_by_user_id,
                        "reported_by_session_id": report.reported_by_session_id,
                        "created": (
                            report.created.isoformat() if report.created else None
                        ),
                        "status": report.status,
                        "reviewed_by": report.reviewed_by,
                        "reviewed_at": (
                            report.reviewed_at.isoformat()
                            if report.reviewed_at
                            else None
                        ),
                        "resolution_notes": report.resolution_notes,
                    }
                    for report in reports
                ]
        except Exception as e:
            logger.error(f"Error getting reports (status={status}): {e}", exc_info=True)
            return []

    def get_reports_by_content_id(self, content_id: UUID) -> List[ContentReport]:
        """
        Get all reports for a specific content item.

        Args:
            content_id: UUID of the content

        Returns:
            List[ContentReport]: List of reports for this content
        """
        try:
            with self.db.get_session() as session:
                reports = (
                    session.query(ContentReport)
                    .filter(ContentReport.content_id == content_id)
                    .order_by(desc(ContentReport.created))
                    .all()
                )
                return reports
        except Exception as e:
            logger.error(
                f"Error getting reports for content {content_id}: {e}", exc_info=True
            )
            return []

    def update_report_status(
        self,
        report_id: UUID,
        status: str,
        reviewed_by: Optional[str] = None,
        resolution_notes: Optional[str] = None,
    ) -> Optional[ContentReport]:
        """
        Update the status of a content report.

        Args:
            report_id: UUID of the report
            status: New status (reviewed, dismissed)
            reviewed_by: User ID of reviewer
            resolution_notes: Optional notes about resolution

        Returns:
            ContentReport: Updated report or None if not found
        """
        try:
            with self.db.get_session() as session:
                report = (
                    session.query(ContentReport)
                    .filter(ContentReport.id == report_id)
                    .first()
                )
                if report:
                    report.status = status
                    report.reviewed_by = reviewed_by
                    report.reviewed_at = datetime.utcnow()
                    report.resolution_notes = resolution_notes
                    session.commit()
                    session.refresh(report)
                    logger.info(f"Updated report {report_id} status to {status}")
                    return report
                else:
                    logger.warning(f"Report {report_id} not found")
                    return None
        except Exception as e:
            logger.error(f"Error updating report status: {e}", exc_info=True)
            return None

    def update_reports_by_content_id(
        self,
        content_id: UUID,
        status: str,
        reviewed_by: Optional[str] = None,
        resolution_notes: Optional[str] = None,
    ) -> int:
        """
        Update all reports for a specific content item.

        Args:
            content_id: UUID of the content
            status: New status (reviewed, dismissed)
            reviewed_by: User ID of reviewer
            resolution_notes: Optional notes about resolution

        Returns:
            int: Number of reports updated
        """
        try:
            with self.db.get_session() as session:
                reports = (
                    session.query(ContentReport)
                    .filter(ContentReport.content_id == content_id)
                    .all()
                )

                count = 0
                for report in reports:
                    report.status = status
                    report.reviewed_by = reviewed_by
                    report.reviewed_at = datetime.utcnow()
                    report.resolution_notes = resolution_notes
                    count += 1

                session.commit()
                logger.info(
                    f"Updated {count} reports for content {content_id} to status {status}"
                )
                return count
        except Exception as e:
            logger.error(
                f"Error updating reports for content {content_id}: {e}", exc_info=True
            )
            return 0

    def get_report_count_by_status(self) -> Dict[str, int]:
        """
        Get count of reports by status.

        Returns:
            Dict[str, int]: Count of reports for each status
        """
        try:
            with self.db.get_session() as session:
                from sqlalchemy import func

                results = (
                    session.query(ContentReport.status, func.count(ContentReport.id))
                    .group_by(ContentReport.status)
                    .all()
                )
                return {status: count for status, count in results}
        except Exception as e:
            logger.error(f"Error getting report counts: {e}", exc_info=True)
            return {}


# Global repository instance
_content_report_repository: Optional[ContentReportRepository] = None


def get_content_report_repository() -> ContentReportRepository:
    """Get or create the global content report repository instance."""
    global _content_report_repository
    if _content_report_repository is None:
        _content_report_repository = ContentReportRepository()
    return _content_report_repository
