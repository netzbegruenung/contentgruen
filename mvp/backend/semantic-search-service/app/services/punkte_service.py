"""
Der Punktestand einer Person (ADR 0004, GLOSSARY.md "Punkte", #352).

Punkte werden bei jedem Abruf aus dem Bestand berechnet und nicht gespeichert. Damit
verlieren gesperrte und endgueltig entfernte Beitraege ihre Punkte von selbst: Sie
stehen nicht mehr unter den sichtbaren Beitraegen der Person. Es gibt auch keine
Tabelle mit Punkten, die Fristen braeuchte.

Woher die drei Stufen kommen:
- Wirkung: die entdoppelte Nutzung der sichtbaren Beitraege (usage_tracking,
  services/entdoppelung.py) und die Zustimmung anderer zu ihnen. Eigene Stimmen und
  die von Startkonten zaehlen nicht; Ablehnung zieht nichts ab.
- Tun: je sichtbarem Beitrag, der mindestens BEITRAG_WARTEZEIT alt ist, und je
  Einwurf der Person, der ebenso lange in einem nicht gesperrten Beitrag
  ausformuliert ist; je Tag gedeckelt.
- Quests: ANNAHME (#352): gibt es noch nicht; die Stufe bleibt 0, bis sie kommen.
  Gewicht und Deckel stehen schon in der Konfiguration, weil ADR 0004 alle drei
  Stufen dort verlangt.

Ein Startkonto sammelt keine Punkte.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Protocol, Set

from core.config import Settings
from domain.punkte import Punktegewichte, Punktestand, Wirkungsdaten, punkte_berechnen

BEITRAG_WARTEZEIT = timedelta(days=3)
"""
Ein Beitrag bringt Punkte fuers Tun erst, wenn er so lange steht (ADR 0004).
ANNAHME (#352): "drei Tage ohne Sperre" heisst: heute sichtbar und mindestens drei
Tage alt. Eine Sperre, die vorher schon wieder aufgehoben wurde, zaehlt nicht.
"""

SichtbareBeitraege = Callable[[str], Awaitable[List[Any]]]
"""Die sichtbaren Beitraege einer Person (ohne Aussagen und Herkuenfte), mit id und created."""


class NutzungsQuelle(Protocol):
    def get_nutzung_entdoppelt_batch(
        self, content_ids: List[Any]
    ) -> Dict[str, int]: ...


class StimmenUndEinwuerfe(Protocol):
    def zustimmungen(self, content_ids: List[Any], ausgenommen: Set[str]) -> int: ...

    def einwuerfe_ausformuliert_je_tag(
        self, user_id: str, bis: datetime
    ) -> Dict[date, int]: ...


def gewichte_aus(settings: Settings) -> Punktegewichte:
    return Punktegewichte(
        nutzung=settings.punkte_nutzung,
        zustimmung=settings.punkte_zustimmung,
        beitrag=settings.punkte_beitrag,
        einwurf_ausformuliert=settings.punkte_einwurf_ausformuliert,
        deckel_tun_je_tag=settings.punkte_deckel_tun_je_tag,
        quest=settings.punkte_quest,
        deckel_quests_je_tag=settings.punkte_deckel_quests_je_tag,
    )


def _je_tag(tage: Iterable[date]) -> Dict[date, int]:
    zaehler: Dict[date, int] = {}
    for tag in tage:
        zaehler[tag] = zaehler.get(tag, 0) + 1
    return zaehler


class PunkteService:
    def __init__(
        self,
        sichtbare_beitraege: SichtbareBeitraege,
        nutzung: NutzungsQuelle,
        stimmen_und_einwuerfe: StimmenUndEinwuerfe,
        settings: Settings,
        jetzt: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self._sichtbare_beitraege = sichtbare_beitraege
        self._nutzung = nutzung
        self._stimmen_und_einwuerfe = stimmen_und_einwuerfe
        self._settings = settings
        self._jetzt = jetzt

    async def punkte(self, user_id: str) -> Punktestand:
        gewichte = gewichte_aus(self._settings)
        if self._settings.ist_startkonto(user_id):
            return punkte_berechnen(Wirkungsdaten(), gewichte)

        beitraege = await self._sichtbare_beitraege(user_id)
        ids = [b.id for b in beitraege]
        nutzung = sum(self._nutzung.get_nutzung_entdoppelt_batch(ids).values())
        zustimmungen = self._stimmen_und_einwuerfe.zustimmungen(
            ids, {user_id} | set(self._settings.startkonto_kennungen())
        )
        grenze = self._jetzt() - BEITRAG_WARTEZEIT
        stehende = [
            b.created.astimezone(timezone.utc).date()
            for b in beitraege
            if b.created.astimezone(timezone.utc) <= grenze
        ]
        daten = Wirkungsdaten(
            nutzungen=nutzung,
            zustimmungen=zustimmungen,
            beitraege_je_tag=_je_tag(stehende),
            einwuerfe_ausformuliert_je_tag=(
                self._stimmen_und_einwuerfe.einwuerfe_ausformuliert_je_tag(
                    user_id, bis=grenze
                )
            ),
        )
        return punkte_berechnen(daten, gewichte)
