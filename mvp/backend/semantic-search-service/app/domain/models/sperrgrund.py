"""
Sperrgruende: warum ein Admin einen Beitrag sperrt (Glossar „Sperrgrund“, #448).

Die Liste folgt Abschnitt 6 der Nutzungsbedingungen („Was hier nicht hingehört“); was
genau am Beitrag nicht stimmt, steht in der Begruendung daneben. Beides erfaehrt der
Autor in der Sperrnachricht (Art. 17 DSA). Gespeicherte Sperren tragen den Wert als
freien Text, ein Wert darf deshalb nicht umbenannt oder entfernt werden, solange
Sperren mit ihm in der Datenbank liegen. Das Frontend fuehrt dieselben Werte mit ihrer
Beschriftung in ``shared/sperrgruende.ts``; TestSperrgruende in
tests/unit/services/test_sperre_mit_grund.py gleicht beide ab.
"""

from typing import Literal, get_args

Sperrgrund = Literal[
    "rechtswidrig",
    "rechte_dritter",
    "personendaten_dritter",
    "unterstellung",
    "ohne_bezug",
    "anderer_verstoss",
]

SPERRGRUENDE: tuple[str, ...] = get_args(Sperrgrund)
