"""
Die Zustimmung zur Sichtbarkeit der Meilenstein-Abzeichen (#351, GLOSSARY.md
"Zustimmung zur Sichtbarkeit", ADR 0004 "Ranglisten nur mit Zustimmung").

Eine eigene Einwilligung neben der Art.-9-Einwilligung: Die Art.-9-Einwilligung deckt
Meilensteine nur fuer die Person selbst. Andere Angemeldete sehen das Abzeichen am
Anzeigenamen erst, wenn die Person hier zustimmt. Gefragt wird einmal mit zwei
gleichwertigen Knoepfen, nichts ist vorbelegt, die Antwort laesst sich jederzeit
aendern (docs/VISION.md "Ranglisten", docs/DSFA.md Abschnitt 3 Risiko 1).

Der Wortlaut traegt eine Kennung wie die Art.-9-Einwilligung (Stand-Datum); wer ihn
aendert, legt eine neue Kennung an und laesst die alte stehen.
"""

from typing import Dict

AKTUELLER_WORTLAUT = "2026-11-09-b"

# Die Frage selbst, kurz. Was eine informierte Einwilligung ausserdem braucht, steht je
# Kennung in MEHR_DAZU und erscheint aufklappbar direkt unter der Frage.
WORTLAUTE: Dict[str, str] = {
    "2026-11-09": (
        "Sollen andere Angemeldete an deinem Namen sehen, wie viele Meilensteine du "
        "erreicht hast? Das Abzeichen verrät, dass und wie viel du bei Gut gesagt "
        "mitmachst. Angemeldet sind nicht nur Mitglieder, und ein Screenshot kann es "
        "weitertragen. Besucher ohne Anmeldung sehen es nie. Du kannst das jederzeit "
        "unter „Meine Beiträge“ ändern; mehr in der Datenschutzerklärung unter „Punkte“."
    ),
    # Gekuerzt nach Entscheidung des Maintainers (09.11.2026); die Hinweise stehen
    # jetzt unter "Mehr dazu".
    "2026-11-09-b": (
        "Sollen andere Angemeldete an deinem Namen sehen, wie viele Meilensteine du "
        "erreicht hast? Besucher sehen es nie. Du kannst das jederzeit unter "
        "„Meine Beiträge“ ändern."
    ),
}

MEHR_DAZU: Dict[str, str] = {
    "2026-11-09": "",
    "2026-11-09-b": (
        "Das Abzeichen verrät, dass und wie viel du bei Gut gesagt mitmachst. "
        "Angemeldet sind nicht nur Mitglieder, und ein Screenshot kann es weitertragen. "
        "Mehr in der Datenschutzerklärung unter „Punkte“."
    ),
}


class UnbekannterWortlaut(ValueError):
    """Die Kennung gehoert zu keinem bekannten Wortlaut."""
