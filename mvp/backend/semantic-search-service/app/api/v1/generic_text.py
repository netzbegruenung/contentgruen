from typing import List, Optional
from domain.models.zeit import utc_jetzt
from fastapi import APIRouter, HTTPException, Depends, Header
import logging
from uuid import UUID

from dependencies import (
    get_aussage_themen_service,
    get_aufrufer,
    get_generic_text_service,
    get_reference_service,
    get_statement_service,
)
from dtos.generic_text import (
    AddGenericTextRequest,
    AddGenericTextResponse,
)
from dtos.beitrag import VorhandenDto
from services.dublette import Dublette, VorhandenWeg, entscheidung_anwenden
from services.content.generic_text_service import (
    GenericTextService,
    zu_pruefender_text,
)
from services.beitrag_fuer_aufrufer import Aufrufer, als_responses
from dtos.beitrag import HintergrundinfoResponse
from services.content.reference_service import ReferenceService
from services.content.statement_service import AussageNichtGefunden, StatementService
from services.aussage_themen_service import AussageThemenService, themen_beim_anlegen
from dtos.statement import themen_dtos
from domain.models.content_type import ContentType
from domain.models.generic_text import GenericTextReference
from domain.models.reference import Reference
from domain.models.content_status import NEW_CONTENT_STATUS
from domain.models.content_origin import ContentOrigin
from core.fehler import INTERNER_FEHLER, UNGUELTIGE_ANFRAGE, Validierungsfehler


router = APIRouter()
logger = logging.getLogger(__name__)

# Wie eng eine Hintergrundinfo zu ihrer Aussage passt, wenn jemand sie ausdruecklich
# als Antwort darauf verfasst - etwas schwaecher als ein Kommentar.
HINTERGRUNDINFO_RELEVANZ = 0.9


async def _herkunft_anlegen(
    request: AddGenericTextRequest, reference_service: ReferenceService, x_user: str
) -> List[GenericTextReference]:
    """
    Die Herkunftsangaben der Anfrage als Verknuepfungen: eine schon gespeicherte
    Herkunft wiederverwenden, sonst neu anlegen. Die Notiz gehoert an die
    Verknuepfung, nicht an die Herkunft - dieselbe Herkunft kann in einem anderen
    Beitrag anders beschrieben sein.
    """
    verknuepfungen = []
    for ref_input in request.references or []:
        # First check if reference already exists (by exact match)
        existing_reference = await reference_service.find_exact_match(
            ref_input.reference_string
        )
        if existing_reference:
            reference_id = existing_reference.id
            logger.info(
                f"Reusing existing reference {reference_id}: {ref_input.reference_string}"
            )
        else:
            reference_item = Reference(
                text=ref_input.description
                or ref_input.reference_string,  # Use description for semantic indexing, fallback to string
                reference_string=ref_input.reference_string,
            )
            reference_id, _, _ = await reference_service.add_reference(
                reference_item,
                x_user,
                NEW_CONTENT_STATUS,
                ContentOrigin.MANUALLY_CREATED,
            )
            logger.info(
                f"Created new reference {reference_id}: {ref_input.reference_string}"
            )
        verknuepfungen.append(
            GenericTextReference(
                reference_id=reference_id,
                created=utc_jetzt(),
                description=ref_input.description,
            )
        )
    return verknuepfungen


from fastapi import Query


