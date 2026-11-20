"""
Zustimmung zu den Nutzungsbedingungen in der App: Stand lesen, zustimmen, pruefen.

Ohne geltende Zustimmung sperrt ``require_art9_einwilligung`` (dependencies.py) mit
403 ``nutzungsbedingungen_fehlen``, und zwar vor der Art.-9-Einwilligung: dieselben
Endpunkte, die etwas mit Personenbezug fuer andere speichern (Beitraege, Einwuerfe,
Saetze, Stimmen). Lesen, Suchen, Loeschen, Melden, Widerruf und Feedback bleiben offen.
So kann niemand an der Seite in der App vorbei ueber die API beitragen, ohne den
Bedingungen zugestimmt zu haben.

Jede Pruefung fragt die Datenbank (eine Zeile ueber einen Index), damit ein
Loeschkommando oder die Kennungsumstellung sofort wirkt.
"""

from typing import Optional

from domain.nutzungsbedingungen import bekannter_stand, geltender_stand
from repositories.nutzungsbedingungen_repository import (
    NbZustimmung,
    NutzungsbedingungenRepository,
    get_nutzungsbedingungen_repository,
)


class UnbekannterStand(ValueError):
    pass


class StandGiltNicht(ValueError):
    """Bekannt, aber nicht in GELTENDE_STAENDE: Eine Zustimmung dazu zaehlte nicht."""


class NutzungsbedingungenService:
    def __init__(self, repository: NutzungsbedingungenRepository):
        self._repository = repository

    def stand(self, user_id: str) -> Optional[NbZustimmung]:
        return self._repository.lesen(user_id)

    def zugestimmt(self, user_id: str) -> bool:
        zustimmung = self._repository.lesen(user_id)
        return zustimmung is not None and zustimmung.zaehlt

    def zustimmen(self, user_id: str, stand: str) -> None:
        if not bekannter_stand(stand):
            raise UnbekannterStand(stand)
        if not geltender_stand(stand):
            raise StandGiltNicht(stand)
        self._repository.zustimmen(user_id, stand)


_service: Optional[NutzungsbedingungenService] = None


def get_nutzungsbedingungen_service() -> NutzungsbedingungenService:
    global _service
    if _service is None:
        _service = NutzungsbedingungenService(get_nutzungsbedingungen_repository())
    return _service
