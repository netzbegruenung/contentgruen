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

import numpy as np

from core.config import EMBEDDING_MODELL, Settings
from tests.regression.aehnlichkeit_paare import LABELS, PAARE, Paar
from utils.text_normalisierung import ist_dasselbe, text_normalisiert

# Vorschlagsschwelle im Feld "Antwort auf" (Frontend VORSCHLAG_MIN_AEHNLICHKEIT).
VORSCHLAG_SCHWELLE = 0.885

_ZIEL = Path(__file__).with_name("aehnlichkeit_gemessen.py")


def fingerabdruck(paar: Paar) -> str:
    """Kurzer Hash ueber die Texte: Faellt auf, wenn eine ID andere Texte bekommt."""
    roh = "\x00".join((paar.art, paar.kandidat, paar.bestand))
    return hashlib.sha256(roh.encode()).hexdigest()[:10]


def score_und_schwelle(
    paar: Paar, qq: float, pp: float, settings: Settings
) -> tuple[float, float]:
    """Dieselbe Wahl wie die Dublettenpruefung im Dienst je Inhaltstyp."""
    if paar.art == "kommentar":
        return pp, settings.commentary_similarity_threshold
    if paar.art == "hintergrundinfo":
        return pp, settings.generic_text_similarity_threshold
    return qq, settings.statement_similarity_threshold


def entscheidung(paar: Paar, qq: float, pp: float, settings: Settings) -> bool:
    score, schwelle = score_und_schwelle(paar, qq, pp, settings)
    return ist_dasselbe(
        text_normalisiert(paar.kandidat),
        text_normalisiert(paar.bestand),
        score,
        schwelle,
    )


@lru_cache(maxsize=1)
def scores() -> dict[str, tuple[float, float, float]]:
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
        p.id: (
            float(np.dot(qa[i], qb[i])),
            float(np.dot(pa[i], pb[i])),
            float(np.dot(qa[i], pb[i])),
        )
        for i, p in enumerate(PAARE)
    }


def auswertung(gemessen: dict, settings: Settings) -> str:
    """Markdown-Tabellen je Art und Label: wie viele Paare ueber den Schwellen liegen."""
    zeilen = []
    for art in ("aussage", "hintergrundinfo", "kommentar", "suche"):
        paare = [p for p in PAARE if p.art == art]
        schwelle = score_und_schwelle(paare[0], 0, 0, settings)[1]
        zeilen += [
            f"\n{art} (Score {'qq' if art in ('aussage', 'suche') else 'pp'}, "
            f"Dublette ab {schwelle}):\n",
            f"| Label | Paare | train/test | Score min–max | als gleich entschieden "
            f"| ≥ {schwelle} | ≥ {VORSCHLAG_SCHWELLE} |",
            "|---|---|---|---|---|---|---|",
        ]
        for label in LABELS:
            mit = [p for p in paare if p.label == label]
            if not mit:
                continue
            werte = [
                score_und_schwelle(p, *gemessen[p.id][:2], settings)[0] for p in mit
            ]
            teile = Counter(p.teil for p in mit)
            zeilen.append(
                f"| {label} | {len(mit)} | {teile['train']}/{teile['test']} "
                f"| {min(werte):.3f}–{max(werte):.3f} "
                f"| {sum(gemessen[p.id][3] for p in mit)} "
                f"| {sum(w >= schwelle for w in werte)} "
                f"| {sum(w >= VORSCHLAG_SCHWELLE for w in werte)} |"
            )
    return "\n".join(zeilen)


def _schreiben(gemessen: dict) -> None:
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
        f'    "{pid}": ({qq:.4f}, {pp:.4f}, {qp:.4f}, {gleich}, "{fp}"),'
        for pid, (qq, pp, qp, gleich, fp) in gemessen.items()
    ]
    _ZIEL.write_text(kopf + "\n".join(zeilen) + "\n}\n# fmt: on\n", encoding="utf-8")


def main(argv: list[str]) -> None:
    settings = Settings()
    roh = scores()
    gemessen = {
        p.id: (
            *roh[p.id],
            entscheidung(p, roh[p.id][0], roh[p.id][1], settings),
            fingerabdruck(p),
        )
        for p in PAARE
    }
    if "--schreiben" in argv:
        _schreiben(gemessen)
        print(f"geschrieben: {_ZIEL}")
    print(auswertung(gemessen, settings))


if __name__ == "__main__":
    main(sys.argv[1:])
