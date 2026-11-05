"""
Schattenbetrieb der NLI-Stufe (#387): Die Schwelle entscheidet, die NLI-Stufe urteilt
mit, und gezaehlt wird nur, wie oft beide uebereinstimmen. Auswertung vor der
Umstellung auf "an".

Protokolliert werden nur Zaehler, keine Suchtexte, keine Aussage-IDs und kein Ereignis
je Suche: Eine Zeile je Suche mit Uhrzeit liesse sich einem Suchereignis zuordnen
(#239). Die Zaehler gehen alle ZUSAMMENFASSUNG_ALLE Urteile als eine INFO-Zeile ins Log
und beim Neustart verloren. Welche Aussagen die NLI-Stufe zusammenfuehren wuerde, zeigt
der Bericht ueber den Bestand (tests/regression/dieselbe_bericht.py), nicht das Log.
"""

import logging
from collections import Counter
from typing import Optional

from domain.models.base_content import BaseContentSearchResult
from services.content.base_content_service import Dublettenpruefung

logger = logging.getLogger(__name__)

ZUSAMMENFASSUNG_ALLE = 100

# Was gezaehlt wird:
# - beide_neu / beide_dieselbe: Schwelle und NLI-Stufe stimmen ueberein.
# - nur_schwelle: Die Schwelle fuehrt zusammen, die NLI-Stufe nicht (heute vermutlich
#   ein Widerspruch, der still zusammenfaellt).
# - nur_nli: Die NLI-Stufe fuehrt zusammen, die Schwelle nicht (Zerfaserung heute).
# - andere_aussage: Beide fuehren zusammen, aber mit verschiedenen Aussagen.
# - ohne_modell: Das Modell konnte nicht urteilen.
# - uebersprungen: Ein anderes Urteil lief noch.
ARTEN = (
    "beide_neu",
    "beide_dieselbe",
    "nur_schwelle",
    "nur_nli",
    "andere_aussage",
    "ohne_modell",
    "uebersprungen",
)


class Schattenprotokoll:
    def __init__(self) -> None:
        self.zaehler: Counter[str] = Counter()

    def zaehlen(self, art: str) -> None:
        self.zaehler[art] += 1
        if sum(self.zaehler.values()) % ZUSAMMENFASSUNG_ALLE == 0:
            logger.info(
                "NLI-Schattenbetrieb seit Start: %s",
                ", ".join(f"{a}={self.zaehler[a]}" for a in ARTEN),
            )

    def vergleichen(
        self,
        schwelle: Optional[BaseContentSearchResult],
        nach_nli: Optional[Dublettenpruefung],
    ) -> None:
        if nach_nli is None:
            self.zaehlen("ohne_modell")
            return
        nli = nach_nli.vorhanden
        if schwelle is None and nli is None:
            self.zaehlen("beide_neu")
        elif schwelle is None:
            self.zaehlen("nur_nli")
        elif nli is None:
            self.zaehlen("nur_schwelle")
        elif str(schwelle.id) == str(nli.id):
            self.zaehlen("beide_dieselbe")
        else:
            self.zaehlen("andere_aussage")
