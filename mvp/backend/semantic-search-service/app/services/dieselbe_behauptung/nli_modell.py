"""
Das NLI-Modell der NLI-Stufe (#387): ein mehrsprachiger Cross-Encoder, der je Paar
Folgerung, neutral und Widerspruch schaetzt. Lokal auf der CPU, im selben Container
wie die Einbettung; kein Text verlaesst den Dienst (ADR 0005).

Modell: NLI_MODELL in core/config.py (MIT). Nur fp32: Die Model Card schliesst FP16
aus, und dynamisches int8 aenderte in der Erkundung vom 28.10.2026 44 % der Urteile.

Die CPU-Threads teilt es mit der Einbettung (embedding_threads): torch.set_num_threads
gilt prozessweit, deshalb setzt das NLI-Modell keinen eigenen Wert.

Geladen wird beim ersten Urteil (oder mit vorladen() im Hintergrund), nicht beim
Import: Der Dienst startet ohne das Modell, und ohne Modell gilt die heutige Regel.
Scheitert das Laden, bleibt das Modell fuer diesen Prozess aus (eine WARNING), statt
bei jeder Suche neu zu laden.

Je Prozess gibt es ein Modell je Name (nli_modell()): Auch das Seeding baut einen eigenen
StatementService und soll dasselbe, schon vorgeladene Modell nutzen statt eines zweiten.

Dieselbe Klasse laedt auch den Bestaetiger (NLI_BESTAETIGER_MODELL). Sein Repo bringt nur
den langsamen Tokenizer mit, der sentencepiece braucht; den schnellen mit demselben
Vokabular gibt es im Basismodell (tokenizer_name).
"""

import asyncio
import logging
import threading
import time
from typing import Dict, List, Optional, Protocol, Sequence, Tuple

from services.dieselbe_behauptung.regel import Richtung, Urteil

logger = logging.getLogger(__name__)

# So viele Textpaare rechnet das Modell auf einmal; ein Kandidat sind zwei (hin, rueck).
STAPEL = 32
# Laengere Texte schneidet der Tokenizer ab. Eine Aussage hat hoechstens 1000 Zeichen
# (AUSSAGE_MAX_ZEICHEN), das sind deutlich unter 512 Token.
MAX_TOKEN = 512
# So oft fragt ein wartender Aufruf nach, ob die Sperre frei ist (Sekunden). Gewartet
# wird in der Ereignisschleife, nicht in einem Thread: Wartende belegen so keinen Thread
# des gemeinsamen Executors, den auch andere asyncio.to_thread-Nutzer brauchen.
NACHFRAGEN_ALLE = 0.05
# Immer nur ein Modell zugleich laden: from_pretrained ist nicht threadsicher (zwei
# gleichzeitige Ladevorgaenge liessen Gewichte auf dem meta-Geraet zurueck, jedes Urteil
# scheiterte dann), und die Spitzen beim Laden addieren sich so nicht.
_LADE_SPERRE = threading.Lock()


class NliPruefer(Protocol):
    """Was StatementService vom Modell braucht; Tests geben eine Attrappe."""

    async def urteile(
        self,
        paare: Sequence[Tuple[str, str]],
        warte_hoechstens: Optional[float] = None,
    ) -> Optional[List[Urteil]]:
        """Je Paar (neuer Text, Kandidat) das Urteil in beide Richtungen; None, wenn
        das Modell nicht verfuegbar ist. Mit warte_hoechstens (Sekunden) auch None,
        solange es noch laedt oder laenger belegt ist - fuer Anfragen, die lieber ohne
        Urteil weitermachen als zu warten."""
        ...


