"""
Fehler, deren Text an Aufrufer hinausgehen darf, und die festen Texte fuer alle anderen (#486).

Der Text einer beliebigen Ausnahme gehoert nicht in eine Antwort: Aus Datenbank, Qdrant
oder einer Bibliothek traegt er Interna und oft Eingabewerte. Ein eigener
Validierungsfehler ist dagegen fuer Aufrufer formuliert; sein Text steht in ``meldung``.
Der Waechter tests/unit/api/test_fehlerantworten_ohne_fehlertext.py laesst in
Fehlerantworten nur ``e.meldung`` zu.
"""

INTERNER_FEHLER = "Interner Fehler"
UNGUELTIGE_ANFRAGE = "Ungültige Anfrage"
NICHT_ERREICHBAR = "Dienst vorübergehend nicht erreichbar"


class Validierungsfehler(ValueError):
    """Eine Eingabe oder ein Zustand ist ungueltig; der Text ist fuer Aufrufer formuliert."""

    @property
    def meldung(self) -> str:
        return str(self)
