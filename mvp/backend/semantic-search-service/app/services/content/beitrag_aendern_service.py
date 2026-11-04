"""
Der Autor aendert seinen Beitrag: Titel, Text und Herkunft (#299), beim Kommentar
auch Kurz- und Langfassung (#551).

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
from dtos.commentary import KOMMENTAR_TEXT_MAX, KURZFASSUNG_MAX, LANGFASSUNG_MAX
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

# Ob zum Beitrag eine Meldung offen ist (ContentReportRepository.hat_offene_meldung).
OffeneMeldung = Callable[[uuid.UUID], bool]


class TextZuLang(Validierungsfehler):
    """Der neue Text ist laenger, als der Beitragstyp beim Anlegen erlaubt."""


class FassungNichtMoeglich(Validierungsfehler):
    """Kurz- oder Langfassung fuer einen Beitragstyp ohne Fassungen."""


@dataclass(frozen=True)
class HerkunftAngabe:
    reference_string: str
    description: Optional[str] = None


@dataclass(frozen=True)
class Aenderung:
    titel: str
    text: str
    herkuenfte: List[HerkunftAngabe] = field(default_factory=list)
    # Kennung des CC0-Hinweises, den der Dialog gezeigt hat; None von einer aelteren App.
    cc0_wortlaut: Optional[str] = None
    # Kurz- und Langfassung (#551), nur beim Kommentar: None laesst die gespeicherte
    # stehen (eine aeltere App schickt keine), "" entfernt sie.
    kurzfassung: Optional[str] = None
    langfassung: Optional[str] = None


class AenderErgebnis(Enum):
    GEAENDERT = "geaendert"
    NICHT_DA = "nicht_da"
    """Kein Beitrag unter der ID, oder er ist gesperrt oder geloescht."""
    NICHT_AUTOR = "nicht_autor"
    NICHT_AENDERBAR = "nicht_aenderbar"
    """Ein Beitragstyp, den man (noch) nicht aendern kann: Post und Bild."""
    MELDUNG_OFFEN = "meldung_offen"
    """Eine Meldung ist offen: Der Admin soll den gemeldeten Wortlaut sehen."""


class BeitragAendernService:
    def __init__(
        self,
        repository: IBaseContentRepository,
        herkunft_id: HerkunftId,
        offene_meldung: OffeneMeldung,
    ):
        self.repository = repository
        self.herkunft_id = herkunft_id
        self.offene_meldung = offene_meldung

    async def aendern(
        self, beitrag_id: uuid.UUID, aufrufer: str, aenderung: Aenderung
    ) -> AenderErgebnis:
        """
        Titel, Text und Herkunft ersetzen, wenn aufrufer der Autor ist.

        Gesperrte und geloeschte Beitraege sind fuer den Autor nicht da, wie beim
        Loeschen (BeitragLoeschenService). Solange eine Meldung offen ist, bleibt
        der gemeldete Wortlaut stehen (Entscheidung zu #299). Sperrt ein Admin zwischen Lesen und
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
        # Erst nach der Autorpruefung: Andere erfahren nichts ueber Meldungen.
        if self.offene_meldung(beitrag_id):
            return AenderErgebnis.MELDUNG_OFFEN
        if len(aenderung.text) > hoechstens:
            raise TextZuLang(f"Der Text darf höchstens {hoechstens} Zeichen lang sein")
        fassungen = _fassungen(beitrag.content_type, aenderung)

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
            **fassungen,
        }
        # Die neue Formulierung steht unter dem zuletzt gezeigten Wortlaut.
        if aenderung.cc0_wortlaut is not None:
            felder["cc0_wortlaut"] = aenderung.cc0_wortlaut
        await self.repository.inhalt_aendern(
            beitrag_id, beitrag.content_type.value, felder, nicht_aus=AUSGEBLENDET
        )
        logger.info(f"Beitrag {beitrag_id} vom Autor geaendert")
        return AenderErgebnis.GEAENDERT


def _fassungen(content_type: ContentType, aenderung: Aenderung) -> dict:
    """
    Die zu schreibenden Felder short_text und long_text; nur die angegebenen.

    Leer wird None wie beim Anlegen, sonst zeigte die Karte einen Reiter ohne Text.
    Die Grenzen sind die des Anlegens (AddCommentaryRequest).

    Raises:
    - FassungNichtMoeglich, wenn ein Beitrag ohne Fassungen eine bekommen soll.
    - TextZuLang, wenn eine Fassung ihre Grenze ueberschreitet.
    """
    angaben = {
        "short_text": (aenderung.kurzfassung, KURZFASSUNG_MAX, "Kurzfassung"),
        "long_text": (aenderung.langfassung, LANGFASSUNG_MAX, "Langfassung"),
    }
    felder = {}
    for feld, (wert, grenze, name) in angaben.items():
        if wert is None:
            continue
        if content_type is not ContentType.COMMENTARY:
            if wert:
                raise FassungNichtMoeglich(
                    "Kurz- und Langfassung gibt es nur beim Kommentar"
                )
            continue
        if len(wert) > grenze:
            raise TextZuLang(f"Die {name} darf höchstens {grenze} Zeichen lang sein")
        felder[feld] = wert or None
    return felder


def _als_payload(modell) -> dict:
    """Wie upsert() speichert: JSON-Form, Zeitpunkte als ISO-Text."""
    return json.loads(modell.model_dump_json())
