"""
Service layer for content moderation functionality.
Provides business logic for reporting and managing flagged content.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from repositories.content_report_repository import (
    ContentReportRepository,
    get_content_report_repository,
)
from repositories.implementations.qdrant.moderation_repository import (
    FELD_STATUS_VOR_SPERRE,
    get_moderation_repository,
)
from repositories.interfaces.moderation_repository import IModerationRepository
from domain.models.content_type import ContentType
from domain.models.content_status import ContentStatus

logger = logging.getLogger(__name__)

# Obergrenze fuer die Liste gesperrter Beitraege in der Moderation.
GESPERRTE_HOECHSTENS = 500


class ModerationService:
    """Service for managing content reports and moderation actions."""

    def __init__(
        self,
        report_repo: Optional[ContentReportRepository] = None,
        moderation_repo: Optional[IModerationRepository] = None,
    ):
        self.report_repo = report_repo or get_content_report_repository()
        self.moderation_repo = moderation_repo or get_moderation_repository()

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

            # Doppelmeldung desselben Nutzers zum selben Inhalt: nichts anlegen,
            # aber als Erfolg melden. Der Melder hat getan, was er tun sollte;
            # ein Fehler waere irrefuehrend, und eine zweite Zeile im
            # Moderationsposteingang hilft niemandem.
            if user_id and self.report_repo.has_report_from_user(
                content_id=content_uuid, user_id=user_id
            ):
                logger.info(f"Duplicate report for content {content_id} ignored")
                return True

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

    async def content_exists(self, content_id: str) -> bool:
        """
        Existiert der gemeldete Inhalt ueberhaupt?

        Bisher wurde nur das UUID-Format geprueft, weshalb eine nie existierende
        Kennung eine Meldung erzeugte. Das laesst den Moderationsposteingang mit
        Zeilen fluten, die auf nichts zeigen, und macht ihn als Arbeitsvorrat
        unbrauchbar.

        Args:
            content_id: UUID des Inhalts als String

        Returns:
            bool: True, wenn der Inhalt in Qdrant liegt
        """
        try:
            return await self._beitrag_laden(content_id) is not None
        except Exception as e:
            logger.error(f"Error checking content existence: {e}", exc_info=True)
            # Im Zweifel durchlassen: eine Meldung zu verlieren waere schlimmer
            # als eine ins Leere zeigende anzunehmen.
            return True

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
                        content = await self.moderation_repo.laden(content_id)
                        report["content"] = content
                    except Exception as e:
                        # Content might be deleted for reviewed reports
                        logger.debug(f"Could not fetch content {content_id}: {e}")
                        report["content"] = None

            return reports
        except Exception as e:
            logger.error(f"Error getting reports (status={status}): {e}", exc_info=True)
            return []

    async def _beitrag_laden(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Payload eines Beitrags, auch gesperrt; None, wenn es ihn nicht gibt."""
        try:
            UUID(content_id)
        except ValueError:
            logger.warning(f"Invalid content_id format: {content_id}")
            return None

        return await self.moderation_repo.laden(content_id)

    async def sperren(self, content_id: str, gesperrt_von: str) -> bool:
        """
        Einen gemeldeten Beitrag sperren, statt ihn zu loeschen.

        Der Beitrag bleibt im Speicher und bekommt den Status BLOCKED; die
        Repositories blenden ihn damit aus Suche, Einzelansicht, Listen, Zaehlern
        und "Meine Beitraege" aus. Die Moderation findet ihn weiter, weil ihr
        Repository nicht nach Sperre filtert. Alle Meldungen zum Beitrag stehen
        danach auf bearbeitet.

        Erst Qdrant, dann PostgreSQL, ohne gemeinsame Transaktion. Scheitert das
        Meldungs-Update, ist der Beitrag schon gesperrt und der Fehler geht an den
        Aufrufer; erneutes Sperren holt die Meldungen nach, weil der Status von
        vor der ersten Sperre erhalten bleibt.

        Returns:
            bool: False, wenn es den Beitrag nicht gibt
        """
        beitrag = await self._beitrag_laden(content_id)
        if beitrag is None:
            logger.warning(f"Content {content_id} not found")
            return False

        if beitrag.get("status") != ContentStatus.BLOCKED.value:
            await self.moderation_repo.sperren(
                content_id, status_vorher=beitrag.get("status")
            )

        updated_count = self.report_repo.update_reports_by_content_id(
            content_id=UUID(content_id),
            status="reviewed",
            reviewed_by=gesperrt_von,
            resolution_notes="Beitrag gesperrt",
        )
        logger.info(
            f"Content {content_id} gesperrt, "
            f"{updated_count} reports marked as reviewed"
        )
        return True

    async def entsperren(self, content_id: str, entsperrt_von: str) -> bool:
        """
        Eine Sperre aufheben: Der Beitrag bekommt den Status von vor der Sperre
        zurueck und ist wieder so sichtbar wie vorher. Die Meldungen bleiben
        bearbeitet.

        Returns:
            bool: False, wenn es den Beitrag nicht gibt
        """
        beitrag = await self._beitrag_laden(content_id)
        if beitrag is None:
            logger.warning(f"Content {content_id} not found")
            return False

        if beitrag.get("status") != ContentStatus.BLOCKED.value:
            return True

        await self.moderation_repo.entsperren(
            content_id, status_vorher=beitrag.get(FELD_STATUS_VOR_SPERRE)
        )
        logger.info(f"Content {content_id} entsperrt")
        return True

    async def gesperrte_beitraege(
        self, limit: int = GESPERRTE_HOECHSTENS
    ) -> List[Dict[str, Any]]:
        """
        Alle gesperrten Beitraege, auch ohne Meldung.

        Ueber die Meldungen allein waeren sie nicht sicher auffindbar: Ein
        Loeschantrag entfernt die Meldungen der Person (docs/LOESCHKONZEPT.md),
        der gesperrte Beitrag bliebe dann fuer niemanden erreichbar.
        """
        return await self.moderation_repo.gesperrte(limit)

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
            deleted = await self.moderation_repo.entfernen(content_id)

            if deleted:
                # Mark all related reports as reviewed. Der Beitrag ist schon weg;
                # ein Fehler hier macht die Loeschung nicht rueckgaengig.
                try:
                    updated_count = self.report_repo.update_reports_by_content_id(
                        content_id=content_uuid,
                        status="reviewed",
                        reviewed_by=deleted_by,
                        resolution_notes="Content deleted",
                    )
                except Exception:
                    updated_count = 0

                logger.info(
                    f"Content {content_id} ({content_type}) deleted, {updated_count} reports marked as reviewed"
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
            logger.info(
                f"Removing orphaned reply suggestions for deleted content {deleted_content_id}"
            )
            statements_updated = await self.moderation_repo.aus_aussagen_entfernen(
                deleted_content_id
            )

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
                logger.info(f"Report {report_id} dismissed")
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
