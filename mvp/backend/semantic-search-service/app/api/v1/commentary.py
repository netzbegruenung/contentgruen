import datetime
from domain.models.zeit import utc_jetzt
import logging
from fastapi import APIRouter, Header, HTTPException, Depends

from dependencies import (
    get_commentary_service,
    get_reference_service,
    get_statement_service,
)
from dtos.commentary import (
    AddCommentaryRequest,
    AddCommentaryResponse,
    CommentarySearchResponse,
    SearchCommentaryByTextRequest,
)
from services.content.commentary_service import CommentaryService
from services.content.statement_service import AussageNichtGefunden, StatementService
from domain.models.commentary import CommentaryReference
from services.content.reference_service import ReferenceService
from domain.models.reference import Reference
from domain.models.content_status import NEW_CONTENT_STATUS
from domain.models.content_origin import ContentOrigin
from domain.models.content_type import ContentType


router = APIRouter()
logger = logging.getLogger(__name__)

# Wie eng ein Kommentar zu seiner Aussage passt, wenn jemand ihn ausdruecklich
# als Antwort darauf verfasst.
KOMMENTAR_RELEVANZ = 1.0


# Test endpoint to check if the API is running
@router.get("/")
async def read_test():
    return {"message": "This is a test endpoint"}


from fastapi import Query
from uuid import UUID


