"""
Service layer for content moderation functionality.
Provides business logic for reporting and managing flagged content.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from repositories.content_report_repository import (
    ContentReportRepository,
    MeldungNichtOffen,
    get_content_report_repository,
)
from repositories.implementations.qdrant.moderation_repository import (
    get_moderation_repository,
)
from repositories.interfaces.moderation_repository import IModerationRepository
from repositories.einwurf_repository import (
    EinwurfRepository,
    get_einwurf_repository,
)
from repositories.sperre_repository import SperreRepository, get_sperre_repository
from repositories.vote_repository import VoteRepository
from repositories.varianten_repository import (
    VariantenRepository,
    get_varianten_repository,
)
from domain.models.content_status import ContentStatus
from domain.models.meldegrund import MELDEGRUENDE, Meldegrund, beschreibung_fehlt
from domain.models.meldung import (
    MELDUNG_FEHLGESCHLAGEN,
    MeldungErgebnis,
    AngabenGeloescht,
    MelderAdresse,
    MelderAngaben,
    MelderSuche,
)
from domain.models.sperrgrund import SPERRGRUENDE, Sperrgrund
from domain.models.widerspruch import Widerspruchsergebnis
from core.config import settings
from core.fehler import Validierungsfehler
from services.anzeigename_service import (
    EHEMALIGE_PERSON_KENNUNG,
    AnzeigenameService,
    get_anzeigename_service,
)
from services.content.verweise_entfernen import verweise_entfernen
from services.meldung_mitteilen import (
    Entscheidung,
    MeldungMitteilung,
    get_meldung_mitteilung,
)

logger = logging.getLogger(__name__)

# Hoechstens so viele Sekunden wartet eine Anfrage auf den Mailversand (#493). Das
# Timeout von smtplib gilt je Schritt, ein langsamer Server kaeme mit vielen Schritten
# weit darueber; danach antwortet die Anfrage, und der Versand laeuft im Thread zu Ende.
MAIL_FRIST = 15


# Obergrenze fuer die Liste gesperrter Beitraege in der Moderation.
GESPERRTE_HOECHSTENS = 500


class SperreUngueltig(Validierungsfehler):
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


def _titel(beitrag: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Wie die Mail an die meldende Person den Beitrag nennt (#493): nur einen
    sichtbaren mit Titel. Gesperrte und geloeschte findet die Melde-Route auch;
    wer ihre Kennung kennt, bekaeme sonst ihren Titel per Mail.
    """
    if not beitrag or beitrag.get("status", ContentStatus.VISIBLE.value) != (
        ContentStatus.VISIBLE.value
    ):
        return None
    return beitrag.get("title") or beitrag.get("text")


