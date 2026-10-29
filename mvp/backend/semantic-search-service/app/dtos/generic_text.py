from uuid import UUID
from domain.cc0_hinweis import Cc0Wortlaut
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional

from domain.models.generic_text import GenericText
from dtos.beitrag import HintergrundinfoResponse, HintergrundinfoTreffer


### AddGenericText ###

# Wie im Antwort-auf-Feld des Formulars.
AUSSAGE_MIN_ZEICHEN = 10

HINTERGRUNDINFO_TEXT_MAX = 2000


class ReferenceInput(BaseModel):
    reference_string: str
    description: Optional[str] = None


class AddGenericTextRequest(BaseModel):
    generictext: GenericText
    references: List[ReferenceInput]
    # Kennung des CC0-Hinweises, den die Person beim Speichern gesehen hat (#431,
    # domain/cc0_hinweis.py).
    cc0_wortlaut: Cc0Wortlaut = None
    # Worauf die Hintergrundinfo antwortet: ID einer vorhandenen Aussage oder, wenn
    # keine bekannt ist, ihr Text. Ohne beides steht sie fuer sich.
    statement_id: Optional[UUID] = None
    statement_text: Optional[str] = Field(default=None, max_length=1000)
    # Die Person hat diese vorhandene Hintergrundinfo gesehen und speichert trotzdem:
    # Dann wird die neue angelegt, obwohl sie deren Dublette ist. Gilt nur fuer die
    # gezeigte - ist inzwischen eine andere vorhanden, sieht die Person erst sie.
    trotz_dublette_von: Optional[UUID] = None
    # Die Person nimmt diese vorhandene, eigene Hintergrundinfo statt eine neue zu
    # speichern: Dann haengt sie an der mitgeschickten Aussage. Erst diese Wahl
    # verknuepft. Gilt wie trotz_dublette_von nur fuer die gezeigte.
    vorhanden_nehmen: Optional[UUID] = None

    # Trotzdem speichern und die vorhandene nehmen schliessen einander aus.
    @model_validator(mode="after")
    def hoechstens_eine_entscheidung(self) -> "AddGenericTextRequest":
        if self.trotz_dublette_von is not None and self.vorhanden_nehmen is not None:
            raise ValueError(
                "trotz_dublette_von und vorhanden_nehmen schliessen einander aus"
            )
        return self

    # Leer (oder nur Leerraum) heisst: keine Aussage. Sonst mindestens
    # AUSSAGE_MIN_ZEICHEN - kuerzer ist keine Aussage, auf die man antworten kann.
    @field_validator("statement_text")
    @classmethod
    def aussage_leer_oder_lang_genug(cls, text: Optional[str]) -> Optional[str]:
        if text is None or not text.strip():
            return None
        if len(text.strip()) < AUSSAGE_MIN_ZEICHEN:
            raise ValueError(
                f"Die Aussage braucht mindestens {AUSSAGE_MIN_ZEICHEN} Zeichen"
            )
        return text

    # 2000 Zeichen wie im Formular; nur beim Anlegen, damit aeltere, laengere
    # Eintraege lesbar bleiben (wie beim Kommentar).
    @field_validator("generictext")
    @classmethod
    def text_hoechstens_2000_zeichen(cls, generictext: GenericText) -> GenericText:
        if len(generictext.text) > HINTERGRUNDINFO_TEXT_MAX:
            raise ValueError(
                f"Der Text darf hoechstens {HINTERGRUNDINFO_TEXT_MAX} Zeichen lang sein"
            )
        return generictext


class AddGenericTextResponse(BaseModel):
    id: UUID
    # Die Aussage, an der die Hintergrundinfo jetzt haengt; None ohne Aussage oder
    # wenn die Verknuepfung scheiterte.
    statement_id: Optional[UUID] = None
    # Ihr Text - bei Text-Anfragen kann das eine schon vorhandene, sehr aehnliche
    # Aussage sein, nicht wortgleich mit dem Getippten.
    statement_text: Optional[str] = None
    # Ohne Dublette: False nur, wenn eine Aussage angegeben war und nicht verknuepft
    # werden konnte. Bei einer Dublette True nur, wenn die Person die eigene mit
    # vorhanden_nehmen genommen hat und sie jetzt an der Aussage haengt; sonst False.
    verknuepft: bool = True
    # True: Es gibt schon eine sehr aehnliche Hintergrundinfo; id ist deren ID, nichts
    # wurde angelegt. Wie beim Kommentar (dtos/commentary.py) entscheidet die Person:
    # zustimmen (Stimme), die eigene mit vorhanden_nehmen nehmen oder mit
    # trotz_dublette_von trotzdem speichern. Eine fremde wird nie verknuepft.
    dublette: bool = False
    # Titel der vorhandenen Hintergrundinfo, damit das Formular sie nennen kann.
    vorhanden_titel: Optional[str] = None
    # Die vorhandene ist von derselben Person. Ohne Dublette False.
    vorhanden_eigen: bool = False


### GetAll ###


class GenericTextGetAllResponse(BaseModel):
    results_count: int
    results: List[HintergrundinfoResponse]
    total_records_count: int


### SearchGenericText ###


class SearchGenericTextByTextRequest(BaseModel):
    query_text: str
    limit: int = 10
    # TODO: Add a field to specify the search type (content, commentary, etc.)
    # TODO: Add a field to specify minimum score


class GenericTextSearchResponse(BaseModel):
    results: List[HintergrundinfoTreffer]
