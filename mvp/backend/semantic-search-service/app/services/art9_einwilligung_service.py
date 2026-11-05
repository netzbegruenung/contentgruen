"""
Art.-9-Einwilligung (#489): einwilligen, widerrufen, pruefen.

Ohne geltende Einwilligung sperrt ``require_art9_einwilligung`` (dependencies.py)
die Endpunkte, die etwas mit Personenbezug speichern, aus dem sich auf die
politische Meinung schliessen laesst: Beitraege anlegen und aendern, Herkunft
anlegen, Einwurf, Satz und Stufe eines Einwurfs, Bewertungen. Lesen, Suchen,
Loeschen, Melden und Feedback bleiben offen; die Liste steht an den Endpunkten,
``tests/unit/api/test_art9_einwilligung_api.py`` prueft sie.

Wer eingewilligt hat, merkt sich der Prozess, damit nicht jeder Schreibzugriff
eine Abfrage kostet; der Dienst laeuft mit einem Worker (Dockerfile), Einwilligen
und Widerrufen gehen durch denselben Prozess. Ein Nein wird nicht gemerkt: Es
wird gleich nach dem Einwilligen ein Ja.
"""

from typing import Optional, Set

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
        self._eingewilligt: Set[str] = set()

    def stand(self, user_id: str) -> Optional[Art9Einwilligung]:
        return self._repository.lesen(user_id)

    def eingewilligt(self, user_id: str) -> bool:
        if user_id in self._eingewilligt:
            return True
        einwilligung = self._repository.lesen(user_id)
        if einwilligung is None or not einwilligung.gilt:
            return False
        self._eingewilligt.add(user_id)
        return True

    def einwilligen(self, user_id: str, wortlaut: str) -> None:
        if not bekannter_wortlaut(wortlaut):
            raise UnbekannterWortlaut(wortlaut)
        self._repository.einwilligen(user_id, wortlaut)
        self._eingewilligt.add(user_id)

    def widerrufen(self, user_id: str) -> None:
        # Erst schreiben, dann vergessen: Andersherum koennte ein gleichzeitiger
        # Zugriff die noch geltende Zeile lesen und sich die Person wieder merken.
        self._repository.widerrufen(user_id)
        self._eingewilligt.discard(user_id)


_service: Optional[Art9EinwilligungService] = None


def get_art9_einwilligung_service() -> Art9EinwilligungService:
    global _service
    if _service is None:
        _service = Art9EinwilligungService(get_art9_einwilligung_repository())
    return _service
