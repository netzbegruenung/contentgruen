"""
Rohinput ("Fangkorb") - Zustaende und Herkunftskanaele.

Rohinput ist bewusst *kein* ContentType: er wird nicht gesucht, nicht kopiert,
nicht bewertet und nicht moderiert, sondern liegt als Arbeitsvorrat in
PostgreSQL neben dem Inhalt (siehe docs/ROHINPUT.md, Variante C). Deshalb hat er
eigene Enums statt ContentStatus/ContentOrigin - deren Zustaende beschreiben
Moderation und Erzeugung, nicht Bearbeitung.

Beide Enums sind absichtlich *nicht* als CHECK-Constraint in der Datenbank
abgebildet (wie content_reports.status auch nicht): ein weiterer Zustand oder
Kanal soll eine Code-Aenderung sein, keine Migration.
"""

from enum import Enum


class RawInputStatus(str, Enum):
    """
    Bearbeitungsstand eines Einwurfs.

    Heute setzt der Eingang ausschliesslich OPEN; die uebrigen Zustaende sind der
    Andockpunkt fuer die spaetere Bearbeitungs-Queue und werden von nichts
    geschrieben. Sie stehen hier, damit das Feld von Anfang an die volle Bedeutung
    hat und ein spaeteres Nachruesten kein Umdeuten bestehender Zeilen erfordert.

    OPEN -> IN_PROGRESS -> PROCESSED | DISCARDED
    """

    OPEN = "open"
    """Liegt im Fangkorb, niemand hat ihn angefasst."""

    IN_PROGRESS = "in_progress"
    """Jemand arbeitet daran. Wird erst mit der Queue vergeben."""

    PROCESSED = "processed"
    """Daraus ist mindestens ein Beitrag entstanden (siehe raw_input_content_links)."""

    DISCARDED = "discarded"
    """Angeschaut und verworfen. Bleibt liegen, damit er nicht wieder auftaucht."""


class RawInputSource(str, Enum):
    """
    Kanal, ueber den der Einwurf hereinkam.

    Aktuell gibt es genau einen Eingang. Das Feld existiert trotzdem von Anfang
    an, weil der geplante Instagram-Share-Eingang ohne Browser-Session ankommt
    und sich von einem Web-Einwurf unterscheiden lassen muss - ohne Feld waere
    das eine Migration auf einer dann bereits gefuellten Tabelle.
    """

    WEB = "web"
    """Ueber das Einwurf-Formular im Frontend."""
