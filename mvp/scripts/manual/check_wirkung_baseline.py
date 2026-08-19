#!/usr/bin/env python3
"""
Proof of Concept: KI-gestuetzte Wirkungsbewertung von Beitragsentwuerfen.

ZWECK: Baseline, kein Feature. Das Skript beantwortet EINE Frage -- sind die drei
Kriterien trennscharf genug, um zwischen einem schwachen und einem tragfaehigen
Entwurf zu unterscheiden, ohne bei harmlosen Texten ueberall etwas zu finden?

Es ist bewusst standalone: kein Import aus dem app-Paket, kein Endpunkt, keine
Aenderung an Produktivcode. Der Zuschnitt der Anbindung folgt
app/services/vision/caption_suggestion_service.py (asynchroner Client, Key aus
der Umgebung, harter Fehler bei Fehlkonfiguration) -- gerufen wird aber die
Anthropic-API (AsyncAnthropic, Default-Modell claude-sonnet-4-5).

Zwei Dinge werden ABSICHTLICH im Code entschieden und nicht dem Modell ueberlassen:

1. ZITATPFLICHT (siehe _beleg_gilt). Ein Urteil ohne woertlichen Beleg aus dem
   Eingabetext wird verworfen und auf "keine" heruntergestuft. Ein Prompt, der um
   Belege bittet, ist eine Bitte; diese Pruefung ist eine Bedingung.
2. NACHBARTEST (siehe _rollup). Er ist kein viertes Kriterium, sondern eine
   deterministische Funktion der drei Detektoren. Wuerde man ihn das Modell
   beurteilen lassen, korrelierte er mit den Detektoren und wiederholte sie nur.

Modell:
    Default claude-sonnet-4-5, umstellbar mit --model. Welche Zusatzparameter
    rausgehen, entscheidet modell_parameter() -- ab claude-sonnet-5 lehnt die API
    `temperature` ab, und wo von sich aus gedacht wird, braucht `max_tokens` Luft
    fuer Denken UND Antwort. --no-temperature erzwingt das Weglassen fuer ein
    Modell, das die Liste noch nicht kennt.

Key:
    ANTHROPIC_API_KEY oder SEMANTIC_SEARCH_ANTHROPIC_API_KEY
    (dasselbe Paar wie in core/config.py: der blanke SDK-Name plus die
    Projekt-Praefixform, damit es keine dritte Konvention gibt)

Benutzung:
    # Einzeltext
    python mvp/scripts/manual/check_wirkung_baseline.py --text "..." [--titel "..."]

    # Baseline-Lauf aus der eingefrorenen Korpusdatei -- braucht KEINE Dev-DB.
    # Das ist der Weg, wenn der Key nicht auf die Dev-VM darf: Datei mitnehmen,
    # Lauf auf dem eigenen Rechner, nur `anthropic` als Abhaengigkeit.
    python mvp/scripts/manual/check_wirkung_baseline.py \\
        --korpus-datei mvp/scripts/manual/wirkung_korpus.json --out ergebnis.json

    # Korpus frisch aus der Dev-DB ziehen (braucht laufenden Stack + requests)
    python mvp/scripts/manual/check_wirkung_baseline.py --korpus --out ergebnis.json

    # Korpus aus der Dev-DB einfrieren, ohne die API zu rufen
    python mvp/scripts/manual/check_wirkung_baseline.py --korpus \\
        --korpus-export mvp/scripts/manual/wirkung_korpus.json

    # Prompts ansehen, ohne die API zu rufen (braucht keinen Key)
    python mvp/scripts/manual/check_wirkung_baseline.py --korpus-datei ... --dry-run

--korpus liest direkt aus Qdrant (Default http://localhost:6333) und setzt damit --
wie die uebrigen Skripte in diesem Verzeichnis -- einen laufenden Dev-Stack voraus.
Die Auswahl der 10 Seed-Kommentare ist ueber --seed reproduzierbar.
--korpus-datei liest dieselben Eintraege aus einer eingefrorenen JSON-Datei und
kommt ohne Qdrant und ohne `requests` aus.
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


def _als_objekt(wert: Any) -> Optional[Dict[str, Any]]:
    """Ein Objekt -- auch wenn das Modell es als JSON-String geliefert hat.

    Ohne schema-erzwungene Werkzeugargumente kommt ein verschachteltes Objekt
    gelegentlich als String zurueck ('{"stufe": ...}' statt {"stufe": ...}).
    Das Parsen holt dieselbe Information verlustfrei zurueck.

    None heisst: daraus wird kein Objekt. Dann ist das Urteil kaputt und der
    Eintrag gehoert in die Fehlerspalte -- nicht stillschweigend nach
    "bestanden", denn das hiesse, einen ungeprueften Entwurf durchzuwinken.
    """
    if isinstance(wert, dict):
        return wert
    if isinstance(wert, str) and wert.strip():
        try:
            geparst = json.loads(wert)
        except json.JSONDecodeError:
            return None
        if isinstance(geparst, dict):
            return geparst
    return None


def nachbereiten(roh: Any, quelle: str) -> Dict[str, Any]:
    """Enforce the citation requirement, then compute the roll-up."""
    # Was hier ankommt, hat kein Schema hinter sich, solange --model kein
    # strict-faehiges Modell ist. Jede Ebene wird einzeln geprueft, und jede
    # Reparatur wird vermerkt, damit sie im Ergebnis sichtbar bleibt.
    repariert: List[str] = []

    antwort = _als_objekt(roh)
    if antwort is None:
        raise ValueError(f"Antwort ist kein Objekt, sondern {type(roh).__name__}")
    if antwort is not roh:
        repariert.append("antwort")

    detektoren_roh = antwort.get("detektoren")
    detektoren_obj = _als_objekt(detektoren_roh)
    if detektoren_obj is None:
        raise ValueError(
            "Feld 'detektoren' ist kein Objekt, sondern "
            f"{type(detektoren_roh).__name__}: {str(detektoren_roh)[:120]!r}"
        )
    if detektoren_obj is not detektoren_roh:
        repariert.append("detektoren")

    detektoren: Dict[str, Any] = {}
    for schluessel in ("unterstellung", "kein_eigener_punkt", "snark"):
        wert = detektoren_obj.get(schluessel)
        if wert is None:
            # Fehlender Detektor bleibt wie bisher tolerant: nichts gemeldet.
            d: Dict[str, Any] = {}
        else:
            geprueft = _als_objekt(wert)
            if geprueft is None:
                raise ValueError(
                    f"Detektor '{schluessel}' ist kein Objekt, sondern "
                    f"{type(wert).__name__}: {str(wert)[:120]!r}"
                )
            if geprueft is not wert:
                repariert.append(schluessel)
            d = geprueft
        stufe_modell = d.get("stufe", "keine")
        beleg = d.get("beleg", "") or ""
        if not isinstance(beleg, str):  # Beleg als Zahl/Liste ist kein Zitat
            repariert.append(f"{schluessel}.beleg")
            beleg = ""
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
    hinweis = antwort.get("hinweis") or ""
    if not isinstance(hinweis, str):
        repariert.append("hinweis")
        hinweis = ""
    ergebnis["hinweis"] = hinweis.strip()
    ergebnis["repariert"] = repariert
    if ergebnis["gesamtstufe"] == "keine":
        # Nothing survived the citation check -- a hint would have nothing to point at.
        ergebnis["hinweis"] = ""
    return ergebnis


# --------------------------------------------------------------------------------
# Anthropic
# --------------------------------------------------------------------------------

WERKZEUG_NAME = "wirkungspruefung"

MODELLE_MIT_STRICT = (
    "claude-sonnet-5",
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-fable-5",
    "claude-mythos-5",
    "claude-haiku-4-5",
    "claude-opus-4-5",
    "claude-opus-4-1",
)
"""Modelle, die `strict` auf einem Werkzeug annehmen (Strict Tool Use).

