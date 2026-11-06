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
Messung als Datei, für Vergleiche und Folgetickets: je Fall Suchanfrage, Phänomen,
Erwartung, Einordnung und angezeigte Beiträge je Schwelle, dazu Auswertung, Phänomene,
Zerfaserung sowie Modell, Sammlung, Dublettenschwelle und Datum).

Exit-Code 0 nach einer Messung; 2, wenn kein Fall mit Erwartung gemessen wurde (leere
oder falsche Sammlung, oder ein Bestand ohne passende Fälle). Die Zahlen sind dann nicht
aussagekräftig, etwa für den nächtlichen Lauf (#391).

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
- **Präzision:** passende unter allen angezeigten Beiträgen. **Recall@5, Recall@10:**
  Anteil der Fälle mit Erwartung, bei denen ein passender Beitrag unter den ersten 5
  bzw. 10 der Ergebnisseite steht (Recall@1 ist Treffer durch Fälle mit Erwartung).
  **Recall (Seite):** dasselbe für die ganze Ergebnisseite, je Beitragstyp höchstens k,
  also bis zu drei mal k Beiträge.
- **Zerfaserung:** Fälle mit `dieselbe_behauptung` sind dieselbe Behauptung wie eine
  erwartete Aussage (Paar-Label *gleich* nach `MESSSET.md`). Gezählt wird, wie viele
  davon nicht auf dieser Aussage landen, sondern eine neue anlegen würden, insgesamt und
  unter den Suchen ohne Treffer. Ob eine Suchanfrage auf einer Aussage landet, prüft
  dieselbe Dublettenprüfung wie beim Anlegen (`vorhandene_finden`); sie hängt nicht davon
  ab, ob die Aussage Antworten hat. Der Anteil „insgesamt“ gilt deshalb auch für Aussagen
  ohne Antwort. **Grenze:** Am Seed hat jede erwartete Aussage Antworten, solche
  Suchanfragen haben also fast immer Treffer; „0 unter den Suchen ohne Treffer“ ist dort
  kein Befund. Wie viele Aussagen im Bestand aus Suchen ohne Treffer zerfasert sind,
  braucht echte Suchen und Aussagen ohne Antwort, also den Startbestand.
- **Fremd und Verneinung** sind auf den Testbestand bezogen: „fremd“ heißt, der Seed hat
  keine Aussage dazu. Nach dem Startbestand vor dem Messen prüfen, ob er Aussagen zu
  diesen Themen hat; sonst zählen echte Treffer als Fehltreffer.
- Fälle, deren erwartete Aussage im gemessenen Bestand fehlt, zählen nicht mit; die
  Ausgabe nennt sie. Heute stammen alle erwarteten Aussagen aus dem Seed (Testbestand).
- Keine Personendaten, keine Eingaben aus Produktion: Suchanfragen sind selbst
  formuliert oder stammen aus dem Seed bzw. dem Messset.

## Ergebnis am Testbestand (vorläufig)

**Vorläufig:** gemessen am 05.11.2026 gegen den Seed im Dev-Stack mit
`intfloat/multilingual-e5-base`, 42 Fälle (33 mit Erwartung, 9 ohne), mit dem Stemmer
vor #392 (Unterschiede danach unter „Stemmer“). Der Seed hat 14
Aussagen mit Antworten, jede Antwort hängt an einer Aussage, und er ist klein und
geschrieben, um gefunden zu werden. Nach dem Startbestand (#288) kommen Fälle zu dessen
Aussagen dazu (auch zu Aussagen ohne Antwort) und die Fälle „fremd“ werden geprüft;
dann wird einmal mit dem Befehl oben neu gemessen und die Schwelle neu bewertet.

| Schwelle | Treffer | Fehltreffer | keine | ohne Erwartung: keine / Fehltreffer | Präzision | Recall@5 | Recall@10 | Recall (Seite) | direkt: passend / angezeigt |
|---|---|---|---|---|---|---|---|---|---|
| 0.76 | 31/33 | 2 | 0 | 0/9 / 9 | 0.16 | 0.94 | 0.97 | 1.00 | 13 / 368 |
| 0.78 | 30/33 | 2 | 1 | 0/9 / 9 | 0.21 | 0.91 | 0.94 | 0.97 | 13 / 251 |
| 0.79 | 30/33 | 2 | 1 | 1/9 / 8 | 0.25 | 0.91 | 0.94 | 0.97 | 13 / 203 |
| 0.80 (heute) | 29/33 | 2 | 2 | 2/9 / 7 | 0.32 | 0.88 | 0.91 | 0.94 | 11 / 136 |
| 0.81 | 28/33 | 3 | 2 | 3/9 / 6 | 0.39 | 0.88 | 0.91 | 0.94 | 21 / 102 |
| 0.82 | 27/33 | 3 | 3 | 4/9 / 5 | 0.50 | 0.85 | 0.88 | 0.88 | 20 / 54 |
| 0.84 | 24/33 | 3 | 6 | 5/9 / 4 | 0.70 | 0.76 | 0.76 | 0.76 | 12 / 15 |
| 0.86 | 17/33 | 1 | 15 | 5/9 / 4 | 0.71 | 0.52 | 0.52 | 0.52 | 8 / 8 |

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
- **Stemmer (#392):** CISTEM statt der einfachen Suffixkürzung lässt Treffer, keine
  Treffer und Zerfaserung an jeder Schwelle gleich, bei 0,8 auch die Präzision; bei
  0,84 sinkt sie von 0,70 auf 0,66 (S14, S20 zeigen mehr unpassende Beiträge, weil
  „mir“ nicht mehr zählt).
  Snowball German und die spaCy-Lemmata aus dem Gegenlesen messen gleich; nur
  Kleinschreibung und Umlaute ohne Stemmer verliert S25. Pronomen („uns“, „mir“)
  stehen jetzt in der Stoppliste: Mit „uns“ als Schlagwort ging S13 an „Die Grünen
  wollen uns das Fleisch verbieten“ verloren.
- **Fremde Themen:** 3 von 5 zeigen etwas (Rente, Mülltrennung, Deutschlandticket),
  zwei davon nur über den direkten Weg.
- **Zerfaserung:** 14 der 15 Suchanfragen, die dieselbe Behauptung wie eine vorhandene
  Aussage sind, landen nicht auf ihr, sondern ergäben eine neue Aussage; nur der
  wörtliche Fall landet, schon ein Tippfehler („Vögle“) nicht. Die Dublettenprüfung
  (query/query-Ähnlichkeit ab 0,98) fängt also fast nur wörtliche Wiederholungen. Weil
  sie nicht auf Antworten achtet, gilt das ebenso für Aussagen ohne Antwort: Wer eine
  Behauptung in anderen Worten sucht, zu der es noch keine Antwort gibt, legt eine
  weitere Aussage an, und die Suchen ohne Treffer verteilen sich auf mehrere Aussagen in
  „Hier fehlt eine Antwort“. Unter den 4 Suchen ohne Treffer am Seed ist keine dieselbe
  Behauptung wie eine vorhandene Aussage (siehe Grenze oben). Wie groß der Anteil im
  Bestand ist, misst erst der Startbestand; die Trennung gleicher Behauptungen ist
  Aufgabe der NLI-Stufe (#387).
