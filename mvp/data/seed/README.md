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

Geladen wird das Verzeichnis aus `SEMANTIC_SEARCH_DATA_PATH` (Dev: `/data/seed/v1.0`), und
zwar nur auf Anstoß über `/api/v1/seeding/start`; von selbst lädt der Dienst nichts. Der Seed
liegt trotzdem in jedem Image des Semantic-Search-Service (`COPY data /data` im
`Dockerfile`), und ohne gesetzte Variable zeigt der Pfad im Container auf `/data/seed/v1.0`.
In Test und Produktion schützt also nur, dass das BFF `/api/v1/seeding` sperrt: Dort nie
Seeding direkt am Dienst anstoßen.

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
`metadata.usage_count` steht nur in den Dateien, damit sich das prüfen lässt; beim Laden
wird es ignoriert.

Agenten dürfen den Seed nach diesen Regeln neu erzeugen. Danach `add_metadata.py`
ausführen; `tests/unit/test_seed_regeln.py` im Semantic-Search-Service prüft die
Regeln, soweit sie sich mechanisch prüfen lassen.
