"""
Zustimmung zu den Nutzungsbedingungen in der App (GLOSSARY.md "Zustimmung zu den
Nutzungsbedingungen", "Stand der Nutzungsbedingungen").

Bisher fragte die Keycloak-Pflichtaktion "Terms and Conditions" beim Anmelden, und
die App fragte danach noch einmal nach der Art.-9-Einwilligung. Kuenftig fragt die
App beides auf einer Seite (/einwilligung), mit zwei getrennten, nicht vorbelegten
Haekchen: die Nutzungsbedingungen als Pflicht, die Art.-9-Einwilligung freiwillig
(Entscheidung Maintainer, 20.11.2026). Das NB-Haekchen ist keine Einwilligung im
Sinne der DSGVO, sondern die Annahme eines Vertrags (Art. 6 Abs. 1 lit. b DSGVO,
Einbeziehung ueber Link und Haekchen, Paragraf 305 Abs. 2 BGB).

Gespeichert werden Person, Zeitpunkt und der Stand der Nutzungsbedingungen, dem sie
zugestimmt hat. Die Kennung eines Stands ist das Datum seiner Stand-Zeile als
``JJJJ-MM-TT``, wie der Ordnername in docs/nutzungsbedingungen-staende/;
``scripts/tests/test_nutzungsbedingungen_staende.py`` prueft, dass AKTUELLER_STAND
dem Stand der Seite entspricht. Ablauf: docs/ART9_EINWILLIGUNG.md, Abschnitt "Nutzungsbedingungen auf derselben Seite".
"""

from types import MappingProxyType
from typing import Mapping

# Laenge der Spalte in PostgreSQL (nutzungsbedingungen_zustimmungen.stand).
STAND_KENNUNG_MAX = 64

# Kennung -> Stand-Zeile der Seite. Alte Staende bleiben stehen, damit jede
# gespeicherte Kennung ihren Text behaelt (den Text liefert der Release-Tag,
# docs/nutzungsbedingungen-staende/README.md).
STAENDE: Mapping[str, str] = MappingProxyType(
    {
        "2026-11-19": "19. November 2026",
        "2026-11-20": "20. November 2026",
    }
)

AKTUELLER_STAND = "2026-11-20"

# Staende, deren Zustimmung heute zaehlt. Eine reine Korrektur nimmt den neuen Stand
# hinzu (keine neue Frage), ein wesentlicher Stand ersetzt die Menge (alle werden neu
# gefragt), wie in docs/nutzungsbedingungen-staende/README.md.
# 2026-11-20 ist wesentlich (Zustimmung per Haekchen, NB Paragraf 2 und 10).
GELTENDE_STAENDE = frozenset({"2026-11-20"})


def bekannter_stand(kennung: str) -> bool:
    return kennung in STAENDE


def geltender_stand(kennung: str) -> bool:
    return kennung in GELTENDE_STAENDE
