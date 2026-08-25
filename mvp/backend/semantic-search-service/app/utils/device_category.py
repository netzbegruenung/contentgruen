"""
Ableitung der Geraetekategorie aus dem User-Agent.

Warum ueberhaupt eine Ableitung: bis hierher landete der vollstaendige
User-Agent-String (bis zu 500 Zeichen) in ``usage_events``. Gelesen hat ihn nie
eine Abfrage. Was an ihm interessiert, ist hoechstens die grobe Frage "Handy oder
Rechner" -- und die passt in ein Wort. Der Rohwert verlaesst diese Funktion
nicht; der Aufrufer bekommt nur die Kategorie und schreibt nur die.

Bewusst ohne Fremdbibliothek: fuer vier Kategorien braucht es keinen
User-Agent-Parser, und jede weitere Abhaengigkeit will gepflegt werden.

Bekannte Grenze: iPadOS meldet sich seit Version 13 in der Standardeinstellung
als "Macintosh; Intel Mac OS X". Solche Anfragen zaehlen hier als ``desktop``.
Das laesst sich serverseitig nicht aufloesen und ist der Grund, warum die
Kategorie eine grobe Angabe ist und keine Geraetestatistik.
"""

from typing import Optional

MOBILE = "mobile"
TABLET = "tablet"
DESKTOP = "desktop"
UNKNOWN = "unknown"

#: Alle Werte, die diese Funktion zurueckgeben kann. Die Spalte
#: usage_events.device_category ist VARCHAR(20); der laengste Wert hat 7 Zeichen.
CATEGORIES = frozenset({MOBILE, TABLET, DESKTOP, UNKNOWN})

# Reihenfolge zaehlt: Tablet-Kennungen zuerst, weil iPad-Strings auch "Safari"
# und teils "Mobile" enthalten und sonst als Handy durchgingen.
_TABLET_MARKERS = (
    "ipad",
    "tablet",
    "playbook",
    "kindle",
    "silk",
    "nexus 7",
    "nexus 10",
    "sm-t",  # Samsung-Tab-Reihe
)

_MOBILE_MARKERS = (
    "iphone",
    "ipod",
    "windows phone",
    "iemobile",
    "blackberry",
    "bb10",
    "opera mini",
    "opera mobi",
    "webos",
    "palm",
    "mobile",  # deckt "Android ... Mobile Safari" und Firefox Mobile ab
)

_DESKTOP_MARKERS = (
    "windows nt",
    "macintosh",
    "mac os x",
    "cros",  # ChromeOS
    "x11",
    "wayland",
)


def derive_device_category(user_agent: Optional[str]) -> str:
    """
    Die grobe Geraetekategorie zu einem User-Agent.

    Args:
        user_agent: Rohwert des User-Agent-Headers, oder None

    Returns:
        "mobile", "tablet", "desktop" oder "unknown" -- nie etwas anderes.
        Leere, fehlende und unverstaendliche Eingaben ergeben "unknown".
    """
    if not isinstance(user_agent, str):
        return UNKNOWN

    ua = user_agent.strip().lower()
    if not ua:
        return UNKNOWN

    if any(marker in ua for marker in _TABLET_MARKERS):
        return TABLET

    # Android ohne "Mobile" ist per Konvention ein Tablet -- so unterscheidet
    # Google selbst, und mehr Signal gibt der String nicht her.
    if "android" in ua:
        return MOBILE if "mobile" in ua else TABLET

    if any(marker in ua for marker in _MOBILE_MARKERS):
        return MOBILE

    if any(marker in ua for marker in _DESKTOP_MARKERS):
        return DESKTOP

    return UNKNOWN
