"""
Bericht ueber den Bestand (#387): Welche vorhandenen Aussagen waeren nach der NLI-Stufe
dieselbe? Entscheidet wie der Dienst (stufe.dieselben_finden, #614): mit dem Bestaetiger,
wenn SEMANTIC_SEARCH_NLI_BESTAETIGER an ist; die erste Zeile nennt den Weg. Grundlage
fuer die Auswertung des Schattenbetriebs vor der Umstellung auf "an". Es legt nichts
zusammen und aendert nichts; Zusammenlegen im Bestand waere ein eigenes Ticket.

    cd mvp/backend/semantic-search-service/app
    ../venv/bin/python -m tests.regression.dieselbe_bericht            # Zahlen
    ../venv/bin/python -m tests.regression.dieselbe_bericht --paare    # dazu die Paare

Verbindet sich wie der Dienst (SEMANTIC_SEARCH_QDRANT_URL, ..._QDRANT_COLLECTION) und
laedt Einbettungs- und NLI-Modell (zusammen rund 3 GB RAM, mit Bestaetiger rund 2,2 GB
mehr). Im Container des Semantic-Search-Service:
`python -m tests.regression.dieselbe_bericht`. Mit --paare stehen die Texte der
Aussagen in der Ausgabe: nur lokal lesen, nicht in Tickets oder Logs kopieren
(Suchanfragen unter den Aussagen). Paare ueber den Bestaetiger tragen [Bestaetiger];
ihre Folgerung ist die des Bestaetigers.
"""

import argparse
import asyncio
import sys
from typing import List, NamedTuple, Optional, Sequence

SEITE = 200


class Paar(NamedTuple):
    a_id: str
    a_text: str
    b_id: str
    b_text: str
    score: float
    folgerung: float
    weg: str = "nli"


class Modelle(NamedTuple):
    """Die Modelle, mit denen der Bericht urteilt, wie der Dienst sie hat."""

    nli: object
    bestaetiger: Optional[object]


def modelle_laden(settings) -> Modelle:
    """Das erste Modell immer (auch bei dieselbe_aussage_nli = aus: der Bericht misst
    die NLI-Stufe vor der Umstellung), den Bestaetiger, wenn nli_bestaetiger an ist
    (SEMANTIC_SEARCH_NLI_BESTAETIGER) - wie im Dienst. Es sind die Modelle des Prozesses
    (nli_modell), im Dienst schon im Hintergrund geladen, kein zweites im Speicher."""
    from core.config import (
        NLI_BESTAETIGER_MODELL,
        NLI_BESTAETIGER_TOKENIZER,
        NLI_MODELL,
    )
    from services.dieselbe_behauptung.nli_modell import nli_modell

    nli = nli_modell(NLI_MODELL)
    if not nli.laden_abwarten():
        raise SystemExit(f"NLI-Modell {NLI_MODELL} nicht verfuegbar")
    bestaetiger = None
    if settings.nli_bestaetiger:
        bestaetiger = nli_modell(NLI_BESTAETIGER_MODELL, NLI_BESTAETIGER_TOKENIZER)
        if not bestaetiger.laden_abwarten():
            raise SystemExit(
                f"Bestaetiger {NLI_BESTAETIGER_MODELL} nicht verfuegbar; ohne ihn "
                "SEMANTIC_SEARCH_NLI_BESTAETIGER=false setzen"
            )
    return Modelle(nli, bestaetiger)


def weg_beschreiben(settings, mit_bestaetiger: bool) -> str:
    """Welcher Weg aktiv war, mit den Schaltern aus der Umgebung."""
    weg = "erstes Modell und Bestaetiger" if mit_bestaetiger else "nur erstes Modell"
    schalter = "true" if settings.nli_bestaetiger else "false"
    return (
        f"Weg: {weg}; SEMANTIC_SEARCH_DIESELBE_AUSSAGE_NLI="
        f"{settings.dieselbe_aussage_nli}, SEMANTIC_SEARCH_NLI_BESTAETIGER={schalter}"
    )


