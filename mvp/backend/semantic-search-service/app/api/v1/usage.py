"""
API endpoints for usage tracking functionality.
"""

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Depends, Header, Request, Response
from typing import Optional, Dict, Any
from pydantic import BaseModel
import uuid
from datetime import datetime, timedelta, timezone

from dependencies import (
    get_beitrag_laden,
    get_content_repository,
    get_aufrufer,
    get_meilensteine_service,
    get_muster_hinweise_service,
    get_nutzung_rate_limiter,
    get_punkte_service,
    get_settings,
    get_unbeantwortete_aussagen_service,
    get_current_user_optional,
    get_reference_service,
    require_art9_einwilligung,
    require_user,
)
from utils.besucher_pseudonym import besucher_merkmal
from repositories.einwurf_repository import EinwurfRepository, get_einwurf_repository
from repositories.gesehene_nutzung_repository import (
    GeseheneNutzungRepository,
    get_gesehene_nutzung_repository,
)
from services.unbeantwortete_aussagen_service import (
    LIMIT_STANDARD,
    UnbeantworteteAussagenService,
)
from utils.client_identity import derive_client_key
from utils.device_category import derive_device_category
from utils.rate_limiter import RateLimiter
from services.entdoppelung import pruefwert
from utils.aufrufer import ANONYM
from services.meilensteine_service import MeilensteineService
from services.abzeichen_service import AbzeichenService, get_abzeichen_service
from domain.abzeichen_sichtbarkeit import (
    AKTUELLER_WORTLAUT as SICHTBARKEIT_WORTLAUT,
    MEHR_DAZU as SICHTBARKEIT_MEHR_DAZU,
    WORTLAUTE as SICHTBARKEIT_WORTLAUTE,
    UnbekannterWortlaut,
)
from services.punkte_service import PunkteService
from domain.punkte_einwilligung import (
    AKTUELLER_WORTLAUT as PUNKTE_WORTLAUT,
    GELTENDE_WORTLAUTE as PUNKTE_GELTENDE_WORTLAUTE,
    WORTLAUTE as PUNKTE_WORTLAUTE,
)
from repositories.punkte_einwilligung_repository import (
    get_punkte_einwilligung_repository,
)
from services.gepostet_service import GepostetService, get_gepostet_service
from services.art9_einwilligung_service import get_art9_einwilligung_service
from services.usage_tracking_service import get_usage_service
from services.beitrag_laden import BeitragLader, BeitragUnlesbar
from services.oft_genutzt_service import OftGenutztService, sichtbaren_beitrag_laden
from services.guete_service import guete_ergaenzen
from services.beitrag_fuer_aufrufer import Aufrufer, fuer_aufrufer
from domain.models.commentary import Fassung
from domain.models.content_type import ContentType
from dtos.beitrag import BeitragResponse
from dtos.beitragstypen import ANTWORT_JE_TYP
from services.content.reference_service import ReferenceService
from services.cleanup.bereinigungsjob import get_bereinigungsjob
from core.config import Settings
from core.logging import log_pseudonym
from repositories.varianten_repository import (
    VariantenRepository,
    get_varianten_repository,
)
from services.varianten import varianten_ergaenzen

logger = logging.getLogger(__name__)


router = APIRouter()


class TrackUsageRequest(BaseModel):
    """
    Request model for tracking usage.

    Ohne Sitzungskennung (#446): Ein session_id, den ein alter Client noch
    mitschickt, ist ein unbekanntes Feld und wird verworfen.
    """

    # Die kopierte Fassung eines Kommentars (#355); bei anderen Beitragstypen
    # ohne Bedeutung und nicht gespeichert.
    fassung: Optional[Fassung] = None


class TrackUsageResponse(BaseModel):
    """Response model for tracking usage."""

    success: bool
    message: str
    usage_count: int


class UserUsageStatsResponse(BaseModel):
    """Response model for user usage statistics."""

    user_id: str
    unique_contents_contributed: int
    total_usage_count: int
    top_content: list[Dict[str, Any]]


class BesuchResponse(BaseModel):
    """
    Antwort auf einen Besuch: Grundlage der Rueckmeldung beim Anmelden und von "Seit
    deinem letzten Besuch" auf der Startseite. Alles Zaehlerstaende, kein Zeitpunkt.
    """

    nutzung_seit_letztem_besuch: int
    # Einwuerfe anderer seit dem zuletzt gesehenen Stand; nie negativ.
    neue_einwuerfe: int = 0
    # Wie viele Aussagen "Hier fehlt eine Antwort" gerade zeigt (hoechstens deren
    # Grenze); kein Stand, deshalb nennt die Startseite sie nicht "neu".
    unbeantwortete_aussagen: int = 0
    # Die Liste hat ihre Grenze erreicht: Es koennen mehr warten ("50+").
    unbeantwortete_aussagen_mehr: bool = False


