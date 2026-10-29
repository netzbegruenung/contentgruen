"""
Meldegruende: warum jemand einen Beitrag meldet (Glossar „Meldegrund“).

Die einzige Liste im Suchdienst; Schema der Melde-Route und ModerationService
pruefen beide gegen sie. Gespeicherte Meldungen tragen den Wert als freien Text,
ein Wert darf deshalb nicht umbenannt oder entfernt werden, solange Meldungen
mit ihm in der Datenbank liegen. Das Frontend fuehrt dieselben Werte mit ihrer
Beschriftung in ``shared/meldegruende.ts``.
"""

from typing import Literal, get_args

Meldegrund = Literal[
    "spam",
    "inappropriate",
    # Erfunden oder sachlich falsch (#423): erfundene Erlebnisse oder Zahlen
    # nennt docs/VISION.md ausdruecklich als Meldegrund.
    "fabricated_or_false",
    "duplicate",
    "other",
]

MELDEGRUENDE: tuple[str, ...] = get_args(Meldegrund)
