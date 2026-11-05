# Suchtestset

Das Suchtestset misst, ob die Suche zu einer Suchanfrage passende Beiträge zeigt und
unpassende weglässt: Treffer, Fehltreffer, keine Treffer. Es ist die Grundlage für die
Schwelle der Suche (`MINIMUM_SCORE_THRESHOLD` in `services/search/search_orchestrator.py`),
für #302 (Titel in der Einbettung), den Stemmer (#392), den nächtlichen Lauf (#391) und
jeden Modellwechsel (ADR 0005). Das Messset (`MESSSET.md`) misst dagegen Textpaare:
dieselbe Aussage oder nicht.

| Datei | Inhalt |
|---|---|
| `suche_testset.py` | die Fälle: Suchanfrage, Form, Phänomen, erwartete Aussagen (von Hand) |
| `suche_messen.py` | misst gegen den Bestand eines Stacks und gibt die Auswertung aus |
| `../unit/test_suche_testset_aufbau.py` | Aufbau, Bezug zum Seed und Auswertung ohne Stack (in CI) |

## Messen

Gegen den Bestand, mit dem der Dienst läuft, im Container des Semantic-Search-Service:

```bash
python -m tests.regression.suche_messen
```

Das ist auch der Befehl zum Neu-Messen nach dem Startbestand (#288). Lokal gegen den
Dev-Stack:

```bash
cd mvp/backend/semantic-search-service/app
SEMANTIC_SEARCH_QDRANT_URL=http://localhost:6333 SEMANTIC_SEARCH_QDRANT_COLLECTION=content_collection \
  ../venv/bin/python -m tests.regression.suche_messen --faelle
```

Optionen: `--schwellen 0.78,0.8,0.82` (welche Schwellen in der Tabelle stehen), `--k`
(wie viele Beiträge je Suche zählen, Standard 10 wie im Frontend), `--faelle` (jeder
Fall mit erstem angezeigtem und bestem passendem Beitrag), `--json PFAD` (die ganze
Messung als Datei, für Vergleiche und Folgetickets).

Das Skript lädt das Einbettungsmodell (etwa 1,5 GB RAM) und liest nur. Es ruft dieselben
Schritte wie die Suche (`aussagetreffer_finden` und `suchspezifikationen` in
`api/v1/search.py`, dann den `SearchOrchestrator`), aber nicht den Endpunkt. Darum legt
es keine Aussage aus der Suchanfrage an und zählt weder Suchereignis noch Suche ohne
Treffer. Gesammelt wird ohne Schwelle; welche Beiträge eine Schwelle zeigen würde,
rechnet die Auswertung danach aus.

## Regeln

- **Passt:** Ein Beitrag passt, wenn er eine brauchbare Antwort auf die Suchanfrage ist.
  Wer sucht, hat eine Behauptung gehört und sucht eine Antwort darauf. Gemessen wird das
  über die Aussage: Ein Beitrag passt, wenn er an einer erwarteten Aussage hängt oder
  über sie gefunden wurde.
- **Gegenteil:** Eine verneinte oder gegenteilige Suchanfrage („Windräder schützen
  Vögel“) ist eine andere Behauptung. Die Antworten auf das Gegenteil passen nicht,
  erwartet ist kein Treffer.
- **Treffer, Fehltreffer, keine** je Fall: Treffer, wenn der erste angezeigte Beitrag
  passt; Fehltreffer, wenn etwas angezeigt wird und der erste nicht passt (bei einem Fall
  ohne Erwartung: wenn überhaupt etwas angezeigt wird); keine, wenn nichts angezeigt
  wird. Angezeigt sind die besten k Beiträge über der Schwelle, über alle Beitragstypen.
- **Präzision:** passende unter allen angezeigten Beiträgen. **Recall@k:** Anteil der
  Fälle mit Erwartung, bei denen ein passender Beitrag unter den ersten k steht.
- **Zerfaserung:** Fälle mit `dieselbe_behauptung` sind dieselbe Behauptung wie eine
  erwartete Aussage (Paar-Label *gleich* nach `MESSSET.md`). Gezählt wird, wie viele
  davon nicht auf dieser Aussage landen, sondern eine neue anlegen würden, insgesamt und
  unter den Suchen ohne Treffer.
- Fälle, deren erwartete Aussage im gemessenen Bestand fehlt, zählen nicht mit; die
  Ausgabe nennt sie. Heute stammen alle erwarteten Aussagen aus dem Seed (Testbestand).
- Keine Personendaten, keine Eingaben aus Produktion: Suchanfragen sind selbst
  formuliert oder stammen aus dem Seed bzw. dem Messset.

## Ergebnis am Testbestand (vorläufig)

**Vorläufig:** gemessen am 05.11.2026 gegen den Seed im Dev-Stack mit
`intfloat/multilingual-e5-base`, 42 Fälle (33 mit Erwartung, 9 ohne). Der Seed hat 14
Aussagen mit Antworten, jede Antwort hängt an einer Aussage, und er ist klein und
geschrieben, um gefunden zu werden. Nach dem Startbestand (#288) kommen Fälle zu dessen
Aussagen dazu, dann wird einmal mit dem Befehl oben neu gemessen und die Schwelle neu
bewertet.

| Schwelle | Treffer | Fehltreffer | keine | ohne Erwartung: keine / Fehltreffer | Präzision | Recall@k |
|---|---|---|---|---|---|---|
| 0.76 | 26/33 | 5 | 2 | 0/9 / 9 | 0.19 | 0.82 |
| 0.78 | 25/33 | 6 | 2 | 1/9 / 8 | 0.23 | 0.79 |
| 0.79 | 25/33 | 5 | 3 | 1/9 / 8 | 0.28 | 0.79 |
| 0.80 (heute) | 25/33 | 5 | 3 | 2/9 / 7 | 0.37 | 0.79 |
| 0.81 | 20/33 | 5 | 8 | 3/9 / 6 | 0.43 | 0.61 |
| 0.82 | 18/33 | 4 | 11 | 4/9 / 5 | 0.52 | 0.55 |
| 0.84 | 17/33 | 2 | 14 | 5/9 / 4 | 0.67 | 0.52 |
| 0.86 | 12/33 | 1 | 20 | 5/9 / 4 | 0.66 | 0.36 |

- **Schwelle 0,8 bleibt.** Sie liegt am Knick: Darunter kommt kein Treffer dazu, nur
  Fehltreffer; schon bei 0,81 fallen 5 von 25 Treffern weg (Umformulierungen und
  Umgangssprache mit kombiniertem Score knapp über 0,8).
- **Der direkte Weg liefert hier nur Fehltreffer.** Alle 87 direkt gefundenen Beiträge
  über 0,8 passen nicht; jede passende Antwort kommt über ihre Aussage. Ohne den direkten
  Weg blieben es 25 Treffer, die Fehltreffer fielen von 5 auf 1 und die Präzision stiege
  von 0,37 auf 0,61. Am Seed kann der direkte Weg nichts beitragen, weil jede Antwort an
  einer Aussage hängt. Ob eine eigene, höhere Schwelle für ihn trägt, zeigt erst der
  Startbestand.
- **Verneinungen** (4 Fälle) sind alle Fehltreffer: Das Gegenteil einer Aussage liegt bei
  0,89 bis 0,98 und damit weit über jeder Schwelle. Das löst keine Schwelle, sondern eine
  bessere Trennung von Widersprüchen (#387).
- **Schlagwörter:** 7 von 11 Treffer. „Dunkelflaute“, „Fleischverbot“ und „Genderzwang“
  finden nichts, „Heizungsverbot“ zeigt nur einen direkten Fehltreffer.
- **Zerfaserung:** 14 der 15 Suchanfragen, die dieselbe Behauptung wie eine vorhandene
  Aussage sind, landen nicht auf ihr, sondern ergäben eine neue Aussage; nur der
  wörtliche Fall landet. Unter den 5 Suchen ohne Treffer ist keine dieselbe Behauptung
  wie eine vorhandene Aussage: Am Testbestand landen Umformulierungen also als neue
  Aussagen, haben aber Treffer und erscheinen deshalb nicht in „Hier fehlt eine Antwort“.
