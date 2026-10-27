# Seed: Testdaten für die Entwicklung

**Nur für die Entwicklung, nie in Test oder Produktion.** Der Seed füllt den Dev-Stack
(`mvp/run-local.sh seed` und `wipe`), damit Suche und Karten etwas zeigen. Er ist nicht
der Startbestand: Fertige Beiträge im Bestand schreiben Menschen (`docs/VISION.md`, „Bestand“).

| Pfad | Inhalt |
|---|---|
| `v1.0/statements_with_commentaries/` | Aussagen mit Kommentaren |
| `v1.0/statements_with_generictexts/` | Aussagen mit Hintergrundinfos |
| `v1.0/prompt_generate_seedcontent.md` | Vorlage, um den Seed mit KI neu zu erzeugen |
| `add_metadata.py` | ergänzt `metadata`: Nutzung 0, `created_at` fest aus der Position |
| `v0.1/` | alter Stand, wird nicht geladen |

Geladen wird nur das Verzeichnis aus `SEMANTIC_SEARCH_DATA_PATH` (Dev: `/data/seed/v1.0`).

## Regeln

Der Seed folgt denselben Regeln wie der Bestand (`docs/VISION.md`, „Ton und Schreiben“):

1. Für Unentschiedene schreiben.
2. Den Vorwurf nicht wiederholen.
3. Erst die Gemeinsamkeit.
4. Wofür statt wogegen.
5. Nichts erfinden: keine Ich-, Familien- oder Nachbarschaftsgeschichten. Eigene
   Erlebnisse nur als Platzhalter „[Hier ein eigenes Erlebnis: …]“. Jede Zahl hat eine
   geprüfte Herkunft.
6. Kurz, ohne Belehrung, ohne Häme. Kein Sarkasmus, kein Stil „bissig“.

Dazu: keine echten Personen und keine Zitate aus der Presse; Presse höchstens als Link
in der Herkunft. Titel sind ein Satz mit Haltung, 3 bis 120 Zeichen, keine Frage.
Die Nutzung ist überall 0: Kein Zähler wird vorbelegt (`GLOSSARY.md`, „Nutzung“).

Agenten dürfen den Seed nach diesen Regeln neu erzeugen. Danach `add_metadata.py`
ausführen; `tests/unit/test_seed_regeln.py` im Semantic-Search-Service prüft die
Regeln, soweit sie sich mechanisch prüfen lassen.
