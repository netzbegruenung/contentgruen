"""
Loeschauftraege nach dem Widerruf der Art.-9-Einwilligung (GLOSSARY.md
"Loeschauftrag", DSFA R9b, docs/ART9_EINWILLIGUNG.md).

Der Widerruf legt einen Auftrag an (Art9EinwilligungService.widerrufen); ein Admin
fuehrt binnen FRIST_TAGE den Loeschablauf aus: Beitraege anonymisieren wie in
Schritt 3 des Loeschkonzepts (services/wartung/beitraege_anonymisieren.py), eigene
Einwuerfe loeschen und Saetze an fremden Einwuerfen mit Platzhalter versehen wie in
Schritt 2 (LoeschauftragRepository.ausfuehren). Das Konto, der Anzeigename und die
Zeile der Einwilligung als Nachweis (Art. 7 Abs. 1 DSGVO) bleiben.

Was die Person nach einer neuen Einwilligung beitraegt, bleibt unberuehrt
(Entscheidung Maintainer, 13.11.2026, ``Loeschauftrag.obergrenze``); ohne neue
Einwilligung erfasst der Auftrag alles. Hat die Person waehrend der Ausfuehrung
widerrufen oder neu eingewilligt, bricht der PostgreSQL-Teil mit ``StandGeaendert``
ab, der Auftrag bleibt offen, und der naechste Klick nimmt den neuen Stand.

Erst Qdrant, dann PostgreSQL samt Vermerk "erledigt": Scheitert ein Schritt, bleibt
der Auftrag offen, und ein zweiter Klick holt nach, was fehlt; beide Teile sind
wiederholbar.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Union

from repositories.loeschauftrag_repository import (  # noqa: F401 (StandGeaendert)
    FRIST_TAGE,
    Loeschauftrag,
    LoeschauftragRepository,
    StandGeaendert,
)


class AuftragUnbekannt(LookupError):
    pass


class AuftragErledigt(ValueError):
    pass


@dataclass(frozen=True)
class OffenerAuftrag:
    id: uuid.UUID
    user_id: str
    anzeigename: Optional[str]
    # Juengster Widerruf (ohne Zeile der Einwilligung: das Anlegen)
    widerrufen_am: datetime
    angelegt_am: datetime
    frist: datetime
    ueberfaellig: bool
    # Neue Einwilligung nach dem juengsten Widerruf; was ab da kam, erfasst der
    # Auftrag nicht
    neu_eingewilligt_am: Optional[datetime]


@dataclass(frozen=True)
class AnonymisierteBeitraege:
    anzahl: int
    # Beitraege der Person ab der Obergrenze (Qdrant-Punktkennungen), unberuehrt
    behalten: Sequence[Union[int, str]] = ()


@dataclass(frozen=True)
class Ausfuehrung:
    beitraege: int
    einwuerfe: int
    saetze: int


class LoeschauftragService:
    def __init__(
        self,
        repository: LoeschauftragRepository,
        beitraege_anonymisieren: Callable[
            [str, Optional[datetime]], AnonymisierteBeitraege
        ],
        anzeigenamen: Optional[Callable[[Iterable[str]], Dict[str, str]]] = None,
    ):
        """
        ``beitraege_anonymisieren``: Kennung und Obergrenze -> anonymisierte Beitraege
        (nur davor angelegte; ohne Obergrenze alle) und die spaeteren, die bleiben.
        ``anzeigenamen``: Kennungen -> Namen fuer die Liste; ohne nur die Kennung.
        """
        self._repository = repository
        self._beitraege_anonymisieren = beitraege_anonymisieren
        self._anzeigenamen = anzeigenamen

    @property
    def frist_tage(self) -> int:
        return FRIST_TAGE

    def offene(self, jetzt: Optional[datetime] = None) -> List[OffenerAuftrag]:
        jetzt = jetzt or datetime.now(timezone.utc)
        auftraege = self._repository.offene()
        namen = (
            self._anzeigenamen(a.user_id for a in auftraege)
            if self._anzeigenamen is not None and auftraege
            else {}
        )
        return [
            OffenerAuftrag(
                id=a.id,
                user_id=a.user_id,
                anzeigename=namen.get(a.user_id),
                widerrufen_am=a.widerrufen_am or a.angelegt_am,
                angelegt_am=a.angelegt_am,
                frist=a.frist,
                ueberfaellig=a.frist < jetzt,
                neu_eingewilligt_am=a.neu_eingewilligt_am,
            )
            for a in auftraege
        ]

    def ausfuehren(self, auftrag_id: uuid.UUID) -> Ausfuehrung:
        auftrag: Optional[Loeschauftrag] = self._repository.laden(auftrag_id)
        if auftrag is None:
            raise AuftragUnbekannt(str(auftrag_id))
        if auftrag.erledigt_am is not None:
            raise AuftragErledigt(str(auftrag_id))
        beitraege = self._beitraege_anonymisieren(auftrag.user_id, auftrag.obergrenze)
        bericht = self._repository.ausfuehren(
            auftrag, beitraege_behalten=[str(b) for b in beitraege.behalten]
        )
        return Ausfuehrung(
            beitraege=beitraege.anzahl,
            einwuerfe=bericht.einwuerfe,
            saetze=bericht.saetze,
        )


_service: Optional[LoeschauftragService] = None


def get_loeschauftrag_service() -> LoeschauftragService:
    global _service
    if _service is None:
        from repositories.loeschauftrag_repository import get_loeschauftrag_repository
        from repositories.user_repository import get_user_repository
        from services.embeddings.qdrant_embeddings_manager import (
            get_embeddings_manager,
        )
        from services.wartung.beitraege_anonymisieren import anonymisieren

        def beitraege_anonymisieren(
            kennung: str, obergrenze: Optional[datetime]
        ) -> AnonymisierteBeitraege:
            manager = get_embeddings_manager()
            bericht = anonymisieren(
                manager.client,
                manager.collection_name,
                kennung,
                ausfuehren=True,
                angelegt_vor=obergrenze,
            )
            return AnonymisierteBeitraege(len(bericht.treffer), bericht.behalten)

        _service = LoeschauftragService(
            get_loeschauftrag_repository(),
            beitraege_anonymisieren,
            get_user_repository().anzeigenamen,
        )
    return _service
