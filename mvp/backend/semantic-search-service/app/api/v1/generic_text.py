from typing import List, Optional
from domain.models.zeit import utc_jetzt
from fastapi import APIRouter, HTTPException, Depends, Header
import datetime
import logging
from uuid import UUID

from dependencies import (
    get_generic_text_service,
    get_reference_service,
    get_statement_service,
)
from dtos.generic_text import (
    AddGenericTextRequest,
    AddGenericTextResponse,
    GenericTextGetAllResponse,
    GenericTextSearchResponse,
    SearchGenericTextByTextRequest,
)
from domain.models.base_content import BaseContentSearchResult
from services.content.base_content_service import Dublettenpruefung
from services.content.generic_text_service import (
    GenericTextService,
    zu_pruefender_text,
)
from services.anzeigename_service import angemeldet, get_anzeigename_service
from services.content.reference_service import ReferenceService
from services.content.statement_service import AussageNichtGefunden, StatementService
from domain.models.content_type import ContentType
from domain.models.generic_text import GenericTextDbEntry, GenericTextReference
from domain.models.reference import Reference
from domain.models.content_status import NEW_CONTENT_STATUS
from domain.models.content_origin import ContentOrigin


router = APIRouter()
logger = logging.getLogger(__name__)

# Wie eng eine Hintergrundinfo zu ihrer Aussage passt, wenn jemand sie ausdruecklich
# als Antwort darauf verfasst - etwas schwaecher als ein Kommentar.
HINTERGRUNDINFO_RELEVANZ = 0.9


def _ist_gezeigte(
    vorhanden: Optional[BaseContentSearchResult], angefragt: Optional[UUID]
) -> bool:
    """Die Entscheidung der Person gilt genau der vorhandenen, die sie gesehen hat."""
    return (
        vorhanden is not None
        and angefragt is not None
        and str(vorhanden.id) == str(angefragt)
    )


