#!/usr/bin/env python3
"""
Liest den Qdrant-Bestand und gibt nur Zaehler aus - fuer Test und Prod.

NUR LESEND: scroll und get_collection, sonst nichts. Keine Texte, keine IDs, keine
Autoren in der Ausgabe. Laeuft im semantic-search-Container, per stdin, mit dessen
Umgebung (SEMANTIC_SEARCH_QDRANT_URL, SEMANTIC_SEARCH_QDRANT_COLLECTION).

Braucht nur qdrant_client und die Standardbibliothek (fuer --praefix zusaetzlich
numpy und sentence_transformers, die im Image stecken) - keinen App-Code. Laeuft
daher auch gegen einen Container mit aelterem Stand (geprueft mit python -I, also
ohne /app im Pfad, gegen einen Container ohne utils/text_normalisierung.py).

Auf Test/Prod liegt kein Repo-Checkout - Skript herunterladen, dann ausfuehren:

    curl -fsSLO https://raw.githubusercontent.com/netzbegruenung/contentgruen/main/mvp/scripts/manual/bestand_pruefen.py
    docker exec -i contentgruen-semantic-search python - < bestand_pruefen.py

    # zusaetzlich Vektorpraefix-Stichprobe (laedt das Einbettungsmodell, ~1,5 GB RAM,
    # 20 Punkte je Inhaltstyp)
    docker exec -i contentgruen-semantic-search python - --praefix 20 < bestand_pruefen.py

Ausgabe (JSON):
- punkte_je_typ_und_herkunft
- aussagen: je Herkunft gesamt / mit Antworten
- beitraege_ohne_aussage: Kommentare und Hintergrundinfos, die in keiner
  replysuggestions-Liste einer Aussage stehen, je Herkunft
- antwortverweise_ins_leere: Eintraege in replysuggestions, deren Ziel es nicht gibt
- initial_data: Punkte mit origin=initial_data je Typ
- aussagen_normalisiert_gleich: Gruppen von Aussagen mit gleichem normalisiertem Text
- text_normalisiert: Feld vorhanden/fehlt je Typ, Keyword-Index ja/nein
- vektorpraefix (nur mit --praefix): mit welchem Praefix die Stichprobe eingebettet ist
"""

import argparse
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

from qdrant_client import QdrantClient

MODELL = "intfloat/multilingual-e5-base"
FELD = "text_normalisiert"
TYPEN_MIT_FELD = ("statement", "commentary")
BEITRAGSTYPEN = ("commentary", "generic_text")

_APOSTROPHE = str.maketrans({"’": "'", "‘": "'", "ʼ": "'"})
_ANFUEHRUNGSZEICHEN = re.compile("[\"„“”‚«»‹›]")


def normalisiert(text):
    """
    Bewusste Kopie von app/utils/text_normalisierung.py: Das Skript soll ohne App-Code
    laufen, auch gegen aeltere Versionen. Aendert sich die Normalisierung dort, hier
    nachziehen - sie dient hier nur zum Zaehlen.
    """
    t = unicodedata.normalize("NFC", text or "").translate(_APOSTROPHE)
    t = _ANFUEHRUNGSZEICHEN.sub("", t)
    t = " ".join(t.split()).casefold()
    return t.rstrip(".!?… ")


def antwort_ids(payload):
    vorschlaege = payload.get("replysuggestions") or []
    if isinstance(vorschlaege, str):  # die Moderationskaskade schreibt JSON-Strings
        try:
            vorschlaege = json.loads(vorschlaege)
        except json.JSONDecodeError:
            return []
    return [str(v.get("id")) for v in vorschlaege if isinstance(v, dict)]


def alle_punkte(client, collection):
    offset = None
    while True:
        punkte, offset = client.scroll(
            collection_name=collection,
            limit=256,
            offset=offset,
            with_payload=["content_type", "origin", "replysuggestions", "text", FELD],
            with_vectors=False,
        )
        yield from punkte
        if offset is None:
            return


