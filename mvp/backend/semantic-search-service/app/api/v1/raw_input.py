"""
Fangkorb-Endpunkte: einwerfen, auflisten, nach gleichem Link suchen, einzeln
lesen und destillieren.

Drei Stufen: Einwerfen, Destillieren (einen Satz formulieren, je Person),
Ausformulieren (den Einwurf mit einem Beitrag verknuepfen, einem neuen oder einem
vorhandenen).
Eine Sperre gibt es bewusst nicht - mehrere Leute duerfen denselben Einwurf
gleichzeitig destillieren, und alle Saetze sind fuer alle Angemeldeten sichtbar,
die Kennungen der Personen aber nur fuer Admins (#385).
"""

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from dependencies import (
    get_aufrufer,
    get_commentary_service,
    get_generic_text_service,
    get_post_service,
)
from domain.link_vergleich import links_im_text_ohne_tracking, ohne_tracking
from domain.models.content_type import ContentType
from domain.models.raw_input import (
    AktionNichtErlaubt,
    EinwurfNichtGefunden,
    RawInputSource,
    RawInputStatus,
    UebergangNichtErlaubt,
)
from dtos.raw_input import (
    AddRawInputRequest,
    AddRawInputResponse,
    DraftResponse,
    GetRawInputsResponse,
    GleicherLinkRequest,
    GleicherLinkResponse,
    RawInputResponse,
    SaveDraftRequest,
    UpdateRawInputStatusRequest,
)
from services.beitrag_fuer_aufrufer import (
    AUSFORMULIERER,
    DESTILLIERER,
    EINWURF,
    SATZ,
    Aufrufer,
    personen_fuer_aufrufer,
)
from repositories.raw_input_repository import (
    RawInputRepository,
    get_raw_input_repository,
)

router = APIRouter()
logger = logging.getLogger(__name__)

NICHT_GEFUNDEN = "Diesen Einwurf gibt es nicht."
BEITRAG_FEHLT = "Diesen Beitrag gibt es nicht."


def _einwerfende_person(x_user: Optional[str]) -> Optional[str]:
    """
    Die Nutzerkennung aus dem X-User-Header, oder None.

    Das BFF setzt fuer oeffentliche Endpunkte "anonymous"; der Fangkorb ist keiner
    davon, aber ein solcher Wert waere eine Pseudo-Kennung und wird zu None. Damit
    bedeutet ``submitted_by IS NULL`` genau eine Sache: niemand Bekanntes.
    """
    if not x_user or x_user == "anonymous":
        return None
    return x_user


def _angemeldete_person(x_user: Optional[str]) -> str:
    """Wie _einwerfende_person, aber ohne Kennung gibt es hier nichts zu tun."""
    person = _einwerfende_person(x_user)
    if person is None:
        raise HTTPException(status_code=401, detail="Dafür musst du angemeldet sein.")
    return person


def _einwuerfe_fuer_aufrufer(
    rows: List[dict], aufrufer: Aufrufer, mit_namen: bool = True
) -> List[RawInputResponse]:
    """
    Die Einwuerfe, wie der Aufrufer sie sieht (#385, Regel aus #333): Anzeigenamen
    und Kennzeichen zu Einwerfer und Satz-Autoren aus einer Abfrage fuer die ganze
    Seite; die Kennungen, auch von Destillierer und Ausformulierer, nur fuer Admins.
    Ohne ``mit_namen`` nur die Kennungen, fuer Antworten, die keine Person zeigen.
    """
    einwuerfe = [RawInputResponse(**row) for row in rows]
    gruppen = [
        (einwuerfe, EINWURF),
        ([satz for einwurf in einwuerfe for satz in einwurf.drafts], SATZ),
        (einwuerfe, DESTILLIERER),
        (einwuerfe, AUSFORMULIERER),
        ([link for einwurf in einwuerfe for link in einwurf.links], AUSFORMULIERER),
    ]
    if not mit_namen:
        gruppen = [(objekte, bezug.nur_kennung()) for objekte, bezug in gruppen]
    personen_fuer_aufrufer(aufrufer, *gruppen)
    return einwuerfe


