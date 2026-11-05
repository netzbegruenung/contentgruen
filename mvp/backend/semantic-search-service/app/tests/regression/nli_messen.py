"""
Misst die NLI-Stufe (#387) am Messset: je Aussage- und Suchpaar das Urteil von
NLI_MODELL in beide Richtungen, und was die Regel (services/dieselbe_behauptung/regel.py)
mit den Schwellen aus core/config.py daraus macht. Mit --schreiben wird
nli_gemessen.py neu erzeugt, mit --zeit Antwortzeit und Speicher gemessen.

    cd mvp/backend/semantic-search-service/app
    ../venv/bin/python -m tests.regression.nli_messen               # nur Auswertung
    ../venv/bin/python -m tests.regression.nli_messen --schreiben   # nli_gemessen.py neu
    ../venv/bin/python -m tests.regression.nli_messen --zeit [--threads 2]

Laedt das NLI-Modell (~1,2 GB RAM). Kalibriert werden tau und kappa nur am Train-Teil;
der Test-Teil zeigt das Ergebnis (MESSSET.md, Abschnitt NLI-Stufe).
"""

import argparse
import datetime
import resource
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List

from core.config import NLI_MODELL, Settings
from services.dieselbe_behauptung import regel
from services.dieselbe_behauptung.regel import Richtung, Urteil
from tests.regression.aehnlichkeit_messen import (
    VORSCHLAG_SCHWELLE,
    fingerabdruck,
    gemessen,
)
from tests.regression.aehnlichkeit_paare import LABELS, PAARE, Paar

# Die Arten, fuer die die Regel der Aussagen gilt (StatementService).
ARTEN = ("aussage", "suche")
NLI_PAARE = [p for p in PAARE if p.art in ARTEN]

# Paare, die die Regel 1 und 4 zufolge nie dieselbe Aussage sein duerfen und die das
# Ticket ausdruecklich nennt: Gegenteil, Frage gegen Behauptung, nie/immer.
HARTE_FAELLE = ("D11", "B09", "D15")

_ZIEL = Path(__file__).with_name("nli_gemessen.py")
# CPU-Threads der Messung; im Dienst gilt embedding_threads fuer beide Modelle.
THREADS = 2


def urteil(paar_id: str) -> Urteil:
    from tests.regression.nli_gemessen import NLI_GEMESSEN

    hf, hw, rf, rw, _ = NLI_GEMESSEN[paar_id]
    return Urteil(Richtung(hf, hw), Richtung(rf, rw))


def entscheidung_nli(paar: Paar, u: Urteil, settings: Settings) -> bool:
    """Dieselbe Entscheidung wie StatementService._nli_entscheiden fuer einen
    Kandidaten, mit dem query/query-Score aus aehnlichkeit_gemessen.py."""
    return regel.entscheiden(
        paar.kandidat,
        paar.bestand,
        gemessen(paar.id).qq,
        u,
        kandidaten_ab=settings.nli_kandidaten_ab,
        folgerung_ab=settings.nli_folgerung_ab,
        widerspruch_unter=settings.nli_widerspruch_unter,
    )


def kein_vorschlag(paar: Paar, u: Urteil, settings: Settings) -> bool:
    """Das Feld "Antwort auf" schlaegt den Bestandstext nicht vor (Widerspruch)."""
    return regel.widerspricht(u, settings.aussage_vorschlag_widerspruch_ab)


def auswertung(urteile: Dict[str, Urteil], settings: Settings) -> str:
    """Markdown-Tabellen je Art und Label: heute (Schwelle) gegen NLI-Stufe."""
    zeilen = []
    for art in ARTEN:
        paare = [p for p in NLI_PAARE if p.art == art]
        zeilen += [
            f"\n{art} (NLI ab Score {settings.nli_kandidaten_ab}, "
            f"tau {settings.nli_folgerung_ab}, kappa {settings.nli_widerspruch_unter}):\n",
            "| Label | Paare (train/test) | dieselbe heute | dieselbe mit NLI train "
            "| dieselbe mit NLI test | nicht vorgeschlagen (Widerspruch) |",
            "|---|---|---|---|---|---|",
        ]
        for label in LABELS:
            mit = [p for p in paare if p.label == label]
            if not mit:
                continue
            teile = Counter(p.teil for p in mit)

            def nli(teil):
                return sum(
                    entscheidung_nli(p, urteile[p.id], settings)
                    for p in mit
                    if p.teil == teil
                )

            vorgeschlagen = [p for p in mit if gemessen(p.id).qq >= VORSCHLAG_SCHWELLE]
            zeilen.append(
                f"| {label} | {len(mit)} ({teile['train']}/{teile['test']}) "
                f"| {sum(gemessen(p.id).gleich for p in mit)} "
                f"| {nli('train')}/{teile['train']} | {nli('test')}/{teile['test']} "
                f"| {sum(kein_vorschlag(p, urteile[p.id], settings) for p in vorgeschlagen)}"
                f"/{len(vorgeschlagen)} |"
            )
    falsch = [
        p.id
        for p in NLI_PAARE
        if p.label != "gleich" and entscheidung_nli(p, urteile[p.id], settings)
    ]
    verfehlt = [
        p.id
        for p in NLI_PAARE
        if p.label == "gleich" and not entscheidung_nli(p, urteile[p.id], settings)
    ]
    zeilen += [
        "",
        f"Andere Behauptung als dieselbe: {', '.join(falsch) or 'keine'}",
        f"gleich, aber nicht erkannt ({len(verfehlt)}): {', '.join(verfehlt)}",
    ]
    return "\n".join(zeilen)


