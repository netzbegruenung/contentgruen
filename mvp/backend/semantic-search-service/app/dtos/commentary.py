from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

from domain.models.commentary import Commentary, CommentarySearchResult


### AddCommentary ###

# Wie im Antwort-auf-Feld des Formulars.
AUSSAGE_MIN_ZEICHEN = 10

KOMMENTAR_TEXT_MAX = 500


class ReferenceInput(BaseModel):
    reference_string: str
    description: Optional[str] = None


class AddCommentaryRequest(BaseModel):
    commentary: Commentary
    references: List[ReferenceInput]
    # Worauf der Kommentar antwortet: die ID einer vorhandenen Aussage oder, wenn
    # keine bekannt ist, ihr Text. Ohne beides steht der Kommentar fuer sich.
    statement_id: Optional[UUID] = None
    statement_text: Optional[str] = Field(default=None, max_length=1000)

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

    # Eine Antwort, die man so posten kann: 500 Zeichen wie im Formular. Bewusst
    # nur hier beim Anlegen und nicht im Modell - dort liesse sich ein aelterer,
    # laengerer Kommentar sonst nicht mehr lesen.
    @field_validator("commentary")
    @classmethod
    def text_hoechstens_500_zeichen(cls, commentary: Commentary) -> Commentary:
        if len(commentary.text) > KOMMENTAR_TEXT_MAX:
            raise ValueError(
                f"Der Kommentartext darf hoechstens {KOMMENTAR_TEXT_MAX} Zeichen lang sein"
            )
        return commentary


class AddCommentaryResponse(BaseModel):
    id: UUID
    # Die Aussage, an der der Kommentar jetzt haengt; None ohne Aussage oder wenn
    # die Verknuepfung scheiterte.
    statement_id: Optional[UUID] = None
    # Ihr Text - bei Text-Anfragen kann das eine schon vorhandene, sehr aehnliche
    # Aussage sein, nicht wortgleich mit dem Getippten.
    statement_text: Optional[str] = None
    # False nur, wenn eine Aussage angegeben war und nicht verknuepft werden
    # konnte. Der Kommentar ist dann trotzdem gespeichert.
    verknuepft: bool = True
    # True: Es gibt schon einen sehr aehnlichen Kommentar; id ist dessen ID und nichts
    # wurde angelegt. Stammt er von derselben Person und war eine Aussage angegeben,
    # ist er jetzt auch mit ihr verknuepft (statement_id/statement_text, verknuepft wie
    # oben); ist er von jemand anderem, bleiben die Aussagefelder leer.
    duplikat: bool = False


### SearchCommentary ###


class SearchCommentaryByTextRequest(BaseModel):
    query_text: str
    limit: int = 10
    # TODO: Add a field to specify the search type (content, commentary, etc.)
    # TODO: Add a field to specify minimum score


class CommentarySearchResponse(BaseModel):
    results: List[CommentarySearchResult]
