"""
Misst das Messset (aehnlichkeit_paare.py) mit EMBEDDING_MODELL und gibt die
Auswertung je Paar-Label aus. Mit --schreiben wird aehnlichkeit_gemessen.py neu erzeugt.

    cd mvp/backend/semantic-search-service/app
    ../venv/bin/python -m tests.regression.aehnlichkeit_messen [--schreiben]

Laedt das Modell (~1,5 GB RAM). Nach neuen Paaren, einer neuen Normalisierung oder
einem Modellwechsel laufen lassen und den Diff von aehnlichkeit_gemessen.py lesen:
Aendern sich alte Werte, ist das ein Befund, kein Rauschen.
"""

import datetime
import hashlib
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import numpy as np

from core.config import EMBEDDING_MODELL, Settings
from tests.regression.aehnlichkeit_paare import LABELS, PAARE, Paar
from utils.text_normalisierung import ist_dasselbe, text_normalisiert

# Vorschlagsschwelle im Feld "Antwort auf" (Frontend VORSCHLAG_MIN_AEHNLICHKEIT).
VORSCHLAG_SCHWELLE = 0.885
# So nah an der Schwelle kann eine Entscheidung auf anderer Hardware oder mit einer
# anderen Bibliotheksversion kippen; der Regressionstest vergleicht sie dort nicht.
KNAPP = 0.001

# Paare, bei denen die heutige Dublettenpruefung (Kosinus + Schwelle) eine andere
# Behauptung als dieselbe nimmt. Bekannt und gewollt sichtbar: Diese Faelle
# soll die NLI-Stufe (#387) abfangen. Wer hier ein Paar entfernt, hat es geloest.
# Dass die Liste zu aehnlichkeit_gemessen.py passt, prueft der Unit-Test.
# fmt: off
BEKANNTE_FEHLENTSCHEIDUNGEN = frozenset({
    # Aussagen: still als dieselbe Aussage wiederverwendet
    "VB05", "VB09", "WI07", "BS09", "WP04", "WP07", "TL06", "TL07", "TL13", "EA04",
    "EA05", "EA06", "EA07", "EA08", "FL04", "FL09", "FL12", "EE12", "HZ04", "HZ08",
    "HZ09", "HZ11", "HZ12", "EU06", "DB07", "KW08", "SP07", "LR04", "CO05", "CO12",
    "RW05", "RW06", "WS08", "IN05", "IN06", "IN08", "WA06", "WA10", "DT05", "BI04",
    "BI06", "FB03", "FB04", "FB05", "FB06", "FB11", "FB12", "AK04", "AK07", "AK08",
    "MO06", "FW03", "FW04", "FW05", "FW06", "FW08", "FW11", "FW12", "WO08",
    # Hintergrundinfos: andere Zahl oder Verneinung im sonst gleichen Text, als
    # Dublette angeboten
    "HK03", "HK04", "HA04", "HA05", "HA06", "HU04", "HU05", "HJ03", "HJ04", "HT03",
    "HT04", "HG03", "HG04",
})
# fmt: on

_ZIEL = Path(__file__).with_name("aehnlichkeit_gemessen.py")


def fingerabdruck(paar: Paar) -> str:
    """Kurzer Hash ueber die Texte: Faellt auf, wenn eine ID andere Texte bekommt."""
    roh = "\x00".join((paar.art, paar.kandidat, paar.bestand))
    return hashlib.sha256(roh.encode()).hexdigest()[:10]


class Scores(NamedTuple):
    qq: float
    pp: float
    qp: float


class Messung(NamedTuple):
    """Ein Eintrag in aehnlichkeit_gemessen.GEMESSEN."""

    qq: float
    pp: float
    qp: float
    gleich: bool
    fingerabdruck: str


# Je Art: welcher Score und welche Schwelle aus Settings - dieselbe Wahl wie die
# Dublettenpruefung im Dienst (StatementService, CommentaryService, GenericTextService).
PRUEFUNG_JE_ART = {
    "aussage": ("qq", "statement_similarity_threshold"),
    "suche": ("qq", "statement_similarity_threshold"),
    "kommentar": ("pp", "commentary_similarity_threshold"),
    "hintergrundinfo": ("pp", "generic_text_similarity_threshold"),
}


def gemessen(paar_id: str) -> Messung:
    from tests.regression.aehnlichkeit_gemessen import GEMESSEN

    return Messung(*GEMESSEN[paar_id])


def score(paar: Paar, werte: Scores | Messung) -> float:
    return getattr(werte, PRUEFUNG_JE_ART[paar.art][0])


def schwelle(art: str, settings: Settings) -> float:
    return getattr(settings, PRUEFUNG_JE_ART[art][1])


