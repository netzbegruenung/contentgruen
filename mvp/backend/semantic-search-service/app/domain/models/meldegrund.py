"""
Meldegruende: warum jemand einen Beitrag meldet (Glossar „Meldegrund“).

Die einzige Liste im Suchdienst; Schema der Melde-Route und ModerationService
pruefen beide gegen sie. Gespeicherte Meldungen tragen den Wert als freien Text,
ein Wert darf deshalb nicht umbenannt oder entfernt werden, solange Meldungen
mit ihm in der Datenbank liegen. Das Frontend fuehrt dieselben Werte mit ihrer
Beschriftung in ``shared/meldegruende.ts``; test_moderation_meldegrund.py gleicht beide ab.
"""

from typing import Literal, get_args

Meldegrund = Literal[
    "spam",
    "inappropriate",
    # Erfunden oder sachlich falsch (#423): erfundene Erlebnisse oder Zahlen
    # nennt docs/VISION.md ausdruecklich als Meldegrund.
    "fabricated_or_false",
    "duplicate",
    # Rechtswidriger Inhalt (#438): Art. 16 Abs. 2 lit. a DSA verlangt dafuer eine
    # begruendete Erlaeuterung, deshalb ist die Beschreibung hier Pflicht.
    "illegal_content",
    "other",
]

MELDEGRUENDE: tuple[str, ...] = get_args(Meldegrund)

RECHTSWIDRIGER_INHALT = "illegal_content"


def beschreibung_fehlt(reason: str, description: str | None) -> bool:
    """Ob eine Meldung wegen rechtswidrigen Inhalts ohne Begruendung kommt."""
    return reason == RECHTSWIDRIGER_INHALT and not (description or "").strip()
