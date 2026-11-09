import asyncio
import threading
import time
import contextlib
import datetime
from collections import defaultdict
from domain.models.zeit import utc_jetzt
from typing import AbstractSet, Dict, List, Optional, Tuple
import uuid
import logging

from pydantic import ValidationError

from core.config import (
    NLI_BESTAETIGER_MODELL,
    NLI_BESTAETIGER_TOKENIZER,
    NLI_MODELL,
    Settings,
)
from services.content.base_content_service import (
    BaseContentService,
    Dublettenpruefung,
    dublette_nach_schwelle,
)
from services.dieselbe_behauptung.nli_modell import NliModell, NliPruefer, nli_modell
from services.dieselbe_behauptung.schatten import Schattenprotokoll
from services.dieselbe_behauptung import regel
from repositories.interfaces.statement_repository import (
    IStatementRepository,
)
from repositories.interfaces.repository_factory import IRepositoryFactory
from domain.models.statement import (
    AntwortKurz,
    Statement,
    StatementDbEntry,
    StatementSearchResult,
    StatementReplysuggestion,
)
from domain.models.base_content import BaseContentSearchResult
from domain.models.content_type import ContentType
from domain.models.author_entry import AuthorEntry
from domain.models.content_status import NEW_CONTENT_STATUS, ContentStatus
from domain.models.content_origin import ContentOrigin
from utils.text_normalisierung import SperreJeText, text_normalisiert

logger = logging.getLogger(__name__)


# So lange warten die Pruefung auf dieselbe Aussage und der Filter der Vorschlaege
# hoechstens auf das NLI-Modell (Sekunden); danach gilt die Schwelle bzw. ungefiltert.
DIESELBE_WARTET_HOECHSTENS = 3.0
VORSCHLAG_WARTET_HOECHSTENS = 2.0


def _normalisiert_gleich(
    text: str, treffer: List[BaseContentSearchResult]
) -> Optional[BaseContentSearchResult]:
    """Ein normalisiert gleicher Treffer (Altbestand ohne Payload-Feld): Er gilt immer
    als dieselbe, vor jedem Score und jedem NLI-Urteil."""
    normalform = text_normalisiert(text)
    if not normalform:
        return None
    return next((t for t in treffer if text_normalisiert(t.text) == normalform), None)


class AussageNichtGefunden(ValueError):
    """Die Aussage zu einer ID gibt es nicht (mehr) - erwartbar, etwa bei einem alten Link."""


