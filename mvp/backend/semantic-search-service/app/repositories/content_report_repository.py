"""
Repository for managing content reports.
Handles database operations for content moderation.
"""

import logging
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from sqlalchemy import and_, desc, func, or_

from domain.models.meldung import (
    AngabenGeloescht,
    MelderAdresse,
    MelderAngaben,
    MelderSuche,
)
from infrastructure.database.connection import get_app_database
from infrastructure.database.models import ContentReport
from utils.besucher_pseudonym import besucher_tagespseudonym

logger = logging.getLogger(__name__)

# Melder-Kennung anonymer Meldungen (#446). Solange eine Meldung offen ist, steht
# dort das Tagespseudonym des Besuchers; Admins erkennen daran Meldungen aus
# derselben Quelle am selben Tag. Erledigte Meldungen brauchen das nicht mehr.
# Sie bekommen einen Zufallswert, der nur den CHECK der Tabelle erfuellt.
PRAEFIX_PSEUDONYM = "besucher:"
PRAEFIX_OHNE_PSEUDONYM = "anon:"


def melder_pseudonym(besucher_merkmal: str, tag: date) -> str:
    """Die Melder-Kennung einer offenen anonymen Meldung."""
    return PRAEFIX_PSEUDONYM + besucher_tagespseudonym(besucher_merkmal, tag)


def _offene_adressen_merken(reports) -> List[MelderAdresse]:
    """
    Die E-Mail-Adressen der Meldungen, die noch offen sind, bevor sie erledigt werden
    (#493): Nur wer noch keine Entscheidung hat, bekommt eine Mail. Die Zeilen sind
    dabei gesperrt (FOR UPDATE); zwei gleichzeitige Entscheidungen lesen eine offene
    Meldung so nicht beide, und eine Meldung, die dazwischen eingeht, bleibt offen.
    """
    return [
        MelderAdresse(report.content_id, report.melder_email)
        for report in reports
        if report.status == "pending" and report.melder_email
    ]


def _melder_pseudonym_loeschen(report: ContentReport) -> None:
    """
    Beim Abschliessen: Pseudonym und Sitzungskennungen aus der Zeit vor #446 weg.
    Angemeldete Melder behalten nur ihre Kennung, anonyme einen Zufallswert.
    """
    if report.status == "pending":
        return
    if report.reported_by_user_id:
        report.reported_by_session_id = None
    else:
        _anonymes_pseudonym_ersetzen(report)


def _anonymes_pseudonym_ersetzen(report: ContentReport) -> None:
    """Tagespseudonym (oder alte Sitzungskennung) durch einen Zufallswert."""
    if not (report.reported_by_session_id or "").startswith(PRAEFIX_OHNE_PSEUDONYM):
        report.reported_by_session_id = f"{PRAEFIX_OHNE_PSEUDONYM}{uuid4()}"


def _als_dict(report: ContentReport) -> Dict[str, Any]:
    """Eine Meldung, wie die Admin-Ansichten sie bekommen."""
    return {
        "id": str(report.id),
        "content_id": str(report.content_id),
        "content_type": report.content_type,
        "reason": report.reason,
        "description": report.description,
        "reported_by_user_id": report.reported_by_user_id,
        "reported_by_session_id": report.reported_by_session_id,
        "created": report.created.isoformat() if report.created else None,
        "status": report.status,
        "reviewed_by": report.reviewed_by,
        "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None,
        "resolution_notes": report.resolution_notes,
        "melder_name": report.melder_name,
        "melder_email": report.melder_email,
        "guter_glaube": report.guter_glaube,
    }


def _von_melder(suche: MelderSuche):
    """Filter auf die Meldungen mit genau diesen Angaben (MelderSuche).

    Beide Seiten klein in PostgreSQL, nicht die Eingabe in Python: Die beiden
    verkleinern manche Zeichen verschieden (etwa ein Sigma am Wortende).
    """
    bedingungen = []
    if suche.email is not None:
        bedingungen.append(
            func.lower(ContentReport.melder_email) == func.lower(suche.email)
        )
    if suche.name is not None:
        bedingungen.append(
            func.lower(ContentReport.melder_name) == func.lower(suche.name)
        )
    return and_(*bedingungen)


