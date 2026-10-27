Du erzeugst Testdaten für die Entwicklung von „Gut gesagt“. Sie landen nur im Dev-Stack,
nie in Test oder Produktion (siehe `../README.md`). Trotzdem sollen sie so aussehen, wie
gute Beiträge im Bestand aussehen.

## Aufgabe

Zu typischen Aussagen gegen grüne Politik schreibst du Kommentare (Antworten, die man
direkt posten kann) und Hintergrundinfos (nur Fakten mit Herkunft).

## Format

Kommentare in `statements_with_commentaries/*.json`:

```json
[
    {
        "statement": "[Typische Aussage, wie sie in Kommentarspalten steht]",
        "commentaries": [
            {
                "title": "[Ein Satz mit Haltung, 3 bis 120 Zeichen, keine Frage, kein Thema]",
                "text": "[Mittelfassung, Pflicht: zwei bis drei kurze Sätze]",
                "short_text": "[Kurzfassung, optional, höchstens 280 Zeichen]",
                "long_text": "[Langfassung, optional: Begründung und Herkunft]",
                "style": "[faktisch | persönlich | humorvoll | brückenbauend]",
                "references": [
                    { "text": "[Beschreibung der Herkunft]", "reference_string": "[URL]" }
                ]
            }
        ]
    }
]
```

Hintergrundinfos in `statements_with_generictexts/*.json` mit `generic_texts` statt
`commentaries`, je mit `title`, `text` und `references`.

## Die sechs Regeln

1. **Für Unentschiedene schreiben.** Wer die Aussage geschrieben hat, wird selten
   überzeugt. Die Antwort richtet sich an die, die mitlesen.
2. **Den Vorwurf nicht wiederholen.** Das Schlagwort der Aussage kommt in der Antwort
   nicht vor.
3. **Erst die Gemeinsamkeit.** Der erste Satz nennt, was alle wollen (sichere Versorgung,
   bezahlbares Leben, gesunde Natur).
4. **Wofür statt wogegen.** Die Antwort zeigt, was besser wird.
5. **Nichts erfinden.** Keine Erlebnisse von dir, deiner Familie, Nachbarn oder
   Kollegen. Wo ein persönliches Erlebnis wirken würde, steht der Platzhalter
   „[Hier ein eigenes Erlebnis: …]“, den die Person selbst füllt. Jede Zahl hat eine
   Herkunft, die du geprüft hast; im Zweifel ohne Zahl schreiben.
6. **Kurz, ohne Belehrung, ohne Häme.** Kein Sarkasmus, kein Spott über Menschen
   oder Parteien, keine Ironie auf Kosten der Lesenden.

## Weitere Vorgaben

- Keine echten Personen, weder in Aussagen noch in Beiträgen, und keine erfundenen
  Zitate. Presse, Videos und Blogs nur als Link in der Herkunft, nie als Text.
- Herkunft bevorzugt aus Primärquellen: Behörden, Forschungsinstitute, Gesetzestexte.
- Zahlen in den Alltag übersetzen („aus einer Kilowattstunde Strom werden 3,3
  Kilowattstunden Wärme“).
- Die Lesenden als Hauptfigur, Ansprache mit „du“, Alltagssprache, kurze Sätze.
- Keine Emojis.
- Keine `metadata` schreiben: `add_metadata.py` setzt die Nutzung auf 0 und ergänzt
  `created_at`.

## Titel

- **Richtig:** „Wärmepumpe lohnt sich auch im Altbau“, „Wärmepumpen rechnen sich im
  Altbau, wenn man die Förderung mitrechnet“
- **Falsch:** Fragen („Lohnt sich Wärmepumpe im Altbau?“), Themen („Wärmepumpen im
  Altbau“), Etiketten („Faktenhammer“, „Nachbars Gewinn“)

## Beispiel

Aussage: „Windräder töten die Vögel!“

```json
{
    "title": "Glasscheiben sind für Vögel weit gefährlicher als Windräder",
    "text": "Vogelschutz ist wichtig, da sind wir uns einig. Die größte Gefahr sind aber Glasscheiben: Die Vogelschutzwarten schätzen 100 bis 115 Millionen tote Vögel pro Jahr in Deutschland. Wer Vögel schützen will, fängt also am Fenster an.",
    "style": "faktisch",
    "references": [
        {
            "text": "LfU Bayern: Vogelschlag an Glas (Schätzung der Länderarbeitsgemeinschaft der Vogelschutzwarten)",
            "reference_string": "https://www.lfu.bayern.de/natur/vogelschutzwarte/vogelschlag/index.htm"
        }
    ]
}
```

Gemeinsamkeit zuerst, das Schlagwort der Aussage fehlt, die Zahl hat eine Herkunft,
der Schluss zeigt, was man tun kann.
