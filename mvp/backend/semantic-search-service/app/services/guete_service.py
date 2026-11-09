"""
Die Güte an Beiträgen, wie Karten sie im Siegel zeigen (#427; Rechnung: domain/guete.py).

Der Kriterienanteil kommt aus dem Gegenlesen (#358) über Titel und Text, ohne die
Aussage: Ein Beitrag kann auf mehrere Aussagen antworten, die Güte gehört aber zum
Beitrag. Die Regel „übernommene Schlüsselwörter“ prüft deshalb nur das Formular, das
die Aussage kennt. Das Ergebnis des Gegenlesens wird nicht gespeichert, nur im
Arbeitsspeicher je Titel und Text zwischengehalten.

Gezählt werden die Stimmen anderer: ohne Startkonten (#352) und ohne die Stimme der
Person, die den Beitrag geschrieben hat. Die Zähler an den Stimm-Knöpfen zeigen die
Summen ohne Startkonten, wie die Datenschutzerklärung sie nennt („andere sehen nur
Summen“). Einzelne Stimmen oder Kennungen gehen nie hinaus.

Fehlt das Sprachmodell oder antwortet die Datenbank nicht, bleibt die Karte ohne
Güte bzw. ohne Zähler; die Antwort scheitert daran nicht.
"""

import threading
from collections import OrderedDict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from core.logging import get_logger
from domain.guete import Guetegewichte, guete_berechnen
from domain.models.content_type import ContentType
from domain.models.vote import VoteType
from services.gegenlesen.gegenlesen_service import GEWICHTE, GegenlesenService

logger = get_logger(__name__)

#: So viele Ergebnisse des Gegenlesens hält der Prozess vor (je Titel und Text).
ZWISCHENSPEICHER_GROESSE = 4096

#: Titel, die beschreiben statt behaupten (CODING_STANDARDS.md, Titel): dort gilt die
#: Regel zur Verneinung nicht, wie im Formular.
_BESCHREIBENDE_TITEL = {ContentType.POST.value, ContentType.IMAGE.value}

#: Arten, die die Karte prüft. Die Schlüsselwörter brauchen die Aussage (siehe oben).
_KARTEN_ARTEN = [art for art in GEWICHTE if art != "schluesselwoerter"]

Kriterien = Tuple[Optional[int], List[str]]


def _typ(objekt: Any) -> str:
    typ = getattr(objekt, "content_type", None)
    return getattr(typ, "value", typ) or ""


