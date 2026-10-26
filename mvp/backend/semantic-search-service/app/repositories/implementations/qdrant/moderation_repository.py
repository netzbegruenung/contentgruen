import json
import logging
from typing import Any, Dict, List, Optional

from qdrant_client.models import FieldCondition, Filter, MatchValue

from domain.interfaces.embeddings_manager import IEmbeddingsManager
from domain.models.content_status import FELD_STATUS_VOR_SPERRE, ContentStatus
from domain.models.content_type import ContentType
from repositories.interfaces.moderation_repository import IModerationRepository
from services.embeddings.qdrant_embeddings_manager import get_embeddings_manager

logger = logging.getLogger(__name__)

# Wie viele Aussagen aus_aussagen_entfernen je Scroll-Seite holt.
AUSSAGEN_JE_SEITE = 100


def _nur(feld: str, wert: str) -> Filter:
    """Filter auf Punkte, deren Payload-Feld genau diesen Wert hat."""
    return Filter(must=[FieldCondition(key=feld, match=MatchValue(value=wert))])


class QdrantModerationRepository(IModerationRepository):
    """Moderationszugriff auf die Qdrant-Collection aller Beitraege, ohne Sperrfilter."""

    def __init__(self, embeddings_manager: Optional[IEmbeddingsManager] = None):
        self._manager = embeddings_manager or get_embeddings_manager()

    @property
    def _client(self):
        return self._manager.async_client

    @property
    def _collection(self) -> str:
        return self._manager.collection_name

    async def laden(self, beitrag_id: str) -> Optional[Dict[str, Any]]:
        return await self._manager.get_by_id(beitrag_id)

    async def sperren(self, beitrag: Dict[str, Any]) -> None:
        if beitrag.get("status") == ContentStatus.BLOCKED.value:
            return
        await self._client.set_payload(
            collection_name=self._collection,
            payload={
                "status": ContentStatus.BLOCKED.value,
                FELD_STATUS_VOR_SPERRE: beitrag.get("status"),
            },
            points=[beitrag["id"]],
        )

    async def entsperren(self, beitrag: Dict[str, Any]) -> None:
        if beitrag.get("status") != ContentStatus.BLOCKED.value:
            return
        status_vorher = beitrag.get(FELD_STATUS_VOR_SPERRE)

        # Zwei Schreibvorgaenge; scheitert der zweite, bleibt nur das Hilfsfeld
        # stehen, der Beitrag ist trotzdem entsperrt.
        if status_vorher:
            await self._client.set_payload(
                collection_name=self._collection,
                payload={"status": status_vorher},
                points=[beitrag["id"]],
            )
            entfernen = [FELD_STATUS_VOR_SPERRE]
        else:
            entfernen = ["status", FELD_STATUS_VOR_SPERRE]
        await self._client.delete_payload(
            collection_name=self._collection, keys=entfernen, points=[beitrag["id"]]
        )

    async def gesperrte_laden(self, limit: int) -> List[Dict[str, Any]]:
        punkte, _ = await self._client.scroll(
            collection_name=self._collection,
            scroll_filter=_nur("status", ContentStatus.BLOCKED.value),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return [{**(punkt.payload or {}), "id": str(punkt.id)} for punkt in punkte]

    async def entfernen(self, beitrag_id: str) -> bool:
        return await self._manager.delete_by_id(beitrag_id)

    async def aus_aussagen_entfernen(self, beitrag_id: str) -> int:
        offset = None
        geaendert = 0

        while True:
            punkte, naechster = await self._client.scroll(
                collection_name=self._collection,
                scroll_filter=_nur("content_type", ContentType.STATEMENT.value),
                limit=AUSSAGEN_JE_SEITE,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            if not punkte:
                break

            for punkt in punkte:
                vorschlaege = (punkt.payload or {}).get("replysuggestions", [])
                if isinstance(vorschlaege, str):
                    try:
                        vorschlaege = json.loads(vorschlaege)
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse replysuggestions for statement {punkt.id}"
                        )
                        continue

                uebrig = [v for v in vorschlaege if str(v.get("id")) != beitrag_id]
                if len(uebrig) == len(vorschlaege):
                    continue

                # Nur die zwei Felder schreiben: Ein upsert des ganzen Punkts
                # braeuchte den Vektor, den der Scroll nicht mitliefert.
                await self._client.set_payload(
                    collection_name=self._collection,
                    payload={
                        "replysuggestions": json.dumps(uebrig, default=str),
                        "replysuggestions_count": len(uebrig),
                    },
                    points=[punkt.id],
                )
                geaendert += 1
                logger.debug(
                    f"Removed orphaned reply suggestion from statement {punkt.id} "
                    f"({len(vorschlaege)} -> {len(uebrig)} suggestions)"
                )

            if naechster is None:
                break
            offset = naechster

        return geaendert


_moderation_repository: Optional[QdrantModerationRepository] = None


def get_moderation_repository() -> QdrantModerationRepository:
    """Get or create the global moderation repository instance."""
    global _moderation_repository
    if _moderation_repository is None:
        _moderation_repository = QdrantModerationRepository()
    return _moderation_repository
