"""
Widerspruch gegen eine Sperre und das Ergebnis der erneuten Pruefung (Glossar
„Widerspruch“, #448).

Das Pruefergebnis steht als freier Text an der Sperre (Spalte ``pruefergebnis``);
die Werte duerfen deshalb nicht umbenannt werden, solange Sperren mit ihnen in der
Datenbank liegen. Das Frontend vergleicht dieselben Zeichenketten.
"""

from enum import Enum

PRUEFERGEBNIS_SPERRE_BLEIBT = "sperre_bleibt"
PRUEFERGEBNIS_ENTSPERRT = "entsperrt"


class Widerspruchsergebnis(Enum):
    ANGENOMMEN = "angenommen"
    # Keine aktive Sperre mit dieser Kennung, oder sie gilt einer anderen Person.
    NICHT_GEFUNDEN = "nicht_gefunden"
    SCHON_WIDERSPROCHEN = "schon_widersprochen"
