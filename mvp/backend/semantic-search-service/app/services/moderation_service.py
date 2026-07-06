"""
Service layer for content moderation functionality.
Provides business logic for reporting and managing flagged content.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
import json

from repositories.content_report_repository import get_content_report_repository
from services.embeddings.qdrant_embeddings_manager import get_embeddings_manager
from domain.models.content_type import ContentType

logger = logging.getLogger(__name__)


class ModerationService:
    """Service for managing content reports and moderation actions."""

    def __init__(self):
        self.report_repo = get_content_report_repository()
        self.embeddings_manager = get_embeddings_manager()

    async def report_content(
        self,
        content_id: str,
        content_type: str,
        reason: str,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> bool:
        """
        Report a content item.

        Args:
            content_id: UUID of the content
            content_type: Type of content
            reason: Report reason
            user_id: Optional user ID of reporter
            session_id: Optional session ID of reporter
            description: Optional detailed description

        Returns:
            bool: True if report was created successfully
        """
        # Validate inputs
        if not content_id or not content_type or not reason:
            logger.warning("Invalid report submission: missing required fields")
            return False

        if not user_id and not session_id:
            logger.warning("Invalid report submission: no reporter identifier")
            return False

        # Valid reasons
        valid_reasons = ["spam", "inappropriate", "duplicate", "other"]
        if reason not in valid_reasons:
            logger.warning(f"Invalid report reason: {reason}")
            return False

        try:
            content_uuid = UUID(content_id)
            report = self.report_repo.create_report(
                content_id=content_uuid,
                content_type=content_type,
                reason=reason,
                reported_by_user_id=user_id,
                reported_by_session_id=session_id,
                description=description,
            )
            logger.info(f"Content {content_id} reported: {reason}")
            return report is not None
        except ValueError as e:
            logger.error(f"Invalid content_id format: {content_id}")
            return False
        except Exception as e:
            logger.error(f"Error reporting content: {e}", exc_info=True)
            return False

    async def get_pending_reports(
        self, limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get pending content reports (backwards compatibility).

        Args:
            limit: Maximum number of reports to return
            offset: Number of reports to skip

        Returns:
            List of report dictionaries with embedded content
        """
        return await self.get_reports(status="pending", limit=limit, offset=offset)

    async def get_reports(
        self, status: str = "pending", limit: int = 50, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get content reports filtered by status with actual content data.

        Args:
            status: Filter by status (pending, reviewed, dismissed, or all)
            limit: Maximum number of reports to return
            offset: Number of reports to skip

        Returns:
            List of report dictionaries with embedded content
        """
        try:
            # Repository now returns dictionaries directly
            reports = self.report_repo.get_reports(
                status=status, limit=limit, offset=offset
            )

            # Fetch actual content for each report from Qdrant (if content still exists)
            for report in reports:
                content_id = report.get("content_id")
                if content_id:
                    try:
                        content = await self.embeddings_manager.get_by_id(content_id)
                        report["content"] = content
                    except Exception as e:
                        # Content might be deleted for reviewed reports
                        logger.debug(f"Could not fetch content {content_id}: {e}")
                        report["content"] = None

            return reports
        except Exception as e:
            logger.error(f"Error getting reports (status={status}): {e}", exc_info=True)
            return []

    async def delete_content(
        self, content_id: str, content_type: str, deleted_by: str
    ) -> bool:
        """
        Delete content from the system with cascading delete for reply suggestions.

        Args:
            content_id: UUID of the content to delete
            content_type: Type of content
            deleted_by: User ID of the person deleting

        Returns:
            bool: True if deletion was successful
        """
        try:
            content_uuid = UUID(content_id)

            # Delete from Qdrant vector database
            deleted = await self.embeddings_manager.delete_by_id(content_id)

            if deleted:
                # Mark all related reports as reviewed
                updated_count = self.report_repo.update_reports_by_content_id(
                    content_id=content_uuid,
                    status="reviewed",
                    reviewed_by=deleted_by,
                    resolution_notes="Content deleted",
                )

                logger.info(
                    f"Content {content_id} ({content_type}) deleted by {deleted_by}, {updated_count} reports marked as reviewed"
                )

                # If deleting a commentary, remove orphaned reply suggestions from statements
                if content_type == ContentType.COMMENTARY.value:
                    await self._remove_orphaned_reply_suggestions(content_id)

                return True
            else:
                logger.warning(f"Content {content_id} not found or already deleted")
                return False

        except ValueError as e:
            logger.error(f"Invalid content_id format: {content_id}")
            return False
        except Exception as e:
            logger.error(f"Error deleting content: {e}", exc_info=True)
            return False

    async def _remove_orphaned_reply_suggestions(self, deleted_content_id: str) -> None:
        """
        Remove orphaned reply suggestions from statements after content deletion.

        Args:
            deleted_content_id: UUID of the deleted content
        """
        try:
            from qdrant_client.models import (
                Filter,
                FieldCondition,
                MatchValue,
                ScrollRequest,
            )

            logger.info(
                f"Removing orphaned reply suggestions for deleted content {deleted_content_id}"
            )

            # Scroll through all statements to find those with the deleted content in their reply suggestions
            offset = None
            statements_updated = 0

            while True:
                # Fetch batch of statements
                scroll_result = await self.embeddings_manager._async_client.scroll(
                    collection_name=self.embeddings_manager.collection_name,
                    scroll_filter=Filter(
                        must=[
                            FieldCondition(
                                key="content_type",
                                match=MatchValue(value=ContentType.STATEMENT.value),
                            )
                        ]
                    ),
                    limit=100,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )

                points, next_offset = scroll_result

                if not points:
                    break

                # Check each statement for orphaned reply suggestions
                for point in points:
                    payload = point.payload
                    replysuggestions = payload.get("replysuggestions", [])

                    # Parse replysuggestions if it's a JSON string
                    if isinstance(replysuggestions, str):
                        try:
                            replysuggestions = json.loads(replysuggestions)
                        except json.JSONDecodeError:
                            logger.warning(
                                f"Failed to parse replysuggestions for statement {point.id}"
                            )
                            continue

                    # Check if this statement references the deleted content
                    original_count = len(replysuggestions)
                    filtered_suggestions = [
                        rs
                        for rs in replysuggestions
                        if str(rs.get("id")) != deleted_content_id
                    ]

                    # If we removed any suggestions, update the statement
                    if len(filtered_suggestions) < original_count:
                        payload["replysuggestions"] = json.dumps(
                            filtered_suggestions, default=str
                        )
                        payload["replysuggestions_count"] = len(filtered_suggestions)

                        # Update the point in Qdrant
                        from qdrant_client.models import PointStruct

                        await self.embeddings_manager._async_client.upsert(
                            collection_name=self.embeddings_manager.collection_name,
                            points=[
                                PointStruct(
                                    id=point.id,
                                    vector=point.vector or [],
                                    payload=payload,
                                )
                            ],
                        )

                        statements_updated += 1
                        logger.debug(
                            f"Removed orphaned reply suggestion from statement {point.id} "
                            f"({original_count} -> {len(filtered_suggestions)} suggestions)"
                        )

                # Check if we've scrolled through all points
                if next_offset is None:
                    break

                offset = next_offset

            if statements_updated > 0:
                logger.info(
                    f"Cascading delete complete: Updated {statements_updated} statements "
                    f"to remove orphaned reply suggestions for content {deleted_content_id}"
                )
            else:
                logger.info(
                    f"No statements found with reply suggestions referencing deleted content {deleted_content_id}"
                )

        except Exception as e:
            logger.error(
                f"Error removing orphaned reply suggestions for {deleted_content_id}: {e}",
                exc_info=True,
            )
            # Don't raise - the main content is already deleted, this is cleanup

    async def dismiss_report(
        self, report_id: str, dismissed_by: str, notes: Optional[str] = None
    ) -> bool:
        """
        Dismiss a content report without taking action.

        Args:
            report_id: UUID of the report
            dismissed_by: User ID of the person dismissing
            notes: Optional notes about why report was dismissed

        Returns:
            bool: True if dismissal was successful
        """
        try:
            report_uuid = UUID(report_id)
            updated_report = self.report_repo.update_report_status(
                report_id=report_uuid,
                status="dismissed",
                reviewed_by=dismissed_by,
                resolution_notes=notes or "Report dismissed",
            )
            if updated_report:
                logger.info(f"Report {report_id} dismissed by {dismissed_by}")
                return True
            else:
                logger.warning(f"Report {report_id} not found")
                return False
        except ValueError as e:
            logger.error(f"Invalid report_id format: {report_id}")
            return False
        except Exception as e:
            logger.error(f"Error dismissing report: {e}", exc_info=True)
            return False

    def get_report_stats(self) -> Dict[str, Any]:
        """
        Get statistics about content reports.

        Returns:
            Dict with report counts by status
        """
        try:
            counts = self.report_repo.get_report_count_by_status()
            return {
                "total": sum(counts.values()),
                "by_status": counts,
                "pending": counts.get("pending", 0),
                "reviewed": counts.get("reviewed", 0),
                "dismissed": counts.get("dismissed", 0),
            }
        except Exception as e:
            logger.error(f"Error getting report stats: {e}", exc_info=True)
            return {
                "total": 0,
                "by_status": {},
                "pending": 0,
                "reviewed": 0,
                "dismissed": 0,
            }


# Global service instance
_moderation_service: Optional[ModerationService] = None


def get_moderation_service() -> ModerationService:
    """Get or create the global moderation service instance."""
    global _moderation_service
    if _moderation_service is None:
        _moderation_service = ModerationService()
    return _moderation_service
