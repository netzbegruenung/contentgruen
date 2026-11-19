"""
Inhaltstor der Suche: Ein Treffer im unsicheren Band zaehlt nur, wenn Suchanfrage und
Treffer ein Inhaltswort teilen.

Befund auf Produktion 0.9.3 (19.11.2026): "Open Source ist unsicher!" zeigte unter "Passt
zu deinem Suchtext" einen Kommentar zur Arbeitserlaubnis von Gefluechteten. Er kam ueber
den direkten Weg (eigene Aehnlichkeit 0,821, Schwelle 0,82); seine Aussage war nicht
unter den fuenf Aussagetreffern, also pruefte der Bezug (services/search/bezug.py) sie
nicht. Die Einbettung allein trennt in diesem Band nicht: Kurze Texte und gleich gebaute
Saetze liegen dort auch ohne gemeinsames Thema.

Darum, nur fuer Suchanfragen ab MINDESTENS_WOERTER Woertern:

- Inhaltsworte der Suchanfrage: die Lemmata ihrer Nomen und Eigennamen (spaCy, dasselbe
  Modell wie das Gegenlesen, SPRACHWERKZEUGE). Hat sie keine, bleibt das Tor offen.
- Ein Aussagetreffer mit Aehnlichkeit der Aussage im Band suche_inhaltstor_ab bis unter
  suche_inhaltstor_aussage_bis zaehlt nur, wenn eines davon unter den Lemmata von
  Aussage, Titel oder Text des Beitrags ist.
- Ein direkter Treffer mit Rohscore im Band bis unter suche_inhaltstor_direkt_bis ebenso,
  verglichen mit Titel und Text des Beitrags und den Aussagen, auf die er antwortet
  (Payload-Feld antwort_ids, nur wenn der Beitrag selbst keines teilt).

Schlagwoerter (unter drei Woertern) prueft das Tor nicht: Zusammengesetzte Woerter
("Heizungsverbot" zu "Heizung") teilen kein Lemma, am Suchtestset gingen so Treffer
verloren. Ist das Sprachmodell nicht geladen, bleibt das Tor offen: Die Suche wartet
nicht auf das Laden. Gemessen in tests/regression/SUCHTESTSET.md, Abschnitt Inhaltstor.
"""

import logging
from functools import lru_cache
from typing import Awaitable, Callable, Iterable, List, Optional

logger = logging.getLogger(__name__)

MINDESTENS_WOERTER = 3
INHALTS_WORTARTEN = ("NOUN", "PROPN")


class Inhaltstor:
    def __init__(
        self,
        werkzeuge,
        aussagen_zu_antwort: Optional[Callable[[object], Awaitable[List]]],
        ab: float,
        aussage_bis: float,
        direkt_bis: float,
    ):
        self._werkzeuge = werkzeuge
        self._aussagen_zu_antwort = aussagen_zu_antwort
        self._ab = ab
        self._aussage_bis = aussage_bis
        self._direkt_bis = direkt_bis
        # Je Text die Lemmata; Beitraege und Aussagen kommen in vielen Suchen wieder.
        self._lemmata = lru_cache(maxsize=4096)(self._lemmata_berechnen)

    def _lemmata_berechnen(self, text: str):
        doc = self._werkzeuge.analysieren(text)
        return (
            frozenset(t.lemma_.lower() for t in doc),
            frozenset(t.lemma_.lower() for t in doc if t.pos_ in INHALTS_WORTARTEN),
        )

    def inhaltsworte(self, query_text: str) -> frozenset:
        """Die Inhaltsworte der Suchanfrage; leer, wenn das Tor fuer sie offen ist."""
        if not query_text or len(query_text.split()) < MINDESTENS_WOERTER:
            return frozenset()
        if not getattr(self._werkzeuge, "geladen", False):
            return frozenset()
        try:
            return self._lemmata(query_text.strip())[1]
        except Exception as e:
            logger.warning("Inhaltstor offen (%s)", type(e).__name__)
            return frozenset()

    def _teilt(self, inhalt: frozenset, texte: Iterable[Optional[str]]) -> bool:
        for text in texte:
            if text and text.strip() and inhalt & self._lemmata(text.strip())[0]:
                return True
        return False

    def aussage_zaehlt(
        self, query_text: str, aehnlichkeit: float, aussage_text: str, beitrag
    ) -> bool:
        if not (self._ab <= aehnlichkeit < self._aussage_bis):
            return True
        inhalt = self.inhaltsworte(query_text)
        if not inhalt:
            return True
        return self._teilt(
            inhalt,
            (
                aussage_text,
                getattr(beitrag, "title", None),
                getattr(beitrag, "text", None),
            ),
        )

    async def direkt_zaehlt(self, query_text: str, beitrag) -> bool:
        if not (self._ab < beitrag.score < self._direkt_bis):
            return True
        inhalt = self.inhaltsworte(query_text)
        if not inhalt:
            return True
        if self._teilt(
            inhalt, (getattr(beitrag, "title", None), getattr(beitrag, "text", None))
        ):
            return True
        if self._aussagen_zu_antwort is None:
            return False
        try:
            aussagen = await self._aussagen_zu_antwort(beitrag.id)
        except Exception as e:
            logger.warning("Inhaltstor: Aussagen nicht geladen (%s)", type(e).__name__)
            aussagen = []
        return self._teilt(inhalt, (a.text for a in aussagen))


def inhaltstor_fuer(statement_service) -> Optional[Inhaltstor]:
    """Das Inhaltstor nach den Einstellungen; None, wenn es aus ist."""
    from core.config import settings
    from services.gegenlesen.gegenlesen_service import SPRACHWERKZEUGE

    if not settings.suche_inhaltstor:
        return None
    return _tor(statement_service, SPRACHWERKZEUGE)


_TORE: dict = {}


def _tor(statement_service, werkzeuge) -> Inhaltstor:
    # Eins je StatementService, damit der Lemma-Cache ueber Suchen hinweg haelt. Mit
    # dem Dienst als Wert: Eine wiederverwendete id() bekommt kein fremdes Tor.
    eintrag = _TORE.get(id(statement_service))
    if eintrag is None or eintrag[0] is not statement_service:
        from core.config import settings

        tor = Inhaltstor(
            werkzeuge,
            getattr(statement_service, "zu_antwort", None),
            settings.suche_inhaltstor_ab,
            settings.suche_inhaltstor_aussage_bis,
            settings.suche_inhaltstor_direkt_bis,
        )
        eintrag = (statement_service, tor)
        _TORE[id(statement_service)] = eintrag
    return eintrag[1]
