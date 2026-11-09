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
    gleich zählt immer), False, wenn nicht. None, wenn das Modell nicht urteilen
    konnte: Dann entscheidet niemand, und die Stimmen bleiben.
    """
    normalform = text_normalisiert(neu)
    if normalform and normalform == text_normalisiert(alt):
        return True
    score = await aehnlichkeit(alt, neu)
    dieselben = await stufe.dieselben_finden(
        neu,
        [_AlteFassung(alt, score)],
        nli,
        bestaetiger,
        settings,
        warte_hoechstens=warte_hoechstens,
    )
    if dieselben is None:
        return None
    return bool(dieselben)
