"""
Rueckwaertssuche Beitrag -> Aussage (#603).

Die Verknuepfung "antwortet auf" steht nur an der Aussage, als Liste
replysuggestions im Qdrant-Payload. Die Liste liegt mal als JSON-Text, mal als
Liste von Objekten im Punkt (moderation_repository schreibt Text, upsert eine
Liste); Qdrant kann in beiden Faellen nicht nach einer Beitrags-ID darin filtern.

Deshalb fuehrt jede Aussage zusaetzlich das Payload-Feld antwort_ids: die IDs
ihrer Antworten als Liste von Texten, mit Keyword-Index. Damit findet eine einzige
gefilterte Abfrage die Aussagen zu einem Beitrag. Das Feld ist abgeleitet: Es wird
ueberall dort geschrieben, wo replysuggestions geschrieben wird (upsert,
aus_aussagen_entfernen), und fuer den Altbestand nachgetragen
(services/wartung/antwort_ids_nachtrag.py).
"""

import json
from typing import Any, List

FELD_ANTWORT_IDS = "antwort_ids"


def antwort_ids(replysuggestions: Any) -> List[str]:
    """
    Die IDs aus replysuggestions in der Form, die im Payload steht: als JSON-Text,
    als Liste von Objekten oder Modellen. Unlesbares ergibt eine leere Liste; die
    Reihenfolge bleibt, Doppelte fallen weg.
    """
    if isinstance(replysuggestions, str):
        try:
            replysuggestions = json.loads(replysuggestions)
        except json.JSONDecodeError:
            return []
    if not isinstance(replysuggestions, list):
        return []
    ids: List[str] = []
    for vorschlag in replysuggestions:
        if isinstance(vorschlag, dict):
            kennung = vorschlag.get("id")
        else:
            kennung = getattr(vorschlag, "id", None)
        if kennung is None:
            continue
        text = str(kennung)
        if text not in ids:
            ids.append(text)
    return ids
