"""
Art.-9-Einwilligung (#489): einwilligen, widerrufen, pruefen.

Ohne geltende Einwilligung sperrt ``require_art9_einwilligung`` (dependencies.py)
die Endpunkte, die etwas mit Personenbezug speichern, aus dem sich auf die
politische Meinung schliessen laesst: Beitraege anlegen und aendern, Herkunft
anlegen, Einwurf und Satz, Ausformulieren eines Einwurfs, Stimmen. Lesen, Suchen,
Loeschen, Verwerfen, Melden und Feedback bleiben offen; die Liste steht an den Endpunkten,
``tests/unit/api/test_art9_einwilligung_api.py`` prueft sie.

Jede Pruefung fragt die Datenbank (eine Zeile ueber einen Index). Ein Merken im
Prozess wuerde einen Widerruf, das Loeschkommando oder die Kennungsumstellung
erst nach einem Neustart sehen.
"""

from typing import Optional

from domain.art9_einwilligung import bekannter_wortlaut
from repositories.art9_einwilligung_repository import (
    Art9Einwilligung,
    Art9EinwilligungRepository,
    get_art9_einwilligung_repository,
)


class UnbekannterWortlaut(ValueError):
    pass


class Art9EinwilligungService:
    def __init__(self, repository: Art9EinwilligungRepository):
        self._repository = repository

    def stand(self, user_id: str) -> Optional[Art9Einwilligung]:
        return self._repository.lesen(user_id)

    def eingewilligt(self, user_id: str) -> bool:
        einwilligung = self._repository.lesen(user_id)
        return einwilligung is not None and einwilligung.gilt

    def einwilligen(self, user_id: str, wortlaut: str) -> None:
        if not bekannter_wortlaut(wortlaut):
            raise UnbekannterWortlaut(wortlaut)
        self._repository.einwilligen(user_id, wortlaut)

    def widerrufen(self, user_id: str) -> None:
        self._repository.widerrufen(user_id)


_service: Optional[Art9EinwilligungService] = None


def get_art9_einwilligung_service() -> Art9EinwilligungService:
    global _service
    if _service is None:
        _service = Art9EinwilligungService(get_art9_einwilligung_repository())
    return _service