class GueteService:
    def __init__(
        self,
        gegenlesen: GegenlesenService,
        vote_repository: Any,
        startkonten: Iterable[str] = (),
        gewichte: Guetegewichte = Guetegewichte(),
    ):
        self._gegenlesen = gegenlesen
        self._votes = vote_repository
        self._startkonten = frozenset(startkonten)
        self._gewichte = gewichte
        self._lock = threading.Lock()
        self._zwischenspeicher: "OrderedDict[Tuple[str, str, bool], Kriterien]" = (
            OrderedDict()
        )
        self._modell_fehlt_geloggt = False

    def kriterien(self, titel: str, text: str, behauptung: bool) -> Kriterien:
        """Kriterienanteil und die erfüllten Kriterien; (None, []) ohne Text oder Modell."""
        schluessel = ((titel or "").strip(), (text or "").strip(), behauptung)
        with self._lock:
            if schluessel in self._zwischenspeicher:
                self._zwischenspeicher.move_to_end(schluessel)
                return self._zwischenspeicher[schluessel]
        try:
            ergebnis = self._gegenlesen.gegenlesen(
                schluessel[0], schluessel[1], None, titel_ist_behauptung=behauptung
            )
        except (ImportError, OSError) as fehler:
            # Sprachmodell nicht installiert: Karten bleiben ohne Kriterienanteil.
            if not self._modell_fehlt_geloggt:
                self._modell_fehlt_geloggt = True
                logger.error("Guete ohne Gegenlesen: %s", type(fehler).__name__)
            return None, []
        if ergebnis.guete is None:
            kriterien: Kriterien = (None, [])
        else:
            gefunden = {a.art for a in ergebnis.anmerkungen}
            erfuellt = [
                art
                for art in _KARTEN_ARTEN
                if art not in gefunden and (behauptung or art != "verneinung")
            ]
            kriterien = (ergebnis.guete, erfuellt)
        with self._lock:
            self._zwischenspeicher[schluessel] = kriterien
            if len(self._zwischenspeicher) > ZWISCHENSPEICHER_GROESSE:
                self._zwischenspeicher.popitem(last=False)
        return kriterien

    def _stimmen(self, ids: List[Any]) -> Optional[Dict[str, List[Tuple[str, str]]]]:
        try:
            return self._votes.stimmen_je_beitrag(ids, self._startkonten)
        except Exception as fehler:
            logger.error("Guete ohne Stimmen: %s", type(fehler).__name__)
            return None

    def ergaenzen(self, objekte: Sequence[Any]) -> Sequence[Any]:
        """
        Setzt an jedem Beitrag ``guete``, ``guete_erfuellt``, ``guete_stimmen_zaehlen``
        und die Zähler ``stimmen_hilfreich``/``stimmen_nicht_hilfreich``.

        Vor ``fuer_aufrufer`` aufrufen: Danach ist ``original_author`` für alle außer
        Admins geleert, und die eigene Stimme ließe sich nicht mehr auslassen.
        """
        objekte = [o for o in objekte if getattr(o, "id", None) is not None]
        if not objekte:
            return objekte
        stimmen = self._stimmen([o.id for o in objekte])
        for objekt in objekte:
            kriterien, erfuellt = self.kriterien(
                getattr(objekt, "title", None) or "",
                getattr(objekt, "text", None) or "",
                _typ(objekt) not in _BESCHREIBENDE_TITEL,
            )
            hilfreich = nicht_hilfreich = 0
            fremd_hilfreich = fremd_nicht = 0
            autor = getattr(objekt, "original_author", None)
            for kennung, richtung in (stimmen or {}).get(str(objekt.id), []):
                ja = richtung == VoteType.LIKE.value
                hilfreich += ja
                nicht_hilfreich += not ja
                if kennung != autor:
                    fremd_hilfreich += ja
                    fremd_nicht += not ja
            guete = guete_berechnen(
                kriterien, fremd_hilfreich, fremd_nicht, self._gewichte
            )
            objekt.guete = guete.wert
            objekt.guete_erfuellt = erfuellt
            objekt.guete_stimmen_zaehlen = guete.stimmen_zaehlen
            if stimmen is not None:
                objekt.stimmen_hilfreich = hilfreich
                objekt.stimmen_nicht_hilfreich = nicht_hilfreich
        return objekte


async def guete_ergaenzen(objekte: List[Any]) -> List[Any]:
    """
    Die Güte an den Beiträgen einer Antwort ergänzen, vor ``fuer_aufrufer``.

    Das Gegenlesen rechnet auf der CPU, darum im Threadpool. Scheitert etwas, bleiben
    die Karten ohne Siegelwert („neu“) statt die Antwort scheitern zu lassen.
    """
    if not objekte:
        return objekte
    from fastapi.concurrency import run_in_threadpool

    from dependencies import get_guete_service

    try:
        await run_in_threadpool(get_guete_service().ergaenzen, objekte)
    except Exception as fehler:
        logger.error("Guete nicht ergaenzt: %s", type(fehler).__name__, exc_info=True)
    return objekte


async def als_responses_mit_guete(klasse, quellen, aufrufer) -> List[Any]:
    """Wie ``als_responses`` (services/beitrag_fuer_aufrufer.py), mit der Güte (#427)."""
    from services.beitrag_fuer_aufrufer import fuer_aufrufer

    objekte = [klasse.model_validate(quelle) for quelle in quellen]
    return list(fuer_aufrufer(await guete_ergaenzen(objekte), aufrufer))
