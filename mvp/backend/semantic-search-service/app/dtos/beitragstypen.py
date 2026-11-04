"""
Die Antwort je Beitragstyp, in der Schreibweise des Backends (``content_type``).

Ein Ort fuer alle Routen, die Beitraege verschiedener Typen ausliefern: "Diese Woche
oft genutzt" (api/v1/usage.py) und die eigene Adresse eines Beitrags
(api/v1/content.py, #300). Aussage und Herkunft fehlen: Sie sind keine Beitraege
(ADR 0002). Liegt nicht in dtos/beitrag.py, weil BildResponse von dort erbt.
"""

from typing import Dict, Type

from domain.models.content_type import ContentType
from dtos.beitrag import (
    BeitragResponse,
    HintergrundinfoResponse,
    KommentarResponse,
    PostResponse,
)
from dtos.image import BildResponse

ANTWORT_JE_TYP: Dict[str, Type[BeitragResponse]] = {
    ContentType.COMMENTARY.value: KommentarResponse,
    ContentType.GENERIC_TEXT.value: HintergrundinfoResponse,
    ContentType.POST.value: PostResponse,
    ContentType.IMAGE.value: BildResponse,
}
