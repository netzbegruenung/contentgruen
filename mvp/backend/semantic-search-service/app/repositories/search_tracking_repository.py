"""
Repository for search event tracking.
Handles database operations for search analytics.

Suchereignisse bleiben search_event_retention_days Tage als Einzelzeilen. Aeltere
Tage werden zu Tageszaehlern der Suchen verdichtet (suchen_je_tag: Tag, Zahl der
Suchen, Zahl der Personen), ohne Tagespseudonym (#289). Die Zaehlungen je Zeitraum
unten addieren diese Tageszaehler und stimmen so auch ueber die Frist hinaus.
"""

import logging
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import func, distinct, and_, select, text
from sqlalchemy.orm import InstrumentedAttribute, Session
from sqlalchemy.sql.selectable import ScalarSelect

from infrastructure.database.connection import get_app_database
from infrastructure.database.models import SearchEvent, SuchenJeTagZeile

logger = logging.getLogger(__name__)


# Verdichtet in einer Anweisung: Was DELETE entfernt, landet im selben Schritt im
# Tageszaehler. grenze ist Mitternacht UTC und Suchereignisse tragen nur den Tag,
# also wird ein Tag immer ganz verdichtet. Einen Konflikt gibt es nur, wenn ein
# schon verdichteter Tag spaeter noch Suchereignisse bekommt; neue tragen aber
# immer den laufenden Tag. Fuer diesen Fall addiert ON CONFLICT, statt Zeilen zu
# verlieren; personen kann dann eine Person doppelt zaehlen.
_VERDICHTEN = text(
    """
    WITH weg AS (
        DELETE FROM search_events
        WHERE timestamp < :grenze
        RETURNING timestamp, actor_hash
    ), tage AS (
        INSERT INTO suchen_je_tag (tag, suchen, personen)
        SELECT (timestamp AT TIME ZONE 'UTC')::date, count(*),
               count(DISTINCT actor_hash)
        FROM weg
        GROUP BY 1
        ON CONFLICT (tag) DO UPDATE
        SET suchen = suchen_je_tag.suchen + EXCLUDED.suchen,
            personen = suchen_je_tag.personen + EXCLUDED.personen
    )
    SELECT count(*) FROM weg
    """
)


def _in_utc(zeitpunkt: datetime) -> datetime:
    """Naive Zeitpunkte gelten als UTC (wie bei den Aufrufern), andere werden umgerechnet."""
    if zeitpunkt.tzinfo is None:
        return zeitpunkt
    return zeitpunkt.astimezone(timezone.utc).replace(tzinfo=None)


def _tage_im_zeitraum(start_date: datetime, end_date: datetime) -> tuple[date, date]:
    """Erster und letzter UTC-Tag, dessen Mitternacht im Zeitraum liegt.

    So zaehlt ein Tageszaehler genau dann mit, wenn seine Suchereignisse (die nur
    Mitternacht UTC tragen) mitgezaehlt worden waeren.
    """
    start_date, end_date = _in_utc(start_date), _in_utc(end_date)
    erster = start_date.date()
    if start_date.time() != time.min:
        erster += timedelta(days=1)
    return erster, end_date.date()


