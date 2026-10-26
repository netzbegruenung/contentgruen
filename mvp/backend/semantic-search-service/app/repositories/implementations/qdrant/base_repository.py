from abc import abstractmethod
import datetime
import json
from typing import List, Optional, Type, TypeVar, Generic
import os
import uuid
import logging
import asyncio

from pydantic import ValidationError

from core.config import Settings
from services.embeddings.qdrant_embeddings_manager import get_embeddings_manager
from domain.interfaces.embeddings_manager import IEmbeddingsManager
from domain.models.base_content import (
    BaseContentDbEntry,
    BaseContentSearchResult,
)
from repositories.interfaces.base_content_repository import (
    IBaseContentRepository,
)
from domain.models.content_status import (
    ALT_AUFFINDBAR,
    AUSGEBLENDET,
    AUSGEBLENDET_WERTE,
    ContentStatus,
)
from domain.models.content_origin import ContentOrigin
from utils.data_utils import DataSource
from utils.text_normalisierung import (
    FELD_TEXT_NORMALISIERT,
    TYPEN_MIT_TEXT_NORMALISIERT,
    text_normalisiert,
)

logger = logging.getLogger(__name__)

# Wie viele normalisiert gleiche Eintraege finde_normalisiert_gleich zum Sortieren
# holt. Normalerweise einer; mehrere nur aus der Zeit vor der Dublettenpruefung.
NORMALISIERT_GLEICH_HOECHSTENS = 50

TContentDbEntry = TypeVar("TContentDbEntry", bound=BaseContentDbEntry)
TContentSearchResult = TypeVar("TContentSearchResult", bound=BaseContentSearchResult)


def _search_query_origin_conditions() -> list:
    """
    must_not-Bedingung, die Statements aus Suchanfragen ausschliesst.

    Gedacht fuer alles, was Inhalte einer Person zuordnet (get_by_author,
    get_count_by_author). Eine Suchanfrage faellt automatisch an und hat keinen
    Autor - sie ist kein Beitrag und darf in "Meine Beitraege" nicht auftauchen.
    Der Filter greift zusaetzlich zum Systemautor aus SEARCH_QUERY_AUTHOR, damit
    auch Altbestand aussen vor bleibt, an dem noch eine Person haengt.
    """
    from qdrant_client.models import FieldCondition, MatchValue

    return [
        FieldCondition(
            key="origin", match=MatchValue(value=ContentOrigin.SEARCH_QUERY.value)
        )
    ]


def ausgeblendet_bedingungen() -> list:
    """
    must_not-Bedingungen, die alles in AUSGEBLENDET ausschliessen: gesperrte und
    geloeschte Beitraege und Bilder ohne Unterschrift von vor #281.

    Ein Admin sperrt einen Beitrag, statt ihn zu loeschen: Er verschwindet aus
    Suche, Einzelansicht, Listen und "Meine Beitraege", bleibt aber im Speicher
    und damit fuer die Moderation auffindbar (QdrantModerationRepository in
    moderation_repository.py filtert nicht nach Zustand).
    """
    from qdrant_client.models import FieldCondition, MatchValue

    return [
        FieldCondition(key="status", match=MatchValue(value=status.value))
        for status in sorted(AUSGEBLENDET, key=lambda s: s.value)
    ]


def nur_sichtbar_bedingungen() -> list:
    """
    must-Bedingung der Suche: nur sichtbare Beitraege.

    Bis zur Umstellung der Altwerte (#214, ALT_AUFFINDBAR in content_status.py) auch
    Punkte mit einem Altwert, den die Suche vorher fand, und Punkte ohne Status.
    """
    from qdrant_client.models import (
        FieldCondition,
        Filter,
        IsEmptyCondition,
        MatchAny,
        MatchValue,
        PayloadField,
    )

    return [
        Filter(
            should=[
                FieldCondition(
                    key="status", match=MatchValue(value=ContentStatus.VISIBLE.value)
                ),
                FieldCondition(
                    key="status", match=MatchAny(any=sorted(ALT_AUFFINDBAR))
                ),
                IsEmptyCondition(is_empty=PayloadField(key="status")),
            ]
        )
    ]