class StatementService(
    BaseContentService[IStatementRepository, StatementDbEntry, StatementSearchResult]
):
    def __init__(
        self,
        settings: Settings,
        repository_factory: Optional[IRepositoryFactory] = None,
        nli: Optional[NliPruefer] = None,
        nli_warten: bool = False,
        bestaetiger: Optional[NliPruefer] = None,
    ):
        # Use provided factory or default to QdrantRepositoryFactory
        if repository_factory is None:
            from repositories.implementations.qdrant.qdrant_repository_factory import (
                QdrantRepositoryFactory,
            )

            repository_factory = QdrantRepositoryFactory()

        # Eine Sperre je Aussage um Lesen-Aendern-Schreiben der Antwortvorschlaege.
        # Prozesslokal: schuetzt parallele Anfragen in diesem Worker, nicht ueber
        # mehrere Prozesse hinweg.
        self._verknuepfungs_sperren: Dict[uuid.UUID, asyncio.Lock] = defaultdict(
            asyncio.Lock
        )
        # Eine Sperre je normalisiertem Text um Pruefen-und-Anlegen in add_statement.
        self._text_sperre = SperreJeText()

        # NLI-Stufe (#387). Ohne Modell (aus) gilt allein die Schwelle. Ein Modell je
        # Prozess: Das Seeding nutzt dasselbe, schon vorgeladene wie der Dienst.
        if nli is None and settings.dieselbe_aussage_nli != "aus":
            nli = nli_modell(NLI_MODELL)
        self._nli: Optional[NliPruefer] = nli
        # Der Bestaetiger (nli_bestaetiger): zweites Modell, nur mit NLI-Stufe.
        if (
            bestaetiger is None
            and settings.nli_bestaetiger
            and settings.dieselbe_aussage_nli != "aus"
        ):
            bestaetiger = nli_modell(NLI_BESTAETIGER_MODELL, NLI_BESTAETIGER_TOKENIZER)
        self._bestaetiger: Optional[NliPruefer] = bestaetiger if nli else None
        # nli_warten: auf das Modell warten statt nach DIESELBE_WARTET_HOECHSTENS die
        # Schwelle gelten zu lassen - fuer das Seeding, bei dem niemand auf die Antwort
        # wartet und sonst die ersten Aussagen waehrend des Ladens nach der Schwelle
        # gingen (eine Regel fuer alle Wege).
        self._nli_warten = nli_warten
        self.schattenprotokoll = Schattenprotokoll()
        self._schatten_laeuft = False
        self._schatten_tasks: set[asyncio.Task] = set()

        repository = repository_factory.create_statement_repository(settings)
        content_repository = repository_factory.create_content_repository(settings)

        super().__init__(
            settings,
            repository,
            content_repository,
            StatementDbEntry,
            StatementSearchResult,
        )

    def nli_vorladen(self) -> None:
        """Die NLI-Modelle im Hintergrund laden, wenn die NLI-Stufe sie braucht: den
        Bestaetiger erst nach dem ersten Modell, damit sich die Spitzen beim Laden
        nicht addieren."""
        modelle = [
            m for m in (self._nli, self._bestaetiger) if isinstance(m, NliModell)
        ]
        if not modelle:
            return

        def laden():
            for modell in modelle:
                modell.laden_abwarten()

        threading.Thread(target=laden, name="nli-vorladen", daemon=True).start()

    async def nli_laden_abwarten(self) -> bool:
        """Warten, bis das NLI-Modell geladen ist; True, wenn es bereitsteht. Fuer
        Messskripte, die gleich nach dem Start fragen und sonst die Schwelle messen."""
        if isinstance(self._bestaetiger, NliModell):
            if not await asyncio.to_thread(self._bestaetiger.laden_abwarten):
                logger.warning(
                    "Bestaetiger nicht geladen: Es urteilt nur das erste Modell."
                )
        if isinstance(self._nli, NliModell):
            return await asyncio.to_thread(self._nli.laden_abwarten)
        return self._nli is not None

    async def search_statements(
        self, query_text: str, limit: int = 10, min_replysuggestions_count: int = 0
    ) -> List[StatementSearchResult]:
        """
        Search the statement repository for statements similar to the provided query text with a minimum number of reply suggestions.

        Args:
        - query_text: The query text to search for.
        - limit: The maximum number of results to return.
        - min_replysuggestions_count: The minimum number of reply suggestions a statement must have to be included in the results.

        Returns:
        - A list of StatementResult objects representing the most similar statements to the query text.
        """
        logger.debug(
            f"Searching for statements with at least {min_replysuggestions_count} reply suggestions"
        )

        return await self._repository.search_statements_with_replies(
            query_text, limit, min_replysuggestions_count
        )

    async def search_filtered(
        self,
        query_text: str,
        limit: int = 10,
        nur_kuratiert: bool = False,
        min_similarity: Optional[float] = None,
        ueber_der_schwelle: AbstractSet[uuid.UUID] = frozenset(),
    ) -> List[StatementSearchResult]:
        """
        Aehnliche Statements fuer die Vorschlaege im Beitragsformular.

        Args:
        - nur_kuratiert: Unbeantwortete Suchanfragen weglassen (Kriterium wie
          count_curated).
        - ueber_der_schwelle: Mit nur_kuratiert diese Suchanfragen trotzdem
          behalten, die ueber der Schwelle (#436).
        - min_similarity: Nur Treffer mit mindestens diesem Score. Gefiltert wird
          nach der Suche; es kommen also hoechstens `limit` Treffer zurueck.
        """
        if nur_kuratiert:
            results = await self._repository.search_curated(
                query_text, limit, ueber_der_schwelle
            )
        else:
            results = await self._repository.search(query_text, limit)

        if min_similarity is None:
            return results
        return [r for r in results if r.score is not None and r.score >= min_similarity]

    async def count_curated(
        self, ueber_der_schwelle: AbstractSet[uuid.UUID] = frozenset()
    ) -> int:
        """
        Anzahl der Statements ohne die unbeantworteten Suchanfragen, ausser denen
        in ueber_der_schwelle.

        Grundlage des Zaehlers "Aussagen" auf der Startseite; die Begruendung
        des Kriteriums steht in StatementRepository.count_curated.
        """
        return await self._repository.count_curated(ueber_der_schwelle)

    async def get_all_curated(
        self,
        limit: int,
        offset: int,
        ueber_der_schwelle: AbstractSet[uuid.UUID] = frozenset(),
    ) -> List[StatementDbEntry]:
        """Wie get_all, ohne die unbeantworteten Suchanfragen unter der Schwelle."""
        return await self._repository.get_all_curated(limit, offset, ueber_der_schwelle)

    async def kuratierte(self) -> List[StatementDbEntry]:
        """
        Alle sichtbaren Aussagen ohne die unbeantworteten Suchanfragen
        (StatementRepository.kuratierte), fuer die Zuordnung von Themen.
        """
        return await self._repository.kuratierte()

    async def ohne_kommentar(self) -> List[StatementDbEntry]:
        """
        Sichtbare Aussagen ohne Kommentar, ohne die unbeantworteten Suchanfragen;
        Grundlage von "Hier fehlt eine Antwort" (StatementRepository.ohne_kommentar).
        """
        return await self._repository.ohne_kommentar()

    async def zu_antwort(self, beitrag_id: uuid.UUID) -> List[StatementDbEntry]:
        """Sichtbare Aussagen, auf die der Beitrag antwortet (#603)."""
        return await self._repository.zu_antwort(beitrag_id)

    async def sichtbare_antworten(self, ids: List[uuid.UUID]) -> List[AntwortKurz]:
        """Die sichtbaren Beitraege unter den IDs, mit Typ und Titel (#603)."""
        return await self._repository.sichtbare_antworten(ids)

    async def vorab_anlegen(
        self, text: str, author: str
    ) -> tuple[bool, uuid.UUID, str]:
        """
        Eine Aussage vorab anlegen ("Hier fehlt eine Antwort"), mit der Person als
        Autorin. Gibt es dieselbe schon (add_statement), kommt sie zurueck.

        Ist die vorhandene eine unbeantwortete Suchanfrage, uebernimmt die Person
        sie: Herkunft und Autor wechseln, und die Aussage erscheint danach wie eine
        vorab angelegte auf der Seite. Sonst bliebe sie dort unsichtbar, obwohl die
        Person gerade dieselbe Aussage benannt hat. Andere vorhandene Aussagen
        bleiben unveraendert.
        """
        neu, statement_id, statement_text = await self.add_statement(
            Statement(text=text, replysuggestions=[]),
            author,
            NEW_CONTENT_STATUS,
            ContentOrigin.MANUALLY_CREATED,
        )
        if neu:
            return neu, statement_id, statement_text

        async with self._verknuepfungs_sperre(statement_id):
            aussage = await self._aussage_laden(statement_id)
            if (
                aussage.origin is ContentOrigin.SEARCH_QUERY
                and aussage.replysuggestions_count == 0
            ):
                aussage.origin = ContentOrigin.MANUALLY_CREATED
                aussage.original_author = author
                aussage.last_modified_by = author
                aussage.authors = [AuthorEntry(name=author)]
                aussage.last_modified = utc_jetzt()
                await self.update_statement(aussage)
        return neu, statement_id, statement_text

    async def vorhandene_finden(self, text: str) -> Optional[BaseContentSearchResult]:
        """
        Die Aussage, auf der dieser Text landen wuerde, ohne etwas anzulegen: dieselbe
        Pruefung wie in add_statement. None, wenn er eine neue Aussage ergaebe. Fuer die
        Messung der Zerfaserung im Suchtestset (tests/regression/suche_messen.py) und
        den Bericht ueber den Bestand (tests/regression/dieselbe_bericht.py).
        """
        return (await self._dieselbe_pruefen(text, schatten=False)).vorhanden

    async def _dieselbe_pruefen(self, text: str, schatten: bool) -> Dublettenpruefung:
        """
        Die Pruefung auf dieselbe Aussage, gemeinsam fuer add_statement und
        vorhandene_finden. Normalisiert gleich zaehlt immer. Sonst je nach
        dieselbe_aussage_nli:

        - aus, oder das NLI-Modell ist nicht verfuegbar: query/query-Aehnlichkeit ab
          statement_similarity_threshold (Regel vor #387).
        - schatten: dieselbe Entscheidung; mit schatten=True urteilt die NLI-Stufe im
          Hintergrund mit und wird nur gezaehlt (Schattenprotokoll).
        - an: die NLI-Stufe entscheidet (_nli_entscheiden).
        """
        gleich, treffer = await self._dublettenkandidaten(text, praefix="query")
        if gleich is not None:
            return Dublettenpruefung(vorhanden=gleich, aehnlichster=gleich)
        heute = dublette_nach_schwelle(
            text, treffer, self.settings.statement_similarity_threshold
        )
        modus = self.settings.dieselbe_aussage_nli
        gleich = _normalisiert_gleich(text, treffer)
        if gleich is not None:
            return Dublettenpruefung(vorhanden=gleich, aehnlichster=heute.aehnlichster)
        if self._nli is None or modus == "aus":
            return heute
        if modus == "an":
            nach_nli = await self._nli_entscheiden(text, treffer)
            return heute if nach_nli is None else nach_nli
        if schatten:
            self._schatten_starten(text, treffer, heute)
        return heute

    def _nli_kandidaten(
        self, text: str, treffer: List[BaseContentSearchResult]
    ) -> List[BaseContentSearchResult]:
        """Die Treffer, die das Modell pruefen soll: ab nli_kandidaten_ab, die
        Vorpruefungen bestanden (regel.nli_darf_pruefen), hoechstens
        nli_kandidaten_hoechstens; mit Bestaetiger dazu hoechstens ebenso viele, die
        nur regel.bestaetiger_darf_pruefen bestehen."""
        hoechstens = self.settings.nli_kandidaten_hoechstens
        ab_untergrenze = [
            k
            for k in treffer
            if k.score is not None and k.score >= self.settings.nli_kandidaten_ab
        ]
        kandidaten = [k for k in ab_untergrenze if regel.nli_darf_pruefen(text, k.text)]
        if self._bestaetiger is None:
            return kandidaten[:hoechstens]
        # Paare, die nur der Bestaetiger pruefen darf ("kein"), kommen dazu, ohne
        # einem Kandidaten der Regel oben den Platz zu nehmen.
        nur_bestaetiger = [
            k
            for k in ab_untergrenze
            if regel.bestaetiger_darf_pruefen(text, k.text)
            and not regel.nli_darf_pruefen(text, k.text)
        ]
        return kandidaten[:hoechstens] + nur_bestaetiger[:hoechstens]

    async def _nli_entscheiden(
        self, text: str, treffer: List[BaseContentSearchResult]
    ) -> Optional[Dublettenpruefung]:
        """
        Die Entscheidung der NLI-Stufe: der Kandidat mit der staerksten beidseitigen
        Folgerung, der dieselbe Behauptung ist (regel.entscheiden); ist es keiner, mit
        Bestaetiger der, den er bestaetigt (_bestaetigen); sonst keiner. None, wenn das
        erste Modell nicht urteilen konnte - dann gilt die Schwelle.
        """
        beginn = time.monotonic()
        aehnlichster = treffer[0] if treffer else None
        kandidaten = self._nli_kandidaten(text, treffer)
        if not kandidaten:
            return Dublettenpruefung(vorhanden=None, aehnlichster=aehnlichster)
        # Begrenzt warten: Ist das Modell belegt oder laedt noch, gilt die Schwelle,
        # statt dass alle Suchen hintereinander auf die Sperre warten.
        urteile = await self._nli.urteile(
            [(text, k.text) for k in kandidaten],
            warte_hoechstens=None if self._nli_warten else DIESELBE_WARTET_HOECHSTENS,
        )
        if urteile is None:
            return None
        dieselben = [
            (u.folgerung, k)
            for k, u in zip(kandidaten, urteile)
            if regel.entscheiden(
                text,
                k.text,
                k.score,
                u,
                kandidaten_ab=self.settings.nli_kandidaten_ab,
                folgerung_ab=self.settings.nli_folgerung_ab,
                widerspruch_unter=self.settings.nli_widerspruch_unter,
            )
        ]
        if dieselben:
            vorhanden = max(dieselben, key=lambda paar: paar[0])[1]
        else:
            # Beide Modelle zusammen warten hoechstens DIESELBE_WARTET_HOECHSTENS.
            rest = (
                None
                if self._nli_warten
                else max(0.0, DIESELBE_WARTET_HOECHSTENS - (time.monotonic() - beginn))
            )
            vorhanden = await self._bestaetigen(text, kandidaten, urteile, rest)
        return Dublettenpruefung(vorhanden=vorhanden, aehnlichster=aehnlichster)

    async def _bestaetigen(
        self,
        text: str,
        kandidaten: List[BaseContentSearchResult],
        urteile: List[regel.Urteil],
        warte_hoechstens: Optional[float] = None,
    ) -> Optional[BaseContentSearchResult]:
        """
        Der zweite Weg (regel.bestaetigt): Der Bestaetiger urteilt nur ueber die
        Kandidaten im unsicheren Band des ersten Modells (regel.braucht_bestaetiger);
        dieselbe ist der mit der staerksten beidseitigen Folgerung des Bestaetigers.
        None ohne Bestaetiger, ohne Kandidat im Band oder wenn er nicht urteilen konnte -
        dann bleibt es bei der Entscheidung des ersten Modells.
        """
        if self._bestaetiger is None:
            return None
        s = self.settings
        band = [
            (k, u)
            for k, u in zip(kandidaten, urteile)
            if regel.braucht_bestaetiger(
                u, s.nli_widerspruch_unter, s.nli_bestaetiger_veto_ab
            )
        ]
        if not band:
            return None
        bestaetigungen = await self._bestaetiger.urteile(
            [(text, k.text) for k, _ in band],
            warte_hoechstens=warte_hoechstens,
        )
        if bestaetigungen is None:
            return None
        bestaetigte = [
            (b.folgerung, k)
            for (k, u), b in zip(band, bestaetigungen)
            if regel.bestaetigt(
                text,
                k.text,
                k.score,
                u,
                b,
                kandidaten_ab=s.nli_kandidaten_ab,
                folgerung_ab=s.nli_folgerung_ab,
                widerspruch_unter=s.nli_widerspruch_unter,
                veto_folgerung_ab=s.nli_bestaetiger_veto_ab,
            )
        ]
        return max(bestaetigte, key=lambda paar: paar[0])[1] if bestaetigte else None

    def _schatten_starten(
        self,
        text: str,
        treffer: List[BaseContentSearchResult],
        heute: Dublettenpruefung,
    ) -> None:
        """
        Schattenbetrieb: die NLI-Stufe im Hintergrund urteilen lassen, ohne dass die
        Anfrage wartet. Laeuft schon ein Urteil, wird dieses uebersprungen (gezaehlt),
        damit sich beim Seeding oder unter Last keine Warteschlange bildet.
        """
        if self._schatten_laeuft:
            self.schattenprotokoll.zaehlen("uebersprungen")
            return
        self._schatten_laeuft = True

        async def urteilen():
            try:
                nach_nli = await self._nli_entscheiden(text, treffer)
                self.schattenprotokoll.vergleichen(heute.vorhanden, nach_nli)
            except Exception as e:  # der Schatten darf nie etwas stoeren
                logger.warning("NLI-Schatten gescheitert (%s)", type(e).__name__)
            finally:
                self._schatten_laeuft = False

        task = asyncio.create_task(urteilen())
        # Referenz halten: asyncio haelt Tasks nur schwach.
        self._schatten_tasks.add(task)
        task.add_done_callback(self._schatten_tasks.discard)

    async def ohne_widerspruch(
        self,
        text: str,
        treffer: List[StatementSearchResult],
        hoechstens: Optional[int] = None,
    ) -> List[StatementSearchResult]:
        """
        Die Treffer ohne die, die dem Text in einer Richtung widersprechen
        (aussage_vorschlag_widerspruch_ab) - fuer die Vorschlaege im Feld "Antwort
        auf". Ohne NLI-Modell (aus oder nicht verfuegbar) bleiben alle.

        Mit hoechstens prueft das Modell die Treffer in Score-Reihenfolge stapelweise
        und hoert auf, sobald so viele uebrig sind: Meist reicht ein Stapel, statt bei
        jedem Tastendruck den ganzen Vorrat zu pruefen. Kann das Modell einen Stapel
        nicht pruefen, bleiben dieser und die restlichen Treffer ungefiltert.
        """
        if self._nli is None or self.settings.dieselbe_aussage_nli == "aus":
            return treffer
        behalten: List[StatementSearchResult] = []
        rest = list(treffer)
        while rest and (hoechstens is None or len(behalten) < hoechstens):
            groesse = len(rest) if hoechstens is None else hoechstens - len(behalten)
            stapel, rest = rest[:groesse], rest[groesse:]
            try:
                # Nicht auf das Laden oder ein laufendes Urteil warten: Die Vorschlaege
                # kommen beim Tippen, lieber ungefiltert als spaet.
                urteile = await self._nli.urteile(
                    [(text, t.text) for t in stapel],
                    warte_hoechstens=VORSCHLAG_WARTET_HOECHSTENS,
                )
            except Exception as e:
                logger.warning(
                    "NLI-Filter der Vorschlaege gescheitert (%s)", type(e).__name__
                )
                urteile = None
            if urteile is None:
                return behalten + stapel + rest
            behalten += [
                t
                for t, u in zip(stapel, urteile)
                if not regel.widerspricht(
                    u, self.settings.aussage_vorschlag_widerspruch_ab
                )
            ]
        return behalten

    async def add_statement(
        self,
        statement: Statement,
        author: str,
        status: ContentStatus,
        origin: ContentOrigin,
        id: Optional[uuid.UUID] = None,
        created_at: Optional[datetime.datetime] = None,
    ) -> tuple[bool, uuid.UUID, str]:
        """
        Eine Aussage anlegen - oder die vorhandene liefern, wenn es dieselbe schon gibt.

        Dieselbe ist: normalisiert gleicher Text (utils/text_normalisierung.py) oder,
        je nach NLI-Stufe (_dieselbe_pruefen), query/query-Aehnlichkeit >=
        statement_similarity_threshold bzw. dieselbe Behauptung nach dem NLI-Modell.
        Inhaltlich nur aehnliche Aussagen gelten nicht als dieselbe - sie schlaegt das
        Formular vor, uebernommen wird still nichts. Gilt fuer alle Wege: Formular,
        Suche, Seeding. Bei einer vorhandenen bleibt deren Wortlaut; der neue Text
        wird nicht gespeichert (#387, vgl. #370).

        Pruefen und Schreiben laufen unter einer Sperre je normalisiertem Text, damit
        zwei gleichzeitige Anfragen mit demselben neuen Text nicht zwei Aussagen anlegen.

        Returns:
            - (neu angelegt, ID, Text) - bei einer vorhandenen Aussage deren ID und Text.
        """
        async with self._text_sperre.halten(statement.text):
            pruefung = await self._dieselbe_pruefen(statement.text, schatten=True)
            vorhandene, bester = pruefung.vorhanden, pruefung.aehnlichster
            if vorhandene is not None:
                # DEBUG: Jede Suche laeuft hier durch; eine INFO-Zeile mit ID und
                # Uhrzeit je Suche ordnete die Aussage einem Suchereignis zu (#239).
                logger.debug(
                    f"Statement already exists with ID {vorhandene.id} "
                    f"(score {vorhandene.score:.3f}, threshold {self.settings.statement_similarity_threshold})"
                )
                return False, vorhandene.id, vorhandene.text

            now = created_at or utc_jetzt()
            statement_input = StatementDbEntry(
                text=statement.text,
                id=id or uuid.uuid4(),
                created=now,
                last_modified=now,
                original_author=author,
                last_modified_by=author,
                authors=[AuthorEntry(name=author)],
                edit_history=[],
                status=status,
                origin=origin,
                most_similar_similarity_score=bester.score if bester else None,
                most_similar_content_id=bester.id if bester else None,
                replysuggestions=statement.replysuggestions,
                replysuggestions_count=len(statement.replysuggestions),
            )

            await super()._upsert(statement_input)
            logger.debug(
                f"Successfully created new statement with ID {statement_input.id}"
            )
            return True, statement_input.id, statement_input.text

    async def update_statement(self, updated_statement: StatementDbEntry) -> uuid.UUID:

        # TODO: Add any checks here?

        result = await super()._upsert(updated_statement)
        return result

    async def add_statementreplysuggestion_to_statement(
        self,
        statement_id: uuid.UUID,
        replysuggestion_id: uuid.UUID,
        content_type: ContentType,
        relevance: float,
    ) -> bool:
        """
        Add a reply suggestion to a statement in the index.

        Args:
        - statement_id: The ID of the statement to add the reply suggestion to.
        - statement_reply_suggestion: The reply suggestion to add to the statement.

        Returns:
        - True if the reply suggestion was successfully added to the statement, False otherwise.
        """

        async with self._verknuepfungs_sperre(statement_id):
            return await self._antwortvorschlag_anhaengen(
                statement_id, replysuggestion_id, content_type, relevance
            )

    @contextlib.asynccontextmanager
    async def _verknuepfungs_sperre(self, statement_id: uuid.UUID):
        """
        Die Sperre je Aussage fuer Lesen-Aendern-Schreiben ihres Payloads (Verknuepfen,
        Uebernahme beim Vorab-Anlegen).
        """
        sperre = self._verknuepfungs_sperren[statement_id]
        try:
            async with sperre:
                yield
        finally:
            # Aufraeumen, sobald niemand mehr die Sperre haelt oder auf sie wartet -
            # sonst sammelte sich je beruehrter Aussage eine Sperre an.
            if not sperre.locked() and not getattr(sperre, "_waiters", None):
                self._verknuepfungs_sperren.pop(statement_id, None)

    async def _antwortvorschlag_anhaengen(
        self,
        statement_id: uuid.UUID,
        replysuggestion_id: uuid.UUID,
        content_type: ContentType,
        relevance: float,
    ) -> bool:
        """Lesen, aendern, schreiben - nur unter der Sperre der Aussage aufrufen."""
        statement_db_entry = await self._aussage_laden(statement_id)

        # Zweimal dieselbe Antwort (etwa ein wiederholter Speicheraufruf) haengt
        # nicht doppelt an und zaehlt nicht doppelt.
        if any(
            vorschlag.id == replysuggestion_id
            for vorschlag in statement_db_entry.replysuggestions
        ):
            logger.info(
                f"Reply suggestion {replysuggestion_id} already linked to statement {statement_id}"
            )
            return True

        statement_replysuggestion = StatementReplysuggestion(
            id=replysuggestion_id,
            content_type=content_type,
            relevance=relevance,
            created=utc_jetzt(),
            updated=utc_jetzt(),
            number_of_usages=0,
        )

        statement_db_entry.replysuggestions.append(statement_replysuggestion)
        statement_db_entry.replysuggestions_count += 1

        await self.update_statement(statement_db_entry)

        return True

    async def _aussage_laden(self, statement_id: uuid.UUID) -> StatementDbEntry:
        """
        Die Aussage zur ID; AussageNichtGefunden, wenn es sie nicht gibt. Ein nicht
        lesbarer Datensatz (ValidationError) oder ein Speicherfehler geht unveraendert
        weiter - das ist kaputt, nicht abwesend.
        """
        try:
            return await self.get(statement_id)
        except ValidationError:
            raise
        except ValueError as fehler:
            raise AussageNichtGefunden(str(statement_id)) from fehler

    async def beitrag_als_antwort_verknuepfen(
        self,
        beitrag_id: uuid.UUID,
        content_type: ContentType,
        relevance: float,
        author: str,
        statement_id: Optional[uuid.UUID] = None,
        statement_text: Optional[str] = None,
    ) -> Optional[Tuple[uuid.UUID, str]]:
        """
        Einen gerade gespeicherten Beitrag als Antwort an seine Aussage haengen.

        Mit statement_id wird direkt verknuepft. Ist nur der Text bekannt, wird
        die Aussage jetzt gesucht oder angelegt (add_statement erkennt sehr
        aehnliche Aussagen selbst) - ausdruecklich benannt, also mit der Person
        als Autorin. Ohne beides passiert nichts.

        Returns:
        - ID und Text der tatsaechlich verknuepften Aussage (mit Text kann das eine
          schon vorhandene, sehr aehnliche sein), oder None ohne Aussage.

        Raises:
        - AussageNichtGefunden, wenn die Aussage zur ID nicht existiert; sonst, was
          Suche oder Speichern werfen. Der Beitrag selbst ist dann trotzdem gespeichert.
        """
        text = (statement_text or "").strip()
        if statement_id is None and not text:
            return None

        if statement_id is None:
            _, statement_id, aussage_text = await self.add_statement(
                Statement(text=text, replysuggestions=[]),
                author,
                NEW_CONTENT_STATUS,
                ContentOrigin.MANUALLY_CREATED,
            )
        else:
            aussage_text = (await self._aussage_laden(statement_id)).text

        await self.add_statementreplysuggestion_to_statement(
            statement_id=statement_id,
            replysuggestion_id=beitrag_id,
            content_type=content_type,
            relevance=relevance,
        )
        return statement_id, aussage_text
