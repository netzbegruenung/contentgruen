"""
Loeschfristen fuer Meldungen, Einwuerfe, Sperren, geloeschte Beitraege und deren Stimmen (#421),
fuer nie benutzte Konten aus Einladungen (#538) und fuer das Tagespseudonym an
Suchereignissen (#495).

Fachliche Quelle der Fristen ist docs/LOESCHKONZEPT.md ("Fristen"); im Code stehen
ihre Zahlen hier und nur hier, damit die Datenschutzerklaerung sie zitieren kann.
Andere Fristen stehen bei ihrer Datenart: Feedback in services/feedback_service.py, Suchen ohne Treffer in
services/suchen_ohne_treffer_service.py, Nutzungsereignisse in core/config.py.

- Meldungen: bearbeitete und abgewiesene MELDUNG_NACH_BEARBEITUNG_TAGE nach der
  Bearbeitung. Sechs Monate, weil so lange eine Entscheidung nach Art. 20 Abs. 1 DSA
  noch angefochten werden kann. Offene Meldungen bleiben: Sie sind Arbeit.
- Einwuerfe, die in keinem Beitrag ausformuliert sind (offen, destilliert, verworfen, oder
  ausformuliert in einen inzwischen entfernten Beitrag): EINWURF_OHNE_BEITRAG_TAGE
  nach der letzten Arbeit daran (Einwerfen oder Satz gespeichert), mit ihren Saetzen.
  Wer ein Jahr lang nichts daraus gemacht hat, macht es nicht mehr. Ausformulierte
  bleiben, solange ihr Beitrag besteht: Sie sind seine Herkunft in der Kette.
- Geloeschte Beitraege: GELOESCHTER_BEITRAG_TAGE nach dem Loeschen endgueltig
  entfernt, ueber denselben Weg wie die Entfernung durch einen Admin
  (ModerationService.delete_content), also samt Verweisen der Aussagen, Stimmen und
  "ausformuliert in". Die Frist zaehlt ab dem Tag in FELD_GELOESCHT_AM, den
  der erste Lauf nach dem Loeschen setzt, also hoechstens einen Tag spaeter.
- Sperren (#448): aufgehobene SPERRE_NACH_AUFHEBUNG_TAGE nach der Aufhebung, samt
  Widerspruch und Pruefung. Wie bei den Meldungen kann die Entscheidung so lange
  angefochten werden (Art. 20 Abs. 1 DSA). Aktive Sperren haben keine Frist: Der
  Beitrag ist gesperrt, und Sperrgrund und Begruendung gehoeren zu dieser Entscheidung.
- Nie benutzte Konten aus Einladungen (#538): NIE_BENUTZTES_KONTO_TAGE nach Ablauf
  des Links in der Mail (MAIL_GUELTIG_SEKUNDEN ab dem Anlegen) im Realm geloescht.
  Bleibt der Link ungenutzt, war die Adresse vertippt oder fremd, oder die Person hat
  es sich anders ueberlegt; einen Monat lang kommt sie noch ueber "Passwort vergessen"
  hinein. Was "nie benutzt" heisst: KeycloakKonten.nie_benutzte_loeschen. Ohne Zugang
  zur Keycloak-Admin-Schnittstelle (Dev-Stack) entfaellt die Frist.
- Suchereignisse (#495): Ist ein UTC-Tag abgeschlossen, werden seine Suchereignisse
  zum Tageszaehler der Suchen verdichtet (SearchTrackingRepository.verdichten_vor):
  Zahl der Suchen, der Suchen ohne Treffer und der Personen, kein Tagespseudonym.
  Das Pseudonym lebt so hoechstens bis zum naechsten Lauf nach Mitternacht. Der
  erste Lauf verdichtet auch die Tage, die bis dahin 90 Tage als Einzelzeilen
  blieben.
- Stimmen haben keine eigene Frist: Aus ihnen entsteht die Guete eines Beitrags, sie
  leben so lange wie er und gehen mit ihm.

loeschen_im_takt ist ein eigener Hintergrund-Task aus main.py und laeuft taeglich und
zusaetzlich um Mitternacht (UTC). Wie beim Feedback haengt er nicht am abschaltbaren
Bereinigungsjob: Die Fristen stehen im Loeschkonzept ohne Bedingung.
"""

import asyncio
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional

from core.logging import get_logger
from domain.interfaces.konten_im_realm import MAIL_GUELTIG_SEKUNDEN, INieBenutzteKonten
from domain.models.content_status import FELD_GELOESCHT_AM
from repositories.content_report_repository import ContentReportRepository
from repositories.interfaces.moderation_repository import IModerationRepository
from repositories.einwurf_repository import EinwurfRepository
from repositories.search_tracking_repository import SearchTrackingRepository
from repositories.sperre_repository import SperreRepository
from services.moderation_service import ModerationService
from utils.utc_tag import heute_utc, sekunden_bis_mitternacht

logger = get_logger(__name__)

MELDUNG_NACH_BEARBEITUNG_TAGE = 180
EINWURF_OHNE_BEITRAG_TAGE = 365
GELOESCHTER_BEITRAG_TAGE = 30
SPERRE_NACH_AUFHEBUNG_TAGE = 180
NIE_BENUTZTES_KONTO_TAGE = 30
LOESCH_TAKT_SEKUNDEN = 24 * 60 * 60


