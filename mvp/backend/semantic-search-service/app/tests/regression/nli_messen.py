"""
Misst die NLI-Stufe (#387) am Messset: je Aussage- und Suchpaar das Urteil von
NLI_MODELL und des Bestaetigers NLI_BESTAETIGER_MODELL in beide Richtungen, und was die
Regel (services/dieselbe_behauptung/regel.py) mit den Schwellen aus core/config.py daraus
macht, ohne und mit Bestaetiger. Mit --schreiben werden nli_gemessen.py und
nli_bestaetiger_gemessen.py neu erzeugt, mit --zeit Antwortzeit und Speicher gemessen.

    cd mvp/backend/semantic-search-service/app
    ../venv/bin/python -m tests.regression.nli_messen               # nur Auswertung
    ../venv/bin/python -m tests.regression.nli_messen --schreiben   # nli_gemessen.py neu
    ../venv/bin/python -m tests.regression.nli_messen --zeit [--threads 2]

Laedt das NLI-Modell (~1,2 GB RAM), mit --schreiben oder --zeit auch den Bestaetiger
(~2,2 GB). Kalibriert werden tau und kappa nur am Train-Teil;
der Test-Teil zeigt das Ergebnis (MESSSET.md, Abschnitt NLI-Stufe).
"""

import argparse
import datetime
import resource
import statistics
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from core.config import (
    NLI_BESTAETIGER_MODELL,
    NLI_BESTAETIGER_TOKENIZER,
    NLI_MODELL,
    Settings,
)
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

# Paare, die mit Bestaetiger als dieselbe gelten, obwohl sie es nicht sind (beide im
# Train-Teil): TL13 doppelte Verneinung ("Nicht nichts bringt ein Tempolimit"), IN05
# "mitschuld" / "schuld". Der Preis fuer 20 erkannte gleich-Paare mehr (MESSSET.md).
BEKANNT_FALSCH_MIT_BESTAETIGER = ("TL13", "IN05")

_ZIEL = Path(__file__).with_name("nli_gemessen.py")
_ZIEL_BESTAETIGER = Path(__file__).with_name("nli_bestaetiger_gemessen.py")
# CPU-Threads der Messung; im Dienst gilt embedding_threads fuer beide Modelle.
THREADS = 2


def urteil(paar_id: str) -> Urteil:
    from tests.regression.nli_gemessen import NLI_GEMESSEN

    hf, hw, rf, rw, _ = NLI_GEMESSEN[paar_id]
    return Urteil(Richtung(hf, hw), Richtung(rf, rw))


def bestaetigung(paar_id: str) -> Urteil:
    from tests.regression.nli_bestaetiger_gemessen import NLI_BESTAETIGER_GEMESSEN

    hf, hw, rf, rw, _ = NLI_BESTAETIGER_GEMESSEN[paar_id]
    return Urteil(Richtung(hf, hw), Richtung(rf, rw))


def entscheidung_nli(
    paar: Paar, u: Urteil, settings: Settings, b: Optional[Urteil] = None
) -> bool:
    """Dieselbe Entscheidung wie StatementService._nli_entscheiden fuer einen
    Kandidaten, mit dem query/query-Score aus aehnlichkeit_gemessen.py; mit dem
    Urteil b des Bestaetigers wie mit nli_bestaetiger."""
    score = gemessen(paar.id).qq
    if regel.entscheiden(
        paar.kandidat,
        paar.bestand,
        score,
        u,
        kandidaten_ab=settings.nli_kandidaten_ab,
        folgerung_ab=settings.nli_folgerung_ab,
        widerspruch_unter=settings.nli_widerspruch_unter,
    ):
        return True
    return b is not None and regel.bestaetigt(
        paar.kandidat,
        paar.bestand,
        score,
        u,
        b,
        kandidaten_ab=settings.nli_kandidaten_ab,
        folgerung_ab=settings.nli_folgerung_ab,
        widerspruch_unter=settings.nli_widerspruch_unter,
        veto_folgerung_ab=settings.nli_bestaetiger_veto_ab,
    )


