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

Optionen: `--schwellen 0.78,0.8,0.82` (welche Schwellen gemessen werden; die von heute
immer), `--k` (Beiträge je Beitragstyp, Standard 10 wie im Frontend), `--faelle` (jeder
Fall mit erstem angezeigtem und erstem passendem Beitrag), `--json PFAD` (die ganze
Messung als Datei, für Vergleiche und Folgetickets).

Das Skript lädt das Einbettungsmodell (etwa 1,5 GB RAM) und liest den Bestand nur;
einzige Ausnahme ist der Start der Einbettung, der wie im Dienst eine fehlende Sammlung
anlegt (bei falsch geschriebenem `SEMANTIC_SEARCH_QDRANT_COLLECTION` also eine leere,
und alle Fälle stehen dann unter „nicht gemessen“). Es ruft dieselben Schritte wie die
Suche (`aussagetreffer_finden`, `suchspezifikationen` und `treffer_sammeln` in
`api/v1/search.py`: Limit, Kürzen und Umsortieren wie im Dienst),
aber nicht den Endpunkt. Darum legt es keine Aussage aus der Suchanfrage an und zählt
weder Suchereignis noch Suche ohne Treffer. Je Schwelle läuft der Orchestrator einmal,
so wie er im Dienst mit dieser Schwelle liefe.

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
  wird. Angezeigt ist, was die Suche liefert, in der Reihenfolge der Ergebnisseite:
  Kommentare, dann Hintergrundinfos, dann Posts, je Typ höchstens k. Bilder zeigt die
  Ergebnisseite nicht, sie zählen nicht.
- **Präzision:** passende unter allen angezeigten Beiträgen. **Recall:** Anteil der
  Fälle mit Erwartung, bei denen ein passender Beitrag irgendwo auf der Ergebnisseite
  steht (je Beitragstyp höchstens k), nicht nur unter den ersten k.
- **Zerfaserung:** Fälle mit `dieselbe_behauptung` sind dieselbe Behauptung wie eine
  erwartete Aussage (Paar-Label *gleich* nach `MESSSET.md`). Gezählt wird, wie viele
  davon nicht auf dieser Aussage landen, sondern eine neue anlegen würden, insgesamt und
  unter den Suchen ohne Treffer. **Grenze:** Am Seed hat jede erwartete Aussage
  Antworten, solche Suchanfragen haben also fast immer Treffer. Die Fälle, um die es bei
  Suchen ohne Treffer eigentlich geht (dieselbe Behauptung wie eine Aussage noch ohne
  Antwort, etwa eine vorab angelegte), kann das Set erst mit dem Startbestand enthalten;
  bis dahin ist „0 unter den Suchen ohne Treffer“ kein Befund.
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

| Schwelle | Treffer | Fehltreffer | keine | ohne Erwartung: keine / Fehltreffer | Präzision | Recall | direkt: passend / angezeigt |
|---|---|---|---|---|---|---|---|
| 0.76 | 31/33 | 2 | 0 | 0/9 / 9 | 0.16 | 1.00 | 13 / 368 |
| 0.78 | 30/33 | 2 | 1 | 0/9 / 9 | 0.21 | 0.97 | 13 / 251 |
| 0.79 | 30/33 | 2 | 1 | 1/9 / 8 | 0.25 | 0.97 | 13 / 203 |
| 0.80 (heute) | 29/33 | 2 | 2 | 2/9 / 7 | 0.32 | 0.94 | 11 / 136 |
| 0.81 | 28/33 | 3 | 2 | 3/9 / 6 | 0.39 | 0.94 | 21 / 102 |
| 0.82 | 27/33 | 3 | 3 | 4/9 / 5 | 0.50 | 0.88 | 20 / 54 |
| 0.84 | 24/33 | 3 | 6 | 5/9 / 4 | 0.70 | 0.76 | 12 / 15 |
| 0.86 | 17/33 | 1 | 15 | 5/9 / 4 | 0.71 | 0.52 | 8 / 8 |

- **Schwelle 0,8 bleibt (vorläufig).** Es gibt keinen klaren Knick, nur einen Tausch:
  Darunter kommt ein Treffer dazu, und die Fälle ohne passende Aussage zeigen fast
  immer etwas; darüber gehen ein bis zwei Treffer verloren, dafür steigt die Präzision
  (0,82: 27 statt 29 Treffer, Präzision 0,50 statt 0,32). Für Gut gesagt zählt zuerst,
  dass eine passende Antwort erscheint; am kleinen Seed trägt das keine Verschiebung.
- **Der direkte Weg rettet Fälle, bringt aber viel Unpassendes.** Bei 0,8 kommen 5
  Treffer nur über ihn („Heizungsverbot“, „Fleischverbot“, „Bürokratiemonster“, die
  Gurken, die Dunkelflaute in Worten); zugleich sind 125 der 136 direkt angezeigten
  Beiträge unpassend, und bei S09 steht ein unpassender direkter Kommentar vor der
  passenden Hintergrundinfo. Ob eine eigene Schwelle für den direkten Weg trägt, zeigt
  erst der Startbestand.
- **Verneinungen** (4 Fälle) sind alle Fehltreffer: Das Gegenteil einer Aussage liegt bei
  0,89 bis 0,98 und damit weit über jeder Schwelle. Das löst keine Schwelle, sondern eine
  bessere Trennung von Widersprüchen (#387).
- **Fremde Themen:** 3 von 5 zeigen etwas (Rente, Mülltrennung, Deutschlandticket),
  zwei davon nur über den direkten Weg.
- **Zerfaserung:** 14 der 15 Suchanfragen, die dieselbe Behauptung wie eine vorhandene
  Aussage sind, landen nicht auf ihr, sondern ergäben eine neue Aussage; nur der
  wörtliche Fall landet. Unter den 4 Suchen ohne Treffer ist keine dieselbe Behauptung
  wie eine vorhandene Aussage. Das folgt aus dem Seed (siehe Grenze oben): Umformulierungen
  landen als neue Aussagen, haben aber Treffer und erscheinen deshalb nicht in „Hier
  fehlt eine Antwort“. Wie oft Suchen ohne Treffer eine Aussage ohne Antwort zerfasern,
  misst erst der Startbestand.
