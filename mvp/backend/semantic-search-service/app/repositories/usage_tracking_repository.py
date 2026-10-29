"""
Repository for managing usage tracking data.
Handles all database operations for usage statistics.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import uuid
import asyncio

from sqlalchemy import func, desc
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from infrastructure.database.connection import AppDatabase, get_app_database
from infrastructure.database.models import (
    NutzungJeFassung,
    UsageTracking,
    UsageEvent,
)

logger = logging.getLogger(__name__)

# Der Zeitraum fuer den Zuwachs in "Meine Beitraege" (#349); das Frontend nennt
# ihn im Text an der Karte mit.
ZUWACHS_TAGE = 7


class UsageTrackingRepository:
    """Repository for usage tracking operations."""

    def __init__(self, db: Optional[AppDatabase] = None):
        """``db``: eine AppDatabase; ohne Angabe die globale."""
        self.db = db if db is not None else get_app_database()

    def track_usage(
        self,
        content_id: uuid.UUID,
        event_type: str = "copy",
        session_id: Optional[str] = None,
        device_category: Optional[str] = None,
        fassung: Optional[str] = None,
    ) -> bool:
        """
        Track a usage event for a content item.

        Args:
            content_id: UUID of the content item
            event_type: Type of usage event (default: "copy")
            session_id: Optional session identifier
            device_category: Grobe Geraetekategorie, bereits vom Aufrufer
                abgeleitet (utils.device_category). Der User-Agent-Rohwert
                kommt hier nicht mehr an.
            fassung: Die kopierte Fassung eines Kommentars (#355), vom Aufrufer
                geprueft; None bei anderen Beitragstypen.

        Returns:
            bool: True if tracking was successful
        """
        logger.info(
            f"Repository: Tracking usage for content {content_id}, event: {event_type}"
        )
        try:
            with self.db.get_session() as session:
                # Get or create usage tracking record
                tracking = (
                    session.query(UsageTracking)
                    .filter_by(content_id=content_id)
                    .first()
                )

                if not tracking:
                    tracking = UsageTracking(content_id=content_id, usage_count=0)
                    session.add(tracking)

                # Increment usage count
                tracking.increment_usage()

                # Create usage event record
                event = UsageEvent(
                    content_id=content_id,
                    event_type=event_type,
                    session_id=session_id,
                    device_category=device_category,
                    fassung=fassung,
                )
                session.add(event)

                if fassung:
                    # Erst nach usage_tracking (Fremdschluessel); hochzaehlen in der
                    # Datenbank, damit zwei gleichzeitige Kopien beide zaehlen.
                    session.flush()
                    session.execute(
                        insert(NutzungJeFassung)
                        .values(content_id=content_id, fassung=fassung, nutzung=1)
                        .on_conflict_do_update(
                            index_elements=["content_id", "fassung"],
                            set_={"nutzung": NutzungJeFassung.nutzung + 1},
                        )
                    )

                neu = tracking.usage_count
            # Festgeschrieben beim Verlassen von get_session; erst danach gilt es.
            logger.info(
                f"Repository: Successfully tracked usage for content {content_id}, new count: {neu}"
            )
            return True

        except Exception as e:
            logger.error(
                f"Error tracking usage for content {content_id}: {e}", exc_info=True
            )
            return False

    def get_usage_count(self, content_id: uuid.UUID) -> int:
        """
        Get the usage count for a specific content item.

        Args:
            content_id: UUID of the content item

        Returns:
            int: Usage count (0 if not found)
        """
        with self.db.get_session() as session:
            tracking = (
                session.query(UsageTracking).filter_by(content_id=content_id).first()
            )
            return tracking.usage_count if tracking else 0

    def get_usage_counts_batch(self, content_ids: List[uuid.UUID]) -> Dict[str, int]:
        """
        Get usage counts for multiple content items.

        Args:
            content_ids: List of content UUIDs

        Returns:
            Dict mapping content_id (as string) to usage count
        """
        with self.db.get_session() as session:
            trackings = (
                session.query(UsageTracking)
                .filter(UsageTracking.content_id.in_(content_ids))
                .all()
            )

            result = {str(content_id): 0 for content_id in content_ids}
            for tracking in trackings:
                result[str(tracking.content_id)] = tracking.usage_count

            return result

    def get_nutzung_letzte_7_tage_batch(
        self, content_ids: List[uuid.UUID]
    ) -> Dict[str, int]:
        """
        Der Zuwachs je Beitrag: Nutzungen der letzten ZUWACHS_TAGE Tage (#349).

        Gezaehlt aus usage_events, nicht aus usage_tracking: nur dort steht, wann
        genutzt wurde. Deren Frist (90 Tage, cleanup_old_events) liegt weit ueber
        einer Woche. Die eigene Kopie kommt gar nicht erst hinein (api/v1/usage.py).

        Returns:
            Dict content_id (als String) -> Zahl, 0 ohne Nutzung im Zeitraum
        """
        result = {str(content_id): 0 for content_id in content_ids}
        if not content_ids:
            return result
        seit = datetime.now(timezone.utc) - timedelta(days=ZUWACHS_TAGE)
        with self.db.get_session() as session:
            zeilen = (
                session.query(UsageEvent.content_id, func.count(UsageEvent.id))
                .filter(
                    UsageEvent.content_id.in_(content_ids),
                    UsageEvent.timestamp >= seit,
                )
                .group_by(UsageEvent.content_id)
                .all()
            )
            for content_id, anzahl in zeilen:
                result[str(content_id)] = anzahl
        return result

    def get_nutzung_je_fassung_batch(
        self, content_ids: List[uuid.UUID]
    ) -> Dict[str, Dict[str, Dict[str, int]]]:
        """
        Nutzung und Zuwachs der letzten ZUWACHS_TAGE Tage je Fassung (#355), fuer
        "Meine Beitraege".

        Die Summe kommt aus nutzung_je_fassung und ueberdauert die Frist der
        usage_events, der Zuwachs aus usage_events wie beim Zuwachs je Beitrag.
        Nutzung ohne Fassung (andere Beitragstypen, Nutzung von vor #355) fehlt.

        Returns:
            Dict content_id (als String) -> {Fassung: {"nutzung", "letzte_7_tage"}},
            ein leeres Dict fuer Beitraege ohne Nutzung je Fassung
        """
        result: Dict[str, Dict[str, Dict[str, int]]] = {
            str(content_id): {} for content_id in content_ids
        }
        if not content_ids:
            return result
        seit = datetime.now(timezone.utc) - timedelta(days=ZUWACHS_TAGE)
        with self.db.get_session() as session:
            summen = (
                session.query(
                    NutzungJeFassung.content_id,
                    NutzungJeFassung.fassung,
                    NutzungJeFassung.nutzung,
                )
                .filter(NutzungJeFassung.content_id.in_(content_ids))
                .all()
            )
            for content_id, fassung, nutzung in summen:
                result[str(content_id)][fassung] = {
                    "nutzung": nutzung,
                    "letzte_7_tage": 0,
                }
            zuwachs = (
                session.query(
                    UsageEvent.content_id, UsageEvent.fassung, func.count(UsageEvent.id)
                )
                .filter(
                    UsageEvent.content_id.in_(content_ids),
                    UsageEvent.fassung.isnot(None),
                    UsageEvent.timestamp >= seit,
                )
                .group_by(UsageEvent.content_id, UsageEvent.fassung)
                .all()
            )
            for content_id, fassung, anzahl in zuwachs:
                eintrag = result[str(content_id)].get(fassung)
                if eintrag is not None:
                    eintrag["letzte_7_tage"] = anzahl
        return result

    async def get_user_statistics(
        self, user_id: str, content_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get usage statistics for a specific user's contributed content.

        Uses Qdrant as the source of truth for content ownership (original_author field),
        then gets usage counts from the usage_tracking table. This ensures statistics
        remain accurate even after old usage_events are cleaned up.

        Args:
            user_id: User identifier
            content_types: nur diese Typen zaehlen; ohne Angabe alles, was der Person
                zugeordnet ist (auch Aussagen und Herkunftsangaben)

        Returns:
            Dict containing user statistics
        """
        from repositories.aggregated.content_repository import ContentRepository
        from core.config import settings

        # Query Qdrant for all content created by this user
        content_repo = ContentRepository(settings)

        # Get all content by this author (using scroll/pagination)
        user_content = await content_repo.get_by_author(
            user_id, limit=10000, offset=0, content_types=content_types
        )

        if not user_content:
            return {
                "user_id": user_id,
                "unique_contents_contributed": 0,
                "total_usage_count": 0,
                "top_content": [],
            }

        # Extract content IDs
        content_ids = [content.id for content in user_content]

        # Get usage counts from usage_tracking table
        with self.db.get_session() as session:
            trackings = (
                session.query(UsageTracking)
                .filter(UsageTracking.content_id.in_(content_ids))
                .all()
            )

            # Build lookup map
            usage_map = {
                tracking.content_id: tracking.usage_count for tracking in trackings
            }

            # Calculate total usage
            total_usage = sum(usage_map.values())

            # Get top 5 content items by usage
            content_with_usage = [
                {
                    "content_id": str(content_id),
                    "usage_count": usage_map.get(content_id, 0),
                }
                for content_id in content_ids
            ]
            top_content = sorted(
                content_with_usage, key=lambda x: x["usage_count"], reverse=True
            )[:5]

            return {
                "user_id": user_id,
                "unique_contents_contributed": len(content_ids),
                "total_usage_count": total_usage,
                "top_content": top_content,
            }

    def get_trending_content(
        self, limit: int = 10, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get trending content based on recent usage.

        Das Fenster ist in Stunden angegeben, weil der Service es so fuehrt und
        "trending" auf 24 Stunden gemeint ist. Vorher nahm diese Methode days
        entgegen, waehrend der Service hours uebergab -- der Aufruf warf einen
        TypeError, den der Service-Handler abfing, sodass /api/v1/usage/trending
        durchgehend 500 lieferte.

        Args:
            limit: Maximum number of items to return
            hours: Size of the time window in hours

        Returns:
            List of trending content with usage stats
        """
        from datetime import timedelta

        with self.db.get_session() as session:
            since_date = datetime.utcnow() - timedelta(hours=hours)

            trending = (
                session.query(
                    UsageEvent.content_id,
                    func.count(UsageEvent.id).label("recent_uses"),
                    UsageTracking.usage_count.label("total_uses"),
                )
                .select_from(UsageEvent)
                .join(UsageTracking, UsageEvent.content_id == UsageTracking.content_id)
                .filter(
                    UsageEvent.timestamp >= since_date, UsageEvent.event_type == "copy"
                )
                .group_by(UsageEvent.content_id, UsageTracking.usage_count)
                .order_by(desc("recent_uses"))
                .limit(limit)
                .all()
            )

            return [
                {
                    "content_id": str(content_id),
                    "recent_uses": recent,
                    "total_uses": total,
                }
                for content_id, recent, total in trending
            ]

    def cleanup_old_events(self, days_to_keep: int = 90) -> int:
        """
        Clean up old usage events from the database.

        Only deletes from usage_events table - usage_tracking aggregate counters
        are preserved forever. This maintains accurate total usage counts while
        removing detailed event history for privacy compliance.

        Args:
            days_to_keep: Number of days of event data to retain (default: 90)

        Returns:
            int: Number of event records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        logger.info(
            f"Cleaning up usage events older than {days_to_keep} days (before {cutoff_date})"
        )

        try:
            with self.db.get_session() as session:
                # Delete old events
                deleted_count = (
                    session.query(UsageEvent)
                    .filter(UsageEvent.timestamp < cutoff_date)
                    .delete(synchronize_session=False)
                )

                session.commit()

                logger.info(f"Deleted {deleted_count} old usage event records")
                return deleted_count

        except Exception as e:
            logger.error(f"Error during cleanup of old events: {e}", exc_info=True)
            raise


# Global repository instance
_usage_repository: Optional[UsageTrackingRepository] = None


def get_usage_repository() -> UsageTrackingRepository:
    """Get or create the global usage repository instance."""
    global _usage_repository
    if _usage_repository is None:
        _usage_repository = UsageTrackingRepository()
    return _usage_repository
