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
        # Variante B (#559): nennt die Zwecke aus docs/DSFA.md Abschnitt 4:
        # Punkte, Level, Quests und Meilenstein-Abzeichen (fuer andere Angemeldete nur
        # mit gesonderter Zustimmung), Freischaltungen und die Muster-Hinweise. Zweiter
        # Wortlaut vom selben Tag, deshalb mit Suffix. Vor dem Merge noch zweimal
        # geaendert (Level, Freischaltungen, Abzeichen nur mit Zustimmung); die Kennung
        # blieb, weil sie nie auf main und in keinem Release war.
        "2026-11-05-b": (
            "Ich willige ausdrücklich ein, dass Gut gesagt meine Mitwirkung "
            "verarbeitet, auch wenn sich daraus auf meine politische Meinung "
            "schließen lässt (Art. 9 Abs. 2 lit. a DSGVO). Das betrifft Beiträge, "
            "Einwürfe, Sätze und Bewertungen, die ich mit meinem Konto speichere, "
            "und meinen Anzeigenamen daran. Beiträge sind für alle sichtbar, mein "
            "Anzeigename nur für Angemeldete. Gut gesagt nutzt meine Mitwirkung "
            "nur für den Betrieb der Plattform. Dazu gehören ein Punktestand, ein "
            "Level, Quests und Meilenstein-Abzeichen, die nur ich sehe, solange "
            "ich nicht gesondert zustimme, sie anderen Angemeldeten zu zeigen; "
            "neue Aktionen, die ein höheres Level freischaltet; und ein Hinweis an "
            "die Admins, wenn zwei Konten sich auffällig oft gegenseitig nutzen. "
            "Gut gesagt wertet meine Mitwirkung nicht nach politischer Haltung aus "
            "und gibt sie nicht an Dritte weiter. Ich kann die Einwilligung "
            "jederzeit im Profilmenü unter „Einwilligung“ widerrufen. Danach kann "
            "ich nichts mehr beitragen oder bewerten; was ich schon gespeichert "
            "habe, bleibt, bis ich es lösche oder mein Konto löschen lasse. Was "
            "bis zum Widerruf geschehen ist, bleibt rechtmäßig."
        ),
        # Redaktionell (#644): Der Menuepunkt heisst jetzt „Datenschutz-Einstellungen“;
        # nur der Name des Widerrufswegs ist neu, Zwecke und Folgen sind wortgleich mit
        # 2026-11-05-b. Neue Kennung, weil 2026-11-05-b schon in v0.8.1 war. Wer
        # 2026-11-05-b zugestimmt hat, wird nicht neu gefragt (docs/ART9_EINWILLIGUNG.md).
        "2026-11-10": (
            "Ich willige ausdrücklich ein, dass Gut gesagt meine Mitwirkung "
            "verarbeitet, auch wenn sich daraus auf meine politische Meinung "
            "schließen lässt (Art. 9 Abs. 2 lit. a DSGVO). Das betrifft Beiträge, "
            "Einwürfe, Sätze und Bewertungen, die ich mit meinem Konto speichere, "
            "und meinen Anzeigenamen daran. Beiträge sind für alle sichtbar, mein "
            "Anzeigename nur für Angemeldete. Gut gesagt nutzt meine Mitwirkung "
            "nur für den Betrieb der Plattform. Dazu gehören ein Punktestand, ein "
            "Level, Quests und Meilenstein-Abzeichen, die nur ich sehe, solange "
            "ich nicht gesondert zustimme, sie anderen Angemeldeten zu zeigen; "
            "neue Aktionen, die ein höheres Level freischaltet; und ein Hinweis an "
            "die Admins, wenn zwei Konten sich auffällig oft gegenseitig nutzen. "
            "Gut gesagt wertet meine Mitwirkung nicht nach politischer Haltung aus "
            "und gibt sie nicht an Dritte weiter. Ich kann die Einwilligung "
            "jederzeit im Profilmenü unter „Datenschutz-Einstellungen“ widerrufen. "
            "Danach kann "
            "ich nichts mehr beitragen oder bewerten; was ich schon gespeichert "
            "habe, bleibt, bis ich es lösche oder mein Konto löschen lasse. Was "
            "bis zum Widerruf geschehen ist, bleibt rechtmäßig."
        ),
        # Folgen des Widerrufs (juristische Vorpruefung vom 12.11.2026, Art. 17 Abs. 1
        # lit. b DSGVO): Der Widerruf loescht die Bewertungen
        # (Art9EinwilligungService.widerrufen). Zwecke und Datenarten wie 2026-11-10;
        # die Aenderung wirkt nur zugunsten der Person, deshalb keine neue Frage
        # (docs/ART9_EINWILLIGUNG.md).
        "2026-11-12": (
            "Ich willige ausdrücklich ein, dass Gut gesagt meine Mitwirkung "
            "verarbeitet, auch wenn sich daraus auf meine politische Meinung "
            "schließen lässt (Art. 9 Abs. 2 lit. a DSGVO). Das betrifft Beiträge, "
            "Einwürfe, Sätze und Bewertungen, die ich mit meinem Konto speichere, "
            "und meinen Anzeigenamen daran. Beiträge sind für alle sichtbar, mein "
            "Anzeigename nur für Angemeldete. Gut gesagt nutzt meine Mitwirkung "
            "nur für den Betrieb der Plattform. Dazu gehören ein Punktestand, ein "
            "Level, Quests und Meilenstein-Abzeichen, die nur ich sehe, solange "
            "ich nicht gesondert zustimme, sie anderen Angemeldeten zu zeigen; "
            "neue Aktionen, die ein höheres Level freischaltet; und ein Hinweis an "
            "die Admins, wenn zwei Konten sich auffällig oft gegenseitig nutzen. "
            "Gut gesagt wertet meine Mitwirkung nicht nach politischer Haltung aus "
            "und gibt sie nicht an Dritte weiter. Ich kann die Einwilligung "
            "jederzeit im Profilmenü unter „Datenschutz-Einstellungen“ widerrufen. "
            "Danach kann ich nichts mehr beitragen oder bewerten, und meine "
            "Bewertungen werden gelöscht. Was ich sonst gespeichert habe, bleibt, "
            "bis ich es lösche oder mein Konto löschen lasse. Was bis zum Widerruf "
            "geschehen ist, bleibt rechtmäßig."
        ),
        # Folgen des Widerrufs nach dem Loeschauftrag (Entscheidung Maintainer,
        # 13.11.2026, DSFA R9b): Binnen sieben Tagen werden Beitraege, Einwuerfe und
        # Saetze von der Person geloest (services/loeschauftrag_service.py), nur was bis
        # zum Widerruf angelegt war. Sonst wortgleich mit 2026-11-12 (ein Test sichert
        # das). Die Folgen gehen weiter als bisher, deshalb fragt die App alle neu, die
        # einem frueheren Wortlaut zugestimmt haben (GELTENDE_WORTLAUTE).
        "2026-11-13": (
            "Ich willige ausdrücklich ein, dass Gut gesagt meine Mitwirkung "
            "verarbeitet, auch wenn sich daraus auf meine politische Meinung "
            "schließen lässt (Art. 9 Abs. 2 lit. a DSGVO). Das betrifft Beiträge, "
            "Einwürfe, Sätze und Bewertungen, die ich mit meinem Konto speichere, "
            "und meinen Anzeigenamen daran. Beiträge sind für alle sichtbar, mein "
            "Anzeigename nur für Angemeldete. Gut gesagt nutzt meine Mitwirkung "
            "nur für den Betrieb der Plattform. Dazu gehören ein Punktestand, ein "
            "Level, Quests und Meilenstein-Abzeichen, die nur ich sehe, solange "
            "ich nicht gesondert zustimme, sie anderen Angemeldeten zu zeigen; "
            "neue Aktionen, die ein höheres Level freischaltet; und ein Hinweis an "
            "die Admins, wenn zwei Konten sich auffällig oft gegenseitig nutzen. "
            "Gut gesagt wertet meine Mitwirkung nicht nach politischer Haltung aus "
            "und gibt sie nicht an Dritte weiter. Ich kann die Einwilligung "
            "jederzeit im Profilmenü unter „Datenschutz-Einstellungen“ widerrufen. "
            "Danach kann ich nichts mehr beitragen oder bewerten, und meine "
            "Bewertungen werden gelöscht. Innerhalb von sieben Tagen werden auch "
            "meine Beiträge, Einwürfe und Sätze von mir gelöst: Meine Beiträge "
            "bleiben stehen und zeigen „ehemalige Person“ statt meines Namens, "
            "meine Einwürfe werden gelöscht, und meine Sätze an Einwürfen anderer "
            "bleiben ohne meinen Namen. Was ich nach einer neuen Einwilligung "
            "beitrage, bleibt davon unberührt. Mein Konto bleibt. Was bis zum "
            "Widerruf geschehen ist, bleibt rechtmäßig."
        ),
        # Ohne Spielelemente (Entscheidung Maintainer, 13.11.2026, nach juristischer
        # Pruefung): Punktestand, Level, Quests, Freischaltungen und der Muster-Hinweis
        # gehoeren nicht in die Einwilligung, ohne die niemand beitragen kann
        # (ErwG 43 S. 2, Art. 7 Abs. 4 DSGVO); Punkte und Meilensteine bekommen eine
        # eigene, freiwillige Einwilligung (#668). Sonst wortgleich mit 2026-11-13 (ein
        # Test sichert das). Neue Kennung statt Ueberschreiben, weil 2026-11-13 seit
        # dem Merge von #661 in einem gebauten Image auf main steht. Nur dieser
        # Wortlaut zaehlt: Wer 2026-11-13 bestaetigt hat, bestaetigte die Spielelemente
        # mit und wird zum korrigierten Text neu gefragt.
        "2026-11-14": (
            "Ich willige ausdrücklich ein, dass Gut gesagt meine Mitwirkung "
            "verarbeitet, auch wenn sich daraus auf meine politische Meinung "
            "schließen lässt (Art. 9 Abs. 2 lit. a DSGVO). Das betrifft Beiträge, "
            "Einwürfe, Sätze und Bewertungen, die ich mit meinem Konto speichere, "
            "und meinen Anzeigenamen daran. Beiträge sind für alle sichtbar, mein "
            "Anzeigename nur für Angemeldete. Gut gesagt nutzt meine Mitwirkung "
            "nur für den Betrieb der Plattform, wertet sie nicht nach politischer "
            "Haltung aus und gibt sie nicht an Dritte weiter. Ich kann die "
            "Einwilligung "
            "jederzeit im Profilmenü unter „Datenschutz-Einstellungen“ widerrufen. "
            "Danach kann ich nichts mehr beitragen oder bewerten, und meine "
            "Bewertungen werden gelöscht. Innerhalb von sieben Tagen werden auch "
            "meine Beiträge, Einwürfe und Sätze von mir gelöst: Meine Beiträge "
            "bleiben stehen und zeigen „ehemalige Person“ statt meines Namens, "
            "meine Einwürfe werden gelöscht, und meine Sätze an Einwürfen anderer "
            "bleiben ohne meinen Namen. Was ich nach einer neuen Einwilligung "
            "beitrage, bleibt davon unberührt. Mein Konto bleibt. Was bis zum "
            "Widerruf geschehen ist, bleibt rechtmäßig."
        ),
    }
)

# Der Wortlaut, den die App heute zeigt.
AKTUELLER_WORTLAUT = "2026-11-14"

# Wortlaute, deren Einwilligung heute zaehlt. Eine Einwilligung zu einem anderen
# bekannten Wortlaut bleibt als Nachweis stehen und kann widerrufen werden, zaehlt
# aber nicht: Die App fragt neu (GET meldet eingewilligt=false), und was die
# Einwilligung verlangt, ist gesperrt, bis die Person dem aktuellen Wortlaut
# zustimmt. Bis 2026-11-12 galt jede Kennung (redaktionelle Aenderungen ohne neue
# Frage); 2026-11-13 erweitert die Folgen des Widerrufs, deshalb nur dieser
# (Entscheidung Maintainer, 13.11.2026, docs/ART9_EINWILLIGUNG.md). 2026-11-14 nimmt
# die Spielelemente heraus; nur er zaehlt, damit niemand sie mitbestaetigt.
GELTENDE_WORTLAUTE = frozenset({"2026-11-14"})


def bekannter_wortlaut(kennung: str) -> bool:
    return kennung in WORTLAUTE


def geltender_wortlaut(kennung: str) -> bool:
    return kennung in GELTENDE_WORTLAUTE