def praefix_stichprobe(client, collection, typen, n):
    import numpy as np
    from qdrant_client.models import FieldCondition, Filter, MatchValue
    from sentence_transformers import SentenceTransformer

    modell = SentenceTransformer(MODELL)
    ergebnis = {}
    for typ in sorted(typen):
        punkte, _ = client.scroll(
            collection_name=collection,
            scroll_filter=Filter(
                must=[FieldCondition(key="content_type", match=MatchValue(value=typ))]
            ),
            limit=n,
            with_payload=["text"],
            with_vectors=True,
        )
        punkte = [p for p in punkte if (p.payload or {}).get("text") and p.vector]
        if not punkte:
            continue
        texte = [p.payload["text"] for p in punkte]
        gespeichert = np.array([p.vector for p in punkte], dtype=np.float32)
        gespeichert /= np.linalg.norm(gespeichert, axis=1, keepdims=True)
        varianten = {
            "query": modell.encode(["query: " + t for t in texte], normalize_embeddings=True),
            "passage": modell.encode(["passage: " + t for t in texte], normalize_embeddings=True),
            "ohne": modell.encode(texte, normalize_embeddings=True),
        }
        zaehler = Counter()
        for i in range(len(punkte)):
            werte = {k: float(v[i] @ gespeichert[i]) for k, v in varianten.items()}
            bester = max(werte, key=werte.get)
            zaehler[bester if werte[bester] > 0.999 else "keins_passt"] += 1
        ergebnis[typ] = dict(zaehler)
    return {"modell": MODELL, "stichprobe_je_typ": n, "je_typ": ergebnis}


def main():
    parser = argparse.ArgumentParser(description="Bestand zaehlen (nur lesend)")
    parser.add_argument(
        "--praefix", type=int, default=0, metavar="N",
        help="Vektorpraefix an N Punkten je Typ pruefen (laedt das Modell)",
    )
    args = parser.parse_args()

    url = os.environ.get("SEMANTIC_SEARCH_QDRANT_URL", "http://localhost:6333")
    collection = os.environ.get("SEMANTIC_SEARCH_QDRANT_COLLECTION", "content_collection")
    client = QdrantClient(url=url, timeout=60, check_compatibility=False)
    info = client.get_collection(collection)

    je_typ_herkunft = defaultdict(Counter)
    aussagen = defaultdict(Counter)
    beitraege = {}  # id -> (typ, herkunft)
    verknuepft = set()
    verweise = []
    feld = defaultdict(Counter)
    aussage_normalformen = Counter()
    vorhandene_ids = set()

    for p in alle_punkte(client, collection):
        pl = p.payload or {}
        typ, herkunft = pl.get("content_type") or "ohne", pl.get("origin") or "ohne"
        pid = str(p.id)
        vorhandene_ids.add(pid)
        je_typ_herkunft[typ][herkunft] += 1
        if typ in TYPEN_MIT_FELD:
            feld[typ]["mit_feld" if FELD in pl else "ohne_feld"] += 1
        if typ == "statement":
            ids = antwort_ids(pl)
            aussagen[herkunft]["gesamt"] += 1
            aussagen[herkunft]["mit_antworten"] += 1 if ids else 0
            verknuepft.update(ids)
            verweise.extend(ids)
            aussage_normalformen[normalisiert(pl.get("text"))] += 1
        elif typ in BEITRAGSTYPEN:
            beitraege[pid] = (typ, herkunft)

    ohne_aussage = defaultdict(lambda: defaultdict(Counter))
    for pid, (typ, herkunft) in beitraege.items():
        ohne_aussage[typ][herkunft]["gesamt"] += 1
        ohne_aussage[typ][herkunft]["ohne_aussage"] += 0 if pid in verknuepft else 1

    gruppen = [n for n in aussage_normalformen.values() if n > 1]
    ausgabe = {
        "collection_punkte": info.points_count,
        "punkte_je_typ_und_herkunft": {t: dict(c) for t, c in sorted(je_typ_herkunft.items())},
        "aussagen": {h: dict(c) for h, c in sorted(aussagen.items())},
        "beitraege_ohne_aussage": {
            t: {h: dict(c) for h, c in sorted(hs.items())} for t, hs in sorted(ohne_aussage.items())
        },
        "antwortverweise_ins_leere": sum(1 for i in verweise if i not in vorhandene_ids),
        "initial_data": {
            t: c["initial_data"] for t, c in sorted(je_typ_herkunft.items()) if c["initial_data"]
        },
        "aussagen_normalisiert_gleich": {
            "gruppen": len(gruppen),
            "aussagen_in_gruppen": sum(gruppen),
        },
        "text_normalisiert": {
            "keyword_index": FELD in (info.payload_schema or {}),
            "je_typ": {t: dict(c) for t, c in sorted(feld.items())},
        },
    }
    if args.praefix > 0:
        ausgabe["vektorpraefix"] = praefix_stichprobe(
            client, collection, set(je_typ_herkunft) - {"ohne"}, args.praefix
        )

    json.dump(ausgabe, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
