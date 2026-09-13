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
    Bearbeitungsstand eines Einwurfs - drei Stufen: Einwerfen, Destillieren,
    Ausformulieren.

    Der Eingang setzt OPEN. Der erste gespeicherte Satz macht daraus IN_PROGRESS,
    das Loeschen des letzten Satzes wieder OPEN (``status_nach_satz``,
    ``status_ohne_saetze``). Der Destillier-Ablauf setzt DISCARDED oder PROCESSED
    (``uebergang_erlaubt``).

    OPEN <-> IN_PROGRESS (ueber Saetze)
    OPEN | IN_PROGRESS -> PROCESSED | DISCARDED,  DISCARDED -> PROCESSED
    """

    OPEN = "open"
    """Liegt im Fangkorb, niemand hat einen Satz dazu gespeichert."""

    IN_PROGRESS = "in_progress"
    """
    Destilliert: mindestens ein Satz ist gespeichert, ein Beitrag noch nicht.
    Keine Sperre - andere duerfen weitere Saetze formulieren.
    """

    PROCESSED = "processed"
    """Daraus ist mindestens ein Beitrag entstanden (siehe raw_input_content_links)."""

    DISCARDED = "discarded"
    """Angeschaut und verworfen. Bleibt liegen, damit er nicht wieder auftaucht."""


class RawInputSource(str, Enum):
    """
    Kanal, ueber den der Einwurf hereinkam.

    Das Feld existierte von Anfang an, bevor es einen zweiten Kanal gab -- eine
    Migration auf einer bereits gefuellten Tabelle waere teurer gewesen als ein
    Feld, das eine Weile nur einen Wert kennt. Inzwischen gibt es den zweiten.
    """

    WEB = "web"
    """Ueber das Einwurf-Formular im Frontend."""

    SHARE = "share"
    """
    Ueber das Android-Teilen-Menue (PWA Share Target).

    Landet ebenfalls im Einwurf-Formular und damit auf demselben Endpunkt -- der
    Unterschied ist nicht technisch, sondern der, den man spaeter wissen will:
    wie viele Einwuerfe ueber das Teilen hereinkamen und wie viele von Hand.
    """


# Von welchem Status aus ein Ziel erreichbar ist. Dasselbe Ziel noch einmal zu
# setzen ist erlaubt und aendert nichts: ein wiederholter Aufruf nach verlorener
# Antwort darf nicht scheitern, und bei processed kann ein zweiter Beitrag aus
# demselben Einwurf entstehen (keine Sperre, Verknuepfung ist n:m).
_ERLAUBTE_VORGAENGER = {
    RawInputStatus.DISCARDED: frozenset(
        {RawInputStatus.OPEN, RawInputStatus.IN_PROGRESS, RawInputStatus.DISCARDED}
    ),
    RawInputStatus.PROCESSED: frozenset(
        {
            RawInputStatus.OPEN,
            RawInputStatus.IN_PROGRESS,
            RawInputStatus.DISCARDED,
            RawInputStatus.PROCESSED,
        }
    ),
}


def uebergang_erlaubt(von: RawInputStatus, nach: RawInputStatus) -> bool:
    """
    Ob ein Einwurf per Statuswechsel von ``von`` nach ``nach`` wechseln darf.

    discarded aus open oder in_progress (ein verarbeiteter Einwurf wird nicht
    nachtraeglich verworfen); processed aus open, in_progress oder discarded
    (andere duerfen Verworfenes trotzdem destillieren). open und in_progress sind
    kein Ziel eines Statuswechsels - die ergeben sich aus den Saetzen.
    """
    return von in _ERLAUBTE_VORGAENGER.get(nach, frozenset())


def status_nach_satz(aktuell: RawInputStatus) -> RawInputStatus:
    """
    Der Status, nachdem jemand einen nicht-leeren Satz gespeichert hat.

    Nur ein offener Einwurf wird dadurch destilliert. Verworfenes bleibt verworfen
    (grau, andere duerfen trotzdem destillieren), Verarbeitetes bleibt verarbeitet.
    """
    if aktuell == RawInputStatus.OPEN:
        return RawInputStatus.IN_PROGRESS
    return aktuell


def status_ohne_saetze(aktuell: RawInputStatus) -> RawInputStatus:
    """
    Der Status, nachdem der letzte Satz zu einem Einwurf geloescht wurde.

    Nur ein destillierter Einwurf faellt zurueck auf offen; verworfene und
    verarbeitete behalten ihren Stand.
    """
    if aktuell == RawInputStatus.IN_PROGRESS:
        return RawInputStatus.OPEN
    return aktuell


class EinwurfNichtGefunden(LookupError):
    """Den angefragten Einwurf gibt es nicht."""


class AktionNichtErlaubt(PermissionError):
    """Die Person darf diese Aktion an diesem Einwurf nicht ausfuehren."""


class UebergangNichtErlaubt(ValueError):
    """Der Statuswechsel ist aus dem aktuellen Status nicht erlaubt."""

    def __init__(self, von: RawInputStatus, nach: RawInputStatus):
        super().__init__(
            f"Ein Einwurf im Status {von.value} kann nicht auf {nach.value} wechseln."
        )
        self.von = von
        self.nach = nach