def _seite(rows: List[dict], gesamt: int, aufrufer: Aufrufer) -> GetRawInputsResponse:
    """Eine Seite Einwuerfe fuer den Aufrufer, wie Fangkorb und Meine Einwuerfe sie liefern."""
    results = _einwuerfe_fuer_aufrufer(rows, aufrufer)
    return GetRawInputsResponse(
        results_count=len(results), results=results, total_records_count=gesamt
    )


@router.post("/addRawInput", response_model=AddRawInputResponse, status_code=201)
async def add_raw_input(
    request: AddRawInputRequest,
    aufrufer: Aufrufer = Depends(get_aufrufer),
    repository: RawInputRepository = Depends(get_raw_input_repository),
) -> AddRawInputResponse:
    """Einen Einwurf in den Fangkorb legen."""
    try:
        raw_input = repository.create(
            content=links_im_text_ohne_tracking(request.content),
            url=ohne_tracking(request.url),
            image_url=request.image_url,
            submitted_by=_einwerfende_person(aufrufer.kennung),
            source_channel=(request.source_channel or RawInputSource.WEB).value,
            cc0_wortlaut=request.cc0_wortlaut,
        )
        return AddRawInputResponse(id=raw_input["id"])
    except Exception as e:
        logger.error(f"Fehler in /addRawInput: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Der Einwurf konnte nicht gespeichert werden. Bitte versuche es erneut.",
        )


@router.get("/getRawInputs", response_model=GetRawInputsResponse)
async def get_raw_inputs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    aufrufer: Aufrufer = Depends(get_aufrufer),
    repository: RawInputRepository = Depends(get_raw_input_repository),
) -> GetRawInputsResponse:
    """
    Den Fangkorb auflisten: eigene Einwuerfe zuerst, dann neueste zuerst.

    Absichtlich alle Einwuerfe, nicht nur die eigenen: der Fangkorb ist ein
    gemeinsamer Vorrat. Je Einwurf kommen Status, ``destilled_by``, alle Saetze
    (Text, Person, Zeitpunkt) und alle verknuepften Beitraege (Typ, ID,
    ``draft_id``) mit. Die anfragende Person bestimmt nur die Reihenfolge und
    welcher Satz als ``own_draft`` mitkommt.
    """
    try:
        offset = (page - 1) * page_size
        rows = repository.get_all(
            limit=page_size,
            offset=offset,
            current_user=_einwerfende_person(aufrufer.kennung),
        )
        return _seite(rows, repository.count(), aufrufer)
    except Exception as e:
        logger.error(f"Fehler in /getRawInputs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Der Fangkorb konnte nicht geladen werden."
        )


@router.post("/gleicherLink", response_model=GleicherLinkResponse)
async def einwuerfe_mit_gleichem_link(
    request: GleicherLinkRequest,
    aufrufer: Aufrufer = Depends(get_aufrufer),
    repository: RawInputRepository = Depends(get_raw_input_repository),
) -> GleicherLinkResponse:
    """
    Einwuerfe mit gleichem Link, fuer die Anzeige beim Einwerfen (#263).

    Was als gleicher Link gilt, steht in ``domain.link_vergleich``. Die Anzeige
    haelt niemanden auf - eingeworfen werden darf trotzdem. Kein Link ergibt eine
    leere Liste, keinen Fehler: Das Formular fragt schon beim Tippen.

    POST statt GET, obwohl nur gelesen wird: Der Link steht so im Body und nicht
    in der Adresse, die Webserver und Proxy protokollieren. Links fuehren oft auf
    Profile Dritter. Anzeigenamen loest der Endpunkt nicht auf: Das Formular
    zeigt nur Stufe und Beitrag. Die Kennungen sehen wie ueberall nur Admins (#385).
    """
    person = _angemeldete_person(aufrufer.kennung)
    try:
        rows = repository.mit_gleichem_link(request.url, person)
        return GleicherLinkResponse(
            results=_einwuerfe_fuer_aufrufer(rows, aufrufer, mit_namen=False)
        )
    except Exception as e:
        logger.error(f"Fehler in /gleicherLink: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Der Fangkorb konnte nicht geprüft werden."
        )


