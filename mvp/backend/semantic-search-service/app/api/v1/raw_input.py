"""
Fangkorb-Endpunkte: einwerfen und auflisten.

Mehr ist bewusst nicht da. Bearbeitungs-Queue, Zuweisung und Punkte setzen
spaeter hierauf auf; das Datenmodell haelt ihnen die Tuer offen (Statusfeld,
n:m-Verknuepfungstabelle), gebaut ist davon nichts.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from domain.models.raw_input import RawInputSource
from dtos.raw_input import (
    AddRawInputRequest,
    AddRawInputResponse,
    GetRawInputsResponse,
    RawInputResponse,
)
from repositories.raw_input_repository import (
    RawInputRepository,
    get_raw_input_repository,
)

router = APIRouter()
logger = logging.getLogger(__name__)


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
            source_channel=RawInputSource.WEB.value,
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
    repository: RawInputRepository = Depends(get_raw_input_repository),
) -> GetRawInputsResponse:
    """
    Den Fangkorb auflisten, neueste zuerst.

    Absichtlich alle Einwuerfe, nicht nur die eigenen: der Fangkorb ist ein
    gemeinsamer Vorrat und diese Liste die Vorstufe der spaeteren Queue.
    """
    try:
        offset = (page - 1) * page_size
        rows = repository.get_all(limit=page_size, offset=offset)
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