async def _hoechstens_mail_frist(funktion, *args) -> None:
    """Fuehrt den Versand im Thread aus und wartet hoechstens MAIL_FRIST darauf."""
    try:
        await asyncio.wait_for(asyncio.to_thread(funktion, *args), timeout=MAIL_FRIST)
    except asyncio.TimeoutError:
        logger.warning("Mail not sent within the deadline, sending continues")


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
        einwurf_repo: Optional[EinwurfRepository] = None,
        sperre_repo: Optional[SperreRepository] = None,
        mitteilung: Optional[MeldungMitteilung] = None,
        varianten_repo: Optional[VariantenRepository] = None,
        anzeigenamen: Optional[AnzeigenameService] = None,
    ):
        self.report_repo = report_repo or get_content_report_repository()
        self.moderation_repo = moderation_repo or get_moderation_repository()
        # Erst beim endgueltigen Entfernen gebraucht; vorher keine Verbindung.
        self._vote_repo = vote_repo
        self._einwurf_repo = einwurf_repo
        self._sperre_repo = sperre_repo
        self._varianten_repo = varianten_repo
        # Mails an die meldende Person (#493); ohne eingerichteten Versand geht nichts hinaus.
        self._mitteilung = mitteilung
        # Anzeigenamen fuer "Gemeldet von" und "Bearbeitet von"; erst beim Lesen gebraucht.
        self._anzeigenamen = anzeigenamen

    async def _namen_anhaengen(self, meldungen: List[Dict[str, Any]]) -> None:
        """
        Haengt an jede Meldung ``reported_by_name`` und ``reviewed_by_name`` (Anzeigename
        der meldenden bzw. bearbeitenden Person, sonst None), eine Abfrage fuer alle.
        Nur fuer die Admin-Listen; die Endpunkte verlangen Admin-Rechte.
        """
        kennungen = {
            kennung
            for meldung in meldungen
            for kennung in (
                meldung.get("reported_by_user_id"),
                meldung.get("reviewed_by"),
            )
            if kennung
        }
        namen: Dict[str, str] = {}
        if kennungen:
            # Ohne Namen bleibt die Liste brauchbar (Kurzform der Kennung im Frontend):
            # ein Fehler beim Nachschlagen darf sie nicht leeren.
            try:
                dienst = self._anzeigenamen or get_anzeigename_service()
                namen = await asyncio.to_thread(dienst.namen, kennungen)
            except Exception as e:
                logger.warning(
                    f"Anzeigenamen fuer Meldungen nicht lesbar: {type(e).__name__}"
                )
        for meldung in meldungen:
            meldung["reported_by_name"] = namen.get(
                meldung.get("reported_by_user_id") or ""
            )
            meldung["reviewed_by_name"] = namen.get(meldung.get("reviewed_by") or "")

    async def report_content(
        self,
        content_id: str,
        content_type: str,
        reason: Meldegrund,
        *,
        melder: MelderAngaben,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> MeldungErgebnis:
        """
        Report a content item.

        Args:
            content_id: UUID of the content
            content_type: Type of content
            reason: Report reason
            user_id: Optional user ID of reporter
            session_id: Optional session ID of reporter
            description: Optional detailed description
            melder: Angaben der meldenden Person nach Art. 16 Abs. 2 DSA

        Returns:
            MeldungErgebnis: wahr, wenn angenommen; ``neu`` und ``mit_email`` wie dort
        """
        # Validate inputs
        if not content_id or not content_type or not reason:
            logger.warning("Invalid report submission: missing required fields")
            return MELDUNG_FEHLGESCHLAGEN

        if not user_id and not session_id:
            logger.warning("Invalid report submission: no reporter identifier")
            return MELDUNG_FEHLGESCHLAGEN

        if reason not in MELDEGRUENDE:
            # Der Grund ist hier freier Text von aussen (#422).
            logger.warning("Invalid report reason")
            return MELDUNG_FEHLGESCHLAGEN

        # Art. 16 Abs. 2 lit. d DSA (#438): keine neue Meldung ohne die Erklaerung
        # guten Glaubens, auch nicht an der API vorbei; fuer jeden Meldegrund.
        if melder.guter_glaube is not True:
            logger.warning("Invalid report submission: no Erklaerung guten Glaubens")
            return MELDUNG_FEHLGESCHLAGEN

        if beschreibung_fehlt(reason, description):
            logger.warning("Invalid report submission: illegal_content without reason")
            return MELDUNG_FEHLGESCHLAGEN

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
                return MeldungErgebnis(erfolg=True, neu=False, mit_email=False)

            report = self.report_repo.create_report(
                content_id=content_uuid,
                content_type=content_type,
                reason=reason,
                reported_by_user_id=user_id,
                reported_by_session_id=session_id,
                description=description,
                melder=melder,
            )
            logger.info(f"Content {content_id} reported: {reason}")
        except ValueError as e:
            logger.error("Invalid content_id format")
            return MELDUNG_FEHLGESCHLAGEN
        except Exception as e:
            logger.error(f"Error reporting content: {type(e).__name__}", exc_info=True)
            return MELDUNG_FEHLGESCHLAGEN

        if report is None:
            return MELDUNG_FEHLGESCHLAGEN
        # Art. 16 Abs. 4 DSA (#493): nur fuer eine neu angelegte Meldung, nicht fuer
        # die Doppelmeldung oben.
        if melder.email:
            await self._eingang_bestaetigen(content_id, melder.email)
        return MeldungErgebnis(erfolg=True, neu=True, mit_email=bool(melder.email))

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
            logger.error(
                f"Error checking content existence: {type(e).__name__}", exc_info=True
            )
            # Im Zweifel durchlassen: eine Meldung zu verlieren waere schlimmer
            # als eine ins Leere zeigende anzunehmen.
            return True

    def _mitteilung_holen(self) -> MeldungMitteilung:
        if self._mitteilung is None:
            self._mitteilung = get_meldung_mitteilung()
        return self._mitteilung

    async def _eingang_bestaetigen(self, content_id: str, email: str) -> None:
        """Eingangsbestaetigung; MeldungMitteilung faengt jeden Fehler beim Versand."""
        beitrag = await self._beitrag_fuer_mail(content_id)
        await _hoechstens_mail_frist(
            self._mitteilung_holen().eingang_bestaetigen, email, _titel(beitrag)
        )

    async def _beitrag_fuer_mail(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Der Beitrag fuer seinen Titel in der Mail; ohne ihn nennt sie keinen."""
        try:
            return await self._beitrag_laden(content_id)
        except Exception as e:
            logger.warning(f"Loading content for the mail failed ({type(e).__name__})")
            return None

    async def _entscheidung_mitteilen(
        self,
        adressen: List[MelderAdresse],
        entscheidung: Entscheidung,
        titel: Optional[str],
    ) -> None:
        """
        Art. 16 Abs. 5 DSA (#493): je Adresse eine Mail, auch bei mehreren Meldungen.
        Nacheinander in einem Thread: Viele Meldungen belegen so nicht den ganzen
        Thread-Pool des Dienstes. MeldungMitteilung faengt jeden Fehler beim Versand.
        """
        if not adressen:
            return
        empfaenger = {adresse.email.lower(): adresse.email for adresse in adressen}
        mitteilung = self._mitteilung_holen()

        def alle_verschicken() -> None:
            for email in empfaenger.values():
                mitteilung.entscheidung_mitteilen(email, entscheidung, titel)

        await _hoechstens_mail_frist(alle_verschicken)

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
                        logger.debug(
                            f"Could not fetch content {content_id}: {type(e).__name__}"
                        )
                        report["content"] = None

            await self._namen_anhaengen(reports)
            return reports
        except Exception as e:
            logger.error(
                f"Error getting reports (status={status}): {type(e).__name__}",
                exc_info=True,
            )
            return []

    async def meldungen_einer_person(self, suche: MelderSuche) -> List[Dict[str, Any]]:
        """
        Alle Meldungen mit diesen Angaben der meldenden Person, fuer die Auskunft
        an Personen ohne Konto (Art. 15 DSGVO, #494). Regeln der Suche: MelderSuche.
        """
        meldungen = await asyncio.to_thread(self.report_repo.von_melder, suche)
        await self._namen_anhaengen(meldungen)
        return meldungen

    async def angaben_der_person_loeschen(
        self,
        suche: MelderSuche,
        meldung_ids: List[UUID],
        dieselbe_person: bool = False,
    ) -> AngabenGeloescht:
        """
        Die Angaben einer Person an ihren Meldungen loeschen (Art. 17 DSGVO, #494):
        erledigte Meldungen ganz, offene nur Name, E-Mail-Adresse und Pseudonym.
        Nur die Meldungen aus ``meldung_ids`` (die der Admin gesehen hat), die noch
        zu den Angaben passen.

        Raises:
            ValueError: nur nach dem Namen gesucht, ohne dass der Admin bestaetigt
                hat, dass alle Treffer dieselbe Person sind
        """
        if suche.nur_name and not dieselbe_person:
            raise ValueError("Nur nach dem Namen gesucht: dieselbe Person bestaetigen")
        return await asyncio.to_thread(
            self.report_repo.angaben_loeschen, suche, list(meldung_ids)
        )

    async def _beitrag_laden(self, content_id: str) -> Optional[Dict[str, Any]]:
        """Payload eines Beitrags, auch gesperrt; None, wenn es ihn nicht gibt."""
        try:
            UUID(content_id)
        except ValueError:
            logger.warning("Invalid content_id format")
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
        # Vor dem Sperren: Danach ist der Beitrag nicht mehr sichtbar (_titel).
        titel = _titel(beitrag)
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
        # Auch bei schon bestehender Sperre: So holt erneutes Sperren eine
        # gescheiterte Zahl nach.
        await self._antwortzahl_nachziehen(content_id)

        adressen: List[MelderAdresse] = []
        updated_count = self.report_repo.update_reports_by_content_id(
            content_id=UUID(content_id),
            status="reviewed",
            reviewed_by=gesperrt_von,
            resolution_notes="Beitrag gesperrt",
            melder_adressen=adressen,
        )
        logger.info(
            f"Content {content_id} gesperrt, "
            f"{updated_count} reports marked as reviewed"
        )
        await self._entscheidung_mitteilen(adressen, Entscheidung.GESPERRT, titel)
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
        await self._antwortzahl_nachziehen(content_id)
        await asyncio.to_thread(
            self._sperre_repository().aufheben,
            UUID(content_id),
            entsperrt_von,
            datetime.now(timezone.utc),
        )
        logger.info(f"Content {content_id} entsperrt")
        return True

    async def _antwortzahl_nachziehen(self, content_id: str) -> None:
        """
        Die Antwortzahl der Aussagen, die auf den Beitrag verweisen, nach Sperren
        oder Entsperren neu zaehlen (#631). Scheitert das, bleibt die Sperre oder
        Entsperrung trotzdem bestehen: Die Zahl ist Anzeige, die Moderation nicht.
        Erneutes Sperren oder Entsperren zieht sie nach.
        """
        try:
            geaendert = await self.moderation_repo.antwortzahl_nachziehen(content_id)
        except Exception as e:
            logger.error(
                f"Recounting replies for statements of {content_id} failed: "
                f"{type(e).__name__}",
                exc_info=True,
            )
            return
        logger.info(f"Reply count of {geaendert} statements updated for {content_id}")

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
        seinen Stimmen, dem "ausformuliert in" der Einwuerfe, die in ihm
        ausformuliert sind (#421), und seinen Verknuepfungen als Variante oder
        Original (#356).

        Die Verweise gehen fuer jeden Beitragstyp weg, unabhaengig von content_type:
        Aussagen verweisen auf Beitraege jedes Typs (#294). Erst Verweise, Stimmen,
        "ausformuliert in" und Varianten, dann der Beitrag: Scheitert davor etwas,
        bleibt der Beitrag stehen und ein erneuter Versuch raeumt auf. Andersherum
        stuende ein Verweis auf einen Beitrag, den kein zweiter Aufruf mehr findet. Was ein abgebrochener Lauf
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
        beitrag = await self._beitrag_laden(content_id)
        if beitrag is None:
            logger.warning(f"Content {content_id} not found or already deleted")
            return False
        titel = _titel(beitrag)

        await verweise_entfernen(self.moderation_repo, content_id)
        stimmen = await asyncio.to_thread(
            self._stimmen().loeschen_fuer_beitrag, UUID(content_id)
        )
        ausformuliert = await asyncio.to_thread(
            self._einwuerfe().ausformuliert_in_loeschen, UUID(content_id)
        )
        varianten = await asyncio.to_thread(
            self._varianten().verknuepfungen_entfernen, UUID(content_id)
        )
        logger.info(
            f"Content {content_id}: {stimmen} votes, {ausformuliert} "
            f"raw input links and {varianten} variant links deleted"
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
        adressen: List[MelderAdresse] = []
        try:
            updated_count = self.report_repo.update_reports_by_content_id(
                content_id=UUID(content_id),
                status="reviewed",
                reviewed_by=deleted_by,
                resolution_notes="Content deleted",
                nur_offene=True,
                melder_adressen=adressen,
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
        # Ohne Admin hat die Loeschfrist entfernt, entschieden hat niemand.
        await self._entscheidung_mitteilen(
            adressen,
            Entscheidung.ENTFERNT if deleted_by else Entscheidung.NICHT_MEHR_DA,
            titel,
        )
        return True

    def _stimmen(self) -> VoteRepository:
        if self._vote_repo is None:
            self._vote_repo = VoteRepository()
        return self._vote_repo

    def _einwuerfe(self) -> EinwurfRepository:
        if self._einwurf_repo is None:
            self._einwurf_repo = get_einwurf_repository()
        return self._einwurf_repo

    def _varianten(self) -> VariantenRepository:
        if self._varianten_repo is None:
            self._varianten_repo = get_varianten_repository()
        return self._varianten_repo

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
            adressen: List[MelderAdresse] = []
            updated_report = self.report_repo.update_report_status(
                report_id=report_uuid,
                status="dismissed",
                reviewed_by=dismissed_by,
                resolution_notes=notes or "Report dismissed",
                melder_adressen=adressen,
                nur_offene=True,
            )
            if updated_report:
                logger.info(f"Report {report_id} dismissed")
                if adressen:
                    beitrag = await self._beitrag_fuer_mail(str(adressen[0].content_id))
                    await self._entscheidung_mitteilen(
                        adressen, Entscheidung.ABGEWIESEN, _titel(beitrag)
                    )
                return True
            else:
                logger.warning(f"Report {report_id} not found")
                return False
        except MeldungNichtOffen:
            raise
        except ValueError as e:
            logger.error("Invalid report_id format")
            return False
        except Exception as e:
            logger.error(f"Error dismissing report: {type(e).__name__}", exc_info=True)
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
            logger.error(
                f"Error getting report stats: {type(e).__name__}", exc_info=True
            )
            return {
                "total": 0,
                "by_status": {},
                "pending": 0,
                "reviewed": 0,
                "dismissed": 0,
            }