async def _herkunft_anlegen(
    request: AddGenericTextRequest, reference_service: ReferenceService, x_user: str
) -> List[GenericTextReference]:
    """
    Die Herkunftsangaben der Anfrage als Verknuepfungen: vorhandene Referenzen
    wiederverwenden, neue anlegen. Die Notiz gehoert an die Verknuepfung, nicht an
    die Referenz - dieselbe Quelle kann in einem anderen Beitrag anders beschrieben
    sein.
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


# Test endpoint to check if the API is running
@router.get("/")
async def read_test():
    return {"message": "This is a test endpoint"}


from fastapi import Query


# Endpoint to search generic text by UUID
@router.get("/getById")
async def get_by_id(
    generic_text_id: UUID = Query(
        ..., description="The UUID of the generic text to retrieve"
    ),
    generic_text_service: GenericTextService = Depends(get_generic_text_service),
    x_user: Optional[str] = Header(default=None),
):
    try:
        # Retrieve generic text by ID
        generic_text = await generic_text_service.get(generic_text_id)

        # If no generic text is found, raise a 404 error
        if generic_text is None:
            raise HTTPException(
                status_code=404,
                detail=f"GenericText with id {generic_text_id} not found",
            )

        if angemeldet(x_user):
            return get_anzeigename_service().mit_autor_name(generic_text)
        return generic_text

    except Exception as e:
        logger.error(
            f"Error fetching generic text with id {generic_text_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


# Retrieves all generic text from the index
@router.get("/getAll")
async def get_all(
    generic_text_service: GenericTextService = Depends(get_generic_text_service),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> GenericTextGetAllResponse:
    try:
        logger.debug("/getAll was called")

        offset = (page - 1) * page_size
        generic_text_index_results: List[GenericTextDbEntry] = (
            await generic_text_service.get_all(limit=page_size, offset=offset)
        )
        logger.debug(f"/getAll got {len(generic_text_index_results)} results")

        response: GenericTextGetAllResponse = GenericTextGetAllResponse(
            results_count=len(generic_text_index_results),
            results=generic_text_index_results,
            total_records_count=await generic_text_service.count(),
        )

        return response
    except Exception as e:
        logger.error(f"Error in /getAll: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Searches for generic texts in the generic_text_index using similarity search
@router.post("/searchGenericText", response_model=GenericTextSearchResponse)
async def search_generic_text(
    request: SearchGenericTextByTextRequest,
    generic_text_service: GenericTextService = Depends(get_generic_text_service),
) -> GenericTextSearchResponse:
    try:
        logger.debug("/searchGenericText was called")

        generic_text_index_results = await generic_text_service.search(
            request.query_text, request.limit
        )
        logger.debug(
            f"/searchGenericText got {len(generic_text_index_results)} results"
        )

        response: GenericTextSearchResponse = GenericTextSearchResponse(
            results=generic_text_index_results
        )

        return response
    except Exception as e:
        logger.error(f"Error in search_generic_text: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Adds a new generic text to the generic_text_index
@router.post("/addGenericText", response_model=AddGenericTextResponse)
async def add_generic_text(
    request: AddGenericTextRequest,
    generic_text_service: GenericTextService = Depends(get_generic_text_service),
    reference_service: ReferenceService = Depends(get_reference_service),
    statement_service: StatementService = Depends(get_statement_service),
    x_user: str = Header(...),
) -> AddGenericTextResponse:
    try:
        logger.debug("/addGenericText was called")

        if not x_user:
            raise HTTPException(status_code=400, detail="X-User header missing")

        # Pruefen und Anlegen unter einer Sperre je normalisiertem Text, wie beim
        # Kommentar (api/v1/commentary.py): Zwei gleichzeitige gleiche
        # Hintergrundinfos legen nur eine an, und die Dublette wird vor den
        # Herkunftsangaben geprueft - sonst entstuenden verwaiste Referenzen.
        text = zu_pruefender_text(request.generictext)
        async with generic_text_service.sperre(text):
            pruefung = await generic_text_service.pruefe_dublette(text)
            if _ist_gezeigte(pruefung.vorhanden, request.trotz_dublette_von):
                # Die Person hat genau diese vorhandene gesehen und entschieden:
                # anlegen. Der aehnlichste Treffer bleibt fuer most_similar_* erhalten.
                logger.info(
                    f"Generic text saved although an existing one is similar: {pruefung.vorhanden.id}"
                )
                pruefung = Dublettenpruefung(
                    vorhanden=None, aehnlichster=pruefung.aehnlichster
                )
            if pruefung.vorhanden is None and request.vorhanden_nehmen is not None:
                # Die gewaehlte vorhandene ist weg: Eine neue anzulegen, hat die
                # Person nicht gewaehlt.
                raise HTTPException(
                    status_code=409,
                    detail="The existing generic text is no longer available",
                )
            if pruefung.vorhanden is None:
                request.generictext.references = await _herkunft_anlegen(
                    request, reference_service, x_user
                )
                success, generic_text_id, _ = (
                    await generic_text_service.add_generic_text(
                        request.generictext,
                        x_user,
                        NEW_CONTENT_STATUS,
                        ContentOrigin.MANUALLY_CREATED,
                        dublettenpruefung=pruefung,
                    )
                )
                if not success:
                    raise HTTPException(
                        status_code=400, detail="Failed to add generic text"
                    )

        # Nichts angelegt? Dann ist die Antwort die vorhandene Hintergrundinfo.
        # Verknuepft wird sie nur, wenn sie von derselben Person ist und sie sie mit
        # vorhanden_nehmen gewaehlt hat - eine fremde nie (Glossar "Dublette"; zur
        # Begruendung siehe api/v1/commentary.py).
        vorhanden = pruefung.vorhanden
        dublette = vorhanden is not None
        vorhanden_eigen = dublette and vorhanden.original_author == x_user
        vorhanden_genommen = vorhanden_eigen and _ist_gezeigte(
            vorhanden, request.vorhanden_nehmen
        )
        if dublette:
            generic_text_id = vorhanden.id
            logger.info(
                f"Generic text is a duplicate of {generic_text_id} "
                f"({'same author' if vorhanden_eigen else 'other author'}, "
                f"{'taken' if vorhanden_genommen else 'not linked'})"
            )

        # Antwort auf eine Aussage: im selben Aufruf verknuepfen. Scheitert das,
        # bleibt die Hintergrundinfo gespeichert und die Antwort sagt es. Bei einer
        # Dublette True nur, wenn die genommene jetzt an der Aussage haengt.
        statement_id = None
        statement_text = None
        verknuepft = not dublette
        aussage_mitgeschickt = bool(
            request.statement_id or (request.statement_text or "").strip()
        )
        if aussage_mitgeschickt and (not dublette or vorhanden_genommen):
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
            except AussageNichtGefunden:
                # Erwartbar (Aussage geloescht, alter Link): ohne Traceback.
                logger.warning(
                    f"Generic text {generic_text_id} saved, but its statement {request.statement_id} no longer exists"
                )
                verknuepft = False
            except Exception as e:
                logger.error(
                    f"Generic text {generic_text_id} saved, but not linked to its statement: {e}",
                    exc_info=True,
                )
                verknuepft = False

        return AddGenericTextResponse(
            id=generic_text_id,
            statement_id=statement_id,
            statement_text=statement_text,
            verknuepft=verknuepft,
            dublette=dublette,
            vorhanden_titel=vorhanden.title if dublette else None,
            vorhanden_eigen=vorhanden_eigen,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error in add_generic_text: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in add_generic_text: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while adding generic text. Please try again later.",
        )


# getTitleForGenericText()


# getTagsForGenericText()


# getAnalysisForGenericText()
