"""
Kennungen der Wortlaute des CC0-Hinweises (#431).

Jedes Formular, das etwas fuer andere sichtbar speichert, zeigt den CC0-Hinweis
(Frontend: ``shared/consent-hinweis.ts``) und schickt die Kennung des gezeigten
Wortlauts mit. Gespeichert wird sie an Beitrag, Satz und Einwurf, damit spaeter
nachvollziehbar ist, welchem Wortlaut jemand zugestimmt hat. Die Wortlaute selbst
stehen in ``docs/CC0_HINWEIS_WORTLAUTE.md``. Ein geaenderter Wortlaut bekommt eine
neue Kennung; die alten bleiben hier stehen, damit gespeicherte Kennungen lesbar
bleiben.

Bestand von vor #431 hat keine Kennung (None). Eine Anfrage ohne Kennung (aeltere
App im Browser-Cache) wird angenommen und ohne Kennung gespeichert, eine
unbekannte abgewiesen.
"""

from typing import Annotated, Optional

from pydantic import AfterValidator

# Laenge der Spalte in PostgreSQL (raw_inputs, raw_input_drafts).
CC0_WORTLAUT_MAX = 64

CC0_WORTLAUTE = frozenset(
    {
        "2026-10-29-formular",
        "2026-10-29-satz",
    }
)


def _bekannter_wortlaut(kennung: Optional[str]) -> Optional[str]:
    if kennung is not None and kennung not in CC0_WORTLAUTE:
        raise ValueError(f"Unbekannter Wortlaut des CC0-Hinweises: {kennung}")
    return kennung


Cc0Wortlaut = Annotated[Optional[str], AfterValidator(_bekannter_wortlaut)]
