"""
Die Güte eines Beitrags (GLOSSARY.md "Güte", "Siegel"; #427).

Die Güte ist eine Zahl von 1 bis 10 aus zwei Teilen:

- dem **Kriterienanteil**: was das Gegenlesen (#358) am Beitrag findet, 10 minus die
  Gewichte der Anmerkungen (services/gegenlesen/gegenlesen_service.py);
- dem **Stimmenanteil**: der Anteil der Stimmen „hilfreich“ unter den Stimmen anderer,
  auf 1 bis 10 gestreckt.

Stimmen zählen erst ab einer Mindestzahl verschiedener Stimmender (DSFA, Maßnahme M5):
Darunter ließe sich aus einer Änderung der Güte ablesen, wie eine einzelne Person
gestimmt hat. Ihr Gewicht wächst mit der Zahl der Stimmen, bleibt aber unter einer
Obergrenze, damit gute Formulierung sichtbar bleibt und eine Gruppe, die sich abspricht,
einen schwachen Text nicht ganz nach oben trägt. Die Nutzung fließt nicht ein.

Ohne Kriterienanteil (das Sprachmodell fehlt, oder es gibt keinen Text) und ohne genug
Stimmen hat ein Beitrag keine Güte: Er ist „neu“, das Siegel grau und waagrecht.

Hier steht nur die Rechnung; die Werte kommen aus der Konfiguration (core/config.py,
``guete_*``), die Zahlen aus services/guete_service.py.
"""

import math
from dataclasses import dataclass
from typing import Optional

GUETE_MIN = 1
GUETE_MAX = 10


@dataclass(frozen=True)
class Guetegewichte:
    """Wie die Stimmen in die Güte eingehen; aus der Konfiguration."""

    #: Ab so vielen verschiedenen Stimmenden zählen Stimmen überhaupt (M5).
    stimmen_ab: int = 3
    #: Höchstens dieser Anteil der Güte kommt aus den Stimmen (0 bis 1).
    stimmen_gewicht_max: float = 0.6
    #: Bei so vielen Stimmen erreicht ihr Gewicht die Hälfte der Obergrenze.
    stimmen_halbwert: int = 5


@dataclass(frozen=True)
class Guete:
    #: 1–10; None = „neu“, ohne Daten.
    wert: Optional[int]
    #: Ob Stimmen eingegangen sind (genug Stimmende, M5).
    stimmen_zaehlen: bool


def _runden(x: float) -> int:
    # Kaufmännisch statt Pythons round(): 8,5 wird 9, nicht 8.
    return int(math.floor(x + 0.5))


def guete_berechnen(
    kriterien: Optional[int],
    hilfreich: int,
    nicht_hilfreich: int,
    gewichte: Guetegewichte = Guetegewichte(),
) -> Guete:
    """
    Die Güte aus dem Kriterienanteil und den Stimmen anderer.

    ``hilfreich`` und ``nicht_hilfreich`` sind schon gefiltert: ohne Startkonten und
    ohne die eigene Stimme der Person, die den Beitrag geschrieben hat.
    """
    stimmen = hilfreich + nicht_hilfreich
    zaehlen = stimmen >= max(1, gewichte.stimmen_ab)
    if not zaehlen:
        return Guete(wert=kriterien, stimmen_zaehlen=False)

    stimmenanteil = GUETE_MIN + (GUETE_MAX - GUETE_MIN) * hilfreich / stimmen
    if kriterien is None:
        wert = stimmenanteil
    else:
        gewicht = (
            gewichte.stimmen_gewicht_max
            * stimmen
            / (stimmen + max(1, gewichte.stimmen_halbwert))
        )
        wert = (1 - gewicht) * kriterien + gewicht * stimmenanteil
    return Guete(
        wert=min(GUETE_MAX, max(GUETE_MIN, _runden(wert))), stimmen_zaehlen=True
    )