def kein_vorschlag(paar: Paar, u: Urteil, settings: Settings) -> bool:
    """Das Feld "Antwort auf" schlaegt den Bestandstext nicht vor (Widerspruch)."""
    return regel.widerspricht(u, settings.aussage_vorschlag_widerspruch_ab)


def auswertung(
    urteile: Dict[str, Urteil],
    settings: Settings,
    bestaetigungen: Optional[Dict[str, Urteil]] = None,
) -> str:
    """Markdown-Tabellen je Art und Label: heute (Schwelle) gegen NLI-Stufe; mit
    bestaetigungen die NLI-Stufe mit Bestaetiger."""

    def entscheidung(p: Paar) -> bool:
        b = None if bestaetigungen is None else bestaetigungen[p.id]
        return entscheidung_nli(p, urteile[p.id], settings, b)

    mit = (
        ""
        if bestaetigungen is None
        else f", mit Bestaetiger (Veto ab {settings.nli_bestaetiger_veto_ab})"
    )
    zeilen = []
    for art in ARTEN:
        paare = [p for p in NLI_PAARE if p.art == art]
        zeilen += [
            f"\n{art} (NLI ab Score {settings.nli_kandidaten_ab}, "
            f"tau {settings.nli_folgerung_ab}, kappa {settings.nli_widerspruch_unter}"
            f"{mit}):\n",
            "| Label | Paare (train/test) | dieselbe heute | dieselbe mit NLI train "
            "| dieselbe mit NLI test | nicht vorgeschlagen (Widerspruch) |",
            "|---|---|---|---|---|---|",
        ]
        for label in LABELS:
            mit_label = [p for p in paare if p.label == label]
            if not mit_label:
                continue
            teile = Counter(p.teil for p in mit_label)

            def nli(teil):
                return sum(entscheidung(p) for p in mit_label if p.teil == teil)

            vorgeschlagen = [
                p for p in mit_label if gemessen(p.id).qq >= VORSCHLAG_SCHWELLE
            ]
            zeilen.append(
                f"| {label} | {len(mit_label)} ({teile['train']}/{teile['test']}) "
                f"| {sum(gemessen(p.id).gleich for p in mit_label)} "
                f"| {nli('train')}/{teile['train']} | {nli('test')}/{teile['test']} "
                f"| {sum(kein_vorschlag(p, urteile[p.id], settings) for p in vorgeschlagen)}"
                f"/{len(vorgeschlagen)} |"
            )
    falsch = [p.id for p in NLI_PAARE if p.label != "gleich" and entscheidung(p)]
    verfehlt = [p.id for p in NLI_PAARE if p.label == "gleich" and not entscheidung(p)]
    nur_heute = [
        p.id
        for p in NLI_PAARE
        if p.label == "gleich" and gemessen(p.id).gleich and not entscheidung(p)
    ]
    zeilen += [
        "",
        f"Andere Behauptung als dieselbe: {', '.join(falsch) or 'keine'}",
        f"gleich, nur mit der Schwelle erkannt ({len(nur_heute)}): "
        f"{', '.join(nur_heute) or 'keine'}",
        f"gleich, aber nicht erkannt ({len(verfehlt)}): {', '.join(verfehlt)}",
    ]
    return "\n".join(zeilen)


def urteile_messen(
    threads: int,
    modell_name: str = NLI_MODELL,
    tokenizer_name: Optional[str] = None,
) -> Dict[str, Urteil]:
    from services.dieselbe_behauptung.nli_modell import NliModell

    import torch

    torch.set_num_threads(threads)
    modell = NliModell(modell_name, tokenizer_name)
    ergebnis = modell.urteile_sync([(p.kandidat, p.bestand) for p in NLI_PAARE])
    if ergebnis is None:
        raise SystemExit(f"NLI-Modell {modell_name} nicht verfuegbar")
    return {p.id: u for p, u in zip(NLI_PAARE, ergebnis)}


