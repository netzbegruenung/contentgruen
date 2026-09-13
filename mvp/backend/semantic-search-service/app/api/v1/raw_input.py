"""
Fangkorb-Endpunkte: einwerfen, auflisten, einzeln lesen und destillieren.

Destillieren heisst: einen Satz formulieren (Entwurf, je Person), dann entweder
verwerfen oder einen Beitrag daraus machen und den Einwurf damit verknuepfen.
Eine Sperre gibt es bewusst nicht - mehrere Leute duerfen denselben Einwurf
gleichzeitig destillieren.
"""

import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from domain.models.raw_input import (
    AktionNichtErlaubt,
    EinwurfNichtGefunden,
    RawInputSource,
    UebergangNichtErlaubt,
)
from dtos.raw_input import (
    AddRawInputRequest,
    AddRawInputResponse,
    DraftResponse,
    GetRawInputsResponse,
    RawInputResponse,
    SaveDraftRequest,
    UpdateRawInputStatusRequest,
)
from repositories.raw_input_repository import (
    RawInputRepository,
    get_raw_input_repository,
)

router = APIRouter()
logger = logging.getLogger(__name__)

NICHT_GEFUNDEN = "Diesen Einwurf gibt es nicht."


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
        raise HTTPException(status_code=401, detail="Dafuer musst du angemeldet sein.")
    return person


@router.post("/addRawInput", response_model=AddRawInputResponse, status_code=201)
async def add_raw_input(
    request: AddRawInputRequest,
    x_user: Optional[str] = Header(default=None),
    repository: RawInputRepository = Depends(get_raw_input_repository),
) -> AddRawInputResponse:
    """Einen Einwurf in den Fangkorb legen."""
    try:
        raw_input = repository.create(
            content=request.content,
            url=request.url,
            image_url=request.image_url,
            submitted_by=_einwerfende_person(x_user),
            source_channel=(request.source_channel or RawInputSource.WEB).value,
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
    x_user: Optional[str] = Header(default=None),
    repository: RawInputRepository = Depends(get_raw_input_repository),
) -> GetRawInputsResponse:
    """
    Den Fangkorb auflisten: eigene Einwuerfe zuerst, dann neueste zuerst.

    Absichtlich alle Einwuerfe, nicht nur die eigenen: der Fangkorb ist ein
    gemeinsamer Vorrat. Die anfragende Person bestimmt nur die Reihenfolge und
    welcher Entwurfssatz mitkommt (ihr eigener).
    """
    try:
        offset = (page - 1) * page_size
        rows = repository.get_all(
            limit=page_size,
            offset=offset,
            current_user=_einwerfende_person(x_user),
        )
        results: List[RawInputResponse] = [RawInputResponse(**row) for row in rows]
        return GetRawInputsResponse(
            results_count=len(results),
            results=results,
            total_records_count=repository.count(),
        )
    except Exception as e:
        logger.error(f"Fehler in /getRawInputs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Der Fangkorb konnte nicht geladen werden."
        )


@router.get("/{raw_input_id}", response_model=RawInputResponse)
async def get_raw_input(
    raw_input_id: uuid.UUID,
    x_user: Optional[str] = Header(default=None),
    repository: RawInputRepository = Depends(get_raw_input_repository),
) -> RawInputResponse:
    """
    Einen Einwurf lesen, mit eigenem Entwurfssatz.

    Die Destillier-Ansicht laedt hierueber nach einem PWA-Neustart alles, was sie
    braucht - in der Adresse steht nur die ID.
    """
    try:
        row = repository.get_by_id(raw_input_id, _einwerfende_person(x_user))
    except Exception as e:
        logger.error(f"Fehler in GET /rawinput/{{id}}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Der Einwurf konnte nicht geladen werden."
        )
    if row is None:
        raise HTTPException(status_code=404, detail=NICHT_GEFUNDEN)
    return RawInputResponse(**row)


@router.put("/{raw_input_id}/draft", response_model=DraftResponse)
async def save_draft(
    raw_input_id: uuid.UUID,
    request: SaveDraftRequest,
    x_user: Optional[str] = Header(default=None),
    repository: RawInputRepository = Depends(get_raw_input_repository),
) -> DraftResponse:
    """
    Den eigenen Entwurfssatz speichern; ein leerer Satz loescht ihn.

    Wird oft aufgerufen (verzoegert beim Tippen, beim Verlassen des Felds, beim
    Wegwechseln der App) und ist deshalb idempotent und nicht gedrosselt.
    """
    person = _angemeldete_person(x_user)
    try:
        gespeichert = repository.save_draft(raw_input_id, person, request.sentence)
        return DraftResponse(**gespeichert)
    except EinwurfNichtGefunden:
        raise HTTPException(status_code=404, detail=NICHT_GEFUNDEN)
    except Exception as e:
        logger.error(f"Fehler in PUT /rawinput/{{id}}/draft: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Der Entwurf konnte nicht gespeichert werden."
        )


@router.patch("/{raw_input_id}/status", response_model=RawInputResponse)
async def update_status(
    raw_input_id: uuid.UUID,
    request: UpdateRawInputStatusRequest,
    x_user: Optional[str] = Header(default=None),
    repository: RawInputRepository = Depends(get_raw_input_repository),
) -> RawInputResponse:
    """
    Verwerfen (nur die einwerfende Person) oder als verarbeitet markieren.

    ``processed`` schreibt in derselben Transaktion die Verknuepfung mit dem
    entstandenen Beitrag. Erlaubt: discarded aus open, processed aus open oder
    discarded; eine Wiederholung desselben Ziels ist unschaedlich.
    """
    person = _angemeldete_person(x_user)
    try:
        row = repository.set_status(
            raw_input_id, request.status, person, request.content_id
        )
        return RawInputResponse(**row)
    except EinwurfNichtGefunden:
        raise HTTPException(status_code=404, detail=NICHT_GEFUNDEN)
    except AktionNichtErlaubt:
        raise HTTPException(
            status_code=403,
            detail="Verwerfen kann nur, wer den Einwurf eingeworfen hat.",
        )
    except UebergangNichtErlaubt as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Fehler in PATCH /rawinput/{{id}}/status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Der Status konnte nicht geaendert werden."
        )