# Endpoint to search generic text by UUID
@router.get("/getById", response_model=HintergrundinfoResponse)
async def get_by_id(
    generic_text_id: UUID = Query(
        ..., description="The UUID of the generic text to retrieve"
    ),
    generic_text_service: GenericTextService = Depends(get_generic_text_service),
    aufrufer: Aufrufer = Depends(get_aufrufer),
) -> HintergrundinfoResponse:
    try:
        # Retrieve generic text by ID
        generic_text = await generic_text_service.get(generic_text_id)

        # If no generic text is found, raise a 404 error
        if generic_text is None:
            raise HTTPException(
                status_code=404,
                detail=f"GenericText with id {generic_text_id} not found",
            )

        return als_responses(HintergrundinfoResponse, [generic_text], aufrufer)[0]

    except Exception as e:
        logger.error(
            f"Error fetching generic text with id {generic_text_id}: {type(e).__name__}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=INTERNER_FEHLER)


# Adds a new generic text to the generic_text_index
@router.post("/addGenericText", response_model=AddGenericTextResponse)
async def add_generic_text(
    request: AddGenericTextRequest,
    generic_text_service: GenericTextService = Depends(get_generic_text_service),
    reference_service: ReferenceService = Depends(get_reference_service),
    statement_service: StatementService = Depends(get_statement_service),
    themen_service: AussageThemenService = Depends(get_aussage_themen_service),
    x_user: str = Header(...),
) -> AddGenericTextResponse:
    try:
        logger.debug("/addGenericText was called")

        if not x_user:
            raise HTTPException(status_code=400, detail="X-User header missing")

        # Pruefen und Anlegen unter einer Sperre je normalisiertem Text, wie beim
        # Kommentar (api/v1/commentary.py): Zwei gleichzeitige gleiche
        # Hintergrundinfos legen nur eine an, und die Dublette wird vor den
        # Herkunftsangaben geprueft - sonst entstuenden Herkuenfte, die an keinem
        # Beitrag haengen.
        text = zu_pruefender_text(request.generictext)
        async with generic_text_service.sperre(text):
            gefunden = await generic_text_service.pruefe_dublette(text)
            try:
                pruefung = entscheidung_anwenden(
                    gefunden, request.trotz_dublette_von, request.vorhanden_nehmen
                )
            except VorhandenWeg:
                # Die gewaehlte vorhandene ist weg.
                raise HTTPException(
                    status_code=409,
                    detail="The existing generic text is no longer available",
                )
            if gefunden.vorhanden is not None and pruefung.vorhanden is None:
                logger.info(
                    f"Generic text saved although an existing one is similar: {gefunden.vorhanden.id}"
                )
            if pruefung.vorhanden is None:
                request.generictext.references = await _herkunft_anlegen(
                    request, reference_service, x_user
                )
                # Ohne vorhandene in der Pruefung legt add_generic_text immer an.
                _, generic_text_id, _ = await generic_text_service.add_generic_text(
                    request.generictext,
                    x_user,
                    NEW_CONTENT_STATUS,
                    ContentOrigin.MANUALLY_CREATED,
                    dublettenpruefung=pruefung,
                    cc0_wortlaut=request.cc0_wortlaut,
                )

        # Nichts angelegt? Dann ist die Antwort die vorhandene Hintergrundinfo.
        # Verknuepft wird sie nur, wenn sie von derselben Person ist und sie sie mit
        # vorhanden_nehmen gewaehlt hat - eine fremde nie (Glossar "Dublette"; zur
        # Begruendung siehe api/v1/commentary.py).
        dublette = Dublette.aus(pruefung.vorhanden, x_user, request.vorhanden_nehmen)
        if dublette:
            generic_text_id = dublette.vorhanden.id
            logger.info(
                f"Generic text is a duplicate of {generic_text_id} "
                f"({'same author' if dublette.eigen else 'other author'}, "
                f"{'taken' if dublette.genommen else 'not linked'})"
            )

        # Antwort auf eine Aussage: im selben Aufruf verknuepfen. Scheitert das,
        # bleibt die Hintergrundinfo gespeichert und die Antwort sagt es. Bei einer
        # Dublette True nur, wenn die genommene jetzt an der Aussage haengt.
        statement_id = None
        statement_text = None
        themen: List[str] = []
        verknuepft = dublette is None
        aussage_mitgeschickt = bool(
            request.statement_id or (request.statement_text or "").strip()
        )
        if aussage_mitgeschickt and (dublette is None or dublette.genommen):
            try:
                statement_id, statement_text = (
                    await statement_service.beitrag_als_antwort_verknuepfen(
                        beitrag_id=generic_text_id,
                        content_type=ContentType.GENERIC_TEXT,
                        relevance=HINTERGRUNDINFO_RELEVANZ,
                        author=x_user,
                        statement_id=request.statement_id,
                        statement_text=request.statement_text,
                    )
                )
                verknuepft = True
                # Kam die Aussage per Text, gelten fuer sie die gewaehlten Themen
                # (#455); scheitert das Zuordnen, bleibt alles andere, wie es ist.
                if request.statement_id is None and request.themen:
                    themen = await themen_beim_anlegen(
                        themen_service, statement_id, request.themen
                    )
            except AussageNichtGefunden:
                # Erwartbar (Aussage geloescht, alter Link): ohne Traceback.
                logger.warning(
                    f"Generic text {generic_text_id} saved, but its statement {request.statement_id} no longer exists"
                )
                verknuepft = False
            except Exception as e:
                logger.error(
                    f"Generic text {generic_text_id} saved, but not linked to its statement: {type(e).__name__}",
                    exc_info=True,
                )
                verknuepft = False

        return AddGenericTextResponse(
            id=generic_text_id,
            statement_id=statement_id,
            statement_text=statement_text,
            themen=themen_dtos(themen),
            verknuepft=verknuepft,
            vorhanden=(
                VorhandenDto.aus(dublette.vorhanden, dublette.eigen)
                if dublette
                else None
            ),
        )

    except HTTPException:
        raise
    except Validierungsfehler as e:
        logger.warning(f"Validation error in add_generic_text: {type(e).__name__}")
        raise HTTPException(status_code=400, detail=e.antworttext)
    except ValueError as e:
        logger.warning(f"Validation error in add_generic_text: {type(e).__name__}")
        raise HTTPException(status_code=400, detail=UNGUELTIGE_ANFRAGE)
    except Exception as e:
        logger.error(
            f"Unexpected error in add_generic_text: {type(e).__name__}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while adding generic text. Please try again later.",
        )


# getTitleForGenericText()


# getTagsForGenericText()


# getAnalysisForGenericText()
