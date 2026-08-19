#!/usr/bin/env python3
"""
Proof of Concept: KI-gestuetzte Wirkungsbewertung von Beitragsentwuerfen.

ZWECK: Baseline, kein Feature. Das Skript beantwortet EINE Frage -- sind die drei
Kriterien trennscharf genug, um zwischen einem schwachen und einem tragfaehigen
Entwurf zu unterscheiden, ohne bei harmlosen Texten ueberall etwas zu finden?

Es ist bewusst standalone: kein Import aus dem app-Paket, kein Endpunkt, keine
Aenderung an Produktivcode. Vorbild fuer die OpenAI-Anbindung ist
app/services/vision/caption_suggestion_service.py (AsyncOpenAI, Key aus der
Umgebung, harter Fehler bei Fehlkonfiguration).

Zwei Dinge werden ABSICHTLICH im Code entschieden und nicht dem Modell ueberlassen:

1. ZITATPFLICHT (siehe _beleg_gilt). Ein Urteil ohne woertlichen Beleg aus dem
   Eingabetext wird verworfen und auf "keine" heruntergestuft. Ein Prompt, der um
   Belege bittet, ist eine Bitte; diese Pruefung ist eine Bedingung.
2. NACHBARTEST (siehe _rollup). Er ist kein viertes Kriterium, sondern eine
   deterministische Funktion der drei Detektoren. Wuerde man ihn das Modell
   beurteilen lassen, korrelierte er mit den Detektoren und wiederholte sie nur.

Key:
    OPENAI_API_KEY oder SEMANTIC_SEARCH_OPENAI_API_KEY
    (dieselben zwei Namen wie core/config.py, damit es keine dritte Konvention gibt)

Benutzung:
    # Einzeltext
    python mvp/scripts/manual/check_wirkung_baseline.py --text "..." [--titel "..."]

    # Baseline-Lauf: 3 handangelegte Dev-DB-Beitraege + 10 zufaellige Seed-Kommentare
    python mvp/scripts/manual/check_wirkung_baseline.py --korpus --out ergebnis.json

    # Prompts ansehen, ohne die API zu rufen (braucht keinen Key)
    python mvp/scripts/manual/check_wirkung_baseline.py --korpus --dry-run

--korpus liest direkt aus Qdrant (Default http://localhost:6333) und setzt damit --
wie die uebrigen Skripte in diesem Verzeichnis -- einen laufenden Dev-Stack voraus.
Die Auswahl der 10 Seed-Kommentare ist ueber --seed reproduzierbar.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

# --------------------------------------------------------------------------------
# Prompt
# --------------------------------------------------------------------------------

SYSTEM_PROMPT = """\
Du bist ein Pruefwerkzeug fuer Beitragsentwuerfe auf einer parteiinternen Plattform.
Du bewertest AUSSCHLIESSLICH Wirkung und Formulierung eines Entwurfs auf Menschen,
die politisch NICHT festgelegt sind.

HARTE VERBOTE -- Verstoesse machen die Ausgabe unbrauchbar:
- Du pruefst KEINE Fakten. Ob eine Zahl, ein Datum, ein Name oder eine Behauptung
  zutrifft, ist nicht deine Aufgabe. Du behauptest dazu nichts und korrigierst nichts.
- Du korrigierst KEINE Inhalte und schreibst den Text NICHT um.
- Du lieferst KEINEN Ersatztext, keine Alternativformulierung, keinen Beispielsatz.
- Du bewertest nicht, ob die politische Position richtig oder falsch ist.
Du sagst nur, WIE etwas gesagt ist -- nie, OB es stimmt.

DREI UNABHAENGIGE DETEKTOREN. Pruefe jeden einzeln und lass das Ergebnis des einen
nicht auf die anderen durchschlagen. Ein Text kann herablassend klingen und trotzdem
ein starkes eigenes Argument haben; beides wird getrennt bewertet.

(a) unterstellung -- Unterstellung oder Lagerzuschreibung.
    Wird einer Gruppe oder einer Person ein Motiv, eine Gesinnung, ein Charakterzug
    oder ein Hintergedanke zugeschrieben? Marker: "die gleichen Leute, die ...",
    "typisch fuer ...", "was X immer machen", Aussagen ueber die Psyche oder die
    wahren Absichten von Gegnern, Zuweisung zu einem politischen Lager als Ersatz
    fuer eine Begruendung.
    NICHT gemeint: Kritik an einer Position, einem Gesetz oder einer Entscheidung.

