"""
Wortlaute der Art.-9-Einwilligung (#489): die eine Quelle im Repository.

Mitwirkung bei Gut gesagt kann auf eine politische Meinung schliessen lassen
(Art. 9 DSGVO, Lueckenliste D-N15). Rechtsgrundlage ist eine ausdrueckliche
Einwilligung beim ersten Anmelden (Art. 9 Abs. 2 lit. a), ein eigenes Haekchen,
getrennt von den Nutzungsbedingungen (Entscheidung Maintainer, 29.10. und
05.11.2026). Die App zeigt den Wortlaut von hier (GET /api/v1/art9-einwilligung)
und speichert zur Einwilligung den Zeitpunkt und die Kennung des gezeigten
Wortlauts.

Die Kennung ist das Stand-Datum des Wortlauts, ein zweiter Wortlaut vom selben Tag
bekommt ein Suffix (``-b``, ``-c`` ...). Ein geaenderter Wortlaut bekommt
eine neue Kennung und wird hier ergaenzt; alte bleiben stehen, damit jede
gespeicherte Kennung ihren Text behaelt. Ablauf: docs/ART9_EINWILLIGUNG.md.

Die Wortlaute vom 05.11.2026 sind vorlaeufig, bis die juristische Pruefung (#296)
sie bestaetigt oder ersetzt.
"""

from types import MappingProxyType
from typing import Mapping

# Laenge der Spalte in PostgreSQL (art9_einwilligungen.wortlaut).
WORTLAUT_KENNUNG_MAX = 64

WORTLAUTE: Mapping[str, str] = MappingProxyType(
    {
        "2026-11-05": (
            "Ich willige ausdrücklich ein, dass Gut gesagt meine Mitwirkung "
            "verarbeitet, auch wenn sich daraus auf meine politische Meinung "
            "schließen lässt (Art. 9 Abs. 2 lit. a DSGVO). Das betrifft Beiträge, "
            "Einwürfe, Sätze und Bewertungen, die ich mit meinem Konto speichere, "
            "und meinen Anzeigenamen daran. Beiträge sind für alle sichtbar, "
            "mein Anzeigename nur für Angemeldete. Gut gesagt nutzt meine "
            "Mitwirkung nur für den Betrieb der Plattform, wertet sie nicht nach "
            "politischer Haltung aus und gibt sie nicht an Dritte weiter. Ich kann die Einwilligung jederzeit im "
            "Profilmenü unter „Einwilligung“ widerrufen. Danach kann ich nichts "
            "mehr beitragen oder bewerten; was ich schon gespeichert habe, bleibt, "
            "bis ich es lösche oder mein Konto löschen lasse. Was bis zum Widerruf "
            "geschehen ist, bleibt rechtmäßig."
        ),
        # Variante B (#559): nennt die Zwecke aus docs/DSFA_PUNKTE.md Abschnitt 4:
        # Punkte, Level und Quests, Freischaltungen, Meilenstein-Abzeichen am
        # Anzeigenamen und die Muster-Hinweise. Zweiter Wortlaut vom selben Tag,
        # deshalb mit Suffix. Vor dem Merge noch einmal geaendert (Level,
        # Freischaltungen, Abzeichen fuer Angemeldete); die Kennung blieb, weil sie
        # nie auf main und in keinem Release war.
        "2026-11-05-b": (
            "Ich willige ausdrücklich ein, dass Gut gesagt meine Mitwirkung "
            "verarbeitet, auch wenn sich daraus auf meine politische Meinung "
            "schließen lässt (Art. 9 Abs. 2 lit. a DSGVO). Das betrifft Beiträge, "
            "Einwürfe, Sätze und Bewertungen, die ich mit meinem Konto speichere, "
            "und meinen Anzeigenamen daran. Beiträge sind für alle sichtbar, "
            "mein Anzeigename nur für Angemeldete. Gut gesagt nutzt meine "
            "Mitwirkung nur für den Betrieb der Plattform. Dazu gehören ein "
            "Punktestand, ein Level und Quests, die nur ich sehe, solange ich nicht "
            "gesondert zustimme, sie anderen zu zeigen; neue Aktionen, die ein "
            "höheres Level freischaltet; Meilenstein-Abzeichen an meinem "
            "Anzeigenamen, die nur Angemeldete sehen; und ein Hinweis an die Admins, "
            "wenn zwei Konten sich auffällig oft gegenseitig nutzen. Gut gesagt wertet meine Mitwirkung nicht nach "
            "politischer Haltung aus und gibt sie nicht an Dritte weiter. Ich kann "
            "die Einwilligung jederzeit im "
            "Profilmenü unter „Einwilligung“ widerrufen. Danach kann ich nichts "
            "mehr beitragen oder bewerten; was ich schon gespeichert habe, bleibt, "
            "bis ich es lösche oder mein Konto löschen lasse. Was bis zum Widerruf "
            "geschehen ist, bleibt rechtmäßig."
        ),
    }
)

# Der Wortlaut, den die App heute zeigt.
AKTUELLER_WORTLAUT = "2026-11-05-b"


def bekannter_wortlaut(kennung: str) -> bool:
    return kennung in WORTLAUTE