class NliModell:
    def __init__(self, modell_name: str, tokenizer_name: Optional[str] = None):
        self._modell_name = modell_name
        self._tokenizer_name = tokenizer_name or modell_name
        self._sperre = threading.Lock()
        self._tokenizer = None
        self._modell = None
        self._kaputt = False
        self._etiketten: Tuple[int, int] = (0, 2)

    @property
    def verfuegbar(self) -> bool:
        return not self._kaputt

    @property
    def geladen(self) -> bool:
        """Das Modell steht bereit; ein None aus urteile() heisst dann: Sperre belegt."""
        return self._modell is not None and not self._kaputt

    def _laden(self) -> bool:
        """Unter self._sperre aufrufen. True, wenn das Modell bereitsteht."""
        if self._modell is not None:
            return True
        if self._kaputt:
            return False
        try:
            import torch
            from transformers import (
                AutoModelForSequenceClassification,
                AutoTokenizer,
            )

            with _LADE_SPERRE:
                tokenizer = AutoTokenizer.from_pretrained(self._tokenizer_name)
                modell = AutoModelForSequenceClassification.from_pretrained(
                    self._modell_name, torch_dtype=torch.float32
                ).eval()
            nach_name = {
                name.lower(): idx for idx, name in modell.config.id2label.items()
            }
            self._etiketten = (nach_name["entailment"], nach_name["contradiction"])
        except Exception as e:
            self._kaputt = True
            logger.warning(
                "NLI-Modell %s nicht geladen (%s): Es gilt die heutige Regel.",
                self._modell_name,
                type(e).__name__,
            )
            return False
        self._tokenizer, self._modell = tokenizer, modell
        logger.info("NLI-Modell %s geladen", self._modell_name)
        return True

    def laden_abwarten(self) -> bool:
        """Blockiert, bis das Modell geladen ist (oder das Laden scheiterte). True,
        wenn es bereitsteht. Fuer Messskripte, die sofort nach dem Start fragen."""
        with self._sperre:
            return self._laden()

    def vorladen(self) -> None:
        """Laedt das Modell in einem Hintergrund-Thread, damit das erste Urteil nicht
        auf das Laden wartet."""

        def laden():
            with self._sperre:
                self._laden()

        threading.Thread(target=laden, name="nli-vorladen", daemon=True).start()

    def _wahrscheinlichkeiten(
        self, praemissen: List[str], hypothesen: List[str]
    ) -> List[Richtung]:
        import torch

        folgerung_idx, widerspruch_idx = self._etiketten
        ergebnis: List[Richtung] = []
        for start in range(0, len(praemissen), STAPEL):
            eingabe = self._tokenizer(
                praemissen[start : start + STAPEL],
                hypothesen[start : start + STAPEL],
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=MAX_TOKEN,
            )
            with torch.inference_mode():
                werte = torch.softmax(self._modell(**eingabe).logits, dim=-1)
            ergebnis += [
                Richtung(float(z[folgerung_idx]), float(z[widerspruch_idx]))
                for z in werte
            ]
        return ergebnis

    def _rechnen(self, paare: List[Tuple[str, str]]) -> Optional[List[Urteil]]:
        """Unter self._sperre aufrufen. Laedt bei Bedarf und urteilt in beide
        Richtungen; None, wenn das Modell nicht verfuegbar ist oder scheitert."""
        try:
            if not self._laden():
                return None
            texte = [a for a, _ in paare]
            kandidaten = [b for _, b in paare]
            # Hin und rueck in einem Durchlauf: ein Stapel statt zwei.
            richtungen = self._wahrscheinlichkeiten(
                texte + kandidaten, kandidaten + texte
            )
        except Exception as e:
            logger.warning("NLI-Urteil gescheitert (%s)", type(e).__name__)
            return None
        n = len(paare)
        return [Urteil(richtungen[i], richtungen[n + i]) for i in range(n)]

    def urteile_sync(
        self,
        paare: Sequence[Tuple[str, str]],
        warte_hoechstens: Optional[float] = None,
    ) -> Optional[List[Urteil]]:
        if not paare:
            return []
        if warte_hoechstens is not None and self._modell is None:
            return None  # laedt noch (oder nie): nicht auf das Laden warten
        if not self._sperre.acquire(
            timeout=-1 if warte_hoechstens is None else warte_hoechstens
        ):
            return None
        try:
            return self._rechnen(list(paare))
        finally:
            self._sperre.release()

    async def _sperre_holen(self, warte_hoechstens: Optional[float]) -> bool:
        """Die Sperre holen, ohne einen Thread zu belegen; False nach der Wartezeit."""
        frist = (
            None if warte_hoechstens is None else time.monotonic() + warte_hoechstens
        )
        while not self._sperre.acquire(blocking=False):
            if frist is not None and time.monotonic() >= frist:
                return False
            await asyncio.sleep(NACHFRAGEN_ALLE)
        return True

    async def urteile(
        self,
        paare: Sequence[Tuple[str, str]],
        warte_hoechstens: Optional[float] = None,
    ) -> Optional[List[Urteil]]:
        if not paare:
            return []
        if warte_hoechstens is not None and self._modell is None:
            return None  # laedt noch (oder nie): nicht auf das Laden warten
        if not await self._sperre_holen(warte_hoechstens):
            return None
        try:
            # Rechnet in einem Thread: Die Suche anderer Personen wartet nicht darauf.
            return await asyncio.to_thread(self._rechnen, list(paare))
        finally:
            self._sperre.release()


_MODELLE: Dict[Tuple[str, Optional[str]], NliModell] = {}
_MODELLE_SPERRE = threading.Lock()


def nli_modell(modell_name: str, tokenizer_name: Optional[str] = None) -> NliModell:
    """Das eine NliModell dieses Prozesses fuer modell_name (Dienst, Seeding, Bericht)."""
    with _MODELLE_SPERRE:
        schluessel = (modell_name, tokenizer_name)
        if schluessel not in _MODELLE:
            _MODELLE[schluessel] = NliModell(modell_name, tokenizer_name)
        return _MODELLE[schluessel]