def _grenze(heute: date, tage: int) -> datetime:
    """Beginn (UTC) des aeltesten Tages, der bleibt; alles davor wird geloescht."""
    return datetime.combine(heute - timedelta(days=tage), time.min, timezone.utc)


def _geloescht_am(beitrag: Dict[str, Any]) -> Optional[date]:
    try:
        return date.fromisoformat(beitrag.get(FELD_GELOESCHT_AM) or "")
    except (TypeError, ValueError):
        return None


class LoeschfristenService:
    def __init__(
        self,
        meldungen: ContentReportRepository,
        einwuerfe: EinwurfRepository,
        beitraege: IModerationRepository,
        moderation: ModerationService,
        sperren: SperreRepository,
        konten: Optional[INieBenutzteKonten] = None,
        suchereignisse: Optional[SearchTrackingRepository] = None,
    ):
        self._meldungen = meldungen
        self._einwuerfe = einwuerfe
        self._beitraege = beitraege
        self._moderation = moderation
        self._sperren = sperren
        self._konten = konten
        self._suchereignisse = suchereignisse

    async def fristen_anwenden(self, heute: Optional[date] = None) -> None:
        """
        Alle Fristen einmal anwenden. Ein Fehler in einer Datenart haelt die anderen
        nicht auf; der naechste Lauf holt nach, was liegen blieb.
        """
        heute = heute or heute_utc()
        if self._suchereignisse is not None:
            # Zuerst: das Pseudonym soll so kurz wie moeglich nach Mitternacht weg sein.
            await self._frist_anwenden(
                self._suchereignisse.verdichten_vor,
                _grenze(heute, 0),
                "search events of closed days (compacted into day counters)",
            )
        await self._frist_anwenden(
            self._meldungen.bearbeitete_loeschen_vor,
            _grenze(heute, MELDUNG_NACH_BEARBEITUNG_TAGE),
            "handled reports",
        )
        await self._frist_anwenden(
            self._einwuerfe.ohne_beitrag_loeschen_vor,
            _grenze(heute, EINWURF_OHNE_BEITRAG_TAGE),
            "raw inputs",
        )
        await self._frist_anwenden(
            self._sperren.aufgehobene_loeschen_vor,
            _grenze(heute, SPERRE_NACH_AUFHEBUNG_TAGE),
            "lifted Sperren",
        )
        if self._konten is not None:
            await self._frist_anwenden(
                self._konten.nie_benutzte_loeschen,
                _grenze(heute, NIE_BENUTZTES_KONTO_TAGE)
                - timedelta(seconds=MAIL_GUELTIG_SEKUNDEN),
                "never used accounts from invitations",
            )
        try:
            await self._geloeschte_beitraege(heute)
        except Exception as e:
            logger.error(
                f"Error removing deleted content: {type(e).__name__}", exc_info=True
            )

    @staticmethod
    async def _frist_anwenden(loeschen_vor, grenze: datetime, was: str) -> None:
        """Eine Frist in PostgreSQL oder im Realm anwenden; ein Fehler wird nur protokolliert."""
        try:
            n = await asyncio.to_thread(loeschen_vor, grenze)
            logger.info(f"Deleted {n} {was} past their Loeschfrist")
        except Exception as e:
            logger.error(f"Error deleting old {was}: {type(e).__name__}", exc_info=True)

    async def _geloeschte_beitraege(self, heute: date) -> None:
        grenze = heute - timedelta(days=GELOESCHTER_BEITRAG_TAGE)
        ohne_tag: List[str] = []
        faellig: List[Dict[str, Any]] = []
        for beitrag in await self._beitraege.geloeschte_laden():
            tag = _geloescht_am(beitrag)
            if tag is None:
                ohne_tag.append(beitrag["id"])
            elif tag < grenze:
                faellig.append(beitrag)

        if ohne_tag:
            await self._beitraege.geloescht_am_setzen(ohne_tag, heute)

        entfernt = 0
        for beitrag in faellig:
            try:
                if await self._moderation.delete_content(
                    beitrag["id"], str(beitrag.get("content_type", "")), None
                ):
                    entfernt += 1
            except Exception as e:
                logger.error(
                    f"Error removing deleted content {beitrag['id']}: {type(e).__name__}",
                    exc_info=True,
                )
        logger.info(
            f"Removed {entfernt} of {len(faellig)} deleted contents past their "
            f"Loeschfrist, dated {len(ohne_tag)}"
        )


async def loeschen_im_takt(
    service: LoeschfristenService, takt_sekunden: float = LOESCH_TAKT_SEKUNDEN
) -> None:
    """
    Hintergrund-Task: wendet die Fristen sofort und dann taeglich an, spaetestens
    aber um Mitternacht (UTC), bis er abgebrochen wird.
    """
    while True:
        try:
            await service.fristen_anwenden()
        except Exception as e:
            logger.error(
                f"Error applying Loeschfristen: {type(e).__name__}", exc_info=True
            )
        await asyncio.sleep(min(takt_sekunden, sekunden_bis_mitternacht() + 1))