class ContentReportRepository:
    """Repository for managing content report data."""

    def __init__(self):
        self.db = get_app_database()

    def create_report(
        self,
        content_id: UUID,
        content_type: str,
        reason: str,
        *,
        melder: MelderAngaben,
        reported_by_user_id: Optional[str] = None,
        reported_by_session_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> ContentReport:
        """
        Create a new content report.

        Args:
            content_id: UUID of the reported content
            content_type: Type of content (commentary, generictext, etc.)
            reason: Report reason, one of MELDEGRUENDE (domain/models/meldegrund.py)
            reported_by_user_id: Optional user ID of reporter
            reported_by_session_id: Optional session ID of reporter
            description: Optional detailed description
            melder: Name, E-Mail-Adresse und Erklaerung guten Glaubens (#438)

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
                    melder_name=melder.name,
                    melder_email=melder.email,
                    guter_glaube=melder.guter_glaube,
                    status="pending",
                )
                session.add(report)
                session.commit()
                session.refresh(report)
                # Wer gemeldet hat, steht in der Zeile selbst; im Log ist es Dublette.
                logger.info(f"Created report {report.id} for content {content_id}")
                return report
        except Exception as e:
            logger.error(
                f"Error creating content report: {type(e).__name__}", exc_info=True
            )
            raise

    def has_report_from_user(self, content_id: UUID, user_id: str) -> bool:
        """
        Hat dieser angemeldete Nutzer diesen Inhalt bereits gemeldet?

        Nur fuer angemeldete Melder: bei anonymen Meldungen gibt es keine
        belastbare Kennung, auf die sich eine Deduplizierung stuetzen koennte --
        die dortige Begrenzung leistet das Rate-Limit auf der Adresse.

        Args:
            content_id: UUID des gemeldeten Inhalts
            user_id: Kennung des Melders

        Returns:
            bool: True, wenn bereits eine Meldung dieses Nutzers zu diesem Inhalt
            vorliegt
        """
        try:
            with self.db.get_session() as session:
                existing = (
                    session.query(ContentReport)
                    .filter(
                        ContentReport.content_id == content_id,
                        ContentReport.reported_by_user_id == user_id,
                    )
                    .first()
                )
                return existing is not None
        except Exception as e:
            logger.error(
                f"Error checking existing report: {type(e).__name__}", exc_info=True
            )
            # Im Zweifel nicht deduplizieren: eine doppelte Meldung ist harmloser
            # als eine verschluckte.
            return False

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
                return [_als_dict(report) for report in reports]
        except Exception as e:
            logger.error(
                f"Error getting reports (status={status}): {type(e).__name__}",
                exc_info=True,
            )
            return []

    def von_melder(self, suche: MelderSuche) -> List[Dict[str, Any]]:
        """
        Alle Meldungen mit diesen Angaben der meldenden Person, neueste zuerst,
        in jedem Status (#494). Fuer die Auskunft an Personen ohne Konto: Nur
        ueber Name und E-Mail-Adresse sind ihre Meldungen zu finden. Fehler gehen
        an den Aufrufer; eine leere Liste hiesse sonst "nichts gespeichert".
        """
        with self.db.get_session() as session:
            meldungen = (
                session.query(ContentReport)
                .filter(_von_melder(suche))
                .order_by(desc(ContentReport.created))
                .all()
            )
            return [_als_dict(m) for m in meldungen]

    def angaben_loeschen(
        self, suche: MelderSuche, meldung_ids: List[UUID]
    ) -> AngabenGeloescht:
        """
        Die Angaben einer Person loeschen, die es verlangt (Art. 17 DSGVO, #494).

        Nur die Meldungen, die der Admin in der Suche gesehen hat (``meldung_ids``)
        und die noch zu den Angaben passen: Eine Meldung, die seitdem eingegangen
        ist, hat niemand geprueft.

        Bearbeitete und abgewiesene Meldungen gehen ganz, wie sonst nach ihrer
        Frist. Offene haben keine Frist, weil sie noch Arbeit sind (Art. 16 DSA):
        Sie bleiben mit Grund und Beschreibung stehen und verlieren Name,
        E-Mail-Adresse und das Tagespseudonym (wie beim Abschluss ein Zufallswert,
        #446). Alles in einer Transaktion (get_session schreibt am Ende); Fehler
        gehen an den Aufrufer.
        """
        if not meldung_ids:
            return AngabenGeloescht(geloescht=0, angaben_entfernt=0)
        gesehen = and_(_von_melder(suche), ContentReport.id.in_(meldung_ids))
        with self.db.get_session() as session:
            # Gesperrt gelesen und je Zeile entschieden: Schliesst ein anderer
            # Admin eine Meldung gerade ab, wartet das hier und sieht ihren neuen
            # Status, statt sie zwischen zwei Anweisungen zu uebergehen.
            meldungen = (
                session.query(ContentReport).filter(gesehen).with_for_update().all()
            )
            geloescht = 0
            offene = []
            for meldung in meldungen:
                if meldung.status == "pending":
                    meldung.melder_name = None
                    meldung.melder_email = None
                    if not meldung.reported_by_user_id:
                        _anonymes_pseudonym_ersetzen(meldung)
                    offene.append(meldung)
                else:
                    session.delete(meldung)
                    geloescht += 1
            # Wessen Angaben, steht nicht im Log: nur die Zahlen.
            logger.info(
                f"Melder-Angaben geloescht: {geloescht} Meldungen entfernt, "
                f"{len(offene)} offene ohne Angaben"
            )
            return AngabenGeloescht(geloescht=geloescht, angaben_entfernt=len(offene))

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
                f"Error getting reports for content {content_id}: {type(e).__name__}",
                exc_info=True,
            )
            return []

    def update_report_status(
        self,
        report_id: UUID,
        status: str,
        reviewed_by: Optional[str] = None,
        resolution_notes: Optional[str] = None,
        *,
        melder_adressen: Optional[List[MelderAdresse]] = None,
    ) -> Optional[ContentReport]:
        """
        Update the status of a content report.

        Args:
            report_id: UUID of the report
            status: New status (reviewed, dismissed)
            reviewed_by: User ID of reviewer
            resolution_notes: Optional notes about resolution
            melder_adressen: bekommt die E-Mail-Adresse, wenn die Meldung bis eben
                offen war (#493, _offene_adressen_merken)

        Returns:
            ContentReport: Updated report or None if not found
        """
        try:
            with self.db.get_session() as session:
                report = (
                    session.query(ContentReport)
                    .filter(ContentReport.id == report_id)
                    .with_for_update()
                    .first()
                )
                if report:
                    adressen = _offene_adressen_merken([report])
                    report.status = status
                    _melder_pseudonym_loeschen(report)
                    report.reviewed_by = reviewed_by
                    report.reviewed_at = datetime.now(timezone.utc)
                    report.resolution_notes = resolution_notes
                    session.commit()
                    session.refresh(report)
                    if melder_adressen is not None:
                        melder_adressen.extend(adressen)
                    logger.info(f"Updated report {report_id} status to {status}")
                    return report
                else:
                    logger.warning(f"Report {report_id} not found")
                    return None
        except Exception as e:
            logger.error(
                f"Error updating report status: {type(e).__name__}", exc_info=True
            )
            return None

    def update_reports_by_content_id(
        self,
        content_id: UUID,
        status: str,
        reviewed_by: Optional[str] = None,
        resolution_notes: Optional[str] = None,
        nur_offene: bool = False,
        *,
        melder_adressen: Optional[List[MelderAdresse]] = None,
    ) -> int:
        """
        Update all reports for a specific content item.

        Mit nur_offene bleiben bearbeitete und abgewiesene Meldungen, wie sie sind.
        melder_adressen bekommt die E-Mail-Adressen der Meldungen, die bis eben offen
        waren (#493, _offene_adressen_merken).

        Args:
            content_id: UUID of the content
            status: New status (reviewed, dismissed)
            reviewed_by: User ID of reviewer
            resolution_notes: Optional notes about resolution

        Returns:
            int: Number of reports updated

        Raises:
            Datenbankfehler werden weitergereicht: Sperren darf keinen Erfolg
            melden, wenn die Meldungen offen geblieben sind.
        """
        try:
            with self.db.get_session() as session:
                abfrage = session.query(ContentReport).filter(
                    ContentReport.content_id == content_id
                )
                if nur_offene:
                    abfrage = abfrage.filter(ContentReport.status == "pending")
                reports = abfrage.with_for_update().all()
                adressen = _offene_adressen_merken(reports)

                count = 0
                for report in reports:
                    report.status = status
                    _melder_pseudonym_loeschen(report)
                    report.reviewed_by = reviewed_by
                    report.reviewed_at = datetime.now(timezone.utc)
                    report.resolution_notes = resolution_notes
                    count += 1

                session.commit()
                if melder_adressen is not None:
                    melder_adressen.extend(adressen)
                logger.info(
                    f"Updated {count} reports for content {content_id} to status {status}"
                )
                return count
        except Exception as e:
            logger.error(
                f"Error updating reports for content {content_id}: {type(e).__name__}",
                exc_info=True,
            )
            raise

    def bearbeitete_loeschen_vor(self, grenze: datetime) -> int:
        """
        Bearbeitete und abgewiesene Meldungen loeschen, die vor ``grenze``
        bearbeitet wurden (services/loeschfristen_service.py). Offene bleiben.

        Ohne Zeitpunkt der Bearbeitung (Altbestand) zaehlt der Eingang. Fehler gehen
        an den Aufrufer.

        Returns:
            int: Zahl der geloeschten Meldungen
        """
        with self.db.get_session() as session:
            return (
                session.query(ContentReport)
                .filter(
                    ContentReport.status != "pending",
                    or_(
                        ContentReport.reviewed_at < grenze,
                        and_(
                            ContentReport.reviewed_at.is_(None),
                            ContentReport.created < grenze,
                        ),
                    ),
                )
                .delete(synchronize_session=False)
            )

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
            logger.error(
                f"Error getting report counts: {type(e).__name__}", exc_info=True
            )
            return {}


# Global repository instance
_content_report_repository: Optional[ContentReportRepository] = None


def get_content_report_repository() -> ContentReportRepository:
    """Get or create the global content report repository instance."""
    global _content_report_repository
    if _content_report_repository is None:
        _content_report_repository = ContentReportRepository()
    return _content_report_repository
