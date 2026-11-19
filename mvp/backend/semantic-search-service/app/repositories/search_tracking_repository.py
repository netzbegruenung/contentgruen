"""
Repository for search event tracking.
Handles database operations for search analytics.

Suchereignisse bleiben nur fuer den laufenden UTC-Tag als Einzelzeilen. Ist ein
Tag abgeschlossen, werden sie zu seinem Tageszaehler der Suchen verdichtet
(suchen_je_tag: Tag, Zahl der Suchen, der Suchen ohne Treffer und der Personen),
ohne Tagespseudonym (#289; seit #495 am Tagesende statt nach 90 Tagen, ausgeloest
von services/loeschfristen_service.py). Die Zaehlungen je Zeitraum unten addieren
diese Tageszaehler zu den Einzelzeilen des laufenden Tages.

Jede Suche schreibt ihr Suchereignis in einer eigenen Transaktion; xmin und die
physische Lage der Zeilen (ctid, pg_dump) ergeben deshalb die Reihenfolge der
Suchen des laufenden Tages. Bis #495 schrieb der Bereinigungsjob jeden
abgeschlossenen Tag gemischt neu (#337); seit abgeschlossene Tage gar keine
Einzelzeilen mehr haben, gibt es nichts mehr zu mischen.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Dict, Any, List
from sqlalchemy import func, distinct, and_, select, text
from sqlalchemy.orm import InstrumentedAttribute, Session
from sqlalchemy.sql.selectable import ScalarSelect

from infrastructure.database.connection import get_app_database
from infrastructure.database.models import SearchEvent, SuchenJeTagZeile
from utils.utc_tag import utc_zeitraum

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Tageswert:
    """Suchen eines UTC-Tages: aus Suchereignissen und dem Tageszaehler.

    ohne_treffer ist None, wenn der Tageszaehler es nicht kennt (vor #467).
    """

    tag: date
    suchen: int
    personen: int
    ohne_treffer: Optional[int]


# Verdichtet in einer Anweisung: Was DELETE entfernt, landet im selben Schritt im
# Tageszaehler. grenze ist Mitternacht UTC und Suchereignisse tragen nur den Tag,
# also wird ein Tag immer ganz verdichtet. personen zaehlt die verschiedenen
# Tagespseudonyme des Tages; das ist die einzige Stelle, an der sie noch zaehlbar
# sind. Einen Konflikt gibt es nur, wenn ein schon verdichteter Tag spaeter noch
# Suchereignisse bekommt (eine Suche kurz vor Mitternacht, deren Zeile erst nach
# dem Lauf eingeht). Fuer diesen Fall addiert ON CONFLICT, statt Zeilen zu
# verlieren; personen kann dann eine Person doppelt zaehlen. Ein ohne_treffer, das
# ein vor #467 verdichteter Tag nicht kennt (NULL), bleibt dabei unbekannt.
_VERDICHTEN = text(
    """
    WITH weg AS (
        DELETE FROM search_events
        WHERE timestamp < :grenze
        RETURNING timestamp, actor_hash, results_count
    ), tage AS (
        INSERT INTO suchen_je_tag (tag, suchen, personen, ohne_treffer)
        SELECT (timestamp AT TIME ZONE 'UTC')::date, count(*),
               count(DISTINCT actor_hash),
               count(*) FILTER (WHERE results_count = 0)
        FROM weg
        GROUP BY 1
        ON CONFLICT (tag) DO UPDATE
        SET suchen = suchen_je_tag.suchen + EXCLUDED.suchen,
            personen = suchen_je_tag.personen + EXCLUDED.personen,
            ohne_treffer = suchen_je_tag.ohne_treffer + EXCLUDED.ohne_treffer
    )
    SELECT count(*) FROM weg
    """
)


# Tageswerte fuer die Bilanz (#467): Einzelzeilen je Tag und Tageszaehler in einer
# Anweisung, also einem Snapshot, wie in _mit_tageszaehlern. Ein Tag kann in beiden
# stehen (siehe _VERDICHTEN), deshalb wird je Tag summiert. ohne_treffer bleibt
# unbekannt, sobald ein Teil es nicht kennt.
_TAGESWERTE = text(
    """
    SELECT tag, sum(suchen), sum(personen),
           CASE WHEN bool_or(ohne_treffer IS NULL) THEN NULL
                ELSE sum(ohne_treffer) END
    FROM (
        SELECT (timestamp AT TIME ZONE 'UTC')::date AS tag, count(*) AS suchen,
               count(DISTINCT actor_hash) AS personen,
               count(*) FILTER (WHERE results_count = 0) AS ohne_treffer
        FROM search_events
        WHERE timestamp >= :von AND timestamp < :bis
        GROUP BY 1
        UNION ALL
        SELECT tag, suchen, personen, ohne_treffer
        FROM suchen_je_tag
        WHERE tag >= :erster AND tag <= :letzter
    ) AS beide
    GROUP BY tag
    ORDER BY tag
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
            logger.error(
                f"Error tracking search event: {type(e).__name__}", exc_info=True
            )
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
            logger.error(
                f"Error getting unique active users: {type(e).__name__}", exc_info=True
            )
            return 0

    def get_searches_per_user(self, days: int = 7) -> Dict[str, Any]:
        """
        Suchen je aktiver Person und Tag.

        Gezaehlt je Personentag, nicht je Person: Das Pseudonym wechselt taeglich,
        wer an drei Tagen des Zeitraums sucht, zaehlt dreimal. Abgeschlossene Tage
        kommen aus den Tageszaehlern (Suchen und Personen), der laufende aus den
        Einzelzeilen; einen Median gibt es seit #495 nicht mehr, denn dafuer
        braeuchte es die Suchen je Pseudonym ueber das Tagesende hinaus.

        Args:
            days: Number of days to analyze

        Returns:
            Dict with average, total_users (Personentage) and total_searches
        """
        leer = {"average": 0.0, "total_users": 0, "total_searches": 0}
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            end_date = datetime.utcnow()
            zeitraum = and_(
                SearchEvent.timestamp >= start_date,
                SearchEvent.timestamp <= end_date,
            )
            personen = (
                select(func.count(distinct(SearchEvent.actor_hash)))
                .where(zeitraum)
                .scalar_subquery()
            )
            # Alle Suchen wie im Tageszaehler, auch Altbestand ohne Pseudonym.
            suchen = select(func.count()).where(zeitraum).scalar_subquery()
            erster, letzter = _tage_im_zeitraum(start_date, end_date)
            im_zeitraum = and_(
                SuchenJeTagZeile.tag >= erster, SuchenJeTagZeile.tag <= letzter
            )
            tage_personen = (
                select(func.coalesce(func.sum(SuchenJeTagZeile.personen), 0))
                .where(im_zeitraum)
                .scalar_subquery()
            )
            tage_suchen = (
                select(func.coalesce(func.sum(SuchenJeTagZeile.suchen), 0))
                .where(im_zeitraum)
                .scalar_subquery()
            )
            with self.db.get_session() as session:
                # Eine Anweisung, also ein Snapshot (siehe _mit_tageszaehlern).
                zeile = session.execute(
                    select(personen + tage_personen, suchen + tage_suchen)
                ).one()
            total_users, total_searches = int(zeile[0] or 0), int(zeile[1] or 0)
            if total_users == 0:
                return leer
            return {
                "average": round(total_searches / total_users, 2),
                "total_users": total_users,
                "total_searches": total_searches,
            }
        except Exception as e:
            logger.error(
                f"Error getting searches per user: {type(e).__name__}", exc_info=True
            )
            return leer

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
            logger.error(
                f"Error getting search count: {type(e).__name__}", exc_info=True
            )
            return 0

    def get_tageswerte(self, erster: date, letzter: date) -> List[Tageswert]:
        """
        Suchen, Personen und Suchen ohne Treffer je UTC-Tag, beide Grenzen
        eingeschlossen; Tage ohne Suche fehlen.

        Wirft bei Datenbankfehlern: Leere Tage sind in der Bilanz ein Wert (0),
        ein Fehler darf nicht so aussehen.
        """
        von, bis = utc_zeitraum(erster, letzter)
        with self.db.get_session() as session:
            zeilen = session.execute(
                _TAGESWERTE,
                {
                    "von": von,
                    "bis": bis,
                    "erster": erster,
                    "letzter": letzter,
                },
            ).all()
        return [
            Tageswert(
                tag=tag,
                suchen=int(suchen),
                personen=int(personen),
                ohne_treffer=None if ohne_treffer is None else int(ohne_treffer),
            )
            for tag, suchen, personen, ohne_treffer in zeilen
        ]

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

    def verdichten_vor(self, grenze: datetime) -> int:
        """
        Suchereignisse vor grenze zu Tageszaehlern verdichten.

        Der Aufrufer (services/loeschfristen_service.py) gibt Mitternacht UTC des
        laufenden Tages, so werden alle abgeschlossenen Tage verdichtet: je Tag
        Zahl der Suchen, der Suchen ohne Treffer und der Personen (verschiedene
        Tagespseudonyme); die Einzelzeilen samt Pseudonym werden geloescht. Ein
        erster Lauf verdichtet auch alle aelteren Tage, die bis #495 noch 90 Tage
        als Einzelzeilen blieben.

        Wirft bei Datenbankfehlern, anders als die Lesemethoden hier: Der Lauf soll
        einen Fehler als Fehler loggen, nicht als "nichts zu tun".

        Args:
            grenze: Zeitpunkt; Suchereignisse davor werden verdichtet

        Returns:
            int: Zahl der geloeschten Suchereignisse
        """
        with self.db.get_session() as session:
            geloescht = session.execute(_VERDICHTEN, {"grenze": grenze}).scalar() or 0
            session.commit()
        logger.info(
            f"Compacted {geloescht} search events of closed days into day counters"
        )
        return geloescht


# Global repository instance
_search_tracking_repository: Optional[SearchTrackingRepository] = None


def get_search_tracking_repository() -> SearchTrackingRepository:
    """Get or create the global search tracking repository instance."""
    global _search_tracking_repository
    if _search_tracking_repository is None:
        _search_tracking_repository = SearchTrackingRepository()
    return _search_tracking_repository
