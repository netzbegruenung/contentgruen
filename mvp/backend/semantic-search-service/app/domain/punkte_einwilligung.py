"""
Die Einwilligung "Punkte und Meilensteine" (GLOSSARY.md "Einwilligung Punkte und
Meilensteine", ADR 0004, #351).

Eine eigene, freiwillige Einwilligung nach Art. 9 Abs. 2 lit. a DSGVO, getrennt von der
Art.-9-Einwilligung zur Mitwirkung: Punkte, Meilensteine (auch Wegmarken) und
Muster-Hinweise braucht niemand zum Beitragen. Hingen sie an der Einwilligung, ohne
die man nicht beitragen kann, waere die Kopplung vermutlich unfreiwillig (Art. 7
Abs. 4, ErwG 43; Entscheidung des Maintainers 13.11.2026 nach juristischer
Vorpruefung). Angeboten wird ein Haekchen, nichts ist vorausgewaehlt; der Widerruf
geht jederzeit, danach wird nichts mehr berechnet. Das Abzeichen am Namen bleibt eine
dritte, eigene Zustimmung (domain/abzeichen_sichtbarkeit.py).

Der Wortlaut traegt eine Kennung (Stand-Datum) wie die Art.-9-Einwilligung; wer ihn
aendert, legt eine neue Kennung an und laesst die alte stehen. Es gilt eine
Einwilligung nur zu einem geltenden Wortlaut.
"""

from typing import Dict, FrozenSet

AKTUELLER_WORTLAUT = "2026-11-13"

# ANNAHME (13.11.2026): Entwurf, geht noch zur Freigabe; erst mit punkte_aktiv gezeigt.
WORTLAUTE: Dict[str, str] = {
    "2026-11-13": (
        "Freiwillig: Ich willige ausdrücklich ein, dass Gut gesagt aus meiner Mitwirkung "
        "Punkte und Meilensteine (z. B. „Erster Einwurf“, „10-mal genutzt“) berechnet, "
        "die nur ich sehe, und dass die Admins einen Hinweis bekommen, wenn sich zwei "
        "Konten auffällig oft gegenseitig nutzen (Art. 9 Abs. 2 lit. a DSGVO). Ohne "
        "diese Einwilligung kann ich genauso beitragen und bewerten. Ich kann sie "
        "jederzeit unter „Datenschutz-Einstellungen“ widerrufen; danach wird nichts mehr "
        "berechnet."
    ),
}

# Zu welchen Wortlauten eine Einwilligung gilt; eine neue Fassung mit mehr Zwecken
# fragt neu, indem sie die alte hier herausnimmt.
GELTENDE_WORTLAUTE: FrozenSet[str] = frozenset({"2026-11-13"})


class UnbekannterWortlaut(ValueError):
    """Die Kennung gehoert zu keinem bekannten Wortlaut."""
