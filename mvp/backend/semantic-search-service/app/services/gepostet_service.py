"""
Rueckmeldung "Gepostet?" nach dem Kopieren (#643): Wer einen Beitrag kopiert hat,
meldet mit einem Klick, dass er oeffentlich gekontert hat. Das misst den Nordstern
(docs/VISION.md): wie viele verschiedene Menschen je Woche oeffentlich kontern. Es
zaehlt eine Person je Kalenderwoche, nicht jeder Klick.

Gemerkt wird nicht, wer gemeldet hat, sondern nach dem Muster der entdoppelten
Nutzung (services/entdoppelung.py) nur ein Pruefwert: ein HMAC ueber die Kennung mit
einem Wochenschluessel, der nur im Speicher liegt und mit jeder Kalenderwoche (UTC,
ab Montag) neu entsteht. Auch mit Datenbank und Konfiguration laesst sich ein Wert
nicht nachrechnen. Nach Wochenende verdichtet das Repository die Werte zur Zahl der
Woche und loescht sie. Welcher Beitrag kopiert wurde, steht nirgends.

Der Preis wie bei der Entdoppelung: Nach einem Neustart zaehlt eine Person, die in
derselben Woche noch einmal meldet, ein zweites Mal; das setzt einen uvicorn-Worker
voraus.

Wer zaehlt: nur angemeldete Personen mit geltender Art.-9-Einwilligung, keine
Startkonten, und nur mit dem Schalter ``gepostet_aktiv`` (api/v1/usage.py).
"""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

from repositories.gepostet_repository import GepostetRepository
from utils.besucher_pseudonym import Tagesschluessel
from utils.utc_tag import heute_utc, wochenbeginn

# Ein Schluessel je Montag: der Tagesschluessel, gefragt nur mit Wochenbeginnen.
_WOCHENSCHLUESSEL = Tagesschluessel()


def gepostet_pruefwert(kennung: str, woche: date) -> str:
    """Gleich fuer dieselbe Kennung in derselben Woche, solange der Prozess laeuft."""
    return hmac.new(
        _WOCHENSCHLUESSEL.fuer(woche),
        f"gepostet|{kennung}|{woche.isoformat()}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


@dataclass(frozen=True)
class GepostetWoche:
    woche: date
    personen: int


class GepostetService:
    def __init__(self, repository: GepostetRepository):
        self._repository = repository

    def melden(self, kennung: str, heute: Optional[date] = None) -> int:
        """
        "Ja, gepostet" fuer diese Woche; synchron, im Thread aufrufen. Gibt zurueck,
        wie viele verschiedene Personen diese Woche gemeldet haben, die Person
        eingeschlossen.
        """
        woche = wochenbeginn(heute or heute_utc())
        return self._repository.melden(gepostet_pruefwert(kennung, woche), woche)

    def diese_woche(self, heute: Optional[date] = None) -> int:
        """Wie viele verschiedene Personen diese Woche gemeldet haben."""
        return self._repository.anzahl(wochenbeginn(heute or heute_utc()))

    def wochen(self, anzahl: int, heute: Optional[date] = None) -> List[GepostetWoche]:
        """Die letzten ``anzahl`` Kalenderwochen, die laufende zuletzt; ohne Meldung 0."""
        laufende = wochenbeginn(heute or heute_utc())
        von = laufende - timedelta(weeks=anzahl - 1)
        zahlen = self._repository.wochen(von, laufende)
        return [
            GepostetWoche(woche=w, personen=zahlen.get(w, 0))
            for w in (von + timedelta(weeks=i) for i in range(anzahl))
        ]


_service: Optional[GepostetService] = None


def get_gepostet_service() -> GepostetService:
    global _service
    if _service is None:
        from repositories.gepostet_repository import get_gepostet_repository

        _service = GepostetService(get_gepostet_repository())
    return _service