def urteile_messen(threads: int) -> Dict[str, Urteil]:
    from services.dieselbe_behauptung.nli_modell import NliModell

    import torch

    torch.set_num_threads(threads)
    modell = NliModell(NLI_MODELL)
    ergebnis = modell.urteile_sync([(p.kandidat, p.bestand) for p in NLI_PAARE])
    if ergebnis is None:
        raise SystemExit(f"NLI-Modell {NLI_MODELL} nicht verfuegbar")
    return {p.id: u for p, u in zip(NLI_PAARE, ergebnis)}


def _schreiben(urteile: Dict[str, Urteil]) -> None:
    kopf = (
        '"""\n'
        f"Erzeugt von tests/regression/nli_messen.py am "
        f"{datetime.date.today().isoformat()} mit {NLI_MODELL} (fp32).\n"
        "Nicht von Hand aendern. Je Paar-ID (Aussage, Suche): (Folgerung hin,\n"
        "Widerspruch hin, Folgerung rueck, Widerspruch rueck, fingerabdruck);\n"
        "hin = Kandidat -> Bestand, rueck = Bestand -> Kandidat.\n"
        '"""\n\n'
        "# fmt: off\n"
        "NLI_GEMESSEN = {\n"
    )
    nach_id = {p.id: p for p in NLI_PAARE}
    zeilen = [
        f'    "{pid}": ({u.hin.folgerung:.4f}, {u.hin.widerspruch:.4f}, '
        f"{u.rueck.folgerung:.4f}, {u.rueck.widerspruch:.4f}, "
        f'"{fingerabdruck(nach_id[pid])}"),'
        for pid, u in urteile.items()
    ]
    _ZIEL.write_text(kopf + "\n".join(zeilen) + "\n}\n# fmt: on\n", encoding="utf-8")


def _rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def zeit_messen(threads: int, laeufe: int = 5) -> str:
    """Antwortzeit je Aufruf (Median aus `laeufe`) fuer 1, 5 und 10 Kandidaten (je
    zwei Richtungen) und den zusaetzlichen Speicher. Kurze deutsche Aussagen aus dem
    Messset, wie in der Suche."""
    import torch  # laedt der Dienst ohnehin fuer die Einbettung
    import transformers  # noqa: F401

    from services.dieselbe_behauptung.nli_modell import NliModell

    torch.set_num_threads(threads)
    vorher = _rss_mb()
    start = time.perf_counter()
    modell = NliModell(NLI_MODELL)
    modell.urteile_sync([("a", "b")])
    laden = time.perf_counter() - start
    zeilen = [
        f"NLI-Modell {NLI_MODELL}, fp32, {threads} Threads",
        f"Laden: {laden:.1f} s, Speicher (max. RSS, ohne torch) +{_rss_mb() - vorher:.0f} MB",
        "| Kandidaten | Paare (hin+rueck) | Median ms |",
        "|---|---|---|",
    ]
    paare = [(p.kandidat, p.bestand) for p in NLI_PAARE]
    for kandidaten in (1, 5, 10):
        dauer: List[float] = []
        for lauf in range(laeufe):
            stueck = paare[lauf * kandidaten : (lauf + 1) * kandidaten]
            start = time.perf_counter()
            modell.urteile_sync(stueck)
            dauer.append((time.perf_counter() - start) * 1000)
        zeilen.append(
            f"| {kandidaten} | {2 * kandidaten} | {statistics.median(dauer):.0f} |"
        )
    return "\n".join(zeilen)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--schreiben", action="store_true")
    parser.add_argument("--zeit", action="store_true")
    parser.add_argument("--threads", type=int, default=THREADS)
    args = parser.parse_args()
    if args.zeit:
        print(zeit_messen(args.threads))
        return
    settings = Settings()
    if args.schreiben:
        urteile = urteile_messen(args.threads)
        _schreiben(urteile)
        print(f"geschrieben: {_ZIEL}")
    else:
        urteile = {p.id: urteil(p.id) for p in NLI_PAARE}
    print(auswertung(urteile, settings))


if __name__ == "__main__":
    main()