@router.get("/getOwnRawInputs", response_model=GetRawInputsResponse)
async def get_own_raw_inputs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    aufrufer: Aufrufer = Depends(get_aufrufer),
    repository: RawInputRepository = Depends(get_raw_input_repository),
) -> GetRawInputsResponse:
    """
    Meine Einwuerfe: nur, was die anfragende Person eingeworfen hat, neueste zuerst.

    Die Rueckmeldung an den Einwerfer, was aus seinen Einwuerfen geworden ist - jede
    Stufe, auch verworfen, mit allen verknuepften Beitraegen. Steht vor /{id}, sonst
    lese FastAPI den Pfad als Einwurf-ID.
    """
    person = _angemeldete_person(aufrufer.kennung)
    try:
        rows = repository.get_all(
            limit=page_size,
            offset=(page - 1) * page_size,
            current_user=person,
            submitted_by=person,
        )
        return _seite(rows, repository.count(submitted_by=person), aufrufer)
    except Exception as e:
        logger.error(f"Fehler in /getOwnRawInputs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Deine Einwürfe konnten nicht geladen werden."
        )


@router.get("/{raw_input_id}", response_model=RawInputResponse)
async def get_raw_input(
    raw_input_id: uuid.UUID,
    aufrufer: Aufrufer = Depends(get_aufrufer),
    repository: RawInputRepository = Depends(get_raw_input_repository),
) -> RawInputResponse:
    """
    Einen Einwurf lesen, mit allen Saetzen und dem eigenen als ``own_draft``.

    Die Destillier-Ansicht laedt hierueber nach einem PWA-Neustart alles, was sie
    braucht - in der Adresse steht nur die ID.
    """
    try:
        row = repository.get_by_id(raw_input_id, _einwerfende_person(aufrufer.kennung))
    except Exception as e:
        logger.error(f"Fehler in GET /rawinput/{{id}}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Der Einwurf konnte nicht geladen werden."
        )
    if row is None:
        raise HTTPException(status_code=404, detail=NICHT_GEFUNDEN)
    return _einwuerfe_fuer_aufrufer([row], aufrufer)[0]


@router.put("/{raw_input_id}/draft", response_model=DraftResponse)
async def save_draft(
    raw_input_id: uuid.UUID,
    request: SaveDraftRequest,
    aufrufer: Aufrufer = Depends(get_aufrufer),
    repository: RawInputRepository = Depends(get_raw_input_repository),
) -> DraftResponse:
    """
    Den eigenen Satz speichern; ein leerer Satz loescht ihn.

    Der erste Satz macht einen offenen Einwurf zu ``in_progress`` und traegt
    ``destilled_by`` ein; wird der letzte Satz geloescht, ist er wieder offen.
    Wird oft aufgerufen (verzoegert beim Tippen, beim Verlassen des Felds, beim
    Wegwechseln der App) und ist deshalb idempotent und nicht gedrosselt.
    """
    person = _angemeldete_person(aufrufer.kennung)
    try:
        gespeichert = repository.save_draft(
            raw_input_id, person, request.sentence, cc0_wortlaut=request.cc0_wortlaut
        )
        return DraftResponse(**gespeichert)
    except EinwurfNichtGefunden:
        raise HTTPException(status_code=404, detail=NICHT_GEFUNDEN)
    except Exception as e:
        logger.error(f"Fehler in PUT /rawinput/{{id}}/draft: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Der Satz konnte nicht gespeichert werden."
        )


