from enum import Enum


class ContentStatus(Enum):
    """
    Zustand eines Beitrags (GLOSSARY.md, "Zustaende eines Beitrags"): sichtbar,
    gesperrt oder geloescht. Dazu kommen zwei Altwerte fuer Bilder ohne Unterschrift
    aus der Zeit, als ein Hintergrunddienst sie nachbeschrieb (bis #281). Das ist
    kein Bild im Sinne des Glossars ("Ein Bild mit Unterschrift") und damit kein
    Beitrag, den jemand finden kann. Neu angelegt werden sie nicht mehr: Ein Bild
    wird nur mit Unterschrift gespeichert (ADR 0003).

    Die Suche findet nur VISIBLE. Einzelansicht, Listen und "Meine Beitraege"
    blenden alles in AUSGEBLENDET aus (repositories/implementations/qdrant/
    base_repository.py). Altwerte aus der Zeit vor #214 stellt
    services/wartung/zustaende_umstellen.py um; bis dahin gilt der Uebergang unten.
    """

    VISIBLE = "visible"
    """Sichtbar: Alle Nutzenden, auch Besucher, koennen den Beitrag finden und kopieren."""

    BLOCKED = "blocked"
    """
    Gesperrt: Ein Admin hat den Beitrag aus Suche und Ansicht genommen, etwa nach
    einer Meldung. Er bleibt gespeichert und laesst sich entsperren; der Zustand
    von vor der Sperre steht dann im Payload-Feld status_vor_sperre
    (repositories/implementations/qdrant/moderation_repository.py).
    """

    DELETED = "deleted"
    """
    Geloescht: Der Autor hat den Beitrag entfernt
    (services/content/beitrag_loeschen_service.py). Er bleibt bis zu seiner
    Loeschfrist gespeichert (services/loeschfristen_service.py) und laesst sich
    nicht zurueckholen.
    """

    PENDING_DESCRIPTION = "pending_description"
    """Altwert: Bild ohne Unterschrift, das auf den frueheren Hintergrunddienst wartete."""

    DESCRIPTION_FAILED = "description_failed"
    """Altwert: Der fruehere Hintergrunddienst konnte keine Unterschrift erzeugen."""


NEW_CONTENT_STATUS = ContentStatus.VISIBLE
"""
Zustand, mit dem neue Beitraege angelegt werden - der eine Ort, an dem diese
Entscheidung faellt. Alle Anlagewege in api/v1 und Seeding beziehen sich
hierauf. Neue Beitraege sind sofort sichtbar.
"""

AUSGEBLENDET = frozenset(
    {
        ContentStatus.BLOCKED,
        ContentStatus.DELETED,
        ContentStatus.PENDING_DESCRIPTION,
        ContentStatus.DESCRIPTION_FAILED,
    }
)
"""
Zustaende, in denen ein Beitrag fuer Leser nicht da ist, auch nicht ueber seine ID.
Die beiden Altwerte fuer Bilder ohne Unterschrift gehoeren dazu: Das ist kein Bild,
und seit #281 holt es nichts mehr aus diesem Zustand.
"""

AUSGEBLENDET_WERTE = frozenset(status.value for status in AUSGEBLENDET)


# --- Uebergang bis zur Umstellung der Altwerte (#214) -------------------------------
# Zwischen dem Ausrollen und dem Lauf von scripts/manual/zustaende_umstellen.py stehen
# noch die Werte des frueheren CMS-Status im Suchindex. Damit in dieser Zeit weder das
# Lesen scheitert noch die Suche leer ist (und die Dublettenpruefung Aussagen doppelt
# anlegt), liest das Modell sie als sichtbar und die Suche findet, was sie vorher fand.
# Entfaellt, sobald die Umstellung auf Test und Produktion gelaufen ist.

ALT_AUFFINDBAR = frozenset(
    {
        "draft",
        "flagged",
        "approved",
        "rejected",
        "released_internal",
        "published_external",
        "archived",
        "duplicate",
    }
)
"""Altwerte, die die Suche vor #214 fand (wie Punkte ohne Status)."""

ALT_SICHTBAR = ALT_AUFFINDBAR | {"pending_review"}
"""
Altwerte, die sichtbar werden. pending_review blendete die Suche aus, es war aber nur
ein Rest des frueheren Anlage-Status, der schon einmal auf den sichtbaren gehoben
wurde; einen Arbeitsschritt, der auf diese Punkte wartet, gibt es nicht.
"""


def zustand_aus_altwert(wert):
    """
    Der Zustand fuer einen gespeicherten Altwert oder einen fehlenden Status (den die
    Suche vorher ebenfalls fand); andere Werte unveraendert. Nutzen das Lesen
    (BaseContentDbEntry), Entsperren (moderation_repository.py) und die Umstellung.
    """
    if wert is None or wert in ALT_SICHTBAR:
        return ContentStatus.VISIBLE.value
    return wert


FELD_STATUS_VOR_SPERRE = "status_vor_sperre"
"""
Payload-Feld mit dem Zustand von vor der Sperre, damit Entsperren ihn
wiederherstellt. Fehlt er oder ist er ein Altwert von vor #214, macht Entsperren
den Beitrag sichtbar (repositories/implementations/qdrant/moderation_repository.py).
"""


FELD_GELOESCHT_AM = "geloescht_am"
"""
Payload-Feld mit dem UTC-Tag (ISO-Datum), ab dem ein geloeschter Beitrag als
geloescht gilt. Der taegliche Task der Loeschfristen setzt es beim ersten Lauf, der
den Beitrag geloescht findet, und entfernt den Beitrag nach seiner Frist endgueltig
(services/loeschfristen_service.py).
"""