# So lange warten Einwuerfe und Luecken hoechstens; danach gilt 0, damit die
# Rueckmeldung zur Nutzung beim Anmelden nicht auf sie wartet.
BESUCH_NEBENZAHLEN_TIMEOUT_S = 1.5


class PunkteResponse(BaseModel):
    """Der eigene Punktestand je Stufe (ADR 0004, #352)."""

    tun: int
    quests: int
    wirkung: int
    gesamt: int
    # False fuer Startkonten und ohne Einwilligung "Punkte und Meilensteine": Das
    # Konto hat keine Punkte (GLOSSARY.md "Punkte"), das Frontend zeigt dann keinen Stand.
    sammelt: bool = True


class MeilensteinResponse(BaseModel):
    """
    Ein Meilenstein mit Stand (#351); ``erreicht`` ab ``stand >= schwelle``. ``bild``
    ist ein Pfad unter public/ des Frontends, ``art`` ``weg`` eine Wegmarke, die nicht
    fuers Abzeichen zaehlt (domain/meilensteine.py).
    """

    kennung: str
    name: str
    untertitel: str
    beschreibung: str
    bild: str
    bildnachweis: str
    art: str
    schwelle: int
    stand: int
    erreicht: bool


class MeilensteineResponse(BaseModel):
    """Die eigenen Meilensteine; leer fuer Startkonten und ohne Einwilligung zu Punkten."""

    meilensteine: list[MeilensteinResponse]


class SichtbarkeitWortlaut(BaseModel):
    kennung: str
    text: str
    # Aufklappbar unter der Frage: was die Einwilligung ausserdem wissen muss.
    mehr_dazu: str


class AbzeichenSichtbarkeitResponse(BaseModel):
    """Ob die Person gefragt wurde und was sie geantwortet hat (#351)."""

    gefragt: bool
    zeigen: Optional[bool]
    aktueller_wortlaut: SichtbarkeitWortlaut


class AbzeichenSichtbarkeitRequest(BaseModel):
    zeigen: bool
    wortlaut: str


class PunkteEinwilligungWortlaut(BaseModel):
    kennung: str
    text: str


class PunkteEinwilligungResponse(BaseModel):
    """
    Die Einwilligung "Punkte und Meilensteine" der Person (#351): ob sie gilt, zu
    welchem Wortlaut sie zuletzt geantwortet hat, und der Wortlaut fuer das Haekchen.
    """

    eingewilligt: bool
    wortlaut: Optional[str] = None
    aktueller_wortlaut: PunkteEinwilligungWortlaut


class PunkteEinwilligungRequest(BaseModel):
    eingewilligt: bool
    wortlaut: str


class GepostetResponse(BaseModel):
    """Wie viele verschiedene Personen diese Kalenderwoche "Ja, gepostet" gemeldet haben (#643)."""

    personen_diese_woche: int


class TrendingContentResponse(BaseModel):
    """Response model for trending content."""

    trending: list[Dict[str, Any]]


class OftGenutztResponse(BaseModel):
    """Die Beitraege fuer "Diese Woche oft genutzt", leer bei zu wenig Nutzung."""

    results: list[Dict[str, Any]]


class CleanupStatusResponse(BaseModel):
    """Response model for cleanup service status."""

    running: bool
    retention_days: int
    last_cleanup: Optional[str]
    last_cleanup_count: int
    next_cleanup: Optional[str]


class CleanupResultResponse(BaseModel):
    """Response model for cleanup operation result."""

    success: bool
    deleted_count: int
    message: str


async def _eingewilligt(kennung: str) -> bool:
    """
    Hat das Konto eine geltende Art.-9-Einwilligung (#559)? Je Aufruf aus der
    Datenbank gefragt, damit ein Widerruf sofort wirkt. Anders als
    ``require_art9_einwilligung`` kein Fehler, wenn sie nicht lesbar ist: Gezaehlt
    wird trotzdem (Kopieren ist Lesen), im Zweifel aber als nicht erteilt.
    """
    try:
        return await asyncio.to_thread(
            get_art9_einwilligung_service().eingewilligt, kennung
        )
    except Exception as e:
        logger.error(
            f"Art.-9-Einwilligung beim Zaehlen nicht lesbar: {type(e).__name__}",
            exc_info=True,
        )
        return False


async def _punkte_eingewilligt(kennung: str) -> bool:
    """
    Gilt fuer das Konto die Einwilligung "Punkte und Meilensteine" (#351)? Fuer die
    Muster-Hinweise; im Zweifel nicht erteilt, der Zaehler laeuft trotzdem.
    """
    try:
        return await asyncio.to_thread(
            get_punkte_einwilligung_repository().eingewilligt, kennung
        )
    except Exception as e:
        logger.error(
            f"Einwilligung Punkte beim Zaehlen nicht lesbar: {type(e).__name__}",
            exc_info=True,
        )
        return False