async def _beitrag_pruefen(
    content_id: uuid.UUID,
    content_type: Optional[ContentType],
    dienste: dict,
) -> None:
    """
    Gibt es den Beitrag, mit dem der Einwurf verknuepft werden soll?

    Ohne diese Pruefung konnte jede angemeldete Person jeden Einwurf mit einer
    erfundenen ID auf "ausformuliert" setzen; die Verknuepfung zeigte ins Leere.
    Geprueft werden Existenz und Typ, nicht der Autor: Wer beim Ausformulieren
    einem vorhandenen, fremden Kommentar zustimmt, verknuepft den Einwurf mit ihm.

    Ohne ``content_type`` (aeltere App-Version) genuegt ein Beitrag eines der
    destillierbaren Typen. "Nicht gefunden" und "anderer Typ" melden die Dienste als
    ValueError; alles andere ist ein echter Fehler und geht weiter - auch ein
    pydantic.ValidationError, obwohl er von ValueError erbt.
    """
    kandidaten = [dienste[content_type]] if content_type else list(dienste.values())
    for dienst in kandidaten:
        try:
            await dienst.get(content_id)
            return
        except ValidationError:
            # Auch ein ValueError, aber kein "gibt es nicht": der Datensatz ist
            # da und nicht lesbar. Das ist ein Fehler, keine falsche Eingabe.
            raise
        except ValueError:
            continue
    raise HTTPException(status_code=422, detail=BEITRAG_FEHLT)


@router.patch("/{raw_input_id}/status", response_model=RawInputResponse)
async def update_status(
    raw_input_id: uuid.UUID,
    request: UpdateRawInputStatusRequest,
    aufrufer: Aufrufer = Depends(get_aufrufer),
    repository: RawInputRepository = Depends(get_raw_input_repository),
    commentary_service=Depends(get_commentary_service),
    generic_text_service=Depends(get_generic_text_service),
    post_service=Depends(get_post_service),
) -> RawInputResponse:
    """
    Verwerfen (der Einwerfer oder ein Admin) oder als ausformuliert markieren.

    Admin ist, wem das BFF ``X-Is-Admin: true`` mitgibt - dieselbe Grundlage wie
    ``require_admin``. Das BFF entfernt den Header aus jeder Client-Anfrage.

    ``processed`` schreibt in derselben Transaktion die Verknuepfung mit dem
    Beitrag (neu gespeichert oder vorhanden), seinem Typ und dem Satz des
    Ausformulierers.
    Erlaubt: discarded aus open oder in_progress, processed aus open, in_progress
    oder discarded; eine Wiederholung desselben Ziels ist unschaedlich. Den
    Beitrag hinter ``content_id`` muss es mit passendem Typ geben, sonst 422.
    """
    person = _angemeldete_person(aufrufer.kennung)
    try:
        if request.status == RawInputStatus.PROCESSED:
            # Erst der Einwurf, dann der Beitrag: Ein unbekannter Einwurf bleibt
            # 404, ein unerlaubter Wechsel 409 - egal, was hinter content_id steht.
            # Eine Wiederholung mit derselben content_id prueft den Beitrag nicht
            # erneut; er kann inzwischen geloescht sein, und die Wiederholung soll
            # unschaedlich bleiben.
            schon_verknuepft = repository.statuswechsel_vorpruefen(
                raw_input_id, request.status, person, request.content_id
            )
            if not schon_verknuepft:
                await _beitrag_pruefen(
                    request.content_id,
                    request.content_type,
                    {
                        ContentType.COMMENTARY: commentary_service,
                        ContentType.GENERIC_TEXT: generic_text_service,
                        ContentType.POST: post_service,
                    },
                )
        row = repository.set_status(
            raw_input_id,
            request.status,
            person,
            request.content_id,
            request.content_type.value if request.content_type else None,
            ist_admin=aufrufer.ist_admin,
        )
        return _einwuerfe_fuer_aufrufer([row], aufrufer)[0]
    except HTTPException:
        raise
    except EinwurfNichtGefunden:
        raise HTTPException(status_code=404, detail=NICHT_GEFUNDEN)
    except AktionNichtErlaubt:
        raise HTTPException(
            status_code=403,
            detail="Verwerfen können nur der Einwerfer und Admins.",
        )
    except UebergangNichtErlaubt as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Fehler in PATCH /rawinput/{{id}}/status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Der Status konnte nicht geändert werden."
        )
