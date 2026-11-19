"""
Was die Beitragsseite unter der Karte zeigt (#603): die Aussage, auf die der
Beitrag antwortet, und weitere Antworten zu ihr.

Die Verknuepfung steht an der Aussage (replysuggestions); gefunden wird sie ueber
das abgeleitete Payload-Feld antwort_ids (utils/antwort_ids.py). Antwortet ein
Beitrag auf mehrere Aussagen, gilt die, zu der er am besten passt (Relevanz des
Antwortvorschlags), bei Gleichstand die aeltere.

Gezeigt wird nur Sichtbares: Die Aussage muss sichtbar sein, gesperrte und
geloeschte Antworten fallen weg. Eine Aussage mit dieser Antwort ist beantwortet
und damit keine unbeantwortete Suchanfrage einer einzelnen Person (#436).
"""

import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from domain.models.statement import AntwortKurz, StatementDbEntry, angelegt_am

# Wie viele weitere Antworten die Seite zeigt; der Rest steht in der Suche, auf die
# "Antwort auf" verlinkt.
WEITERE_ANTWORTEN_HOECHSTENS = 5
# Wie viele Antwortvorschlaege einer Aussage hoechstens nachgeschlagen werden.
VORSCHLAEGE_HOECHSTENS = 50


@dataclass
class AussageKurz:
    id: uuid.UUID
    text: str


@dataclass
class BeitragKontext:
    aussage: Optional[AussageKurz] = None
    weitere_antworten: List[AntwortKurz] = field(default_factory=list)

    def als_json(self) -> dict:
        return {
            "aussage": (
                {"id": str(self.aussage.id), "text": self.aussage.text}
                if self.aussage
                else None
            ),
            "weitere_antworten": [
                antwort.model_dump(mode="json") for antwort in self.weitere_antworten
            ],
        }


def _relevanz(aussage: StatementDbEntry, beitrag_id: uuid.UUID) -> float:
    return max(
        (v.relevance for v in aussage.replysuggestions if v.id == beitrag_id),
        default=0.0,
    )


def aussage_waehlen(
    aussagen: List[StatementDbEntry], beitrag_id: uuid.UUID
) -> Optional[StatementDbEntry]:
    """Die Aussage, zu der der Beitrag am besten passt; bei Gleichstand die aeltere."""
    if not aussagen:
        return None
    return min(
        aussagen,
        key=lambda a: (-_relevanz(a, beitrag_id), angelegt_am(a), str(a.id)),
    )


async def kontext_laden(beitrag_id: uuid.UUID, statement_service) -> BeitragKontext:
    aussage = aussage_waehlen(
        await statement_service.zu_antwort(beitrag_id), beitrag_id
    )
    if aussage is None:
        return BeitragKontext()

    andere = sorted(
        (v for v in aussage.replysuggestions if v.id != beitrag_id),
        key=lambda v: -v.relevance,
    )
    ids = list(dict.fromkeys(v.id for v in andere))[:VORSCHLAEGE_HOECHSTENS]
    weitere = await statement_service.sichtbare_antworten(ids)
    return BeitragKontext(
        aussage=AussageKurz(id=aussage.id, text=aussage.text),
        weitere_antworten=weitere[:WEITERE_ANTWORTEN_HOECHSTENS],
    )
