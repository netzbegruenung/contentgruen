"""
Service layer for content moderation functionality.
Provides business logic for reporting and managing flagged content.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from uuid import UUID

from repositories.content_report_repository import (
    ContentReportRepository,
    get_content_report_repository,
)
from repositories.implementations.qdrant.moderation_repository import (
    get_moderation_repository,
)
from repositories.interfaces.moderation_repository import IModerationRepository
from repositories.raw_input_repository import (
    RawInputRepository,
    get_raw_input_repository,
)
from repositories.sperre_repository import SperreRepository, get_sperre_repository
from repositories.vote_repository import VoteRepository
from domain.models.content_status import ContentStatus
from domain.models.meldegrund import MELDEGRUENDE, Meldegrund
from domain.models.sperrgrund import SPERRGRUENDE, Sperrgrund
from domain.models.widerspruch import Widerspruchsergebnis
from core.config import settings
from services.anzeigename_service import EHEMALIGE_PERSON_KENNUNG
from services.content.verweise_entfernen import verweise_entfernen

logger = logging.getLogger(__name__)


# Obergrenze fuer die Liste gesperrter Beitraege in der Moderation.
GESPERRTE_HOECHSTENS = 500


class SperreUngueltig(ValueError):
    """Sperren oder Bestaetigen ohne gueltigen Sperrgrund oder ohne Begruendung."""


class SchonGesperrt(Exception):
    """Der Beitrag hat schon eine aktive Sperre; ihr Grund bleibt, wie er ist."""


def _ohne_rand(text: Optional[str]) -> Optional[str]:
    """Text ohne Leerraum am Rand; leer wird None."""
    return (text or "").strip() or None


def _autor(beitrag: Dict[str, Any]) -> Optional[str]:
    """
    Wem die Sperrnachricht gilt: die Kennung, die den Beitrag eingestellt hat.
    Ehemalige Personen (docs/LOESCHKONZEPT.md, Schritt 3) und der Startbestand aus
    den Seed-Daten (initial_data_author, keine Kennung) erreicht keine Nachricht.
    """
    autor = _ohne_rand(beitrag.get("original_author"))
    if (
        autor is None
        or autor.startswith(EHEMALIGE_PERSON_KENNUNG)
        or autor == settings.initial_data_author
    ):
        return None
    return autor


def _iso(zeitpunkt) -> Optional[str]:
    return zeitpunkt.isoformat() if isinstance(zeitpunkt, datetime) else zeitpunkt


def _sperre_fuer_admins(sperre) -> Dict[str, Any]:
    """Was die Moderation zu einer Sperre sieht; die Kennungen bleiben in der Tabelle."""
    return {
        "id": str(sperre.id),
        "sperrgrund": sperre.sperrgrund,
        "begruendung": sperre.begruendung,
        "gesperrt_am": _iso(sperre.gesperrt_am),
        # Ohne Autor sieht niemand die Sperrnachricht (Glossar "Sperrnachricht").
        "ohne_kontaktdaten": sperre.autor is None,
        "widerspruch": sperre.widerspruch,
        "widerspruch_am": _iso(sperre.widerspruch_am),
        "widerspruch_offen": sperre.widerspruch_am is not None
        and sperre.pruefergebnis is None,
        "pruefergebnis": sperre.pruefergebnis,
        "pruefung_begruendung": sperre.pruefung_begruendung,
        "geprueft_am": _iso(sperre.geprueft_am),
    }


class ModerationService:
    """Service for managing content reports and moderation actions."""

    def __init__(
        self,
        report_repo: Optional[ContentReportRepository] = None,
        moderation_repo: Optional[IModerationRepository] = None,
        vote_repo: Optional[VoteRepository] = None,
        raw_input_repo: Optional[RawInputRepository] = None,
        sperre_repo: Optional[SperreRepository] = None,
    ):
        self.report_repo = report_repo or get_content_report_repository()
        self.moderation_repo = moderation_repo or get_moderation_repository()
        # Erst beim endgueltigen Entfernen gebraucht; vorher keine Verbindung.
        self._vote_repo = vote_repo
        self._raw_input_repo = raw_input_repo
        self._sperre_repo = sperre_repo

    async def report_content(
        self,
        content_id: str,
        content_type: str,
        reason: Meldegrund,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        description: Optional[str] = None,
        melder_name: Optional[str] = None,
        melder_email: Optional[str] = None,
        guter_glaube: Optional[bool] = None,
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
            melder_name: Optional name of the reporter (Art. 16 Abs. 2 lit. c DSA)
            melder_email: Optional e-mail address of the reporter (same)
            guter_glaube: Erklaerung guten Glaubens (Art. 16 Abs. 2 lit. d DSA)

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

        if reason not in MELDEGRUENDE:
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
                melder_name=melder_name,
                melder_email=melder_email,
                guter_glaube=guter_glaube,
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

    async def sperren(
        self,
        content_id: str,
        gesperrt_von: str,
        sperrgrund: Sperrgrund,
        begruendung: str,
    ) -> bool:
        """
        Einen gemeldeten Beitrag sperren, statt ihn zu loeschen.

        Ohne Sperrgrund aus SPERRGRUENDE und ohne Begruendung keine Sperre (#448):
        Beides erfaehrt der Autor in der Sperrnachricht (Art. 17 DSA). Die Sperre
        merkt sich den Autor, damit nur er sie sieht und widersprechen kann.

        Der Beitrag bleibt im Speicher und bekommt den Status BLOCKED; die
        Repositories blenden ihn damit aus Suche, Einzelansicht, Listen, Zaehlern
        und "Meine Beitraege" aus. Die Moderation findet ihn weiter, weil ihr
        Repository nicht nach Sperre filtert. Alle Meldungen zum Beitrag stehen
        danach auf bearbeitet.

        Erst Qdrant, dann PostgreSQL (Sperre, dann Meldungen), ohne gemeinsame
        Transaktion. Scheitert ein Schritt in PostgreSQL, ist der Beitrag schon
        gesperrt und der Fehler geht an den Aufrufer. Erneutes Sperren holt die
        Sperre nach, weil der Status von vor der ersten Sperre erhalten bleibt; gibt
        es die Sperre schon, zieht es noch die Meldungen nach und endet mit
        SchonGesperrt. Andersherum saehe der Autor eine Sperre an einem sichtbaren
        Beitrag.

        Raises:
            SperreUngueltig: ohne gueltigen Sperrgrund oder ohne Begruendung
            SchonGesperrt: Es gibt schon eine aktive Sperre, auch wenn eine
                gleichzeitige Anfrage sie eben angelegt hat; ihr Grund bliebe sonst
                still stehen, waehrend der Admin einen neuen angegeben hat.

        Returns:
            bool: False, wenn es den Beitrag nicht gibt
        """
        begruendung = _ohne_rand(begruendung)
        if sperrgrund not in SPERRGRUENDE:
            raise SperreUngueltig("Unbekannter Sperrgrund")
        if begruendung is None:
            raise SperreUngueltig("Begruendung fehlt")

        beitrag = await self._beitrag_laden(content_id)
        if beitrag is None:
            logger.warning(f"Content {content_id} not found")
            return False
        neu = None
        if not await asyncio.to_thread(
            self._sperre_repository().aktive, UUID(content_id)
        ):
            await self.moderation_repo.sperren(beitrag)
            neu = await asyncio.to_thread(
                self._sperre_repository().anlegen,
                content_id=UUID(content_id),
                sperrgrund=sperrgrund,
                begruendung=begruendung,
                gesperrt_von=gesperrt_von,
                autor=_autor(beitrag),
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
        if neu is None:
            raise SchonGesperrt()
        return True

    async def entsperren(
        self, content_id: str, entsperrt_von: Optional[str] = None
    ) -> bool:
        """
        Eine Sperre aufheben: Der Beitrag bekommt den Zustand von vor der Sperre
        zurueck (ohne gemerkten Zustand: sichtbar) und ist wieder so sichtbar wie
        vorher. Die Meldungen bleiben bearbeitet. Die Sperre gilt als aufgehoben,
        ein offener Widerspruch als geprueft mit dem Ergebnis "entsperrt".

        Erst Qdrant, dann PostgreSQL: Scheitert das Aufheben der Sperre, ist der
        Beitrag schon wieder sichtbar; erneutes Entsperren holt es nach.

        Returns:
            bool: False, wenn es den Beitrag nicht gibt
        """
        beitrag = await self._beitrag_laden(content_id)
        if beitrag is None:
            logger.warning(f"Content {content_id} not found")
            return False

        if beitrag.get("status") == ContentStatus.BLOCKED.value:
            await self.moderation_repo.entsperren(beitrag)
        await asyncio.to_thread(
            self._sperre_repository().aufheben,
            UUID(content_id),
            entsperrt_von,
            datetime.now(timezone.utc),
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

        Jeder traegt unter "sperre" seine aktive Sperre mit Sperrgrund und
        Widerspruch; None bei Sperren aus der Zeit vor #448, die keinen Grund haben.
        """
        beitraege = await self.moderation_repo.gesperrte_laden(limit)
        sperren = await asyncio.to_thread(self._sperre_repository().aktive_je_beitrag)
        for beitrag in beitraege:
            try:
                sperre = sperren.get(UUID(str(beitrag.get("id"))))
            except ValueError:
                sperre = None
            beitrag["sperre"] = _sperre_fuer_admins(sperre) if sperre else None
        return beitraege

    async def meine_sperren(self, autor: str) -> List[Dict[str, Any]]:
        """
        Die Sperrnachrichten einer Person: je aktive Sperre an einem ihrer Beitraege
        die Entscheidung mit Sperrgrund und Begruendung, dazu ihr Widerspruch (mit
        ihrem Text, den sie nach der Datenschutzerklaerung einsehen kann) und
        das Ergebnis der erneuten Pruefung; nach einem erfolgreichen Widerspruch
        auch die aufgehobene Sperre. Wer gesperrt oder geprueft hat, steht nicht
        darin.
        """
        nachrichten = []
        for sperre in await asyncio.to_thread(
            self._sperre_repository().fuer_autor, autor
        ):
            beitrag = await self.moderation_repo.laden(str(sperre.content_id)) or {}
            nachrichten.append(
                {
                    "id": str(sperre.id),
                    "content_id": str(sperre.content_id),
                    "content_type": beitrag.get("content_type"),
                    "titel": beitrag.get("title") or beitrag.get("text"),
                    "sperrgrund": sperre.sperrgrund,
                    "begruendung": sperre.begruendung,
                    "gesperrt_am": _iso(sperre.gesperrt_am),
                    "aufgehoben_am": _iso(sperre.aufgehoben_am),
                    "widerspruch": sperre.widerspruch,
                    "widerspruch_am": _iso(sperre.widerspruch_am),
                    "pruefergebnis": sperre.pruefergebnis,
                    "pruefung_begruendung": sperre.pruefung_begruendung,
                    "geprueft_am": _iso(sperre.geprueft_am),
                }
            )
        return nachrichten

    async def widersprechen(
        self, sperre_id: str, autor: str, text: Optional[str]
    ) -> Widerspruchsergebnis:
        """
        Der Autor widerspricht einer Sperre; der Widerspruch ist formlos, der Text
        darf fehlen. Er landet bei den Admins (gesperrte_beitraege) zur erneuten
        Pruefung. Je Sperre geht ein Widerspruch.
        """
        try:
            kennung = UUID(sperre_id)
        except ValueError:
            return Widerspruchsergebnis.NICHT_GEFUNDEN
        ergebnis = await asyncio.to_thread(
            self._sperre_repository().widersprechen,
            kennung,
            autor,
            _ohne_rand(text),
            datetime.now(timezone.utc),
        )
        logger.info(f"Widerspruch gegen Sperre {sperre_id}: {ergebnis.value}")
        return ergebnis

    async def sperre_bestaetigen(
        self, sperre_id: str, geprueft_von: str, begruendung: str
    ) -> bool:
        """
        Nach erneuter Pruefung bleibt die Sperre; die Begruendung erfaehrt der Autor
        in seiner Sperrnachricht. Das andere Ergebnis ist entsperren().

        Raises:
            SperreUngueltig: ohne Begruendung

        Returns:
            bool: False ohne aktive Sperre mit offenem Widerspruch
        """
        begruendung = _ohne_rand(begruendung)
        if begruendung is None:
            raise SperreUngueltig("Begruendung fehlt")
        try:
            kennung = UUID(sperre_id)
        except ValueError:
            return False
        bestaetigt = await asyncio.to_thread(
            self._sperre_repository().sperre_bestaetigen,
            kennung,
            geprueft_von,
            begruendung,
            datetime.now(timezone.utc),
        )
        if bestaetigt:
            logger.info(f"Sperre {sperre_id} nach Widerspruch bestaetigt")
        return bestaetigt

    async def delete_content(
        self, content_id: str, content_type: str, deleted_by: Optional[str]
    ) -> bool:
        """
        Einen Beitrag endgueltig entfernen, samt den Verweisen der Aussagen auf ihn,
        seinen Stimmen und dem "ausformuliert in" der Einwuerfe, die in ihm
        ausformuliert sind (#421).

        Die Verweise gehen fuer jeden Beitragstyp weg, unabhaengig von content_type:
        Aussagen verweisen auf Beitraege jedes Typs (#294). Erst Verweise, Stimmen und
        "ausformuliert in", dann der Beitrag: Scheitert davor etwas, bleibt der Beitrag
        stehen und ein erneuter Versuch raeumt auf. Andersherum stuende ein Verweis auf
        einen Beitrag, den kein zweiter Aufruf mehr findet. Was ein abgebrochener Lauf
        ohne zweiten Versuch hinterlaesst: services/content/verweise_entfernen.py.

        Danach gilt eine Sperre des Beitrags als aufgehoben, und die offenen
        Meldungen zum Beitrag stehen auf bearbeitet. Schon bearbeitete und
        abgewiesene behalten ihre Entscheidung und deren Zeitpunkt, an dem ihre
        Loeschfrist haengt.

        Args:
            content_id: UUID of the content to delete
            content_type: Type of content (nur fuer das Log)
            deleted_by: Kennung des Admins; None, wenn die Loeschfrist entfernt
                (services/loeschfristen_service.py)

        Returns:
            bool: False, wenn es den Beitrag nicht gibt oder er nicht entfernt wurde

        Raises:
            VerweiseNichtEntfernt: Aussagen verweisen noch auf den Beitrag; er ist
                nicht entfernt.
            Datenbankfehler beim Loeschen von Stimmen oder "ausformuliert in" gehen
                weiter; der Beitrag ist dann ebenfalls nicht entfernt.
        """
        if await self._beitrag_laden(content_id) is None:
            logger.warning(f"Content {content_id} not found or already deleted")
            return False

        await verweise_entfernen(self.moderation_repo, content_id)
        stimmen = await asyncio.to_thread(
            self._stimmen().loeschen_fuer_beitrag, UUID(content_id)
        )
        ausformuliert = await asyncio.to_thread(
            self._einwuerfe().ausformuliert_in_loeschen, UUID(content_id)
        )
        logger.info(
            f"Content {content_id}: {stimmen} votes and {ausformuliert} "
            "raw input links deleted"
        )

        if not await self.moderation_repo.entfernen(content_id):
            logger.warning(f"Content {content_id} could not be deleted")
            return False

        # Eine Sperre des Beitrags gilt als aufgehoben, damit ihre Frist laeuft und
        # der Autor keine Sperrnachricht zu einem Beitrag sieht, den es nicht mehr
        # gibt. Wie bei den Meldungen macht ein Fehler die Loeschung nicht rueckgaengig.
        try:
            await asyncio.to_thread(
                self._sperre_repository().aufheben,
                UUID(content_id),
                deleted_by,
                datetime.now(timezone.utc),
                entsperrt=False,
            )
        except Exception as e:
            logger.warning(
                f"Content {content_id} deleted, lifting its Sperre failed "
                f"({type(e).__name__})"
            )

        # Offene Meldungen als bearbeitet markieren. Der Beitrag ist schon weg;
        # ein Fehler hier macht die Loeschung nicht rueckgaengig.
        try:
            updated_count = self.report_repo.update_reports_by_content_id(
                content_id=UUID(content_id),
                status="reviewed",
                reviewed_by=deleted_by,
                resolution_notes="Content deleted",
                nur_offene=True,
            )
        except Exception as e:
            # Nur der Typ: Die Meldung einer Datenbank kann reviewed_by enthalten.
            logger.warning(
                f"Content {content_id} deleted, marking its reports as reviewed "
                f"failed ({type(e).__name__})"
            )
            updated_count = 0

        logger.info(
            f"Content {content_id} ({content_type}) deleted, {updated_count} reports marked as reviewed"
        )
        return True

    def _stimmen(self) -> VoteRepository:
        if self._vote_repo is None:
            self._vote_repo = VoteRepository()
        return self._vote_repo

    def _einwuerfe(self) -> RawInputRepository:
        if self._raw_input_repo is None:
            self._raw_input_repo = get_raw_input_repository()
        return self._raw_input_repo

    def _sperre_repository(self) -> SperreRepository:
        if self._sperre_repo is None:
            self._sperre_repo = get_sperre_repository()
        return self._sperre_repo

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