def bestaetigungen_messen(threads: int) -> Dict[str, Urteil]:
    return urteile_messen(threads, NLI_BESTAETIGER_MODELL, NLI_BESTAETIGER_TOKENIZER)


def _schreiben(
    urteile: Dict[str, Urteil],
    ziel: Path = _ZIEL,
    modell_name: str = NLI_MODELL,
    name: str = "NLI_GEMESSEN",
) -> None:
    kopf = (
        '"""\n'
        f"Erzeugt von tests/regression/nli_messen.py am "
        f"{datetime.date.today().isoformat()} mit {modell_name} (fp32).\n"
        "Nicht von Hand aendern. Je Paar-ID (Aussage, Suche): (Folgerung hin,\n"
        "Widerspruch hin, Folgerung rueck, Widerspruch rueck, fingerabdruck);\n"
        "hin = Kandidat -> Bestand, rueck = Bestand -> Kandidat.\n"
        '"""\n\n'
        "# fmt: off\n"
        f"{name} = {{\n"
    )
    nach_id = {p.id: p for p in NLI_PAARE}
    zeilen = [
        f'    "{pid}": ({u.hin.folgerung:.4f}, {u.hin.widerspruch:.4f}, '
        f"{u.rueck.folgerung:.4f}, {u.rueck.widerspruch:.4f}, "
        f'"{fingerabdruck(nach_id[pid])}"),'
        for pid, u in urteile.items()
    ]
    ziel.write_text(kopf + "\n".join(zeilen) + "\n}\n# fmt: on\n", encoding="utf-8")


def _rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def zeit_messen(
    threads: int,
    laeufe: int = 5,
    modell_name: str = NLI_MODELL,
    tokenizer_name: Optional[str] = None,
) -> str:
    """Antwortzeit je Aufruf (Median aus `laeufe`) fuer 1, 5 und 10 Kandidaten (je
    zwei Richtungen) und den zusaetzlichen Speicher. Kurze deutsche Aussagen aus dem
    Messset, wie in der Suche. Der Speicher ist der Anstieg des hoechsten Stands im
    Prozess; nach einem ersten Modell zaehlt nur, was ueber dessen Spitze hinausgeht."""
    import torch  # laedt der Dienst ohnehin fuer die Einbettung
    import transformers  # noqa: F401

    from services.dieselbe_behauptung.nli_modell import NliModell

    torch.set_num_threads(threads)
    vorher = _rss_mb()
    start = time.perf_counter()
    modell = NliModell(modell_name, tokenizer_name)
    modell.urteile_sync([("a", "b")])
    laden = time.perf_counter() - start
    zeilen = [
        f"NLI-Modell {modell_name}, fp32, {threads} Threads",
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
        print()
        print(
            zeit_messen(
                args.threads,
                modell_name=NLI_BESTAETIGER_MODELL,
                tokenizer_name=NLI_BESTAETIGER_TOKENIZER,
            )
        )
        return
    settings = Settings()
    if args.schreiben:
        urteile = urteile_messen(args.threads)
        _schreiben(urteile)
        bestaetigungen = bestaetigungen_messen(args.threads)
        _schreiben(
            bestaetigungen,
            _ZIEL_BESTAETIGER,
            NLI_BESTAETIGER_MODELL,
            "NLI_BESTAETIGER_GEMESSEN",
        )
        print(f"geschrieben: {_ZIEL}, {_ZIEL_BESTAETIGER}")
    else:
        urteile = {p.id: urteil(p.id) for p in NLI_PAARE}
        bestaetigungen = {p.id: bestaetigung(p.id) for p in NLI_PAARE}
    print(auswertung(urteile, settings))
    print()
    print(auswertung(urteile, settings, bestaetigungen))


if __name__ == "__main__":
    main()
