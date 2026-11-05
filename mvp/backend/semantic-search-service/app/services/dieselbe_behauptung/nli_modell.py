"""
Das NLI-Modell der NLI-Stufe (#387): ein mehrsprachiger Cross-Encoder, der je Paar
Folgerung, neutral und Widerspruch schaetzt. Lokal auf der CPU, im selben Container
wie die Einbettung; kein Text verlaesst den Dienst (ADR 0005).

Modell: NLI_MODELL in core/config.py (MIT). Nur fp32: Die Model Card schliesst FP16
aus, und dynamisches int8 aenderte in der Erkundung vom 28.10.2026 44 % der Urteile.

Geladen wird beim ersten Urteil (oder mit vorladen() im Hintergrund), nicht beim
Import: Der Dienst startet ohne das Modell, und ohne Modell gilt die heutige Regel.
Scheitert das Laden, bleibt das Modell fuer diesen Prozess aus (eine WARNING), statt
bei jeder Suche neu zu laden.
"""

import asyncio
import logging
import threading
from typing import List, Optional, Protocol, Sequence, Tuple

from services.dieselbe_behauptung.regel import Richtung, Urteil

logger = logging.getLogger(__name__)

# So viele Textpaare rechnet das Modell auf einmal; ein Kandidat sind zwei (hin, rueck).
STAPEL = 32
# Laengere Texte schneidet der Tokenizer ab. Eine Aussage hat hoechstens 1000 Zeichen
# (AUSSAGE_MAX_ZEICHEN), das sind deutlich unter 512 Token.
MAX_TOKEN = 512


class NliPruefer(Protocol):
    """Was StatementService vom Modell braucht; Tests geben eine Attrappe."""

    async def urteile(self, paare: Sequence[Tuple[str, str]]) -> Optional[List[Urteil]]:
        """Je Paar (neuer Text, Kandidat) das Urteil in beide Richtungen; None, wenn
        das Modell nicht verfuegbar ist."""
        ...


class NliModell:
    def __init__(self, modell_name: str, threads: int):
        self._modell_name = modell_name
        self._threads = threads
        self._sperre = threading.Lock()
        self._tokenizer = None
        self._modell = None
        self._kaputt = False
        self._etiketten: Tuple[int, int] = (0, 2)

    @property
    def verfuegbar(self) -> bool:
        return not self._kaputt

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

            torch.set_num_threads(self._threads)
            tokenizer = AutoTokenizer.from_pretrained(self._modell_name)
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

    def urteile_sync(self, paare: Sequence[Tuple[str, str]]) -> Optional[List[Urteil]]:
        if not paare:
            return []
        with self._sperre:
            if not self._laden():
                return None
            try:
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

    async def urteile(self, paare: Sequence[Tuple[str, str]]) -> Optional[List[Urteil]]:
        # Rechnet in einem Thread: Die Suche anderer Personen wartet nicht darauf.
        return await asyncio.to_thread(self.urteile_sync, list(paare))
