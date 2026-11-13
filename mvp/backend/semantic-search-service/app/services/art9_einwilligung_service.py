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
12.11.2026). Fuer Beitraege, Einwuerfe und Saetze legt er in derselben Transaktion
einen Loeschauftrag an, den ein Admin binnen sieben Tagen ausfuehrt
(services/loeschauftrag_service.py, DSFA R9b).

Jede Pruefung fragt die Datenbank (eine Zeile ueber einen Index). Ein Merken im
Prozess wuerde einen Widerruf, das Loeschkommando oder die Kennungsumstellung
erst nach einem Neustart sehen.
"""

from typing import Optional, Protocol

from domain.art9_einwilligung import bekannter_wortlaut
from repositories.loeschauftrag_repository import get_loeschauftrag_repository
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


class LoeschauftraegeDerPerson(Protocol):
    def anlegen(self, user_id: str, session=None) -> None: ...


class Art9EinwilligungService:
    def __init__(
        self,
        repository: Art9EinwilligungRepository,
        stimmen: Optional[StimmenDerPerson] = None,
        loeschauftraege: Optional[LoeschauftraegeDerPerson] = None,
    ):
        """
        ``stimmen``: loescht beim Widerruf die Stimmen; ``loeschauftraege``: legt
        beim Widerruf einen Loeschauftrag an. Ohne (Tests) jeweils nichts.
        """
        self._repository = repository
        self._stimmen = stimmen
        self._loeschauftraege = loeschauftraege

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
        Widerruf vermerken, die Stimmen loeschen und einen Loeschauftrag anlegen, in
        einer Transaktion (alle Repositories nutzen die globale AppDatabase):
        Scheitert eins davon, gilt auch der Widerruf nicht, die Person bleibt
        eingewilligt und kann ihn ueber die Oberflaeche wiederholen. Den Auftrag gibt
        es nur, wenn eben eine geltende Einwilligung widerrufen wurde; ein offener
        bleibt ohnehin der einzige.
        """
        stimmen = self._stimmen
        loeschauftraege = self._loeschauftraege
        if stimmen is None and loeschauftraege is None:
            self._repository.widerrufen(user_id)
            return

        def im_selben_zug(session, widerrufen: bool) -> None:
            if stimmen is not None:
                stimmen.loeschen_fuer_person(user_id, session=session)
            if loeschauftraege is not None and widerrufen:
                loeschauftraege.anlegen(user_id, session=session)

        self._repository.widerrufen(user_id, im_selben_zug=im_selben_zug)


_service: Optional[Art9EinwilligungService] = None


def get_art9_einwilligung_service() -> Art9EinwilligungService:
    global _service
    if _service is None:
        _service = Art9EinwilligungService(
            get_art9_einwilligung_repository(),
            VoteRepository(),
            get_loeschauftrag_repository(),
        )
    return _service
