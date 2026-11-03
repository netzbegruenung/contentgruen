"""
Der Autor aendert seinen Beitrag: Titel, Text und Herkunft (#299).

Aenderbar sind Kommentar und Hintergrundinfo, die beiden Beitragstypen mit Herkunft
und Titelregel (CODING_STANDARDS.md). Es gelten dieselben Grenzen wie beim Anlegen.
Geschrieben werden nur die geaenderten Felder; Stimmen, Nutzung, Verknuepfungen mit
Aussagen und Einwuerfen bleiben. Der Vektor wird aus dem neuen Text berechnet, damit
die Suche ihn findet, und edit_history haelt fest, wer wann geaendert hat (ohne den
alten Wortlaut).
"""

import json
import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Awaitable, Callable, Dict, List, Optional

from pydantic import ValidationError

from core.fehler import Validierungsfehler
from domain.content_registry import BEITRAGSTYPEN
from domain.models.content_status import AUSGEBLENDET
from domain.models.content_type import ContentType
from domain.models.edit_entry import EditEntry
from domain.models.generic_text import GenericTextReference
from domain.models.zeit import utc_jetzt
from dtos.commentary import KOMMENTAR_TEXT_MAX
from dtos.generic_text import HINTERGRUNDINFO_TEXT_MAX
from repositories.interfaces.base_content_repository import IBaseContentRepository

logger = logging.getLogger(__name__)

# Je aenderbarem Typ die Laenge des Texts, wie beim Anlegen (dtos/).
TEXT_HOECHSTENS: Dict[ContentType, int] = {
    ContentType.COMMENTARY: KOMMENTAR_TEXT_MAX,
    ContentType.GENERIC_TEXT: HINTERGRUNDINFO_TEXT_MAX,
}

# Die ID der Herkunft zu (Adresse, Notiz, Autor): eine vorhandene oder eine neue
# (ReferenceService.herkunft_id).
HerkunftId = Callable[[str, Optional[str], str], Awaitable[uuid.UUID]]


class TextZuLang(Validierungsfehler):
    """Der neue Text ist laenger, als der Beitragstyp beim Anlegen erlaubt."""


@dataclass(frozen=True)
class HerkunftAngabe:
    reference_string: str
    description: Optional[str] = None


@dataclass(frozen=True)
class Aenderung:
    titel: str
    text: str
    herkuenfte: List[HerkunftAngabe] = field(default_factory=list)


class AenderErgebnis(Enum):
    GEAENDERT = "geaendert"
    NICHT_DA = "nicht_da"
    """Kein Beitrag unter der ID, oder er ist gesperrt oder geloescht."""
    NICHT_AUTOR = "nicht_autor"
    NICHT_AENDERBAR = "nicht_aenderbar"
    """Ein Beitragstyp, den man (noch) nicht aendern kann: Post und Bild."""


class BeitragAendernService:
    def __init__(self, repository: IBaseContentRepository, herkunft_id: HerkunftId):
        self.repository = repository
        self.herkunft_id = herkunft_id

    async def aendern(
        self, beitrag_id: uuid.UUID, aufrufer: str, aenderung: Aenderung
    ) -> AenderErgebnis:
        """
        Titel, Text und Herkunft ersetzen, wenn aufrufer der Autor ist.

        Gesperrte und geloeschte Beitraege sind fuer den Autor nicht da, wie beim
        Loeschen (BeitragLoeschenService). Sperrt ein Admin zwischen Lesen und
        Schreiben, schuetzt nicht_aus die Sperre im selben Schreibvorgang.

        Raises:
        - TextZuLang, wenn der Text die Grenze des Typs ueberschreitet.
        - ValidationError bei einem unlesbaren Datensatz (kein "nicht da").
        """
        try:
            beitrag = await self.repository.get(beitrag_id)
        except ValidationError:
            raise
        except ValueError:
            return AenderErgebnis.NICHT_DA

        if beitrag.content_type not in BEITRAGSTYPEN:
            return AenderErgebnis.NICHT_DA
        if beitrag.original_author != aufrufer:
            return AenderErgebnis.NICHT_AUTOR
        hoechstens = TEXT_HOECHSTENS.get(beitrag.content_type)
        if hoechstens is None:
            return AenderErgebnis.NICHT_AENDERBAR
        if len(aenderung.text) > hoechstens:
            raise TextZuLang(f"Der Text darf höchstens {hoechstens} Zeichen lang sein")

        jetzt = utc_jetzt()
        verknuepfungen = [
            # Kommentar und Hintergrundinfo speichern ihre Herkunft gleich.
            GenericTextReference(
                reference_id=await self.herkunft_id(
                    angabe.reference_string, angabe.description, aufrufer
                ),
                created=jetzt,
                description=angabe.description,
            )
            for angabe in aenderung.herkuenfte
        ]
        verlauf = [
            *beitrag.edit_history,
            EditEntry(editor=aufrufer, timestamp=jetzt, action="edit"),
        ]
        verlauf_payload = [_als_payload(e) for e in verlauf]
        felder = {
            "title": aenderung.titel,
            "text": aenderung.text,
            "references": [_als_payload(v) for v in verknuepfungen],
            "references_count": len(verknuepfungen),
            "edit_history": verlauf_payload,
            # Derselbe Zeitpunkt wie im Verlauf, in derselben Schreibweise.
            "last_modified": verlauf_payload[-1]["timestamp"],
            "last_modified_by": aufrufer,
        }
        await self.repository.inhalt_aendern(
            beitrag_id, beitrag.content_type.value, felder, nicht_aus=AUSGEBLENDET
        )
        logger.info(f"Beitrag {beitrag_id} vom Autor geaendert")
        return AenderErgebnis.GEAENDERT


def _als_payload(modell) -> dict:
    """Wie upsert() speichert: JSON-Form, Zeitpunkte als ISO-Text."""
    return json.loads(modell.model_dump_json())