(b) kein_eigener_punkt -- fehlendes eigenes Argument.
    Enthaelt der Text ein eigenes Argument, eine eigene Beobachtung, eigene Zahlen
    oder eine eigene Erfahrung? Oder ist es eine uebernommene Bildunterschrift, eine
    Parole oder eine blosse Behauptung, die nichts begruendet?
    Beleg fuer (b) ist die Stelle, die ANSTELLE eines Arguments steht -- also die
    Behauptung oder das Etikett, das die Begruendung ersetzt.

(c) snark -- snarky, polarisierend, herabsetzend.
    Spott, Haeme, Herablassung, Triumphgesten, Augenroll-Emojis, hoehnische
    Floskeln ("aber klar, ...", "erzaehl weiter deine Maerchen"), direkte Anrede
    des Gegenuebers im Angriff.
    NICHT gemeint: Zuspitzung, Ironie ueber Sachverhalte, Humor ohne Adressat.
    Pointiert ist erlaubt. Herabsetzend ist es nicht.

ZITATPFLICHT -- ohne Beleg gilt ein Urteil nicht:
Jeder Detektor, der anschlaegt, MUSS ein woertliches Zitat aus dem Entwurf liefern,
Zeichen fuer Zeichen wie im Text, hoechstens 12 Woerter. Kein Paraphrasieren, keine
Auslassungszeichen, keine Korrektur von Schreibweise oder Zeichensetzung. Findest du
keine belegbare Stelle, ist die Stufe "keine".

STUFEN:
- "keine"    -- trifft nicht zu.
- "WARNUNG"  -- schwaecht die Wirkung auf Unentschiedene, ist aber im Rahmen.
                Beispiel: eine haemische Schlussfloskel unter einem sonst
                sachlichen Absatz.
- "STOPP"    -- der Entwurf sollte so nicht hinausgehen. Gilt fuer eindeutige
                Unterstellungen, Lagerzuschreibung als Ersatz fuer Argumente, und
                fuer jede Herabsetzung einer Person ueber Herkunft, Sexualitaet,
                Religion, Behinderung, Geschlecht oder Gesundheit. Letzteres ist
                immer STOPP, unabhaengig vom uebrigen Text.

HINWEIS:
Genau EIN Satz. Er benennt die kleinste Aenderung, die den Entwurf tragfaehig macht,
und ist wenn moeglich eine Streichung ("Streiche ...", "Der letzte Satz ..."). Er
enthaelt NIE eine fertige Ersatzformulierung. Schlaegt kein Detektor an, ist der
Hinweis ein leerer String.