Ohne `strict` sind die Werkzeugargumente nicht schema-validiert: das Modell
darf ein verschachteltes Objekt auch als JSON-String liefern, und genau das
passiert bei claude-sonnet-5 sporadisch. Mit `strict` erzwingt die API die
Struktur, statt dass das Skript sie hinterher reparieren muss.

Wieder eine Positivliste. claude-sonnet-4-5 gehoert nicht dazu -- dort faengt
die Reparatur in _als_objekt() den Fall ab.
"""


def werkzeug_fuer(model: str) -> Dict[str, Any]:
    """Erzwungener Werkzeugaufruf statt json_schema-Antwortformat.

    claude-sonnet-4-5 unterstuetzt `output_config.format` (Structured Outputs)
    nicht -- das gibt es erst ab Sonnet 5 / Opus 4.8 aufwaerts. Ein Werkzeug mit
    `tool_choice` auf genau diesen Namen ist der Weg, der auf jedem Modell
    dasselbe Schema erzwingt. RESPONSE_SCHEMA wandert unveraendert ins
    `input_schema` -- es erfuellt die Anforderungen von `strict` bereits
    (additionalProperties: false und required auf jeder Ebene).
    """
    werkzeug: Dict[str, Any] = {
        "name": WERKZEUG_NAME,
        "description": (
            "Meldet das Pruefergebnis fuer genau einen Entwurf. "
            "Das einzige erlaubte Ausgabeformat."
        ),
        "input_schema": RESPONSE_SCHEMA,
    }
    if model.strip().lower().startswith(MODELLE_MIT_STRICT):
        werkzeug["strict"] = True
    return werkzeug


MODELLE_MIT_TEMPERATURE = (
    "claude-sonnet-4-5",
    "claude-sonnet-4-6",
    "claude-opus-4-1",
    "claude-opus-4-5",
    "claude-opus-4-6",
    "claude-haiku-4-5",
)
"""Modelle, die `temperature` noch annehmen.

