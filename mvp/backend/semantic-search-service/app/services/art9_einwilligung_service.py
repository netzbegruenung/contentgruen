"""
Art.-9-Einwilligung (#489): einwilligen, widerrufen, pruefen.

Ohne geltende Einwilligung sperrt ``require_art9_einwilligung`` (dependencies.py)
die Endpunkte, die etwas mit Personenbezug speichern, aus dem sich auf die
politische Meinung schliessen laesst: Beitraege anlegen und aendern, Herkunft
anlegen, Einwurf und Satz, Ausformulieren eines Einwurfs, Stimmen. Lesen, Suchen,
Loeschen, Verwerfen, Melden und Feedback bleiben offen; die Liste steht an den Endpunkten,
``tests/unit/api/test_art9_einwilligung_api.py`` prueft sie.

Ein Widerruf loescht in derselben Transaktion die Stimmen der Person: Fuer sie fehlt dann die
Rechtsgrundlage (Art. 17 Abs. 1 lit. b DSGVO, juristische Vorpruefung vom
12.11.2026). Beitraege, Einwuerfe und Saetze bleiben bis zur eigenen Loeschung oder
zur Kontoloeschung (docs/ART9_EINWILLIGUNG.md, offen).

Jede Pruefung fragt die Datenbank (eine Zeile ueber einen Index). Ein Merken im
Prozess wuerde einen Widerruf, das Loeschkommando oder die Kennungsumstellung
erst nach einem Neustart sehen.
"""

from typing import Optional, Protocol

from domain.art9_einwilligung import bekannter_wortlaut
from repositories.vote_repository import VoteRepository
from repositories.art9_einwilligung_repository import (
    Art9Einwilligung,
    Art9EinwilligungRepository,
    get_art9_einwilligung_repository,
)


class UnbekannterWortlaut(ValueError):
    pass


class StimmenDerPerson(Protocol):
    def loeschen_fuer_person(self, user_id: str, session=None) -> int: ...


class Art9EinwilligungService:
    def __init__(
        self,
        repository: Art9EinwilligungRepository,
        stimmen: Optional[StimmenDerPerson] = None,
    ):
        """``stimmen``: loescht beim Widerruf die Stimmen; ohne (Tests) nichts."""
        self._repository = repository
        self._stimmen = stimmen

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
        """
        Widerruf vermerken und die Stimmen loeschen, in einer Transaktion (beide
        Repositories nutzen die globale AppDatabase): Scheitert das Loeschen, gilt
        auch der Widerruf nicht, die Person bleibt eingewilligt und kann ihn ueber
        die Oberflaeche wiederholen.
        """
        stimmen = self._stimmen
        if stimmen is None:
            self._repository.widerrufen(user_id)
            return
        self._repository.widerrufen(
            user_id,
            im_selben_zug=lambda session: stimmen.loeschen_fuer_person(
                user_id, session=session
            ),
        )


_service: Optional[Art9EinwilligungService] = None


def get_art9_einwilligung_service() -> Art9EinwilligungService:
    global _service
    if _service is None:
        _service = Art9EinwilligungService(
            get_art9_einwilligung_repository(), VoteRepository()
        )
    return _service