@router.post("/content/{content_id}/usage", response_model=TrackUsageResponse)
async def track_content_usage(
    content_id: str,
    body: TrackUsageRequest,
    request: Request,
    user_agent: Optional[str] = Header(None),
    aufrufer: Optional[str] = Depends(get_current_user_optional),
    laden: BeitragLader = Depends(get_beitrag_laden),
    settings: Settings = Depends(get_settings),
    limiter: RateLimiter = Depends(get_nutzung_rate_limiter),
):
    """
    Track that a content item was used (copied).

    This endpoint should be called when a user clicks the copy button.
    It increments the usage counter for the specified content.

    Die eigene Kopie zaehlt nicht: Der Zaehler soll sagen, wie oft andere einen
    Beitrag brauchbar fanden. Wer den eigenen Text kopiert - um ihn zu posten, zu
    pruefen oder weiterzuschreiben -, erhoeht ihn nicht. Geprueft wird hier und
    nicht im Frontend, weil das Frontend seine eigene Kennung nur kennt, solange es
    ihm passt; ``X-User`` setzt das BFF (IdentityHeaderTransform.cs), der Client
    kann ihn nicht faelschen.

    Der User-Agent wird sofort zu einer groben Geraetekategorie verdichtet; der
    Rohwert wird nicht weitergereicht und nicht gespeichert. Die IP-Adresse wird
    gar nicht mehr angefasst, und eine Kennung der Person oder des Browsers haelt
    das Ereignis seit #446 auch nicht mehr fest.
    """
    logger.debug(f"Tracking usage for content {content_id}")
    # Rate-Limit (#352): angemeldet je Kennung, sonst je Adresse (derive_client_key,
    # ein prozesslokaler Hash, der nirgends gespeichert wird).
    angemeldet = aufrufer and aufrufer != ANONYM
    if await limiter.is_rate_limited(
        f"user:{aufrufer}" if angemeldet else derive_client_key(request)
    ):
        raise HTTPException(status_code=429, detail="Too many copies. Please wait.")
    try:
        # Validate content_id format
        try:
            content_uuid = uuid.UUID(content_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid content ID format")

        service = get_usage_service()

        # Den Beitrag gibt es wirklich? Sonst zaehlte ein alter Link eine Nutzung
        # auf eine ID, hinter der nichts steht. Ist er da, aber unlesbar, wird im
        # Zweifel gezaehlt - wem er gehoert, ist dann nicht feststellbar.
        try:
            beitrag = await laden(content_uuid)
        except BeitragUnlesbar:
            beitrag = None
            unlesbar = True
        else:
            unlesbar = False

        if beitrag is None and not unlesbar:
            raise HTTPException(status_code=404, detail="Content not found")

        # Die eigene Kopie: nicht zaehlen, aber auch kein Fehler - das Frontend hat
        # nichts falsch gemacht, es hat nur nichts zu melden.
        if (
            beitrag is not None
            and aufrufer
            and aufrufer != ANONYM
            and beitrag.original_author == aufrufer
        ):
            logger.debug(f"Own content {content_id} copied by its author, not counted")
            return TrackUsageResponse(
                success=True,
                message="Own content is not counted",
                usage_count=service.get_content_usage(content_id),
            )

        # Ein Startkonto vergibt keine Nutzung (GLOSSARY.md "Startkonto", #352): weder
        # in Meine Beitraege, der Rueckmeldung beim Anmelden, "Diese Woche oft genutzt"
        # oder den Punkten. Wie die eigene Kopie kein Fehler.
        # ANNAHME (#352): auch nicht am Zaehler der Karte, der sonst jede Nutzung
        # zaehlt; "vergibt keine Nutzung" gilt dort ebenso.
        if settings.ist_startkonto(aufrufer):
            logger.debug(f"Content {content_id} copied by a Startkonto, not counted")
            return TrackUsageResponse(
                success=True,
                message="Usage by a Startkonto is not counted",
                usage_count=service.get_content_usage(content_id),
            )

        # Ohne geltende Art.-9-Einwilligung (#559) zaehlt die Kopie am Zaehler der
        # Karte - Kopieren ist Lesen und bleibt offen (#556 F489-2) -, aber es
        # entsteht nichts, was ihr Konto mit dem Beitrag verbindet: kein Pruefwert
        # (also keine entdoppelte Nutzung und keine Wirkung fuer die Autorin) und
        # kein Paar-Pruefwert fuer die Muster-Hinweise.
        eingewilligt = bool(angemeldet) and await _eingewilligt(aufrufer)

        # User-Agent hier verdichten, nicht weiter unten: ab dieser Zeile
        # existiert der Rohwert im weiteren Ablauf nicht mehr.
        device_category = derive_device_category(user_agent)

        # Fassungen hat nur der Kommentar. Bei einem unlesbaren Beitrag ist der Typ
        # unbekannt: Dann zaehlt die Nutzung, aber keine Fassung.
        fassung = (
            body.fassung.value
            if body.fassung
            and beitrag is not None
            and beitrag.content_type == ContentType.COMMENTARY
            else None
        )

        # Ein Zeitpunkt fuer Pruefwert, seinen Tag und die Muster-Hinweise: Sonst
        # gehoerten sie kurz vor Mitternacht (UTC) zu verschiedenen Tagen.
        jetzt = datetime.now(timezone.utc)

        # Entdoppelung fuer Punkte und "oft genutzt" (#352): angemeldet je Kennung,
        # sonst je Besuchermerkmal (#446), je Beitrag und UTC-Tag. Ein Konto ohne
        # Einwilligung bekommt keinen (#559).
        if not angemeldet:
            wert = pruefwert(aufrufer, besucher_merkmal(request), content_uuid, jetzt)
        elif eingewilligt:
            wert = pruefwert(aufrufer, None, content_uuid, jetzt)
        else:
            wert = None

        # Track usage
        logger.debug(f"Calling usage service for content {content_id}")
        success = service.track_content_usage(
            content_id=str(content_uuid),
            device_category=device_category,
            fassung=fassung,
            pruefwert=wert,
            tag=jetzt.date(),
        )

        if not success:
            logger.error(f"Failed to track usage for content {content_id}")
            raise HTTPException(status_code=500, detail="Failed to track usage")

        # Fuer die Muster-Hinweise (#352), nur mit Punkten. Ein Fehler hier kostet
        # die Nutzung nicht, sie ist schon gezaehlt. Kein Depends: Ohne Punkte soll
        # der Dienst gar nicht erst entstehen.
        # Erkannt wird gegenseitige Nutzung innerhalb von MUSTER_FENSTER_TAGE (sieben)
        # Tagen; gemerkt wird dafuer nur ein Paar-Pruefwert mit einem Schluessel im
        # Speicher (services/entdoppelung.py, DSFA Risiko 2).
        # Ein Muster-Hinweis nennt beide Konten: Er steht im Wortlaut der Einwilligung
        # "Punkte und Meilensteine" (#351), nicht mehr in der Art.-9-Einwilligung. Haben
        # nicht beide sie gegeben (oder hat eine widerrufen), keine Meldung - sonst
        # ergaebe ein frueherer Paar-Pruefwert noch einen Hinweis mit ihrer Kennung.
        if (
            settings.punkte_aktiv
            and angemeldet
            and beitrag is not None
            and await _punkte_eingewilligt(aufrufer)
            and await _punkte_eingewilligt(beitrag.original_author)
        ):
            try:
                await asyncio.to_thread(
                    get_muster_hinweise_service().nutzung_melden,
                    aufrufer,
                    beitrag.original_author,
                    jetzt,
                )
            except Exception as e:
                logger.error(
                    f"Pattern check for content {content_id} failed: {type(e).__name__}"
                )

        # Get updated count
        usage_count = service.get_content_usage(content_id)
        logger.info(
            f"Successfully tracked usage for content {content_id}, new count: {usage_count}"
        )

        return TrackUsageResponse(
            success=True, message="Usage tracked successfully", usage_count=usage_count
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error tracking usage for content {content_id}: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/content/{content_id}/usage", response_model=Dict[str, int])
async def get_content_usage(
    content_id: str, settings: Settings = Depends(get_settings)
):
    """
    Get the usage count for a specific content item.
    """
    try:
        # Validate content_id format
        try:
            uuid.UUID(content_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid content ID format")

        service = get_usage_service()
        usage_count = service.get_content_usage(content_id)

        return {"usage_count": usage_count}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting usage for content {content_id}: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/me/usage-stats", response_model=UserUsageStatsResponse)
async def eigene_nutzungsstatistik(
    current_user: str = Depends(require_user),
):
    """
    Wie oft andere die Beitraege der angemeldeten Person genutzt haben.

    Die Person kommt aus ``X-User`` (gesetzt vom BFF), nicht aus dem Pfad: ein Pfad
    mit Kennung stuende im Zugriffslog jedes Webservers davor (#284).
    """
    try:
        service = get_usage_service()
        stats = await service.get_user_usage_stats(current_user)

        return UserUsageStatsResponse(**stats)

    except Exception as e:
        logger.error(
            f"Nutzungsstatistik fuer {log_pseudonym(current_user)} nicht geladen: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


class PunkteStatusResponse(BaseModel):
    """Welche Schalter der Punkte an sind (``GET /punkte/status``)."""

    aktiv: bool
    abzeichen_sichtbar: bool


@router.get("/punkte/status", response_model=PunkteStatusResponse)
async def punkte_status(settings: Settings = Depends(get_settings)):
    """
    Ob die Punkte eingeschaltet sind (``SEMANTIC_SEARCH_PUNKTE_AKTIV``) und ob andere
    Angemeldete Abzeichen sehen koennen (beide Schalter, ``Settings.abzeichen_sichtbar``).
    Ohne Anmeldung lesbar und ohne Personenbezug: Das Frontend fragt hier einmal und ruft
    punkte, meilensteine und abzeichen-sichtbarkeit nur bei eingeschaltetem Schalter auf,
    statt deren 404 abzuwarten (UX-Review B20, Entscheidung Maintainer 13.11.2026).
    """
    return PunkteStatusResponse(
        aktiv=settings.punkte_aktiv,
        abzeichen_sichtbar=settings.abzeichen_sichtbar,
    )


@router.get("/users/me/punkte", response_model=PunkteResponse)
async def eigene_punkte(
    current_user: str = Depends(require_user),
    settings: Settings = Depends(get_settings),
    service: PunkteService = Depends(get_punkte_service),
):
    """
    Die Punkte der angemeldeten Person, je Stufe und gesamt (#352). Nur die Person
    selbst sieht sie; Ranglisten kommen spaeter mit eigenem Opt-in.

    Ohne ``punkte_aktiv`` 404: Die Funktion gibt es dann nicht. Die Person kommt aus
    ``X-User``, nicht aus dem Pfad (#284).
    """
    if not settings.punkte_aktiv:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        stand = await service.punkte(current_user)
    except Exception as e:
        logger.error(
            f"Punkte fuer {log_pseudonym(current_user)} nicht berechnet: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
    return PunkteResponse(
        tun=stand.tun,
        quests=stand.quests,
        wirkung=stand.wirkung,
        gesamt=stand.gesamt,
        sammelt=stand.sammelt,
    )


@router.get("/users/me/meilensteine", response_model=MeilensteineResponse)
async def eigene_meilensteine(
    current_user: str = Depends(require_user),
    settings: Settings = Depends(get_settings),
    service: MeilensteineService = Depends(get_meilensteine_service),
):
    """
    Die Meilensteine der angemeldeten Person (#351), fuer "Meine Beitraege". Nur die
    Person selbst sieht sie; ein Abzeichen fuer andere braucht eine eigene Zustimmung
    zur Sichtbarkeit, die es noch nicht gibt (ADR 0004).

    Wie die Punkte hinter ``punkte_aktiv`` (sonst 404): Beide stuetzen sich auf
    dieselbe Einwilligung und dieselbe DSFA. Die Person kommt aus ``X-User``.
    """
    if not settings.punkte_aktiv:
        raise HTTPException(status_code=404, detail="Not found")
    try:
        meilensteine = await service.meilensteine(current_user)
    except Exception as e:
        logger.error(
            f"Meilensteine fuer {log_pseudonym(current_user)} nicht berechnet: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
    return MeilensteineResponse(
        meilensteine=[
            MeilensteinResponse(
                kennung=m.kennung,
                name=m.name,
                untertitel=m.untertitel,
                beschreibung=m.beschreibung,
                bild=m.bild,
                bildnachweis=m.bildnachweis,
                art=m.art,
                schwelle=m.schwelle,
                stand=m.stand,
                erreicht=m.erreicht,
            )
            for m in meilensteine
        ]
    )


def _abzeichen_dienst(
    settings: Settings = Depends(get_settings),
) -> AbzeichenService:
    """Ohne beide Schalter 404: Sichtbare Abzeichen gibt es dann nicht (#351)."""
    dienst = get_abzeichen_service()
    if not settings.abzeichen_sichtbar or dienst is None:
        raise HTTPException(status_code=404, detail="Not found")
    return dienst


@router.get(
    "/users/me/abzeichen-sichtbarkeit", response_model=AbzeichenSichtbarkeitResponse
)
async def abzeichen_sichtbarkeit(
    current_user: str = Depends(require_user),
    dienst: AbzeichenService = Depends(_abzeichen_dienst),
):
    """
    Die Antwort der Person auf die Frage, ob andere Angemeldete ihre
    Meilenstein-Abzeichen sehen (#351, GLOSSARY.md "Zustimmung zur Sichtbarkeit").
    """
    try:
        antwort = await asyncio.to_thread(dienst.sichtbarkeit, current_user)
    except Exception as e:
        logger.error(
            f"Sichtbarkeit fuer {log_pseudonym(current_user)} nicht gelesen: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
    return AbzeichenSichtbarkeitResponse(
        gefragt=antwort is not None,
        zeigen=antwort.zeigen if antwort else None,
        aktueller_wortlaut=SichtbarkeitWortlaut(
            kennung=SICHTBARKEIT_WORTLAUT,
            text=SICHTBARKEIT_WORTLAUTE[SICHTBARKEIT_WORTLAUT],
            mehr_dazu=SICHTBARKEIT_MEHR_DAZU[SICHTBARKEIT_WORTLAUT],
        ),
    )


@router.put("/users/me/abzeichen-sichtbarkeit", status_code=204)
async def abzeichen_sichtbarkeit_antworten(
    request: AbzeichenSichtbarkeitRequest,
    current_user: str = Depends(require_user),
    dienst: AbzeichenService = Depends(_abzeichen_dienst),
):
    """
    Ja oder Nein zur Sichtbarkeit, jederzeit aenderbar. Ein Nein nimmt das Abzeichen
    sofort weg. Ohne Art.-9-Einwilligung offen wie jedes Zuruecknehmen; ein Ja zeigt
    dann nichts, weil es ohne sie keine Meilensteine gibt.
    """
    try:
        await dienst.antworten(current_user, request.zeigen, request.wortlaut)
    except UnbekannterWortlaut:
        raise HTTPException(status_code=422, detail="Unbekannter Wortlaut")
    except Exception as e:
        logger.error(
            f"Sichtbarkeit fuer {log_pseudonym(current_user)} nicht gespeichert: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
    return Response(status_code=204)


def _punkte_einwilligung_angeboten(
    settings: Settings = Depends(get_settings),
) -> None:
    """Ohne punkte_aktiv 404: Dann gibt es nichts, wozu man einwilligen koennte."""
    if not settings.punkte_aktiv:
        raise HTTPException(status_code=404, detail="Not found")


@router.get("/users/me/punkte-einwilligung", response_model=PunkteEinwilligungResponse)
async def punkte_einwilligung(
    current_user: str = Depends(require_user),
    _angeboten: None = Depends(_punkte_einwilligung_angeboten),
):
    """
    Die Einwilligung "Punkte und Meilensteine" der Person (#351) und der Wortlaut
    fuers Haekchen. Nichts ist vorausgewaehlt: ``eingewilligt`` ist False, bis die
    Person selbst einwilligt.
    """
    try:
        stand = await asyncio.to_thread(
            get_punkte_einwilligung_repository().lesen, current_user
        )
    except Exception as e:
        logger.error(
            f"Einwilligung Punkte fuer {log_pseudonym(current_user)} nicht gelesen: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
    return PunkteEinwilligungResponse(
        eingewilligt=stand is not None and stand.gilt,
        wortlaut=stand.wortlaut if stand else None,
        aktueller_wortlaut=PunkteEinwilligungWortlaut(
            kennung=PUNKTE_WORTLAUT, text=PUNKTE_WORTLAUTE[PUNKTE_WORTLAUT]
        ),
    )


@router.put("/users/me/punkte-einwilligung", status_code=204)
async def punkte_einwilligung_antworten(
    request: PunkteEinwilligungRequest,
    current_user: str = Depends(require_user),
    _angeboten: None = Depends(_punkte_einwilligung_angeboten),
):
    """
    Einwilligen oder widerrufen, jederzeit. Einwilligen geht nur zu einem geltenden
    Wortlaut. Ein Widerruf wirkt sofort: Punkte und Meilensteine werden je Abruf
    berechnet und fragen die Einwilligung; das Abzeichen am Namen verschwindet.
    """
    if request.wortlaut not in PUNKTE_WORTLAUTE or (
        request.eingewilligt and request.wortlaut not in PUNKTE_GELTENDE_WORTLAUTE
    ):
        raise HTTPException(status_code=422, detail="Unbekannter Wortlaut")
    try:
        await asyncio.to_thread(
            get_punkte_einwilligung_repository().antworten,
            current_user,
            request.eingewilligt,
            request.wortlaut,
        )
    except Exception as e:
        logger.error(
            f"Einwilligung Punkte fuer {log_pseudonym(current_user)} nicht gespeichert: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
    if not request.eingewilligt:
        # Ohne Meilensteine kein Abzeichen: sofort weg, nicht erst im naechsten Takt.
        dienst = get_abzeichen_service()
        if dienst is not None:
            dienst.vergessen(current_user)
    return Response(status_code=204)


@router.post("/users/me/besuch", response_model=BesuchResponse)
async def besuch(
    current_user: str = Depends(require_user),
    einwuerfe: EinwurfRepository = Depends(get_einwurf_repository),
    gesehen: GeseheneNutzungRepository = Depends(get_gesehene_nutzung_repository),
    unbeantwortete: UnbeantworteteAussagenService = Depends(
        get_unbeantwortete_aussagen_service
    ),
):
    """
    Ein Besuch der angemeldeten Person: wie oft ihre Beitraege seitdem genutzt
    wurden, fuer die Rueckmeldung beim Anmelden (#349). Das Frontend ruft ihn einmal je
    Anmeldung und zeigt die Rueckmeldung nur bei mehr als 0.

    POST, weil der Aufruf den gezeigten Stand fortschreibt; ein zweiter Aufruf
    direkt danach liefert 0. Die Person kommt aus ``X-User``, nicht aus dem Pfad (#284).
    """
    # Alle drei Zahlen zugleich: Einwuerfe und Luecken haben eine Zeitgrenze, die
    # Nutzung nicht; scheitert sie, ist der Besuch gescheitert (500).
    try:
        anzahl, neu, wartend = await asyncio.gather(
            get_usage_service().nutzung_seit_letztem_besuch(current_user),
            _hoechstens(
                _neue_einwuerfe(current_user, einwuerfe, gesehen), 0, "Neue Einwuerfe"
            ),
            _hoechstens(_unbeantwortete_aussagen(unbeantwortete), 0, "Unbeantwortete"),
        )
    except Exception as e:
        logger.error(
            f"Besuch von {log_pseudonym(current_user)} nicht erfasst: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
    return BesuchResponse(
        nutzung_seit_letztem_besuch=anzahl,
        neue_einwuerfe=neu,
        unbeantwortete_aussagen=wartend,
        unbeantwortete_aussagen_mehr=wartend >= LIMIT_STANDARD,
    )


async def _hoechstens(aufruf, ersatz: int, was: str) -> int:
    """
    ``aufruf`` mit Zeitgrenze (BESUCH_NEBENZAHLEN_TIMEOUT_S); danach ``ersatz``.
    Ein schon laufender Datenbankaufruf im Thread laeuft zu Ende, die Antwort wartet
    nur nicht mehr darauf.
    """
    try:
        return await asyncio.wait_for(aufruf, timeout=BESUCH_NEBENZAHLEN_TIMEOUT_S)
    except asyncio.TimeoutError:
        logger.warning(f"{was} beim Besuch nicht rechtzeitig gezaehlt")
        return ersatz


async def _neue_einwuerfe(
    person: str, einwuerfe: EinwurfRepository, gesehen: GeseheneNutzungRepository
) -> int:
    """
    Neue Einwuerfe anderer seit dem letzten Besuch, als Zaehlerstand wie die Nutzung.
    Scheitert das, bleibt es bei 0: Die Rueckmeldung zur Nutzung soll daran nicht
    haengen.
    """
    try:
        jetzt, offen = await asyncio.gather(
            asyncio.to_thread(einwuerfe.count_von_anderen, person),
            asyncio.to_thread(einwuerfe.count_von_anderen, person, nur_offene=True),
        )
        neu = await asyncio.to_thread(
            gesehen.neue_einwuerfe_seit_letztem_besuch, person, jetzt
        )
        # Der Stand zaehlt alle Zustaende; angezeigt werden hoechstens so viele, wie
        # im Fangkorb noch Arbeit sind, sonst stuende "3 neue" vor einer leeren Liste.
        return max(0, min(neu, offen))
    except Exception as e:
        logger.warning(
            f"Neue Einwuerfe fuer {log_pseudonym(person)} nicht gezaehlt: {type(e).__name__}"
        )
        return 0


async def _unbeantwortete_aussagen(dienst: UnbeantworteteAussagenService) -> int:
    """
    Wie viele Aussagen "Hier fehlt eine Antwort" zeigt: dieselbe Liste und damit
    dieselbe Sichtbarkeit (auch die der Vormoderation, sobald es sie gibt). Bei einem
    Fehler 0.
    """
    try:
        return len(await dienst.liste(mit_themen=False))
    except Exception as e:
        logger.warning(f"Unbeantwortete Aussagen nicht gezaehlt: {type(e).__name__}")
        return 0


def _gepostet_dienst(
    current_user: str = Depends(require_user),
    settings: Settings = Depends(get_settings),
) -> GepostetService:
    """
    Ohne ``gepostet_aktiv`` und fuer Startkonten 404: Die Rueckmeldung gibt es dann
    nicht (#643). Vor der Art.-9-Pruefung, damit ein ausgeschalteter Schalter die
    Datenbank nicht fragt.
    """
    if not settings.gepostet_aktiv or settings.ist_startkonto(current_user):
        raise HTTPException(status_code=404, detail="Not found")
    return get_gepostet_service()


@router.get("/users/me/gepostet", response_model=GepostetResponse)
async def gepostet_stand(
    current_user: str = Depends(require_user),
    dienst: GepostetService = Depends(_gepostet_dienst),
    _einwilligung: None = Depends(require_art9_einwilligung),
):
    """
    Ob die Rueckmeldung "Gepostet?" angeboten wird (200) und wie viele Personen diese
    Woche gemeldet haben. 404 ohne Schalter, 403 ohne Art.-9-Einwilligung; das
    Frontend zeigt "Ja, gepostet" nur nach einer 200.
    """
    try:
        anzahl = await asyncio.to_thread(dienst.diese_woche)
    except Exception as e:
        logger.error(
            f"Gepostet-Stand fuer {log_pseudonym(current_user)} nicht gelesen: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
    return GepostetResponse(personen_diese_woche=anzahl)


@router.post("/users/me/gepostet", response_model=GepostetResponse)
async def gepostet_melden(
    current_user: str = Depends(require_user),
    dienst: GepostetService = Depends(_gepostet_dienst),
    _einwilligung: None = Depends(require_art9_einwilligung),
):
    """
    "Ja, gepostet" nach dem Kopieren (#643): zaehlt die Person einmal je
    Kalenderwoche als "oeffentlich gekontert", ohne Beitrag und ohne festzuhalten,
    wer es war (services/gepostet_service.py). Ein zweiter Klick in derselben Woche
    aendert die Zahl nicht. Die Person kommt aus ``X-User``, nicht aus dem Pfad (#284).
    """
    try:
        anzahl = await asyncio.to_thread(dienst.melden, current_user)
    except Exception as e:
        logger.error(
            f"Gepostet von {log_pseudonym(current_user)} nicht gemerkt: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")
    return GepostetResponse(personen_diese_woche=anzahl)


@router.get("/trending", response_model=TrendingContentResponse)
async def get_trending_content(
    limit: int = 10, settings: Settings = Depends(get_settings)
):
    """
    Get currently trending content based on recent usage.
    """
    try:
        if limit < 1 or limit > 50:
            raise HTTPException(
                status_code=400, detail="Limit must be between 1 and 50"
            )

        service = get_usage_service()
        trending = service.get_trending_content(limit=limit)

        return TrendingContentResponse(trending=trending)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting trending content: {type(e).__name__}", exc_info=True
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/trending/woche", response_model=OftGenutztResponse)
async def oft_genutzt(
    aufrufer: Aufrufer = Depends(get_aufrufer),
    settings: Settings = Depends(get_settings),
    reference_service: ReferenceService = Depends(get_reference_service),
    varianten: VariantenRepository = Depends(get_varianten_repository),
):
    """
    "Diese Woche oft genutzt" auf der Startseite (#364): die sichtbaren Beitraege
    mit der meisten Nutzung der letzten sieben Tage, als Karten wie bei
    /content/recent. Leer, wenn zu wenige oft genug genutzt wurden; dann zeigt die
    Startseite den Bereich gar nicht.

    Unter /trending, weil das BFF diesen Pfad schon fuer Besucher freigibt
    (EndpointPolicy.cs). Je Beitrag das Response-DTO seines Typs, aufbereitet mit
    ``fuer_aufrufer``: Besucher sehen weder Anzeigenamen noch Kennungen.
    """
    from repositories.implementations.qdrant.qdrant_repository_factory import (
        QdrantRepositoryFactory,
    )

    try:
        usage_service = get_usage_service()
        service = OftGenutztService(
            usage_service,
            # Im try gebaut: Scheitert das Repository, antwortet der Endpunkt mit
            # seinem 500 und Log (wie get_beitrag_laden in dependencies.py).
            sichtbaren_beitrag_laden(
                settings,
                get_content_repository(settings),
                QdrantRepositoryFactory(),
                reference_service,
            ),
        )
        angereichert = usage_service.enrich_content_with_usage(
            await service.beitraege()
        )
        # result_type und recent_uses gehoeren nicht zum Beitrag und kommen
        # danach wieder dazu. Die Antwort je Typ: dtos/beitragstypen.py; ein Typ
        # ohne Eintrag bekommt die allgemeine Auswahl.
        antworten = fuer_aufrufer(
            # Vor fuer_aufrufer: Die Guete laesst die Stimme des Autors aus (#427).
            await guete_ergaenzen(
                [
                    ANTWORT_JE_TYP.get(
                        e["result_type"], BeitragResponse
                    ).model_validate(e)
                    for e in angereichert
                ]
            ),
            aufrufer,
        )
        varianten_ergaenzen(antworten, varianten)
        return OftGenutztResponse(
            results=[
                {
                    **antwort.model_dump(mode="json"),
                    "result_type": e["result_type"],
                    "recent_uses": e["recent_uses"],
                }
                for e, antwort in zip(angereichert, antworten)
            ]
        )

    except Exception as e:
        logger.error(f"Error getting oft genutzt: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/cleanup/status", response_model=CleanupStatusResponse)
async def get_cleanup_status(
    current_user: Optional[str] = Depends(get_current_user_optional),
    settings: Settings = Depends(get_settings),
):
    """
    Get the status of the usage data cleanup service.
    Admin only endpoint.
    """
    try:
        # Check if user is admin (simplified check)
        if not settings.is_admin_user(current_user):
            raise HTTPException(status_code=403, detail="Admin access required")

        cleanup_service = get_bereinigungsjob()
        status = cleanup_service.get_status()

        return CleanupStatusResponse(**status)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cleanup status: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/cleanup/run", response_model=CleanupResultResponse)
async def run_cleanup_manually(
    days_to_keep: int = 90,
    current_user: Optional[str] = Depends(get_current_user_optional),
    settings: Settings = Depends(get_settings),
):
    """
    Manually trigger cleanup of old usage data.
    Admin only endpoint.

    Args:
        days_to_keep: Number of days of data to retain (default 90)
    """
    try:
        # Check if user is admin
        if not settings.is_admin_user(current_user):
            raise HTTPException(status_code=403, detail="Admin access required")

        # Validate days_to_keep
        if days_to_keep < 1 or days_to_keep > 365:
            raise HTTPException(
                status_code=400, detail="days_to_keep must be between 1 and 365"
            )

        logger.info(
            f"Manual cleanup triggered by {log_pseudonym(current_user)} with {days_to_keep} days retention"
        )

        # Run cleanup
        service = get_usage_service()
        deleted_count = service.cleanup_old_events(days_to_keep)

        return CleanupResultResponse(
            success=True,
            deleted_count=deleted_count,
            message=f"Successfully deleted {deleted_count} old usage events",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running manual cleanup: {type(e).__name__}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
