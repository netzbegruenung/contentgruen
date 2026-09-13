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

    Der Eingang setzt OPEN, der Destillier-Ablauf setzt DISCARDED oder PROCESSED
    (siehe ``uebergang_erlaubt``). IN_PROGRESS bleibt der Andockpunkt fuer eine
    spaetere Queue mit Zuweisung und wird heute von nichts geschrieben.

    OPEN -> PROCESSED | DISCARDED,  DISCARDED -> PROCESSED
    """

    OPEN = "open"
    """Liegt im Fangkorb, niemand hat ihn angefasst."""

    IN_PROGRESS = "in_progress"
    """Jemand arbeitet daran. Wird nicht vergeben: es gibt bewusst keine Sperre."""

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
        {RawInputStatus.OPEN, RawInputStatus.DISCARDED}
    ),
    RawInputStatus.PROCESSED: frozenset(
        {RawInputStatus.OPEN, RawInputStatus.DISCARDED, RawInputStatus.PROCESSED}
    ),
}


def uebergang_erlaubt(von: RawInputStatus, nach: RawInputStatus) -> bool:
    """
    Ob ein Einwurf von ``von`` nach ``nach`` wechseln darf.

    discarded nur aus open (ein verarbeiteter Einwurf wird nicht nachtraeglich
    verworfen); processed aus open oder discarded (andere duerfen Verworfenes
    trotzdem destillieren). Zurueck nach open oder nach in_progress fuehrt nichts.
    """
    return von in _ERLAUBTE_VORGAENGER.get(nach, frozenset())


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