class QdrantBaseRepository(
    IBaseContentRepository[TContentDbEntry, TContentSearchResult]
):
    """
    Base repository implementation for Qdrant vector database.

    This class provides common functionality for all content repositories using Qdrant,
    with content types logically separated using the content_type field.
    """

    def __init__(
        self,
        index_name: str,
        content_type: Optional[str],
        settings: Settings,
        content_db_entry_model_class: Type[TContentDbEntry],
        content_search_result_model_class: Type[TContentSearchResult],
        embeddings_manager: Optional[IEmbeddingsManager] = None,
    ):
        self.repository_name = index_name
        self.content_type = content_type  # None means no filtering (aggregated view)
        self.initial_data_path = os.path.join(
            settings.index_initial_data_path, index_name
        )
        self.content_db_entry_model_class = content_db_entry_model_class
        self.content_search_result_model_class = content_search_result_model_class
        self.initial_data_author = settings.initial_data_author

        logger.info(
            f"Configured {self.repository_name} (content_type: {self.content_type})"
        )

        # Use injected embeddings manager or get default singleton
        self._shared_manager = embeddings_manager or get_embeddings_manager()

    # Public interface methods (implementing IBaseContentRepository)

    async def initialize_repository(self) -> DataSource:
        """
        Initialize the repository with initial data if needed.

        Returns:
            DataSource: Indicates whether data was loaded from storage or JSON files
        """
        logger.info(f"=== Initializing {self.__class__.__name__} ===")

        if await self.has_content():
            logger.info(
                f"Initialized {self.__class__.__name__} - found existing content"
            )
            return DataSource.STORAGE
        else:
            logger.info(f"Executing initial data load from JSON files")
            self.initialize_with_initial_data()
            return DataSource.JSON

    async def search(
        self, query_text: str, limit: int, praefix: str = "query"
    ) -> List[TContentSearchResult]:
        """
        Async implementation of search.

        praefix: "query" fuer die Suche; "passage" fuer die Dublettenpruefung gegen
        passage-Bestand (siehe QdrantEmbeddingsManager.search).
        """
        try:
            filter_dict = {"must": nur_sichtbar_bedingungen()}

            # Perform search with optional content_type filter
            search_results = await self._shared_manager.search(
                query=query_text,
                content_type=self.content_type,
                limit=limit,
                filter_dict=filter_dict,
                praefix=praefix,
            )

            content_desc = (
                f"all content types" if self.content_type is None else self.content_type
            )
            # Ohne query_text: derselbe Suchtext wie in api/v1/search.py. Nur auf
            # DEBUG: je Suche eine Zeile mit Uhrzeit liesse sich den
            # Suchereignissen zuordnen (#239).
            logger.debug(
                f"Search in {content_desc}: found {len(search_results)} results"
            )

            # Convert to result models
            return [
                self.content_search_result_model_class.model_validate(res)
                for res in search_results
            ]

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            raise

    async def finde_normalisiert_gleich(
        self, normalform: str
    ) -> Optional[TContentSearchResult]:
        """
        Einen Eintrag dieses Typs mit genau dieser Normalform (Payload-Feld
        text_normalisiert, Keyword-Index) - ohne Vektorsuche, also unabhaengig davon,
        wie weit der Score eines normalisiert gleichen Textes abfaellt. Eintraege ohne
        das Feld (Altbestand vor dem Nachtrag) findet das nicht.

        Wie search() nur sichtbare: Ein neuer Beitrag haengt sich nie still an einen
        gesperrten oder geloeschten. Gibt es mehrere, entscheidet die Reihenfolge
        deterministisch: der aelteste (created), dann die ID.
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        must = [
            FieldCondition(
                key=FELD_TEXT_NORMALISIERT, match=MatchValue(value=normalform)
            )
        ]
        if self.content_type:
            must.append(
                FieldCondition(
                    key="content_type", match=MatchValue(value=self.content_type)
                )
            )
        must.extend(nur_sichtbar_bedingungen())
        punkte, _ = await self._shared_manager.async_client.scroll(
            collection_name=self._shared_manager.collection_name,
            scroll_filter=Filter(must=must),
            limit=NORMALISIERT_GLEICH_HOECHSTENS,
            with_payload=True,
            with_vectors=False,
        )
        if not punkte:
            return None

        def rang(punkt):
            payload = punkt.payload or {}
            return (
                str(payload.get("created") or ""),
                str(punkt.id),
            )

        erster = min(punkte, key=rang)
        return self.content_search_result_model_class.model_validate(
            {**erster.payload, "id": str(erster.id), "score": 1.0}
        )

    async def get(self, item_id: uuid.UUID) -> TContentDbEntry:
        """
        Async implementation of get.

        "Nicht gefunden" und "anderer Inhaltstyp unter dieser ID" sind erwartbar
        (geloeschte Aussage, veralteter Link) und werden als ValueError gemeldet -
        im Log als warning ohne Traceback. Als error mit Traceback landen nur echte
        Fehler: der Speicher antwortet nicht, oder der Datensatz ist nicht lesbar.
        """
        try:
            result = await self._shared_manager.get_by_id(str(item_id))
        except Exception as e:
            logger.error(f"Failed to get item by ID: {e}", exc_info=True)
            raise

        if result is None:
            content_desc = (
                f"all content types"
                if self.content_type is None
                else f"content_type: {self.content_type}"
            )
            meldung = f"Entry with id {item_id} not found in {self.repository_name} ({content_desc})"
            logger.warning(meldung)
            raise ValueError(meldung)

        # Verify content_type if filtering is enabled
        if self.content_type and result.get("content_type") != self.content_type:
            meldung = f"Entry with id {item_id} has wrong content_type: {result.get('content_type')}"
            logger.warning(meldung)
            raise ValueError(meldung)

        # Gesperrt, geloescht oder Bild ohne Unterschrift heisst fuer jeden Leser
        # hier "nicht da":
        # Einzelansicht, Stimmen, Antwortvorschlaege der Suche (SearchOrchestrator
        # ueberspringt ValueError).
        if result.get("status") in AUSGEBLENDET_WERTE:
            meldung = (
                f"Entry with id {item_id} is ausgeblendet " f"({result.get('status')})"
            )
            logger.warning(meldung)
            raise ValueError(meldung)

        try:
            entry = self.content_db_entry_model_class.model_validate(result)
        except Exception as e:
            logger.error(f"Failed to read item {item_id}: {e}", exc_info=True)
            raise

        # DEBUG: Die Suche laedt so jeden Treffer nach (#239).
        logger.debug(f"Found entry with id {item_id} in {self.repository_name}")
        return entry

    async def get_by_id(self, item_id: uuid.UUID) -> TContentDbEntry:
        """
        Retrieve a specific content item by its ID.
        This is an alias for get() method for consistency with test expectations.
        """
        return await self.get(item_id)

    async def upsert(
        self, item_id: uuid.UUID, item_input: TContentDbEntry
    ) -> uuid.UUID:
        """Async implementation of upsert."""
        try:
            data_dict = json.loads(item_input.model_dump_json())

            if "text" not in data_dict:
                raise ValueError(
                    f"Item with id {item_id} does not contain a 'text' field"
                )

            # For aggregated repositories, use the content_type from the data itself
            if self.content_type is None:
                if "content_type" not in data_dict:
                    raise ValueError(
                        f"Aggregated index requires content_type in data, but not found for id {item_id}"
                    )
                upsert_content_type = data_dict["content_type"]
            else:
                upsert_content_type = self.content_type
                data_dict["content_type"] = self.content_type

            # DEBUG: Auch die Aussage aus einer Suche laeuft hier durch (#239).
            logger.debug(
                f"QdrantBaseRepository ({self.__class__.__name__}): Upserting item with id {item_id} "
                f"into {self.repository_name} (using content_type: {upsert_content_type})"
            )

            # Extract text for embedding; coerce None to "" for the image entries
            # without Unterschrift from before #281 (pending_description).
            text = data_dict.get("text") or ""

            # Normalform fuer den exakten Abgleich der Dublettenpruefung.
            if upsert_content_type in TYPEN_MIT_TEXT_NORMALISIERT:
                data_dict[FELD_TEXT_NORMALISIERT] = text_normalisiert(text)

            # Upsert to Qdrant
            await self._shared_manager.upsert_batch(
                points=[(str(item_id), data_dict, text)],
                content_type=upsert_content_type,
            )

            return item_id

        except Exception as e:
            logger.error(f"Failed to upsert item: {e}", exc_info=True)
            raise

    async def count(self) -> int:
        """
        Anzahl der sichtbaren Beitraege, also ohne gesperrte: Sie speist die
        Bestandszaehler (getMetrics) und total_records_count der Listen.
        """
        try:
            result = await self._shared_manager.async_client.count(
                collection_name=self._shared_manager.collection_name,
                count_filter=self._sichtbar_filter(),
            )
            return result.count
        except Exception as e:
            logger.error(f"Failed to count items: {e}", exc_info=True)
            return 0

    async def get_all(self, limit: int, offset: int) -> List[TContentDbEntry]:
        """Async implementation of get_all."""
        try:
            # Build filter for content_type if needed
            filter_dict = (
                {"content_type": self.content_type} if self.content_type else None
            )

            # Use search with empty query to get all items
            # This is a workaround since Qdrant doesn't have direct pagination like SQL
            all_results = []
            batch_size = 100
            current_offset = None

            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Build filter
            search_filter = self._sichtbar_filter()

            # Scroll through results
            points_collected = 0
            points_to_skip = offset

            while points_collected < limit:
                result = await self._shared_manager.async_client.scroll(
                    collection_name=self._shared_manager.collection_name,
                    scroll_filter=search_filter,
                    limit=min(batch_size, limit - points_collected + points_to_skip),
                    offset=current_offset,
                    with_payload=True,
                    with_vectors=False,
                )

                if not result[0]:
                    break

                for point in result[0]:
                    if points_to_skip > 0:
                        points_to_skip -= 1
                        continue

                    if points_collected >= limit:
                        break

                    payload = point.payload or {}
                    payload["id"] = str(point.id)
                    all_results.append(
                        self.content_db_entry_model_class.model_validate(payload)
                    )
                    points_collected += 1

                current_offset = result[1]
                if current_offset is None or points_collected >= limit:
                    break

            content_desc = (
                f"all content types"
                if self.content_type is None
                else f"content_type: {self.content_type}"
            )
            logger.info(
                f"Retrieved {len(all_results)} items from {self.repository_name} ({content_desc})"
            )

            return all_results

        except Exception as e:
            logger.error(f"Failed to get all items: {e}", exc_info=True)
            raise

    def _sichtbar_filter(self):
        """Filter fuer Listen: der Typ des Repositorys, falls es einen hat, ohne Gesperrte."""
        from qdrant_client.models import Filter, FieldCondition, MatchValue

        must = None
        if self.content_type:
            must = [
                FieldCondition(
                    key="content_type", match=MatchValue(value=self.content_type)
                )
            ]
        return Filter(must=must, must_not=ausgeblendet_bedingungen())

    def _autoren_filter(self, user_id: str, content_types: Optional[List[str]] = None):
        """
        Filter fuer alles, was einer Person zugeordnet wird.

        Der Typ des Repositorys gilt immer, falls es einen hat. content_types grenzt
        zusaetzlich auf mehrere Typen ein - gedacht fuer das aggregierte Repository,
        etwa fuer "Meine Beitraege" ohne Aussagen und Herkunftsangaben. Ohne Angabe
        bleibt alles wie bisher; die Nutzungsstatistik ruft ohne Eingrenzung auf.
        """
        from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue

        must_conditions = [
            FieldCondition(key="original_author", match=MatchValue(value=user_id))
        ]

        if self.content_type:
            must_conditions.append(
                FieldCondition(
                    key="content_type", match=MatchValue(value=self.content_type)
                )
            )

        if content_types:
            must_conditions.append(
                FieldCondition(
                    key="content_type", match=MatchAny(any=list(content_types))
                )
            )

        return Filter(
            must=must_conditions,
            must_not=_search_query_origin_conditions() + ausgeblendet_bedingungen(),
        )

    async def get_by_author(
        self,
        user_id: str,
        limit: int,
        offset: int,
        content_types: Optional[List[str]] = None,
        eintrag_modell: Optional[Type[BaseContentDbEntry]] = None,
    ) -> List[TContentDbEntry]:
        """
        Async implementation of get_by_author.

        eintrag_modell ersetzt das Modell des Repositorys beim Lesen des Payloads.
        Das aggregierte Repository liest sonst mit ContentDbEntry und verliert dabei
        die typspezifischen Felder (Titel, Bildadresse).

        Neueste zuerst nach created, dem Datum, das die Karte anzeigt. Qdrant scrollt
        ohne order_by in ID-Reihenfolge, und order_by braeuchte einen Payload-Index auf
        created. Wie get_recent werden deshalb alle Punkte der Person geholt, im
        Speicher sortiert und dann die Seite geschnitten; pro Person sind das wenige.
        """
        modell = eintrag_modell or self.content_db_entry_model_class
        try:
            search_filter = self._autoren_filter(user_id, content_types)

            punkte = []
            current_offset = None
            while True:
                seite, naechster_offset = (
                    await self._shared_manager.async_client.scroll(
                        collection_name=self._shared_manager.collection_name,
                        scroll_filter=search_filter,
                        limit=100,
                        offset=current_offset,
                        with_payload=True,
                        with_vectors=False,
                    )
                )
                punkte.extend(seite)
                if (
                    not seite
                    or naechster_offset is None
                    or naechster_offset == current_offset
                ):
                    break
                current_offset = naechster_offset

            # Erst validieren, dann sortieren: ein kaputter Punkt faellt einzeln heraus,
            # statt die ganze Liste mit 500 scheitern zu lassen.
            gueltige = []
            for point in punkte:
                payload = dict(point.payload or {})
                payload["id"] = str(point.id)
                try:
                    eintrag = modell.model_validate(payload)
                except ValidationError as fehler:
                    logger.warning(
                        f"get_by_author: Punkt {point.id} uebersprungen, "
                        f"Payload ungueltig ({fehler.error_count()} Fehler)"
                    )
                    continue
                # created ist ISO ohne Zeitzone, als Text also chronologisch sortierbar;
                # null oder kein Text sortiert ans Ende statt die Sortierung zu sprengen.
                created = payload.get("created")
                gueltige.append((created if isinstance(created, str) else "", eintrag))

            gueltige.sort(key=lambda paar: paar[0], reverse=True)
            all_results = [eintrag for _, eintrag in gueltige[offset : offset + limit]]

            content_desc = (
                f"all content types" if self.content_type is None else self.content_type
            )
            logger.info(
                f"Search results by author in {content_desc}: {len(all_results)} items"
            )

            return all_results

        except Exception as e:
            logger.error(f"Failed to get items by author: {e}", exc_info=True)
            raise

    async def get_count_by_author(
        self, user_id: str, content_types: Optional[List[str]] = None
    ) -> int:
        """Async implementation of get_count_by_author."""
        try:
            search_filter = self._autoren_filter(user_id, content_types)

            # Count with filter
            result = await self._shared_manager.async_client.count(
                collection_name=self._shared_manager.collection_name,
                count_filter=search_filter,
            )

            return result.count

        except Exception as e:
            logger.error(f"Failed to count items by author: {e}", exc_info=True)
            return 0

    async def has_content(self) -> bool:
        """
        Check if there's any content for this content_type in the collection.
        If content_type is None, checks for any content across all types.

        Returns:
            True if content exists, False otherwise.
        """
        try:
            # Ungefiltert: Auch ein ganz gesperrter Bestand ist ein Bestand, sonst
            # spielte initialize_repository die Startdaten erneut ein.
            count = await self._shared_manager.count(self.content_type)
            has_content = count > 0
            content_desc = (
                f"all content types"
                if self.content_type is None
                else f"content_type: {self.content_type}"
            )
            logger.info(f"{self.repository_name} ({content_desc}) has {count} items")
            return has_content
        except Exception as e:
            logger.error(f"Error checking content for {self.repository_name}: {e}")
            return False

    async def get_recent(self, limit: int = 10) -> List[TContentDbEntry]:
        """Async implementation of get_recent. For MVP, fetches a reasonable batch and sorts."""
        try:
            from qdrant_client.models import (
                Filter,
                FieldCondition,
                MatchValue,
            )

            # Build filter for content_type if needed
            search_filter = self._sichtbar_filter()

            # For MVP: Fetch a reasonable batch (10x requested limit) and sort in memory
            # This is acceptable for small datasets. For production with large datasets,
            # consider adding a 'created' payload index with ordering support.
            batch_size = min(limit * 10, 1000)  # Cap at 1000 to avoid memory issues
            all_results = []
            current_offset = None
            fetched = 0

            while fetched < batch_size:
                result = await self._shared_manager.async_client.scroll(
                    collection_name=self._shared_manager.collection_name,
                    scroll_filter=search_filter,
                    limit=min(100, batch_size - fetched),
                    offset=current_offset,
                    with_payload=True,
                    with_vectors=False,
                )

                if not result[0]:
                    break

                for point in result[0]:
                    payload = point.payload or {}
                    payload["id"] = str(point.id)
                    all_results.append(payload)
                    fetched += 1

                current_offset = result[1]
                if current_offset is None:
                    break

            # Sort by created date (newest first)
            all_results.sort(key=lambda x: x.get("created", ""), reverse=True)

            # Take only the requested limit
            recent_results = all_results[:limit]

            content_desc = (
                f"all content types"
                if self.content_type is None
                else f"content_type: {self.content_type}"
            )
            logger.info(
                f"Recent content results for {self.repository_name} ({content_desc}): "
                f"found {len(recent_results)} items (fetched {len(all_results)} to sort)"
            )

            return [
                self.content_db_entry_model_class.model_validate(res)
                for res in recent_results
            ]

        except Exception as e:
            logger.error(f"Failed to get recent items: {e}", exc_info=True)
            return []

    async def count_last_week(self) -> int:
        """Async implementation of count_last_week."""
        try:
            from datetime import datetime, timedelta, timezone

            from domain.models.zeit import als_utc

            def zeitpunkt(wert):
                try:
                    return als_utc(datetime.fromisoformat(str(wert)))
                except (TypeError, ValueError):
                    return None

            from qdrant_client.models import (
                Filter,
                FieldCondition,
                MatchValue,
            )

            # Eine Woche zurueck, in UTC. Verglichen wird nach dem Parsen als Zeitpunkt:
            # gespeichert sind naive Altwerte (UTC) und neue Werte mit Offset.
            one_week_ago = datetime.now(timezone.utc) - timedelta(days=7)

            # Build filter conditions
            must_conditions = []

            if self.content_type:
                must_conditions.append(
                    FieldCondition(
                        key="content_type", match=MatchValue(value=self.content_type)
                    )
                )

            # Note: Qdrant doesn't support OR conditions directly in the same way,
            # and date range filtering requires proper field indexing
            # For now, we'll count items created in the last week
            # This is a simplified implementation

            # Get all items and filter in memory (acceptable for small datasets)
            search_filter = Filter(must=must_conditions) if must_conditions else None

            count = 0
            current_offset = None

            while True:
                result = await self._shared_manager.async_client.scroll(
                    collection_name=self._shared_manager.collection_name,
                    scroll_filter=search_filter,
                    limit=100,
                    offset=current_offset,
                    with_payload=["created", "last_modified"],
                    with_vectors=False,
                )

                if not result[0]:
                    break

                for point in result[0]:
                    payload = point.payload or {}
                    created = zeitpunkt(payload.get("created"))
                    last_modified = zeitpunkt(payload.get("last_modified"))

                    # Check if created or modified in the last week
                    if (created and created >= one_week_ago) or (
                        last_modified and last_modified >= one_week_ago
                    ):
                        count += 1

                current_offset = result[1]
                if current_offset is None:
                    break

            return count

        except Exception as e:
            logger.error(f"Error counting items from last week: {e}", exc_info=True)
            return 0

    async def update_status(
        self,
        item_id: uuid.UUID,
        new_status: ContentStatus,
    ) -> None:
        """
        Partial-payload update: change only the status field without re-embedding.
        """
        try:
            await self._shared_manager.async_client.set_payload(
                collection_name=self._shared_manager.collection_name,
                payload={"status": new_status.value},
                points=[str(item_id)],
            )
            logger.debug(f"Updated status of {item_id} to {new_status.value}")
        except Exception as e:
            logger.error(
                f"Failed to update status of {item_id} to {new_status}: {e}",
                exc_info=True,
            )
            raise

    @abstractmethod
    def initialize_with_initial_data(self):
        """
        Initialize this repository with initial data from JSON files.
        This will only load into this repository, and not have side effects on other repositories!

        Derived classes should override this method to implement specific data loading logic.
        """
        pass

    # Topic and category methods are not implemented for Qdrant
    # These may be added in future versions if needed
