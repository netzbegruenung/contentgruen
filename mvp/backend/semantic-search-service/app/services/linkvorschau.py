"""
Die Angaben fuer die Linkvorschau in Messengern (#360), als Stueck HTML fuer index.html.

Crawler von WhatsApp, Signal und Co. fuehren kein JavaScript aus und sehen nur das
ausgelieferte index.html. Der nginx im Frontend-Image setzt fuer /beitrag/<id> und
/result per SSI dieses Stueck an die Stelle der allgemeinen Angaben
(nginx.conf, nginx.docker.conf, Block "linkvorschau_allgemein" in src/index.html).

Hier stehen nur die Angaben, die sich je Seite aendern: og:title, og:description,
twitter:description und, fuer einen Beitrag, og:url. Bild, Seitenname und Typ bleiben
die aus index.html. Nichts zur Person: kein Name, kein Anzeigename der Autorin.

Jeder Wert steht in einem Attribut und ist mit html.escape (quote=True) maskiert,
also auch " und '. Titel und Suchtext kommen von Nutzenden.
"""

import html
from typing import Optional
from urllib.parse import unquote_plus

# Die allgemeine Beschreibung aus src/index.html (freigegeben am 14.11.2026, E4); dass
# beide gleich sind, prueft scripts/tests/test_vorschau_tags.py.
ALLGEMEINE_BESCHREIBUNG = (
    "Gute Antworten gegen Stimmungsmache im Netz. Finden, kopieren, posten."
)

# WhatsApp zeigt etwa zwei Zeilen Beschreibung, Google kuerzt bei rund 160 Zeichen.
BESCHREIBUNG_HOECHSTENS = 180
# Titel eines Kommentars haben hoechstens 120 Zeichen, die eines Bildes 200
# (CODING_STANDARDS.md, Titel); laengere kuerzt die Vorschau, sie verwirft sie nicht.
TITEL_HOECHSTENS = 200
SUCHTEXT_HOECHSTENS = 80
ERGEBNIS_PRAEFIX = "Antworten auf: "
AUSLASSUNG = "…"


def einzeilig(text: Optional[str]) -> str:
    """Zeilenumbrueche, Tabulatoren und Steuerzeichen zu einfachen Leerzeichen."""
    if not text:
        return ""
    ohne_steuerzeichen = "".join(
        " " if ord(zeichen) < 32 or ord(zeichen) == 127 else zeichen for zeichen in text
    )
    return " ".join(ohne_steuerzeichen.split())


def kuerzen(text: str, hoechstens: int) -> str:
    """``text`` auf hoechstens ``hoechstens`` Zeichen samt Auslassungszeichen, an
    einer Wortgrenze; ein einzelnes zu langes Wort wird hart geschnitten."""
    if len(text) <= hoechstens:
        return text
    platz = hoechstens - len(AUSLASSUNG)
    schnitt = text[: platz + 1]
    grenze = schnitt.rfind(" ")
    if grenze > platz // 2:
        schnitt = schnitt[:grenze]
    else:
        schnitt = text[:platz]
    return schnitt.rstrip(" ,;:-–—.") + AUSLASSUNG


def _meta(art: str, name: str, inhalt: str) -> str:
    return f'<meta {art}="{name}" content="{html.escape(inhalt, quote=True)}">'


def _tags(titel: str, beschreibung: str, adresse: Optional[str] = None) -> str:
    zeilen = [
        _meta("property", "og:title", titel),
        _meta("property", "og:description", beschreibung),
        _meta("name", "twitter:description", beschreibung),
    ]
    if adresse:
        zeilen.append(_meta("property", "og:url", adresse))
    return "\n".join(zeilen) + "\n"


def beitrag_tags(
    titel: Optional[str], text: Optional[str], beitrag_adresse: Optional[str]
) -> Optional[str]:
    """Die Angaben fuer einen sichtbaren Beitrag, oder None ohne Titel.

    ``text`` ist der Text, ueber den der Beitrag gefunden wird: beim Kommentar die
    Mittelfassung, beim Bild die Unterschrift. Ohne Text gilt die allgemeine
    Beschreibung.
    """
    titel = kuerzen(einzeilig(titel), TITEL_HOECHSTENS)
    if not titel:
        return None
    beschreibung = kuerzen(einzeilig(text), BESCHREIBUNG_HOECHSTENS)
    return _tags(titel, beschreibung or ALLGEMEINE_BESCHREIBUNG, beitrag_adresse)


def suchtext_aus_adresse(roh: Optional[str]) -> str:
    """Den Suchtext aus dem Wert von ``searchQuery``, so wie er in der Adresse steht
    (Prozent-Kodierung, ``+`` als Leerzeichen). nginx reicht ihn unveraendert weiter;
    Starlette liest Header als Latin-1, die Bytes sind aber UTF-8."""
    if not roh:
        return ""
    try:
        roh = roh.encode("latin-1").decode("utf-8")
    except UnicodeError:
        pass
    return unquote_plus(roh, encoding="utf-8", errors="replace")


def ergebnis_tags(suchtext: Optional[str]) -> Optional[str]:
    """Die Angaben fuer die Ergebnisseite, oder None ohne Suchtext."""
    suchtext = kuerzen(einzeilig(suchtext), SUCHTEXT_HOECHSTENS)
    if not suchtext:
        return None
    return _tags(ERGEBNIS_PRAEFIX + suchtext, ALLGEMEINE_BESCHREIBUNG)


def beitrag_adresse(app_url: Optional[str], beitrag_id: str) -> Optional[str]:
    """Die kanonische Adresse eines Beitrags, ohne ``app_url`` keine."""
    if not app_url:
        return None
    return f"{app_url.rstrip('/')}/beitrag/{beitrag_id}"
