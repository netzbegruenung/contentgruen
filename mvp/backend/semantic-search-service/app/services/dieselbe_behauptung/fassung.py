"""
Trifft die geänderte Fassung eines Beitrags noch dieselbe Behauptung wie die alte (#427)?

Stimmen bleiben, solange ein geänderter Beitrag dieselbe Behauptung trifft; ändert sich
der Sinn, verfallen sie. Die Behauptung eines Kommentars oder einer Hintergrundinfo ist
ihr Titel (GLOSSARY.md "Titel", CODING_STANDARDS.md): Verglichen werden alter und neuer
Titel. Eine Änderung nur am Text lässt die Behauptung stehen.

Entschieden wird mit derselben Funktion wie bei der Prüfung auf dieselbe Aussage
(stufe.dieselben_finden), mit der alten Fassung als einzigem Kandidaten und deren
query/query-Ähnlichkeit zur neuen als Score. So gelten Untergrenze, Vorprüfungen
(Fragen, Quantoren), beide Modelle und ihre Schwellen genau wie dort.
"""

from typing import Awaitable, Callable, NamedTuple, Optional

from core.config import Settings
from services.dieselbe_behauptung import stufe
from services.dieselbe_behauptung.nli_modell import NliPruefer
from utils.text_normalisierung import text_normalisiert

# query/query-Ähnlichkeit zweier Texte (Kosinus der normierten Einbettungen).
Aehnlichkeit = Callable[[str, str], Awaitable[float]]


class _Beobachteter:
    """Reicht Urteile des Bestaetigers durch und merkt sich, ob er keins hatte.

    stufe.dieselben_finden macht aus "Bestaetiger urteilt nicht" eine leere Liste:
    Fuer Aussagen ist das die sichere Seite (eine neue Aussage mehr). Hier hiesse
    leer "Stimmen verfallen", und Loeschen ist endgueltig; darum wird der Fall
    erkannt und als "niemand entscheidet" gemeldet.
    """

    def __init__(self, pruefer: NliPruefer):
        self._pruefer = pruefer
        self.ohne_urteil = False

    async def urteile(self, paare, warte_hoechstens=None):
        urteile = await self._pruefer.urteile(paare, warte_hoechstens=warte_hoechstens)
        if urteile is None:
            self.ohne_urteil = True
        return urteile


class _AlteFassung(NamedTuple):
    """Der eine Kandidat: stufe braucht von ihm nur Text und Score."""

    text: str
    score: float


async def gleiche_behauptung(
    alt: str,
    neu: str,
    nli: NliPruefer,
    bestaetiger: Optional[NliPruefer],
    settings: Settings,
    aehnlichkeit: Aehnlichkeit,
    warte_hoechstens: Optional[float] = None,
) -> Optional[bool]:
    """
    True, wenn die neue Fassung dieselbe Behauptung ist wie die alte (normalisiert
    gleich zählt immer), False, wenn nicht - auch ohne Modellurteil, wenn die alte
    Fassung unter der Untergrenze liegt oder eine Vorprüfung anschlägt (Frage gegen
    Behauptung, andere Quantoren), wie bei Aussagen. None, wenn ein Modell, das hätte
    urteilen sollen, nicht urteilen konnte: Dann entscheidet niemand, die Stimmen
    bleiben.
    """
    normalform = text_normalisiert(neu)
    if normalform and normalform == text_normalisiert(alt):
        return True
    score = await aehnlichkeit(alt, neu)
    beobachtet = _Beobachteter(bestaetiger) if bestaetiger is not None else None
    dieselben = await stufe.dieselben_finden(
        neu,
        [_AlteFassung(alt, score)],
        nli,
        beobachtet,
        settings,
        warte_hoechstens=warte_hoechstens,
    )
    if dieselben is None:
        return None
    if not dieselben and beobachtet is not None and beobachtet.ohne_urteil:
        return None
    return bool(dieselben)