Bewusst eine Positivliste und keine Sperrliste: die Menge der alten Modelle ist
abgeschlossen, die der neuen waechst mit jedem Release. Ein unbekanntes Modell
bekommt daher keine `temperature` -- das laeuft ueberall, waehrend der
umgekehrte Default bei jedem neuen Modell in einen 400er liefe.

Ab claude-sonnet-5 / claude-opus-4-7 lehnt die API `temperature` ab
("temperature is deprecated for this model"). Der Ersatz fuer Reproduzierbarkeit
ist keiner: temperature=0 hat identische Ausgaben ohnehin nie garantiert.
"""

MODELLE_MIT_DENKEN = (
    "claude-sonnet-5",
    "claude-opus-5",
    "claude-fable-5",
    "claude-mythos-5",
)
"""Modelle, die ohne `thinking`-Parameter von sich aus denken.

`max_tokens` deckelt Denken UND Antwort zusammen. Wer hier mit dem knappen
Budget der aelteren Modelle anfragt, bekommt eine Antwort, die vollstaendig im
Denken aufgeht -- und damit gar keinen Werkzeugaufruf. Deshalb mehr Luft statt
abgeschaltetem Denken: `thinking: {"type": "disabled"}` waere bei
claude-fable-5 selbst ein 400er.
"""

MAX_TOKENS_KNAPP = 1500
MAX_TOKENS_MIT_DENKEN = 8000


def modell_parameter(model: str, ohne_temperature: bool = False) -> Dict[str, Any]:
    """Die Parameter, die genau dieses Modell annimmt."""
    m = model.strip().lower()
    denkt = m.startswith(MODELLE_MIT_DENKEN)
    parameter: Dict[str, Any] = {
        "max_tokens": MAX_TOKENS_MIT_DENKEN if denkt else MAX_TOKENS_KNAPP,
        "tools": [werkzeug_fuer(model)],
    }
    if m.startswith(MODELLE_MIT_TEMPERATURE) and not ohne_temperature:
        parameter["temperature"] = 0
    return parameter


def api_key_aus_umgebung() -> str:
    """Same two variable names as core/config.py. Hard error, no silent fallback."""
    key = os.getenv("ANTHROPIC_API_KEY") or os.getenv(
        "SEMANTIC_SEARCH_ANTHROPIC_API_KEY"
    )
    if not key or not key.strip():
        raise SystemExit(
            "FEHLER: kein API-Key gesetzt.\n"
            "  Setze ANTHROPIC_API_KEY oder SEMANTIC_SEARCH_ANTHROPIC_API_KEY.\n"
            "  Ohne Key laeuft nur --dry-run (zeigt die Prompts, ruft nichts auf)."
        )
    return key.strip()


async def pruefe_einen(
    client, model: str, titel: str, text: str, typ: str, parameter: Dict[str, Any]
) -> Dict:
    """One draft, one API call. Returns the raw model JSON."""
    nachricht = build_user_message(titel, text, typ)
    antwort = await client.messages.create(
        model=model,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": nachricht}],
        tool_choice={"type": "tool", "name": WERKZEUG_NAME},
        **parameter,
    )

    for block in antwort.content:
        if getattr(block, "type", "") == "tool_use" and block.name == WERKZEUG_NAME:
            return dict(block.input)

    # Kein Werkzeugaufruf trotz tool_choice. Der haeufigste Grund ist eine
    # abgeschnittene Antwort -- dann ist das Argument-JSON unvollstaendig und der
    # Block faellt weg. Das ist ein Fehler des Laufs, keine Bewertung.
    if antwort.stop_reason == "max_tokens":
        raise ValueError(
            f"Antwort bei max_tokens ({parameter['max_tokens']}) abgeschnitten "
            "-- kein Ergebnis"
        )

    # Reserve: manche Modelle antworten trotzdem als Text. Die Struktur wird
    # ohnehin in nachbereiten() geprueft, ein Parse-Versuch kostet also nichts.
    text_bloecke = [
        b.text for b in antwort.content if getattr(b, "type", "") == "text" and b.text
    ]
    if text_bloecke:
        geparst = _als_objekt("\n".join(text_bloecke))
        if geparst is not None:
            return geparst

    raise ValueError(
        f"Kein Werkzeugaufruf in der Antwort (stop_reason={antwort.stop_reason})"
    )


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
    # Lazy, damit der Datei-Pfad (--korpus-datei) ohne `requests` auskommt.
    import requests

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


def schreibe_korpus(eintraege: List[Eintrag], pfad: str, seed: int) -> None:
    """Korpus einfrieren, damit der Lauf ohne Dev-DB wiederholbar ist."""
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(
            {
                "seed": seed,
                "anzahl": len(eintraege),
                "eintraege": [
                    {
                        "gruppe": e.gruppe,
                        "quelle": e.quelle,
                        "typ": e.typ,
                        "titel": e.titel,
                        "text": e.text,
                    }
                    for e in eintraege
                ],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


def lade_korpus_datei(pfad: str) -> List[Eintrag]:
    """Dieselben Eintraege aus der eingefrorenen Datei -- ohne Qdrant, ohne requests."""
    with open(pfad, encoding="utf-8") as f:
        daten = json.load(f)
    roh = daten["eintraege"] if isinstance(daten, dict) else daten
    return [
        Eintrag(
            gruppe=e.get("gruppe", "datei"),
            quelle=e.get("quelle", "-"),
            typ=e.get("typ", ""),
            titel=(e.get("titel") or "").strip(),
            text=(e.get("text") or "").strip(),
        )
        for e in roh
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
    if r.get("repariert"):
        print(
            "  !  Struktur repariert (als JSON-String geliefert): "
            + ", ".join(r["repariert"])
        )
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
    repariert = sum(1 for e in eintraege if (e.ergebnis or {}).get("repariert"))
    if repariert:
        print(f"Antworten mit repariertem JSON: {repariert}")
    kaputt = sum(1 for e in eintraege if e.fehler)
    if kaputt:
        print(f"Eintraege ohne Ergebnis (Fehler): {kaputt}")


# --------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------


async def lauf(
    eintraege: List[Eintrag], model: str, parallel: int, ohne_temperature: bool = False
) -> None:
    try:
        import anthropic
    except ModuleNotFoundError as ex:  # haeufigster Fehlstart auf einem neuen Rechner
        raise SystemExit(
            "FEHLER: Paket 'anthropic' fehlt.\n"
            "  pip install anthropic\n"
            "  Ohne das Paket laeuft nur --dry-run."
        ) from ex

    parameter = modell_parameter(model, ohne_temperature)
    anzeige = [f"{k}={v}" for k, v in sorted(parameter.items()) if k != "tools"]
    anzeige.append(
        "strict=True"
        if parameter["tools"][0].get("strict")
        else "strict=nicht moeglich"
    )
    print(
        f"Modell {model}: "
        + ", ".join(anzeige)
        + ("" if "temperature" in parameter else " (temperature wird nicht gesendet)")
    )

    sperre = asyncio.Semaphore(parallel)
    # Ein falscher Key oder eine falsche Modell-ID trifft jeden Aufruf gleich.
    # Sobald so ein Fehler auftritt, laufen die restlichen Entwuerfe nicht mehr
    # los -- sonst steht derselbe Konfigurationsfehler dreizehnmal im Protokoll.
    abbruch: Dict[str, str] = {}

    async with anthropic.AsyncAnthropic(api_key=api_key_aus_umgebung()) as client:

        async def einer(e: Eintrag) -> None:
            async with sperre:
                if abbruch:
                    e.fehler = f"nicht ausgefuehrt ({abbruch['grund']})"
                    return
                try:
                    e.roh = await pruefe_einen(
                        client, model, e.titel, e.text, e.typ, parameter
                    )
                    e.ergebnis = nachbereiten(e.roh, pruefbarer_text(e.titel, e.text))
                except anthropic.NotFoundError as ex:
                    abbruch["grund"] = f"Modell '{model}' nicht verfuegbar"
                    e.fehler = f"{abbruch['grund']}: {ex}"
                except (
                    anthropic.AuthenticationError,
                    anthropic.PermissionDeniedError,
                ) as ex:
                    abbruch["grund"] = "Key abgelehnt (401/403)"
                    e.fehler = f"{abbruch['grund']}: {ex}"
                except anthropic.BadRequestError as ex:
                    # 400 trifft meist alle Entwuerfe (Schema, Parameter); nur bei
                    # Ueberlaenge eines einzelnen Textes ist es ein Einzelfall.
                    if "temperature" in str(ex):
                        abbruch["grund"] = (
                            f"'{model}' lehnt temperature ab "
                            "-- Modell in MODELLE_MIT_TEMPERATURE streichen "
                            "oder --no-temperature setzen"
                        )
                        e.fehler = f"{abbruch['grund']}: {ex}"
                    else:
                        e.fehler = f"Anfrage abgelehnt (400): {ex}"
                except anthropic.RateLimitError as ex:
                    # Das SDK hat bereits zweimal nachgefasst.
                    e.fehler = f"Rate Limit (429), auch nach Retries: {ex}"
                except anthropic.APIStatusError as ex:
                    e.fehler = f"HTTP {ex.status_code}: {ex}"
                except anthropic.APIConnectionError as ex:
                    e.fehler = f"Verbindung fehlgeschlagen: {ex}"
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
    p.add_argument(
        "--korpus-datei",
        help="Baseline-Lauf aus eingefrorener JSON-Datei (ohne Dev-DB)",
    )
    p.add_argument(
        "--korpus-export",
        help="Ausgewaehlten Korpus hierhin schreiben und beenden",
    )
    p.add_argument("--qdrant", default="http://localhost:6333")
    p.add_argument("--collection", default="content_collection")
    p.add_argument(
        "--seed", type=int, default=20260819, help="Auswahl der Seed-Kommentare"
    )
    p.add_argument("--anzahl-seed", type=int, default=10)
    p.add_argument("--model", default="claude-sonnet-4-5")
    p.add_argument("--parallel", type=int, default=4)
    p.add_argument(
        "--no-temperature",
        action="store_true",
        help="temperature auch dann weglassen, wenn das Modell sie annehmen wuerde",
    )
    p.add_argument(
        "--dry-run", action="store_true", help="Prompts zeigen, nichts rufen"
    )
    p.add_argument("--out", help="Rohergebnisse als JSON hierhin schreiben")
    args = p.parse_args()

    if args.korpus_datei:
        eintraege = lade_korpus_datei(args.korpus_datei)
        if not eintraege:
            print(f"Korpusdatei {args.korpus_datei} ist leer.", file=sys.stderr)
            return 1
    elif args.korpus:
        eintraege = lade_korpus(
            args.qdrant, args.collection, args.seed, args.anzahl_seed
        )
        if not eintraege:
            print("Keine Eintraege gefunden -- laeuft der Dev-Stack?", file=sys.stderr)
            return 1
    elif args.text:
        eintraege = [Eintrag("einzeln", "-", args.typ, args.titel, args.text.strip())]
    else:
        p.error("entweder --text, --korpus oder --korpus-datei angeben")
        return 2

    if args.korpus_export:
        schreibe_korpus(eintraege, args.korpus_export, args.seed)
        print(f"{len(eintraege)} Entwuerfe eingefroren: {args.korpus_export}")
        return 0

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

    asyncio.run(lauf(eintraege, args.model, args.parallel, args.no_temperature))

    for e in eintraege:
        drucke_eintrag(e)
    if args.korpus or args.korpus_datei:
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
