"""
Schalter mit Obergrenze und Admin-Wert (#708, GLOSSARY.md "Schalter").

Die Umgebungsvariable (``SEMANTIC_SEARCH_PUNKTE_AKTIV`` usw., ``core/config.py``) ist
die Obergrenze, der Admin-Wert liegt in der Tabelle ``schalter``. Wirksam ist ein
Schalter nur, wenn beide an sind; ohne Admin-Wert gilt aus. So kann auf Prod nichts
angehen, was der Server nicht erlaubt (etwa Punkte ohne beschlossene DSFA), und ein
Admin kann ohne Rollout ein- und ausschalten.

Alle Stellen im Code fragen ``schalter_wirksam``, nicht die Settings direkt. Die
Admin-Werte liest der Dienst mit kurzem Cache (``CACHE_SEKUNDEN``); eine Aenderung
ueber ``setzen`` gilt in diesem Prozess sofort, in anderen nach dem Cache. Ist die
Datenbank nicht erreichbar, gilt aus (wie ohne Eintrag), bis der naechste Versuch
gelingt.
"""

import threading
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from core.config import Settings, settings as globale_settings
from core.logging import get_logger

logger = get_logger(__name__)

CACHE_SEKUNDEN = 45.0

DSFA_HINWEIS = (
    "Vor dem Einschalten auf Prod: DSFA beschlossen (docs/DSFA.md Abschnitt 7)"
)


@dataclass(frozen=True)
class Schalterart:
    name: str
    # Feld in Settings, das die Obergrenze traegt
    feld: str
    umgebungsvariable: str
    erklaerung: str
    dsfa_hinweis: bool = False


SCHALTER: Dict[str, Schalterart] = {
    s.name: s
    for s in (
        Schalterart(
            name="punkte",
            feld="punkte_aktiv",
            umgebungsvariable="SEMANTIC_SEARCH_PUNKTE_AKTIV",
            erklaerung=(
                "Punkte, Meilensteine und die Einwilligung dazu für Mitwirkende, "
                "dazu die Muster-Hinweise für Admins."
            ),
            dsfa_hinweis=True,
        ),
        Schalterart(
            name="abzeichen_sichtbar",
            feld="abzeichen_sichtbar_aktiv",
            umgebungsvariable="SEMANTIC_SEARCH_ABZEICHEN_SICHTBAR_AKTIV",
            erklaerung=(
                "Meilenstein-Abzeichen am Anzeigenamen, die andere Angemeldete sehen; "
                "wirkt nur zusammen mit den Punkten, erscheint spätestens nach 15 Minuten."
            ),
            dsfa_hinweis=True,
        ),
        Schalterart(
            name="gepostet",
            feld="gepostet_aktiv",
            umgebungsvariable="SEMANTIC_SEARCH_GEPOSTET_AKTIV",
            erklaerung=(
                "Rückfrage „Ja, gepostet“ nach dem Kopieren und die Zahl je Woche "
                "in der Übersicht."
            ),
        ),
    )
}


class UnbekannterSchalter(KeyError):
    pass


class ObergrenzeAus(RuntimeError):
    """Einschalten ueber die Obergrenze hinaus: der Server erlaubt es nicht."""


@dataclass(frozen=True)
class Schalterstand:
    name: str
    erklaerung: str
    umgebungsvariable: str
    obergrenze: bool
    admin_wert: bool
    wirksam: bool
    dsfa_hinweis: Optional[str]


class SchalterService:
    def __init__(
        self,
        admin_werte_lesen: Callable[[], Dict[str, bool]],
        admin_wert_setzen: Callable[[str, bool, str], None],
        cache_sekunden: float = CACHE_SEKUNDEN,
        uhr: Callable[[], float] = time.monotonic,
    ):
        self._lesen = admin_werte_lesen
        self._setzen = admin_wert_setzen
        self._cache_sekunden = cache_sekunden
        self._uhr = uhr
        self._werte: Optional[Dict[str, bool]] = None
        self._gelesen_um = 0.0
        self._sperre = threading.Lock()

    def admin_werte(self) -> Dict[str, bool]:
        """Admin-Werte mit Cache; synchron (kurze Abfrage hoechstens je Cache-Dauer)."""
        with self._sperre:
            if (
                self._werte is not None
                and self._uhr() - self._gelesen_um < self._cache_sekunden
            ):
                return self._werte
            try:
                self._werte = dict(self._lesen())
            except Exception as e:
                logger.error(
                    f"Schalter nicht gelesen, gelten als aus: {type(e).__name__}",
                    exc_info=True,
                )
                self._werte = {}
            self._gelesen_um = self._uhr()
            return self._werte

    def admin_wert(self, name: str) -> bool:
        return bool(self.admin_werte().get(name, False))

    def wirksam(self, name: str, einstellungen: Settings) -> bool:
        art = _art(name)
        an = bool(getattr(einstellungen, art.feld)) and self.admin_wert(name)
        if name == "abzeichen_sichtbar":
            # Ohne Punkte keine sichtbaren Abzeichen (wie Settings.abzeichen_sichtbar)
            return an and self.wirksam("punkte", einstellungen)
        return an

    def stand(self, einstellungen: Settings) -> List[Schalterstand]:
        return [
            Schalterstand(
                name=art.name,
                erklaerung=art.erklaerung,
                umgebungsvariable=art.umgebungsvariable,
                obergrenze=bool(getattr(einstellungen, art.feld)),
                admin_wert=self.admin_wert(art.name),
                wirksam=self.wirksam(art.name, einstellungen),
                dsfa_hinweis=DSFA_HINWEIS if art.dsfa_hinweis else None,
            )
            for art in SCHALTER.values()
        ]

    def setzen(self, name: str, an: bool, admin: str, einstellungen: Settings) -> None:
        """Admin-Wert setzen. Ausschalten geht immer, Einschalten nur unter der Obergrenze."""
        art = _art(name)
        if an and not getattr(einstellungen, art.feld):
            raise ObergrenzeAus(name)
        self._setzen(name, an, admin)
        with self._sperre:
            self._werte = None


def _art(name: str) -> Schalterart:
    try:
        return SCHALTER[name]
    except KeyError:
        raise UnbekannterSchalter(name)


def _aus_datenbank() -> SchalterService:
    from repositories.schalter_repository import get_schalter_repository

    return SchalterService(
        admin_werte_lesen=lambda: get_schalter_repository().admin_werte(),
        admin_wert_setzen=lambda n, a, w: get_schalter_repository().setzen(n, a, w),
    )


_service: Optional[SchalterService] = None


def get_schalter_service() -> SchalterService:
    global _service
    if _service is None:
        _service = _aus_datenbank()
    return _service


def schalter_service_setzen(service: Optional[SchalterService]) -> None:
    """Fuer Tests: einen eigenen Dienst einsetzen (None: wieder aus der Datenbank)."""
    global _service
    _service = service


def schalter_wirksam(name: str, einstellungen: Optional[Settings] = None) -> bool:
    """Ob der Schalter wirkt: Obergrenze aus ``einstellungen`` (sonst global) und Admin-Wert."""
    return get_schalter_service().wirksam(
        name, einstellungen if einstellungen is not None else globale_settings
    )