class SearchTrackingRepository:
    """Repository for managing search event data."""

    def __init__(self):
        self.db = get_app_database()

    def track_search(
        self,
        results_count: int,
        day: date,
        actor_hash: Optional[str] = None,
    ) -> bool:
        """
        Track a search event.

        Args:
            results_count: Number of results returned
            day: UTC day of the search. Stored as midnight UTC, never with the
                time of day (see SearchTrackingService).
            actor_hash: Daily pseudonym of the searching actor, already derived by
                SearchTrackingService. Never a raw user or session id.

        Returns:
            bool: True if tracking was successful
        """
        try:
            with self.db.get_session() as session:
                search_event = SearchEvent(
                    results_count=results_count,
                    actor_hash=actor_hash,
                    timestamp=datetime.combine(day, time.min, tzinfo=timezone.utc),
                )
                session.add(search_event)
                session.commit()
                # No log line: its exact time would undo the coarsening above.
                return True
        except Exception as e:
            logger.error(f"Error tracking search event: {e}", exc_info=True)
            return False

    def get_unique_active_users(
        self, start_date: datetime, end_date: Optional[datetime] = None
    ) -> int:
        """
        Get count of unique active actors (authenticated users and anonymous
        sessions alike, which the pseudonym no longer tells apart).

        Exact for a single day. For a longer window it counts active actor-days,
        because the pseudonym rotates at midnight UTC by design.

        Args:
            start_date: Start of period
            end_date: End of period (defaults to now)

        Returns:
            int: Count of distinct actors
        """
        if end_date is None:
            end_date = datetime.utcnow()

        try:
            einzelzeilen = (
                select(func.count(distinct(SearchEvent.actor_hash)))
                .where(
                    and_(
                        SearchEvent.timestamp >= start_date,
                        SearchEvent.timestamp <= end_date,
                        SearchEvent.actor_hash.isnot(None),
                    )
                )
                .scalar_subquery()
            )
            with self.db.get_session() as session:
                # Additiv, weil das Tagespseudonym an jedem Tag ein anderes ist.
                total = self._mit_tageszaehlern(
                    session,
                    einzelzeilen,
                    SuchenJeTagZeile.personen,
                    start_date,
                    end_date,
                )

                logger.debug(f"Active actors {start_date} to {end_date}: {total}")
                return total
        except Exception as e:
            logger.error(f"Error getting unique active users: {e}", exc_info=True)
            return 0

    def get_searches_per_user(self, days: int = 7) -> Dict[str, Any]:
        """
        Get search statistics per active actor.

        Counted per actor-day rather than per person: the pseudonym rotates daily,
        so an actor searching on three days of the window contributes three entries.

        Args:
            days: Number of days to analyze

        Returns:
            Dict with average, median, and distribution stats
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            with self.db.get_session() as session:
                actor_searches = (
                    session.query(
                        SearchEvent.actor_hash,
                        func.count().label("search_count"),
                    )
                    .filter(
                        and_(
                            SearchEvent.timestamp >= start_date,
                            SearchEvent.actor_hash.isnot(None),
                        )
                    )
                    .group_by(SearchEvent.actor_hash)
                    .all()
                )

                all_counts = [count for _, count in actor_searches]

                if not all_counts:
                    return {
                        "average": 0.0,
                        "median": 0,
                        "total_users": 0,
                        "total_searches": 0,
                    }

                all_counts.sort()
                total_users = len(all_counts)
                total_searches = sum(all_counts)
                average = total_searches / total_users if total_users > 0 else 0
                median = all_counts[len(all_counts) // 2] if all_counts else 0

                return {
                    "average": round(average, 2),
                    "median": median,
                    "total_users": total_users,
                    "total_searches": total_searches,
                }
        except Exception as e:
            logger.error(f"Error getting searches per user: {e}", exc_info=True)
            return {"average": 0.0, "median": 0, "total_users": 0, "total_searches": 0}

    def get_search_count_by_period(
        self, start_date: datetime, end_date: Optional[datetime] = None
    ) -> int:
        """
        Get total search count for a period.

        Args:
            start_date: Start of period
            end_date: End of period (defaults to now)

        Returns:
            int: Total search count
        """
        if end_date is None:
            end_date = datetime.utcnow()

        try:
            einzelzeilen = (
                select(func.count())
                .where(
                    and_(
                        SearchEvent.timestamp >= start_date,
                        SearchEvent.timestamp <= end_date,
                    )
                )
                .scalar_subquery()
            )
            with self.db.get_session() as session:
                return self._mit_tageszaehlern(
                    session,
                    einzelzeilen,
                    SuchenJeTagZeile.suchen,
                    start_date,
                    end_date,
                )
        except Exception as e:
            logger.error(f"Error getting search count: {e}", exc_info=True)
            return 0

    @staticmethod
    def _mit_tageszaehlern(
        session: Session,
        einzelzeilen: ScalarSelect,
        spalte: InstrumentedAttribute,
        start_date: datetime,
        end_date: datetime,
    ) -> int:
        """Zaehlung ueber Einzelzeilen plus Summe einer Spalte der Tageszaehler.

        Eine Anweisung, also ein Snapshot: Ein Verdichten zwischen zwei Abfragen
        zaehlte einen Tag sonst doppelt.
        """
        erster, letzter = _tage_im_zeitraum(start_date, end_date)
        tageszaehler = (
            select(func.coalesce(func.sum(spalte), 0))
            .where(
                and_(
                    SuchenJeTagZeile.tag >= erster,
                    SuchenJeTagZeile.tag <= letzter,
                )
            )
            .scalar_subquery()
        )
        return session.execute(select(einzelzeilen + tageszaehler)).scalar() or 0

    def verdichte_alte_suchereignisse(
        self, days_to_keep: int, heute: Optional[date] = None
    ) -> int:
        """
        Suchereignisse vor der Frist zu Tageszaehlern verdichten.

        Wirft bei Datenbankfehlern, anders als die Lesemethoden hier: Der
        Bereinigungsjob soll einen gescheiterten Lauf als Fehler loggen, nicht als
        "nichts zu tun".

        Tage, die mehr als days_to_keep Tage vor heute (UTC) liegen, werden je Tag
        zu Zahl der Suchen und Zahl der Personen (verschiedene Tagespseudonyme)
        zusammengefasst; die Einzelzeilen samt Pseudonym werden geloescht.

        Args:
            days_to_keep: Tage, die als Einzelzeilen bleiben (vor heute)
            heute: Bezugstag, Standard heute in UTC

        Returns:
            int: Zahl der geloeschten Suchereignisse
        """
        heute = heute or datetime.now(timezone.utc).date()
        grenze = datetime.combine(
            heute - timedelta(days=days_to_keep), time.min, tzinfo=timezone.utc
        )
        with self.db.get_session() as session:
            geloescht = session.execute(_VERDICHTEN, {"grenze": grenze}).scalar() or 0
            session.commit()
        logger.info(f"Compacted {geloescht} old search events into day counters")
        return geloescht


# Global repository instance
_search_tracking_repository: Optional[SearchTrackingRepository] = None


def get_search_tracking_repository() -> SearchTrackingRepository:
    """Get or create the global search tracking repository instance."""
    global _search_tracking_repository
    if _search_tracking_repository is None:
        _search_tracking_repository = SearchTrackingRepository()
    return _search_tracking_repository