async def paare_finden(
    statement_service, modelle: Optional[Modelle] = None
) -> tuple[int, List[Paar]]:
    """Je sichtbarer Aussage die Kandidaten wie beim Anlegen, ohne sie selbst, und die
    Entscheidung wie im Dienst (stufe.dieselben_finden, auch der Weg ueber den
    Bestaetiger). Ein Paar zaehlt einmal, auch wenn beide Richtungen es finden; findet
    es eine Richtung ueber das erste Modell, zaehlt es auf diesem Weg."""
    from domain.models.content_status import ContentStatus
    from services.dieselbe_behauptung import stufe

    settings = statement_service.settings
    if modelle is None:
        modelle = await asyncio.to_thread(modelle_laden, settings)
    aussagen = []
    offset = 0
    while True:
        seite = await statement_service.get_all(SEITE, offset)
        aussagen += [a for a in seite if a.status == ContentStatus.VISIBLE]
        if len(seite) < SEITE:
            break
        offset += SEITE

    gefunden: dict[frozenset, Paar] = {}
    for aussage in aussagen:
        _, treffer = await statement_service._dublettenkandidaten(
            aussage.text, praefix="query"
        )
        treffer = [t for t in treffer if str(t.id) != str(aussage.id)]
        dieselben = await stufe.dieselben_finden(
            aussage.text, treffer, modelle.nli, modelle.bestaetiger, settings
        )
        if dieselben is None:
            raise SystemExit("NLI-Modell nicht verfuegbar")
        for d in dieselben:
            k = d.kandidat
            schluessel = frozenset({str(aussage.id), str(k.id)})
            vorher = gefunden.get(schluessel)
            if vorher is None or (
                vorher.weg != stufe.WEG_NLI and d.weg == stufe.WEG_NLI
            ):
                gefunden[schluessel] = Paar(
                    str(aussage.id),
                    aussage.text,
                    str(k.id),
                    k.text,
                    k.score,
                    d.folgerung,
                    d.weg,
                )
    return len(aussagen), list(gefunden.values())


def ausgabe(
    anzahl: int, paare: Sequence[Paar], weg: str, mit_paaren: bool
) -> List[str]:
    """Die Zeilen des Berichts. Die erste beginnt mit "<n> sichtbare Aussagen" (darauf
    greift nli-messen im Ausroll-Skript) und nennt den aktiven Weg."""
    ueber_bestaetiger = sum(1 for p in paare if p.weg != "nli")
    zeilen = [
        f"{anzahl} sichtbare Aussagen, {len(paare)} Paare waeren nach der NLI-Stufe "
        f"dieselbe Aussage, davon {ueber_bestaetiger} ueber den Bestaetiger ({weg})."
    ]
    if mit_paaren:
        for p in sorted(paare, key=lambda p: -p.folgerung):
            markierung = "" if p.weg == "nli" else " [Bestaetiger]"
            zeilen.append(
                f"- {p.score:.3f} / {p.folgerung:.3f}{markierung}: „{p.a_text}“ "
                f"({p.a_id}) = „{p.b_text}“ ({p.b_id})"
            )
    return zeilen


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--paare", action="store_true")
    args = parser.parse_args(argv)

    from core.logging import LoggingConfig, initialize_logging

    initialize_logging(LoggingConfig(level="WARNING", enable_console_utf8=False))
    from tests.regression.suche_messen import dienste_beenden, dienste_starten

    async def laufen():
        dienste = await dienste_starten()
        try:
            service = dienste.statement_service
            modelle = await asyncio.to_thread(modelle_laden, service.settings)
            anzahl, paare = await paare_finden(service, modelle)
            weg = weg_beschreiben(service.settings, modelle.bestaetiger is not None)
            return anzahl, paare, weg
        finally:
            await dienste_beenden()

    anzahl, paare, weg = asyncio.run(laufen())
    for zeile in ausgabe(anzahl, paare, weg, args.paare):
        print(zeile)
    return 0


if __name__ == "__main__":
    sys.exit(main())