def entscheidung(paar: Paar, werte: Scores | Messung, settings: Settings) -> bool:
    return ist_dasselbe(
        text_normalisiert(paar.kandidat),
        text_normalisiert(paar.bestand),
        score(paar, werte),
        schwelle(paar.art, settings),
    )


def knapp(paar: Paar, werte: Scores | Messung, settings: Settings) -> bool:
    """Score liegt weniger als KNAPP neben der Schwelle (normalisiert gleiche Texte
    entscheidet die Normalform, nicht der Score)."""
    if text_normalisiert(paar.kandidat) == text_normalisiert(paar.bestand):
        return False
    return abs(score(paar, werte) - schwelle(paar.art, settings)) < KNAPP


@lru_cache(maxsize=1)
def scores() -> dict[str, Scores]:
    """(qq, pp, qp) je Paar-ID, einmal berechnet."""
    from sentence_transformers import SentenceTransformer

    modell = SentenceTransformer(EMBEDDING_MODELL)

    def einbetten(praefix, texte):
        return modell.encode(
            [f"{praefix}: {t}" for t in texte], normalize_embeddings=True
        )

    kandidaten = [p.kandidat for p in PAARE]
    bestand = [p.bestand for p in PAARE]
    qa, pa = einbetten("query", kandidaten), einbetten("passage", kandidaten)
    qb, pb = einbetten("query", bestand), einbetten("passage", bestand)
    return {
        p.id: Scores(
            float(np.dot(qa[i], qb[i])),
            float(np.dot(pa[i], pb[i])),
            float(np.dot(qa[i], pb[i])),
        )
        for i, p in enumerate(PAARE)
    }


def auswertung(messungen: dict[str, Messung], settings: Settings) -> str:
    """Markdown-Tabellen je Art und Label: wie viele Paare ueber den Schwellen liegen."""
    zeilen = []
    for art, (score_name, _) in PRUEFUNG_JE_ART.items():
        paare = [p for p in PAARE if p.art == art]
        ab = schwelle(art, settings)
        zeilen += [
            f"\n{art} (Score {score_name}, Dublette ab {ab}):\n",
            f"| Label | Paare | train/test | Score min–max | als gleich entschieden "
            f"| ≥ {ab} | ≥ {VORSCHLAG_SCHWELLE} |",
            "|---|---|---|---|---|---|---|",
        ]
        for label in LABELS:
            mit = [p for p in paare if p.label == label]
            if not mit:
                continue
            werte = [score(p, messungen[p.id]) for p in mit]
            teile = Counter(p.teil for p in mit)
            zeilen.append(
                f"| {label} | {len(mit)} | {teile['train']}/{teile['test']} "
                f"| {min(werte):.3f}–{max(werte):.3f} "
                f"| {sum(messungen[p.id].gleich for p in mit)} "
                f"| {sum(w >= ab for w in werte)} "
                f"| {sum(w >= VORSCHLAG_SCHWELLE for w in werte)} |"
            )
    return "\n".join(zeilen)


def _schreiben(messungen: dict[str, Messung]) -> None:
    kopf = (
        '"""\n'
        f"Erzeugt von tests/regression/aehnlichkeit_messen.py am "
        f"{datetime.date.today().isoformat()} mit {EMBEDDING_MODELL}.\n"
        "Nicht von Hand aendern. (qq, pp, qp, gleich, fingerabdruck) je Paar-ID:\n"
        "qq = query/query (Aussagen, Suchanfragen), pp = passage/passage (Kommentare,\n"
        "Hintergrundinfos), qp = query gegen passage (frueherer Kommentarvergleich),\n"
        "gleich = Entscheidung der Dublettenpruefung mit den Schwellen aus core/config.py.\n"
        '"""\n\n'
        "# fmt: off\n"
        "GEMESSEN = {\n"
    )
    zeilen = [
        f'    "{pid}": ({qq:.6f}, {pp:.6f}, {qp:.6f}, {gleich}, "{fp}"),'
        for pid, (qq, pp, qp, gleich, fp) in messungen.items()
    ]
    _ZIEL.write_text(kopf + "\n".join(zeilen) + "\n}\n# fmt: on\n", encoding="utf-8")


def main(argv: list[str]) -> None:
    settings = Settings()
    roh = scores()
    messungen = {
        p.id: Messung(
            *roh[p.id], entscheidung(p, roh[p.id], settings), fingerabdruck(p)
        )
        for p in PAARE
    }
    if "--schreiben" in argv:
        _schreiben(messungen)
        print(f"geschrieben: {_ZIEL}")
    print(auswertung(messungen, settings))


if __name__ == "__main__":
    main(sys.argv[1:])