# Endpoint to search commentary by UUID
@router.get("/getById")
async def get_by_id(
    commentary_id: UUID = Query(
        ..., description="The UUID of the commentary to retrieve"
    ),
    commentary_service: CommentaryService = Depends(get_commentary_service),
):
    try:
        # Retrieve commentary by ID
        commentary = await commentary_service.get(commentary_id)

        # If no commentary is found, raise a 404 error
        if commentary is None:
            raise HTTPException(
                status_code=404, detail=f"Commentary with id {commentary_id} not found"
            )

        return commentary

    except Exception as e:
        logger.error(
            f"Error fetching commentary with id {commentary_id}: {e}", exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


# Searches for commentaries in the commentary_index using similarity search
@router.post("/searchCommentaries", response_model=CommentarySearchResponse)
async def search_commentaries(
    request: SearchCommentaryByTextRequest,
    commentary_service: CommentaryService = Depends(get_commentary_service),
) -> CommentarySearchResponse:
    try:
        logger.debug("/searchCommentaries was called")

        commentary_index_results = await commentary_service.search(
            request.query_text, request.limit
        )
        logger.debug(f"/searchCommentaries got {len(commentary_index_results)} results")

        response: CommentarySearchResponse = CommentarySearchResponse(
            results=commentary_index_results
        )

        return response
    except Exception as e:
        logger.error(f"Error in search_commentaries: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Adds a new commentary to the commentary_index and for each reference in the request, adds a new reference to the reference_index
@router.post("/addCommentary", response_model=AddCommentaryResponse)
async def add_commentary(
    request: AddCommentaryRequest,
    commentary_service: CommentaryService = Depends(get_commentary_service),
    reference_service: ReferenceService = Depends(get_reference_service),
    statement_service: StatementService = Depends(get_statement_service),
    x_user: str = Header(...),
) -> AddCommentaryResponse:
    try:
        logger.debug("/addCommentary was called")

        if not x_user:
            raise HTTPException(status_code=400, detail="X-User header missing")

        # Pruefen und Anlegen unter einer Sperre je normalisiertem Kommentartext:
        # Zwei gleichzeitige gleiche Kommentare legen so nur einen an. Die Dublette
        # wird vor den Herkunftsangaben geprueft - sonst entstuenden Referenzen, die
        # an keinem Beitrag haengen. add_commentary uebernimmt das Pruefergebnis und
        # bettet nicht noch einmal ein.
        async with commentary_service.sperre(request.commentary.text):
            pruefung = await commentary_service.pruefe_dublette(request.commentary.text)
            if pruefung.vorhanden is None:
                # Je Eintrag (reference_id, Notiz): die Notiz gehoert an die Verknuepfung,
                # nicht an die Referenz - dieselbe Quelle kann in einem anderen Beitrag
                # anders beschrieben sein.
                new_references = []
                if request.references is not None and len(request.references) > 0:
                    # Create or find reference entries with duplicate detection
                    for ref_input in request.references:
                        # First check if reference already exists (by exact match)
                        existing_reference = await reference_service.find_exact_match(
                            ref_input.reference_string
                        )

                        if existing_reference:
                            # Reference exists - reuse it
                            reference_id = existing_reference.id
                            logger.info(
                                f"Reusing existing reference {reference_id}: {ref_input.reference_string}"
                            )
                            new_references.append((reference_id, ref_input.description))
                        else:
                            # Reference doesn't exist - create new one
                            reference_item = Reference(
                                text=ref_input.description
                                or ref_input.reference_string,  # Use description for semantic indexing, fallback to string
                                reference_string=ref_input.reference_string,
                            )

                            # Add new reference
                            reference_id, was_new, message = (
                                await reference_service.add_reference(
                                    reference_item,
                                    x_user,
                                    NEW_CONTENT_STATUS,
                                    ContentOrigin.MANUALLY_CREATED,
                                )
                            )
                            new_references.append((reference_id, ref_input.description))
                            logger.info(
                                f"Created new reference {reference_id}: {ref_input.reference_string}"
                            )

                for reference_id, description in new_references:
                    commentary_reference = CommentaryReference(
                        reference_id=reference_id,
                        created=utc_jetzt(),
                        description=description,
                    )

                    if not request.commentary.references:
                        request.commentary.references = []

                    request.commentary.references.append(commentary_reference)

                _, commentary_id, _ = await commentary_service.add_commentary(
                    request.commentary,
                    x_user,
                    NEW_CONTENT_STATUS,
                    ContentOrigin.MANUALLY_CREATED,
                    dublettenpruefung=pruefung,
                )

        # Nichts angelegt? Dann ist die Antwort der vorhandene Kommentar. Verknuepft
        # wird nur die eigene Dublette.
        #
        # Nicht, weil fremde Zuordnungen unerwuenscht waeren - im Gegenteil: Eine gute
        # Antwort passt oft auf viele Aussagen, und dass andere diese Zuordnung
        # vornehmen, ist gewollt. Ueber das Beitragsformular griffe sie aber nur bei
        # wortgleichem Text: Ein Wort daneben, und statt der Zuordnung entstuende eine
        # zweite Kopie derselben Antwort. Die Zuordnung fremder Antworten bekommt
        # deshalb einen eigenen Weg an der Karte ("Passt auch auf ..."), der immer
        # funktioniert und die gewaehlte Aussage sichtbar macht.
        dublette = pruefung.vorhanden
        eigene_dublette = dublette is not None and dublette.original_author == x_user
        if dublette is not None:
            commentary_id = dublette.id
            logger.info(
                f"Commentary is a duplicate of {commentary_id} "
                f"({'same author' if eigene_dublette else 'other author, not linked'})"
            )

        # Antwort auf eine Aussage: im selben Aufruf verknuepfen. Scheitert das,
        # bleibt der Kommentar gespeichert und die Antwort sagt es. Bei einer eigenen
        # Dublette haengt der vorhandene Kommentar danach (auch) an dieser Aussage -
        # die Verknuepfung erkennt, wenn er dort schon haengt.
        statement_id = None
        statement_text = None
        verknuepft = True
        aussage_mitgeschickt = bool(
            request.statement_id or (request.statement_text or "").strip()
        )
        if aussage_mitgeschickt and (dublette is None or eigene_dublette):
            try:
                statement_id, statement_text = (
                    await statement_service.beitrag_als_antwort_verknuepfen(
                        beitrag_id=commentary_id,
                        content_type=ContentType.COMMENTARY,
                        relevance=KOMMENTAR_RELEVANZ,
                        author=x_user,
                        statement_id=request.statement_id,
                        statement_text=request.statement_text,
                    )
                )
            except AussageNichtGefunden:
                # Erwartbar (Aussage geloescht, alter Link): ohne Traceback.
                logger.warning(
                    f"Commentary {commentary_id} stored, but its statement {request.statement_id} no longer exists"
                )
                verknuepft = False
            except Exception as e:
                logger.error(
                    f"Commentary {commentary_id} stored, but not linked to its statement: {e}",
                    exc_info=True,
                )
                verknuepft = False

        return AddCommentaryResponse(
            id=commentary_id,
            statement_id=statement_id,
            statement_text=statement_text,
            verknuepft=verknuepft,
            duplikat=dublette is not None,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.warning(f"Validation error in add_commentary: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in add_commentary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while adding commentary. Please try again later.",
        )


# getTitleForCommentary()


# getTagsForCommentary()


# getAnalysisForCommentary()
