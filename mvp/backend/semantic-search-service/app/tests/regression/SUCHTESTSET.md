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
| `seed_laden.py` | lädt den Seed in eine leere Sammlung, ohne den Dienst (nächtlicher Lauf) |
| `nachtlauf.py` | misst am Seed und vergleicht mit dem Soll (nächtlicher Lauf) |
| `../unit/test_nachtlauf.py` | Soll, Toleranz, Tor und untere Grenze ohne Stack (in CI) |
| `../unit/test_suche_testset_aufbau.py` | Aufbau, Bezug zu Seed und Startbestand, Auswertung ohne Stack (in CI) |

## Messen

Gegen den Bestand, mit dem der Dienst läuft, im Container des Semantic-Search-Service:

```bash
python -m tests.regression.suche_messen
```

Das ist auch der Befehl für die Kontrollmessung nach dem Import des Startbestands auf
Produktion (#288). Lokal gegen den Dev-Stack:

```bash
cd mvp/backend/semantic-search-service/app
SEMANTIC_SEARCH_QDRANT_URL=http://localhost:6333 SEMANTIC_SEARCH_QDRANT_COLLECTION=content_collection \
  ../venv/bin/python -m tests.regression.suche_messen --faelle
```

Optionen: `--schwellen 0.8,0.82,0.84` (welche Schwellen gemessen werden; die von heute
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
  ohne Antwort. **Grenze:** Am Seed und am Startbestand hat jede erwartete Aussage
  Antworten, solche Suchanfragen haben also fast immer Treffer; „0 unter den Suchen ohne
  Treffer“ ist dort kein Befund. Wie viele Aussagen im Bestand aus Suchen ohne Treffer
  zerfasert sind, zeigen erst echte Suchen auf Produktion (siehe Ergebnis am
  Startbestand, Zerfaserung).
- **Ähnliche Aussagen:** dieselbe Abfrage wie die Vorschläge im Beitragsformular
  (höchstens 3 gepflegte Aussagen, ab 0,885; `AEHNLICHE_ANZAHL`, `AEHNLICHE_AB`). Gezählt
  wird, bei wie vielen Fällen mit Erwartung eine erwartete Aussage darunter ist, und bei
  wie vielen Fällen ohne Erwartung trotzdem eine erscheint. Unabhängig von der Schwelle
  der Suche.
- **Fremd und Verneinung** hängen am Bestand: „fremd“ heißt, der gemessene Bestand hat
  keine Aussage dazu. Hat der Startbestand eine (Wolf, Rente, Deutschlandticket), steht
  sie im Fall unter `nur_ohne`, und der Fall zählt dort nicht. Fälle ohne Erwartung, die
  nur am Startbestand etwas aussagen (Verneinung seiner Aussagen, fremde Themen neben
  ihnen), nennen unter `nur_mit` die Aussage, ohne die sie nicht zählen. Kommen Aussagen
  zu einem Thema dazu, vor dem Messen die Fälle „fremd“ prüfen; sonst zählen echte
  Treffer als Fehltreffer.
- Fälle, deren erwartete Aussage im gemessenen Bestand fehlt, zählen nicht mit (außer
  mit Ersatz, siehe unten); die Ausgabe nennt sie. S01 bis S42 erwarten Aussagen des Seeds, ab S43 des Startbestands
  (`STARTBESTAND` in `suche_testset.py`). Zwölf Aussagen hat der Startbestand mit dem
  Seed gemeinsam; am Seed zählen die Fälle zum Startbestand nicht mit. So bleibt das Soll
  des nächtlichen Laufs, wenn Fälle zum Startbestand dazukommen (ein Unit-Test prüft das).
- **Ersatz:** Die vier Fälle zu den zwei Seed-Aussagen, die dem Startbestand fehlen
  (S06 bis S09), zählen dort mit einer Ersatz-Erwartung (`ersatz` in `suche_testset.py`,
  #606): S06 bis S08 erwarten die Dunkelflaute-Aussage, S09 („Ökostrom ist viel zu teuer“)
  die Atomkraft-Aussage, deren Antworten die Kosten von Sonne und Wind gegen neue
  Atomkraftwerke stellen. S09 ist dort nicht dieselbe Behauptung und zählt nicht für die
  Zerfaserung, S06 schon; unter den Phänomenen zählt S09 dort als „verwandt“. Die Ausgabe nennt die Fälle unter „Mit Ersatz gemessen“; am
  Seed gilt weiter die ursprüngliche Erwartung. Ein Unit-Test prüft, dass jeder Fall zu
  einer Seed-Aussage, die dem Startbestand fehlt, einen Ersatz hat.
- Keine Personendaten, keine Eingaben aus Produktion: Suchanfragen sind selbst
  formuliert oder stammen aus dem Seed bzw. dem Messset.

## Ergebnis am Testbestand (Seed)

Gemessen am 05.11.2026 gegen den Seed im Dev-Stack mit
`intfloat/multilingual-e5-base`, 42 Fälle (33 mit Erwartung, 9 ohne), mit dem Stemmer
vor #392 (Unterschiede danach unter „Stemmer“). Der Seed hat 14
Aussagen mit Antworten, jede Antwort hängt an einer Aussage, und er ist klein und
geschrieben, um gefunden zu werden. Die Bewertung der Schwelle steht unter „Ergebnis am
Startbestand“; die Zeile der Schwelle von heute ist hier das Soll des nächtlichen Laufs.
Die Zeile 0,82 ist am 07.11.2026 mit dem nächtlichen Lauf nachgemessen (Stemmer nach
#392); die übrigen Zeilen sind die Messung vom 05.11.

| Schwelle | Treffer | Fehltreffer | keine | ohne Erwartung: keine / Fehltreffer | Präzision | Recall@5 | Recall@10 | Recall (Seite) | direkt: passend / angezeigt |
|---|---|---|---|---|---|---|---|---|---|
| 0.76 | 31/33 | 2 | 0 | 0/9 / 9 | 0.16 | 0.94 | 0.97 | 1.00 | 13 / 368 |
| 0.78 | 30/33 | 2 | 1 | 0/9 / 9 | 0.21 | 0.91 | 0.94 | 0.97 | 13 / 251 |
| 0.79 | 30/33 | 2 | 1 | 1/9 / 8 | 0.25 | 0.91 | 0.94 | 0.97 | 13 / 203 |
| 0.80 | 29/33 | 2 | 2 | 2/9 / 7 | 0.32 | 0.88 | 0.91 | 0.94 | 11 / 136 |
| 0.81 | 28/33 | 3 | 2 | 3/9 / 6 | 0.39 | 0.88 | 0.91 | 0.94 | 21 / 102 |
| 0.82 (heute) | 27/33 | 3 | 3 | 4/9 / 5 | 0.49 | 0.85 | 0.88 | 0.88 | 17 / 51 |
| 0.84 | 24/33 | 3 | 6 | 5/9 / 4 | 0.70 | 0.76 | 0.76 | 0.76 | 12 / 15 |
| 0.86 | 17/33 | 1 | 15 | 5/9 / 4 | 0.71 | 0.52 | 0.52 | 0.52 | 8 / 8 |

- **Schwelle seit #568: 0,82** (Entscheidung am Startbestand, siehe unten). Es gibt
  keinen klaren Knick, nur einen Tausch: Darunter kommt ein Treffer dazu, und die Fälle
  ohne passende Aussage zeigen fast immer etwas; darüber gehen ein bis zwei Treffer
  verloren, dafür steigt die Präzision (0,82: 27 statt 29 Treffer, Präzision 0,49 statt
  0,32).
- **Der direkte Weg rettet Fälle, bringt aber viel Unpassendes.** Bei 0,8 kommen 5
  Treffer nur über ihn („Heizungsverbot“, „Fleischverbot“, „Bürokratiemonster“, die
  Gurken, die Dunkelflaute in Worten); zugleich sind 125 der 136 direkt angezeigten
  Beiträge unpassend, und bei S09 steht ein unpassender direkter Kommentar vor der
  passenden Hintergrundinfo. Am Startbestand rettet er bei 0,8 nichts (unten).
- **Verneinungen** (4 Fälle) sind alle Fehltreffer: Das Gegenteil einer Aussage liegt bei
  0,89 bis 0,98 und damit weit über jeder Schwelle. Das löst keine Schwelle, sondern eine
  bessere Trennung von Widersprüchen (#387).
- **Stemmer (#392):** CISTEM statt der einfachen Suffixkürzung lässt Treffer, keine
  Treffer und Zerfaserung an jeder Schwelle gleich, bei 0,78 und 0,8 auch die
  Präzision; bei 0,82 sinkt sie von 0,50 auf 0,49, bei 0,84 von 0,70 auf 0,66 (S14,
  S20 zeigen mehr unpassende Beiträge, weil „mir“ und „alles“ nicht mehr zählen).
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
- **Ähnliche Aussagen** (gemessen am 06.11.2026, #391): Bei 25 von 33 Fällen mit
  Erwartung ist eine erwartete Aussage unter den ähnlichen Aussagen; 6 von 9 Fällen ohne
  Erwartung zeigen trotzdem eine, darunter alle 4 Verneinungen. Die untere Grenze 0,885
  hält also das Gegenteil einer Aussage nicht fern, das kann nur #387.

## Ergebnis am Startbestand (Entwurf, lokal)

Gemessen am 07.11.2026 am **Entwurf des Startbestands** (#288: 30 Aussagen, je zwei
Kommentare, 60 insgesamt), eingespielt mit `mvp/scripts/manual/beitraege_importieren.py`
in einen eigenen, leeren lokalen Stack ohne Seed; nicht auf Test oder Produktion.
Modell `intfloat/multilingual-e5-base`, NLI-Stufe im Schattenbetrieb (Standard),
106 Fälle, davon 99 gemessen (86 mit Erwartung, 13 ohne); nicht gemessen S06 bis S09
(Seed-Aussagen, die dem Startbestand fehlen) und S38, S39, S42 (nicht fremd). Weicht der
importierte Startbestand auf Produktion vom Entwurf ab, ändern sich einzelne Fälle; dort
reicht eine Kontrollmessung mit dem Befehl oben. S06 bis S09 zählen seit #606 mit ihrem
Ersatz mit (Regeln, „Ersatz“; Messung unten).

| Schwelle | Treffer | Fehltreffer | keine | ohne Erwartung: keine / Fehltreffer | Präzision | Recall@5 | Recall@10 | Recall (Seite) | direkt: passend / angezeigt |
|---|---|---|---|---|---|---|---|---|---|
| 0.76 | 81/86 | 5 | 0 | 0/13 / 13 | 0.18 | 0.99 | 1.00 | 1.00 | 0 / 0 |
| 0.78 | 80/86 | 5 | 1 | 1/13 / 12 | 0.19 | 0.98 | 0.99 | 0.99 | 0 / 3 |
| 0.79 | 80/86 | 5 | 1 | 1/13 / 12 | 0.19 | 0.98 | 0.99 | 0.99 | 0 / 27 |
| 0.80 | 80/86 | 5 | 1 | 1/13 / 12 | 0.22 | 0.98 | 0.99 | 0.99 | 0 / 65 |
| 0.81 | 79/86 | 5 | 2 | 1/13 / 12 | 0.27 | 0.97 | 0.98 | 0.98 | 1 / 97 |
| **0.82** | 78/86 | 4 | 4 | 3/13 / 10 | 0.34 | 0.94 | 0.95 | 0.95 | 4 / 94 |
| 0.83 | 77/86 | 5 | 4 | 3/13 / 10 | 0.40 | 0.94 | 0.95 | 0.95 | 7 / 69 |
| 0.84 | 73/86 | 5 | 8 | 3/13 / 10 | 0.45 | 0.88 | 0.90 | 0.90 | 7 / 29 |
| 0.86 | 67/86 | 3 | 16 | 3/13 / 10 | 0.49 | 0.79 | 0.80 | 0.80 | 2 / 6 |

- **Schwelle 0,82 statt 0,8** (entschieden am 07.11.2026, #568). Bei 0,8 stehen im
  Median zehn Kommentare auf der Seite, von denen meist zwei passen (Präzision 0,22);
  bei 0,82 sind es vier, die Präzision steigt auf 0,34. Der Preis: drei Treffer weniger
  (S26 „Genderzwang“, S72 „Akademikerpartei“, S29 die Gurken; dann ohne Ergebnis), einer
  mehr (S46), 78 statt 80 von 86; zwei fremde Themen zeigen nichts mehr (S70, S89). Wer
  kurze Schlagwörter tippt, bekommt etwas öfter „Hier fehlt eine Antwort“, obwohl es eine
  gibt. 0,84 kostet weitere fünf Treffer.
- **Präzision:** 0,82 hebt sie von 0,22 auf 0,34, 0,84 auf 0,45 (bei 73 statt 80
  Treffern). Sie ist am Startbestand nach oben begrenzt: Je Aussage gibt es
  zwei Kommentare, die Ergebnisseite zeigt bis zu zehn; bei 0,8 stehen im Median zehn
  Kommentare auf der Seite, bei 0,82 vier. Gemessen mit der Pronomen-Stoppliste aus
  #392; der Tausch Treffer gegen Präzision ist derselbe wie am Seed, nur mit mehr
  Treffern auf jeder Stufe.
- **Direkter Weg:** Bei 0,8 zeigt er 65 Beiträge, keiner passt, und keiner steht an
  erster Stelle; er rettet keinen Treffer. Ab 0,81 fallen Aussagetreffer weg und er
  füllt die Plätze, bei 0,82 mit vier passenden (ohne ihn 75 statt 78 Treffer). Am
  Startbestand hängt jeder Kommentar an einer Aussage, ein Beitrag ohne Aussage ist dort
  nicht dabei; am Seed rettete er fünf Treffer. Er bleibt, gerade bei 0,82; eine eigene
  Schwelle trägt das Set nicht.
- **Tor für Roadmap-Stufe 3:** bei 0,82 Recall@10 0,95 (Tor 0,80), Präzision 0,34
  (Tor 0,25); bei 0,8 lag die Präzision mit 0,22 darunter. Tor und Grenze bleiben am
  Seed gesetzt, der nächtliche Lauf misst nur dort.
- **Verneinungen** (8) sind alle Fehltreffer, wie am Seed; **fremde Themen** zeigen in 4
  von 5 Fällen etwas (Mülltrennung, Mietpreisbremse, Bahn, Schuldenbremse). Beides löst
  keine gemessene Schwelle: Auch bei 0,86 zeigen 10 der 13 Fälle ohne Erwartung etwas
  (#387).
- **Ähnliche Aussagen:** bei 65 von 86 Fällen mit Erwartung (76 %) eine erwartete
  Aussage darunter, über der unteren Grenze von 70 %; 9 von 13 Fällen ohne Erwartung
  zeigen trotzdem eine.

**Zerfaserung:**

- **Suchanfragen:** 31 von 41 Suchanfragen, die dieselbe Behauptung wie eine Aussage des
  Startbestands sind, landen nicht auf ihr; die zehn, die landen, sind alle wörtlich.
  Keine Umformulierung, kein Tippfehler und keine Umgangssprache landet. Mit der
  NLI-Stufe „an“ (#387) landen 6 der 31 (S32, S36, S51, S61, S74, S97), 25 bleiben.
  Mit dem **Bestätiger** dazu (`SEMANTIC_SEARCH_NLI_BESTAETIGER=true`, gemessen am
  09.11.2026 am selben Entwurf, nur die 30 Aussagen ohne Kommentare) landen weitere 10
  (S04, S14, S24, S27, S55, S58, S63, S80, S93, S94), **15 bleiben**. Keine der 99
  gemessenen Suchen landet dabei auf einer falschen Aussage, auch die Fälle ohne Erwartung
  nicht. Die 15 sind vor allem Umgangssprache, Bilder und Umschreibungen (S02 „Windkraftanlagen
  bringen Vögel um“) und einseitige Folgerungen (S45). `vorhandene_finden` braucht im Median
  283 statt 257 ms, im 95. Perzentil 890 statt 690 ms: Der Bestätiger urteilt bei 12 der
  99 Suchen über je einen Kandidaten. Das Soll des nächtlichen Laufs bleibt, er misst mit der
  Voreinstellung (Schattenbetrieb, Bestätiger aus).
  Nachmessen: `SEMANTIC_SEARCH_DIESELBE_AUSSAGE_NLI=an SEMANTIC_SEARCH_NLI_BESTAETIGER=true`
  vor den Befehl oben (`suche_messen --faelle`).
  Zu Deutschlandticket und Insektensterben gibt es nur den wörtlichen Fall; Fälle mit
  derselben Behauptung in anderen Worten kommen mit der Kontrollmessung dazu.
- **Aussagen ohne Antwort:** Einmal-Versuch am selben Stack über den Suchendpunkt: Vier
  Suchen zu Themen ohne Aussage legten je eine Aussage ohne Antwort an (Radwege,
  Grundsteuer, Handys an Schulen, Homeoffice), dann je drei Suchen mit derselben
  Behauptung in anderen Worten. 6 von 12 landen, alle mit fast gleichem Wortlaut
  („Die Grundsteuer ist nicht gerecht“, „Home Office macht faul“); die übrigen sechs
  legen eine weitere Aussage an. Die Dublettenprüfung achtet nicht auf Antworten, Aussagen
  ohne Antwort zerfasern also wie die mit Antwort. Die zwölf Suchanfragen stehen nicht
  im Set, der Versuch ist ein Anhaltspunkt und keine wiederholbare Messung.
- **Im Bestand:** Der Bericht der NLI-Stufe (`dieselbe_bericht.py`) findet unter den 30
  Aussagen kein Paar mit derselben Behauptung. Nah beieinander liegen „Die Grünen
  interessieren sich nur für Großstädte …“ und „Die Grünen machen Politik nur für
  Akademiker in der Stadt“: S24 (Land) zeigt zuerst die Antworten auf die zweite.
- **Anteil aus Suchen ohne Treffer:** Im Startbestand hat jede Aussage Antworten; welcher
  Anteil der Aussagen aus Suchen ohne Treffer dieselbe Behauptung wie eine andere ist,
  ist dort nicht messbar, die drei Punkte oben sind Ersatzgrößen. Ihn zeigt erst eine
  Zählung auf Produktion nach einigen Wochen Suchen. Am Startbestand sind bei 0,82
  7 der 99 gemessenen Suchen ohne Treffer (bei 0,8: 2), keine davon dieselbe Behauptung
  wie eine Aussage.

## S06 bis S09 am Startbestand (#606)

In der Kontrollmessung auf Produktion (09.11.2026) fehlten S06 bis S09: Ihre erwarteten
Seed-Aussagen („Erneuerbare Energien sind total unzuverlässig!“, „… sind zu teuer!“) hat
der Startbestand nicht, und die Messung überspringt solche Fälle. Seit #606 zählen sie dort
mit ihrem Ersatz. Gemessen am 09.11.2026 lokal am freigegebenen Startbestand (dieselbe
Datei wie beim Import auf Produktion, 30 Aussagen, 60 Kommentare, eingespielt mit
`beitraege_importieren.py` in einen eigenen, leeren Stack), mit
`SEMANTIC_SEARCH_DIESELBE_AUSSAGE_NLI=an` wie auf Produktion, Bestätiger aus. Beide Zeilen
sind frisch gemessen; die Zeile „vorher“ gleicht bei 0,82 der Messung am Entwurf oben (die
NLI-Stufe ändert nur die Zerfaserung):

| bei 0,82 | gemessen | Treffer | Fehltreffer | keine | Präzision | Recall@10 | Zerfaserung | ähnliche Aussagen |
|---|---|---|---|---|---|---|---|---|
| vorher | 99 von 106 | 78/86 | 4 | 4 | 0.34 | 0.95 | 25/41 | 65/86 |
| mit Ersatz | 103 von 106 | 82/90 | 4 | 4 | 0.34 | 0.96 | 26/42 | 65/90 |

- Alle vier sind bei 0,82 Treffer: S06 (0,918), S07 (0,990) und S08 (0,888) zeigen zuerst
  eine Antwort zur Dunkelflaute-Aussage, S09 eine zur Atomkraft-Aussage, knapp über der
  Schwelle (0,826); erst bei 0,86 fällt S09 auf „keine“.
- S06 landet nicht auf der Dunkelflaute-Aussage (Zerfaserung 26 statt 25 von 42 bzw.
  41). Keiner der vier zeigt eine erwartete Aussage unter den ähnlichen Aussagen
  (65 von 90).
- Nicht gemessen bleiben S38, S39 und S42 (am Startbestand nicht fremd).

## Polarität mit NLI (#574)

Gemessen am 09.11.2026 am selben Entwurf des Startbestands (lokal, eigene Sammlung, ohne
Seed), mit `SEMANTIC_SEARCH_DIESELBE_AUSSAGE_NLI=an` wie auf Produktion, ohne Bestätiger (er
ändert nur die Zerfaserung, nicht die Treffer). Vorher: Wortlisten
(`SEMANTIC_SEARCH_SUCHE_POLARITAET_NLI=aus`); nachher: `an`, Gegenteil heißt Widerspruch in
beiden Richtungen ab 0,9 (Standard). Nachmessen: diese Variablen vor den Befehl oben.

| bei 0,82 | Treffer | Fehltreffer | keine | ohne Erwartung: keine / Fehltreffer | Präzision | Verneinung: Fehltreffer / keine | Aussagetreffer je Suche: Median / 95. Perzentil |
|---|---|---|---|---|---|---|---|
| Wortlisten | 78/86 | 4 | 4 | 3/13 / 10 | 0.34 | 8 / 0 | 84 / 144 ms |
| NLI, beide Richtungen ab 0,9 | 77/86 | 5 | 4 | 5/13 / 8 | 0.34 | 6 / 2 | 364–539 / 694–1390 ms¹ |
| NLI, eine Richtung ab 0,5 (verworfen) | 74/86 | 6 | 6 | 7/13 / 6 | 0.38 | 4 / 4 | 364 / 694 ms |

¹ Beide NLI-Zeilen rechnen dieselben Urteile (dieselben Paare, nur die Grenze ist anders);
die Spanne sind die beiden Läufe, die VM war mit anderen Läufen geteilt.

D11 und D15 aus dem Messset entsprechen in der Suche S21 („Die Grünen sind keine
Verbotspartei“) und S62 („Balkonsolar lohnt sich“): Beide Aussagen bestraft das Modell (1,00 /
0,99 und 0,99 / 0,98), beide Fälle zeigen danach aber eine andere, nur thematisch nahe Aussage.

- **Das Modell erkennt sieben der acht Verneinungen** als Widerspruch in beiden Richtungen
  zur Aussage, deren Gegenteil sie sind (0,98 bis 1,00); S96 widerspricht nur in einer
  Richtung (0,87 und 0,27) und bleibt vorn. Die Wortlisten erkennen keine davon: Die
  Suchanfrage hat meist kein Verneinungswort und gilt als neutral. Die Aussage fällt weg,
  aber bei fünf Fällen rückt etwas anderes auf den ersten Platz: eine andere, nur thematisch
  nahe Aussage (S21, S35, S62) oder ein direkter Treffer, der schon vorher auf der Seite
  stand (S05, S18). Das ist keine Frage der Polarität mehr, sondern der Schwelle (wie bei
  den fremden Themen).
- **Die Antworten des Gegenteils** kamen ohne weitere Regel über den direkten Weg zurück
  (bei S05, S18, S35, S62, S82, S86 stand danach eine Antwort auf das Gegenteil vorn). Deshalb
  schließt ein Widerspruch nach dem Modell auch die Antworten der Aussage vom direkten Weg
  aus; bei den Wortlisten bleibt es wie bisher.
- **Beide Richtungen statt einer:** Mit „eine Richtung ab 0,5“ fallen vier passende Treffer
  heraus (S02 „Windkraftanlagen bringen massenhaft Vögel um“, S16, S73, S76): Das Modell liest
  Umgangssprache in einer Richtung als Widerspruch (S02: 0,99 hin, 0,53 zurück). Mit beiden
  Richtungen bleibt davon nur **S73** („Grün wählen doch nur Lehrer und Studenten“ zu „Die
  Grünen machen Politik nur für Akademiker“, 1,00 und 0,99). Die Grenzen sind an diesem Set
  gewählt, die Wirkung ist also eher zu optimistisch.
- **Fragen und Schlagwörter** prüft das Modell nicht (Fragezeichen oder Verb vorn, unter drei
  Wörtern): Im ersten Lauf ohne diese Regel fielen S37, S44, S64 („Dunkelflaute Blackout“)
  und S60 („Lohnt sich ein Balkonkraftwerk?“) heraus.
- **Laufzeit:** Das Modell urteilt je Suche über bis zu fünf Aussagen in beide Richtungen,
  das kostet auf der Dev-VM rund 0,3 bis 0,45 s mehr im Median (zwei Läufe mit denselben
  Urteilen, die VM war geteilt). Auf der Ziel-VM nachmessen, bevor `an` gilt.
- **Ergebnis:** Zwei von acht Verneinungen zeigen nichts mehr, zwei Fälle ohne Erwartung mehr
  zeigen richtig nichts, ein passender Treffer geht verloren, die Präzision bleibt. Der
  Standard bleibt `schatten`; im Log steht dann, wie oft Wortlisten und Modell bei echten
  Suchen auseinanderliegen.

## Nächtlicher Lauf

`.woodpecker/nacht.yaml` (#391) misst jede Nacht und auf Anstoß das Messset und das
Suchtestset gegen das echte Modell und ein eigenes Qdrant mit dem Seed (Ablauf und
Einrichtung in `docs/CI.md`, „Nightly run“). Für das Suchtestset:

Der Dienststart braucht die App-Datenbank (lokal die des Dev-Stacks auf Port 5433, sonst
`SEMANTIC_SEARCH_APP_DATABASE_URL` setzen).

```bash
cd mvp/backend/semantic-search-service/app
export SEMANTIC_SEARCH_QDRANT_COLLECTION=nachtlauf   # eine leere Sammlung
../venv/bin/python -m tests.regression.seed_laden    # bricht ab, wenn sie nicht leer ist
../venv/bin/python -m tests.regression.nachtlauf     # Tabellen und Prüfungen, Exit 1 = rot
```

Geprüft wird bei der Schwelle von heute (Werte in `nachtlauf.py`):

- **Soll:** die Zahlen der Zeile „(heute)“ oben, dazu Zerfaserung und ähnliche Aussagen.
  Weicht eine um mehr als einen Fall ab, ist der Lauf rot, auch bei einer Verbesserung:
  Wer Modell, Schwelle, Stemmer, Normalisierung oder das Set ändert, zieht `SOLL` und
  diese Seite im selben PR nach (ein Unit-Test vergleicht beide).
- **Tor für Roadmap-Stufe 3** (`docs/VISION.md`): Recall@10 mindestens 0,80 und Präzision
  mindestens 0,25, unabhängig vom Soll. Am Seed heute 0,88 und 0,49.
- **Untere Grenze für ähnliche Aussagen:** Bei mindestens 70 % der Fälle mit Erwartung
  ist eine erwartete Aussage unter den ähnlichen Aussagen. Am Seed heute 76 %.

Tor und Grenze sind am Seed gesetzt, so dass ein erlaubter Ausreißer von einem Fall
nicht rot wird. Am Entwurf des Startbestands (#568) halten bei 0,82 beide (Präzision
0,34, ähnliche Aussagen 76 %). Der Lauf
misst immer am Seed, nie am Bestand von Test oder Produktion.