Antworte ausschliesslich als JSON nach dem vorgegebenen Schema.
"""


def _detektor_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["stufe", "beleg", "begruendung"],
        "properties": {
            "stufe": {
                "type": "string",
                "enum": ["keine", "WARNUNG", "STOPP"],
                "description": "Schweregrad dieses Detektors.",
            },
            "beleg": {
                "type": "string",
                "description": (
                    "Woertliches Zitat aus dem Entwurf, max. 12 Woerter. "
                    "Leerer String, wenn stufe 'keine' ist."
                ),
            },
            "begruendung": {
                "type": "string",
                "description": "Ein kurzer Satz, warum die Stelle anschlaegt.",
            },
        },
    }


RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["detektoren", "hinweis"],
    "properties": {
        "detektoren": {
            "type": "object",
            "additionalProperties": False,
            "required": ["unterstellung", "kein_eigener_punkt", "snark"],
            "properties": {
                "unterstellung": _detektor_schema(),
                "kein_eigener_punkt": _detektor_schema(),
                "snark": _detektor_schema(),
            },
        },
        "hinweis": {
            "type": "string",
            "description": "Genau ein Satz, oder leer, wenn nichts anschlaegt.",
        },
    },
}

DETEKTOR_LABEL = {
    "unterstellung": "(a) Unterstellung/Lagerzuschreibung",
    "kein_eigener_punkt": "(b) kein eigener Punkt",
    "snark": "(c) snarky/polarisierend",
}


def build_user_message(titel: str, text: str, typ: str = "") -> str:
    """Assemble the user message. The model sees exactly this string as the draft."""
    teile = []
    if titel:
        teile.append(f"Titel: {titel}")
    if typ:
        teile.append(f"Typ: {typ}")
    teile.append(f"Text: {text}")
    return "\n".join(teile)


def pruefbarer_text(titel: str, text: str) -> str:
    """The text a citation must be found in -- title and body, nothing else."""
    return f"{titel}\n{text}" if titel else text


# --------------------------------------------------------------------------------
# Zitatpflicht und Roll-up (bewusst im Code, nicht im Prompt)
# --------------------------------------------------------------------------------

_TYPOGRAFIE = {
    "„": '"',
    "“": '"',
    "”": '"',
    "«": '"',
    "»": '"',
    "‘": "'",
    "’": "'",
    "‚": "'",
    "–": "-",
    "—": "-",
    "…": "...",
}


def _normalisiere(s: str) -> str:
    """Fold away the differences a model plausibly introduces when quoting."""
    s = unicodedata.normalize("NFKC", s)
    for alt, neu in _TYPOGRAFIE.items():
        s = s.replace(alt, neu)
    s = s.casefold()
    return re.sub(r"\s+", " ", s).strip()


def _beleg_gilt(beleg: str, quelle: str) -> bool:
    """A citation counts only if it literally occurs in the draft."""
    if not beleg or not beleg.strip():
        return False
    return _normalisiere(beleg) in _normalisiere(quelle)


def _rollup(stufen: List[str]) -> Dict[str, str]:
    """
    Nachbartest als deterministische Funktion der drei Detektoren.

    Ein STOPP genuegt. Zwei Warnungen kippen den Text ebenfalls -- eine haemische
    Floskel allein macht einen Entwurf noch nicht unbrauchbar, zwei Befunde schon.
    """
    if "STOPP" in stufen:
        return {"nachbartest": "nicht_bestanden", "gesamtstufe": "STOPP"}
    warnungen = stufen.count("WARNUNG")
    if warnungen >= 2:
        return {"nachbartest": "nicht_bestanden", "gesamtstufe": "WARNUNG"}
    if warnungen == 1:
        return {"nachbartest": "knapp", "gesamtstufe": "WARNUNG"}
    return {"nachbartest": "bestanden", "gesamtstufe": "keine"}


def nachbereiten(roh: Dict[str, Any], quelle: str) -> Dict[str, Any]:
    """Enforce the citation requirement, then compute the roll-up."""
    detektoren: Dict[str, Any] = {}
    for schluessel in ("unterstellung", "kein_eigener_punkt", "snark"):
        d = dict(roh.get("detektoren", {}).get(schluessel) or {})
        stufe_modell = d.get("stufe", "keine")
        beleg = d.get("beleg", "") or ""
        beleg_ok = _beleg_gilt(beleg, quelle) if stufe_modell != "keine" else True
        detektoren[schluessel] = {
            "stufe": stufe_modell if beleg_ok else "keine",
            "stufe_modell": stufe_modell,
            "beleg": beleg,
            "beleg_ok": beleg_ok,
            "verworfen_ohne_beleg": stufe_modell != "keine" and not beleg_ok,
            "begruendung": d.get("begruendung", ""),
        }

    ergebnis = _rollup([d["stufe"] for d in detektoren.values()])
    ergebnis["detektoren"] = detektoren
    ergebnis["hinweis"] = (roh.get("hinweis") or "").strip()
    if ergebnis["gesamtstufe"] == "keine":
        # Nothing survived the citation check -- a hint would have nothing to point at.
        ergebnis["hinweis"] = ""
    return ergebnis


# --------------------------------------------------------------------------------
# OpenAI
# --------------------------------------------------------------------------------


def api_key_aus_umgebung() -> str:
    """Same two variable names as core/config.py. Hard error, no silent fallback."""
    key = os.getenv("OPENAI_API_KEY") or os.getenv("SEMANTIC_SEARCH_OPENAI_API_KEY")
    if not key or not key.strip():
        raise SystemExit(
            "FEHLER: kein API-Key gesetzt.\n"
            "  Setze OPENAI_API_KEY oder SEMANTIC_SEARCH_OPENAI_API_KEY.\n"
            "  Ohne Key laeuft nur --dry-run (zeigt die Prompts, ruft nichts auf)."
        )
    return key.strip()


async def pruefe_einen(client, model: str, titel: str, text: str, typ: str) -> Dict:
    """One draft, one API call. Returns the raw model JSON."""
    nachricht = build_user_message(titel, text, typ)
    anfrage = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": nachricht},
        ],
        "temperature": 0,
        "max_tokens": 700,
    }
    try:
        antwort = await client.chat.completions.create(
            **anfrage,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "wirkungspruefung",
                    "strict": True,
                    "schema": RESPONSE_SCHEMA,
                },
            },
        )
    except Exception as e:
        # Aeltere Snapshots koennen strict json_schema ablehnen; json_object reicht,
        # weil die Struktur ohnehin in nachbereiten() geprueft wird.
        if "json_schema" not in str(e) and "response_format" not in str(e):
            raise
        print(f"  (Hinweis: json_schema abgelehnt, Fallback auf json_object: {e})")
        antwort = await client.chat.completions.create(
            **anfrage, response_format={"type": "json_object"}
        )

    inhalt = antwort.choices[0].message.content or ""
    if not inhalt.strip():
        raise ValueError("Leere Antwort vom Modell")
    return json.loads(inhalt)


# --------------------------------------------------------------------------------
# Korpus aus Qdrant
# --------------------------------------------------------------------------------

BEITRAGSTYPEN = ("commentary", "generic_text", "post", "image")
"""Beitragstypen. `statement` ist die beantwortete Aussage, `reference` eine Quelle --
beides sind keine Entwuerfe und gehoeren nicht in die Pruefung."""


@dataclass
class Eintrag:
    gruppe: str
    quelle: str
    typ: str
    titel: str
    text: str
    ergebnis: Optional[Dict[str, Any]] = None
    fehler: str = ""
    roh: Dict[str, Any] = field(default_factory=dict)


def _scroll(qdrant: str, collection: str, filt: Optional[Dict]) -> List[Dict]:
    rumpf: Dict[str, Any] = {"limit": 1000, "with_payload": True, "with_vector": False}
    if filt:
        rumpf["filter"] = filt
    r = requests.post(
        f"{qdrant}/collections/{collection}/points/scroll", json=rumpf, timeout=30
    )
    r.raise_for_status()
    return [p["payload"] for p in r.json()["result"]["points"]]


def lade_korpus(
    qdrant: str, collection: str, seed: int, anzahl_seed: int
) -> List[Eintrag]:
    """Die 3 handangelegten Beitraege + `anzahl_seed` zufaellige Seed-Kommentare."""
    alle = _scroll(qdrant, collection, None)

    handgemacht = sorted(
        (
            p
            for p in alle
            if p.get("origin") == "manually_created"
            and p.get("content_type") in BEITRAGSTYPEN
        ),
        key=lambda p: str(p.get("created", "")),
    )
    seed_kommentare = sorted(
        (
            p
            for p in alle
            if p.get("origin") == "initial_data"
            and p.get("content_type") == "commentary"
            and (p.get("text") or "").strip()
        ),
        key=lambda p: str(p.get("id", "")),
    )
    gezogen = random.Random(seed).sample(
        seed_kommentare, min(anzahl_seed, len(seed_kommentare))
    )

    def zu_eintrag(p: Dict, gruppe: str) -> Eintrag:
        return Eintrag(
            gruppe=gruppe,
            quelle=str(p.get("id", ""))[:8],
            typ=p.get("content_type", ""),
            titel=(p.get("title") or "").strip(),
            text=(p.get("text") or "").strip(),
        )

    return [zu_eintrag(p, "handangelegt") for p in handgemacht] + [
        zu_eintrag(p, "seed") for p in gezogen
    ]


# --------------------------------------------------------------------------------
# Ausgabe
# --------------------------------------------------------------------------------

SYMBOL = {"keine": "OK  ", "WARNUNG": "WARN", "STOPP": "STOP"}


def drucke_eintrag(e: Eintrag) -> None:
    kopf = f"[{e.gruppe}/{e.typ}/{e.quelle}] {e.titel or '(ohne Titel)'}"
    print("\n" + "=" * 78)
    print(kopf)
    print("-" * 78)
    print(f"  {e.text[:300]}{'...' if len(e.text) > 300 else ''}")
    print("-" * 78)
    if e.fehler:
        print(f"  FEHLER: {e.fehler}")
        return
    r = e.ergebnis or {}
    for schluessel, label in DETEKTOR_LABEL.items():
        d = r["detektoren"][schluessel]
        zeile = f"  {SYMBOL[d['stufe']]} {label}"
        if d["verworfen_ohne_beleg"]:
            zeile += f"  <- {d['stufe_modell']} VERWORFEN (Beleg nicht im Text)"
        print(zeile)
        if d["beleg"]:
            print(f'         Beleg: "{d["beleg"]}"')
        if d["begruendung"] and d["stufe"] != "keine":
            print(f"         {d['begruendung']}")
    print(f"  => NACHBARTEST: {r['nachbartest']}  (Gesamt: {r['gesamtstufe']})")
    if r["hinweis"]:
        print(f"  => HINWEIS: {r['hinweis']}")


def drucke_zusammenfassung(eintraege: List[Eintrag]) -> None:
    print("\n" + "=" * 78)
    print("ZUSAMMENFASSUNG")
    print("=" * 78)
    print(f"{'Gruppe':<14}{'n':>3}  {'bestanden':>10}{'knapp':>7}{'durchgef.':>11}")
    for gruppe in ("handangelegt", "seed"):
        g = [e for e in eintraege if e.gruppe == gruppe and e.ergebnis]
        if not g:
            continue
        z = [e.ergebnis["nachbartest"] for e in g]
        print(
            f"{gruppe:<14}{len(g):>3}  "
            f"{z.count('bestanden'):>10}{z.count('knapp'):>7}"
            f"{z.count('nicht_bestanden'):>11}"
        )
    verworfen = sum(
        1
        for e in eintraege
        if e.ergebnis
        for d in e.ergebnis["detektoren"].values()
        if d["verworfen_ohne_beleg"]
    )
    print(f"\nOhne gueltigen Beleg verworfene Urteile: {verworfen}")


# --------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------


async def lauf(eintraege: List[Eintrag], model: str, parallel: int) -> None:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key_aus_umgebung())
    sperre = asyncio.Semaphore(parallel)

    async def einer(e: Eintrag) -> None:
        async with sperre:
            try:
                e.roh = await pruefe_einen(client, model, e.titel, e.text, e.typ)
                e.ergebnis = nachbereiten(e.roh, pruefbarer_text(e.titel, e.text))
            except Exception as ex:  # noqa: BLE001 -- Baseline soll weiterlaufen
                e.fehler = f"{type(ex).__name__}: {ex}"

    await asyncio.gather(*(einer(e) for e in eintraege))


def main() -> int:
    p = argparse.ArgumentParser(
        description="PoC Wirkungsbewertung -- Baseline, kein Feature."
    )
    p.add_argument("--text", help="Einzelner Beitragstext")
    p.add_argument("--titel", default="", help="Titel zum Einzeltext")
    p.add_argument("--typ", default="", help="Inhaltstyp zum Einzeltext")
    p.add_argument(
        "--korpus", action="store_true", help="Baseline-Lauf ueber die Dev-DB"
    )
    p.add_argument("--qdrant", default="http://localhost:6333")
    p.add_argument("--collection", default="content_collection")
    p.add_argument(
        "--seed", type=int, default=20260819, help="Auswahl der Seed-Kommentare"
    )
    p.add_argument("--anzahl-seed", type=int, default=10)
    p.add_argument("--model", default="gpt-4o-mini")
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument(
        "--dry-run", action="store_true", help="Prompts zeigen, nichts rufen"
    )
    p.add_argument("--out", help="Rohergebnisse als JSON hierhin schreiben")
    args = p.parse_args()

    if args.korpus:
        eintraege = lade_korpus(
            args.qdrant, args.collection, args.seed, args.anzahl_seed
        )
        if not eintraege:
            print("Keine Eintraege gefunden -- laeuft der Dev-Stack?", file=sys.stderr)
            return 1
    elif args.text:
        eintraege = [Eintrag("einzeln", "-", args.typ, args.titel, args.text.strip())]
    else:
        p.error("entweder --text oder --korpus angeben")
        return 2

    if args.dry_run:
        print(f"--- SYSTEM-PROMPT ({len(SYSTEM_PROMPT)} Zeichen) ---")
        print(SYSTEM_PROMPT)
        for e in eintraege:
            print("=" * 78)
            print(f"--- USER-MESSAGE [{e.gruppe}/{e.typ}/{e.quelle}] ---")
            print(build_user_message(e.titel, e.text, e.typ))
        print("=" * 78)
        print(f"{len(eintraege)} Entwuerfe, kein API-Aufruf (--dry-run).")
        return 0

    asyncio.run(lauf(eintraege, args.model, args.parallel))

    for e in eintraege:
        drucke_eintrag(e)
    if args.korpus:
        drucke_zusammenfassung(eintraege)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "model": args.model,
                    "seed": args.seed,
                    "eintraege": [
                        {
                            "gruppe": e.gruppe,
                            "quelle": e.quelle,
                            "typ": e.typ,
                            "titel": e.titel,
                            "text": e.text,
                            "roh": e.roh,
                            "ergebnis": e.ergebnis,
                            "fehler": e.fehler,
                        }
                        for e in eintraege
                    ],
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"\nRohergebnisse: {args.out}")

    return 1 if any(e.fehler for e in eintraege) else 0


if __name__ == "__main__":
    sys.exit(main())
