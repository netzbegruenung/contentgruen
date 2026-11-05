"""
Bericht ueber den Bestand (#387): Welche vorhandenen Aussagen waeren nach der NLI-Stufe
dieselbe? Grundlage fuer die Auswertung des Schattenbetriebs vor der Umstellung auf
"an". Es legt nichts zusammen und aendert nichts; Zusammenlegen im Bestand waere ein
eigenes Ticket.

    cd mvp/backend/semantic-search-service/app
    ../venv/bin/python -m tests.regression.dieselbe_bericht            # Zahlen
    ../venv/bin/python -m tests.regression.dieselbe_bericht --paare    # dazu die Paare

Verbindet sich wie der Dienst (SEMANTIC_SEARCH_QDRANT_URL, ..._QDRANT_COLLECTION) und
laedt Einbettungs- und NLI-Modell (zusammen rund 3 GB RAM). Im Container des
Semantic-Search-Service: `python -m tests.regression.dieselbe_bericht`. Mit --paare
stehen die Texte der Aussagen in der Ausgabe: nur lokal lesen, nicht in Tickets oder
Logs kopieren (Suchanfragen unter den Aussagen).
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


async def paare_finden(statement_service) -> tuple[int, List[Paar]]:
    """Je sichtbarer Aussage die Kandidaten wie beim Anlegen, ohne sie selbst; ein
    Paar zaehlt einmal, auch wenn beide Richtungen es finden."""
    from domain.models.content_status import ContentStatus
    from services.dieselbe_behauptung import regel
    from services.dieselbe_behauptung.nli_modell import NliModell
    from core.config import NLI_MODELL

    settings = statement_service.settings
    nli = NliModell(NLI_MODELL)
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
        kandidaten = statement_service._nli_kandidaten(aussage.text, treffer)
        if not kandidaten:
            continue
        urteile = await nli.urteile([(aussage.text, k.text) for k in kandidaten])
        if urteile is None:
            raise SystemExit(f"NLI-Modell {NLI_MODELL} nicht verfuegbar")
        for k, u in zip(kandidaten, urteile):
            if regel.entscheiden(
                aussage.text,
                k.text,
                k.score,
                u,
                kandidaten_ab=settings.nli_kandidaten_ab,
                folgerung_ab=settings.nli_folgerung_ab,
                widerspruch_unter=settings.nli_widerspruch_unter,
            ):
                schluessel = frozenset({str(aussage.id), str(k.id)})
                gefunden.setdefault(
                    schluessel,
                    Paar(
                        str(aussage.id),
                        aussage.text,
                        str(k.id),
                        k.text,
                        k.score,
                        u.folgerung,
                    ),
                )
    return len(aussagen), list(gefunden.values())


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
            return await paare_finden(dienste.statement_service)
        finally:
            await dienste_beenden()

    anzahl, paare = asyncio.run(laufen())
    print(
        f"{anzahl} sichtbare Aussagen, {len(paare)} Paare waeren nach der NLI-Stufe "
        "dieselbe Aussage."
    )
    if args.paare:
        for p in sorted(paare, key=lambda p: -p.folgerung):
            print(
                f"- {p.score:.3f} / {p.folgerung:.3f}: „{p.a_text}“ ({p.a_id}) = "
                f"„{p.b_text}“ ({p.b_id})"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
