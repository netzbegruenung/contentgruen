# Messset Ähnlichkeit

Das Messset ist die Grundlage für die Schwellen der Dublettenprüfung, für die NLI-Stufe
(#387) und für jeden Modellwechsel (ADR 0005). Es besteht aus Textpaaren, die ein Mensch
entschieden hat: Ist der Kandidat dieselbe Behauptung wie der Bestandstext?

| Datei | Inhalt |
|---|---|
| `aehnlichkeit_paare.py` | die Paare mit Paar-Label, Kategorie, Phänomen und Gruppe (von Hand) |
| `aehnlichkeit_gemessen.py` | Scores und Entscheidung je Paar (erzeugt, nicht von Hand ändern) |
| `aehnlichkeit_messen.py` | misst und gibt die Auswertung je Paar-Label aus |
| `test_aehnlichkeit_messset.py` | Regressionstest mit Modell (langsam, nicht in CI) |
| `../unit/test_aehnlichkeit_messset_aufbau.py` | Aufbau, Umfang und Split ohne Modell (in CI) |

```bash
cd mvp/backend/semantic-search-service/app
../venv/bin/python -m tests.regression.aehnlichkeit_messen              # nur Auswertung
../venv/bin/python -m tests.regression.aehnlichkeit_messen --schreiben  # gemessen.py neu
../venv/bin/python -m pytest tests/regression -m langsam -q
```

## Paar-Labels

| Label | Bedeutung | Prüffrage |
|---|---|---|
| **gleich** | dieselbe Behauptung | Würde dieselbe Antwort auf beide passen, ohne dass jemand stutzt? |
| **widerspricht** | beide können nicht zugleich stimmen | Wer dem einen zustimmt, muss das andere ablehnen. |
| **verwandt** | selbes Thema, andere Behauptung; beide können zugleich stimmen | Stärker, schwächer, Teil oder anderer Aspekt. |
| **fremd** | anderes Thema | |

Die Labels entsprechen den Verknüpfungen zwischen Aussagen im Glossar: gleiche Aussagen
werden zusammengeführt, die anderen heißen „verwandt mit“ und „widerspricht“.

Daneben bleibt die **Kategorie** A–E vom 17.09.2026 stehen. Sie beschreibt, wie der Text
abweicht, nicht was er behauptet: A identisch, B trivial (Groß/klein, Satzzeichen am Ende,
Leerraum, Anführungszeichen), C andere Worte, D verwandt oder widersprechend, E fremd.
A, B und C sind immer *gleich*, D ist *verwandt* oder *widerspricht*, E ist *fremd*.

Das **Phänomen** sagt, woran sich ein Paar unterscheidet: `identisch`, `trivial`,
`tippfehler`, `wortstellung`, `umformulierung`, `zusatz` (angehängte Herkunft),
`verneinung`, `antonym`, `quantor`, `skopus`, `frage`, `zahl`, `mehrfachthema`, `aspekt`,
`fremd`. Minimalpaare sind die Paare mit den Phänomenen `verneinung`, `antonym` und
`quantor`: Kandidat und Bestand unterscheiden sich vor allem in dieser Verneinung, diesem
Gegenwort oder diesem Quantor, meist in ein bis zwei Wörtern, manchmal in einer längeren
Wendung („Es stimmt nicht, dass …“). Als harte Negative zählen nur die, deren Label nicht
*gleich* ist (`test_umfang_der_aussage_paare`).

### Altbestand vom 17.09.2026

Die 77 alten Paare behalten ID, Text und Kategorie. Das Paar-Label folgt aus der
Kategorie (A–C *gleich*, E *fremd*); bei D ist es nach den Regeln unten entschieden,
z. B. D11 und D15 *widerspricht*, B09 *verwandt* (Regel 4). Zwei Kategorien haben sich
geändert: C07 ist jetzt D, *verwandt* (Regel 6, Mehrfachthema), und C03 ist jetzt D,
*verwandt* (Regel 1, „immer alles verbieten“ ist stärker als „Verbotspartei“). Die ID zeigt die
Kategorie vom 17.09.2026 und wird nicht umbenannt; B09 stand schon damals unter D.

## Regeln für Grenzfälle

Modelle können diese Fälle nicht für Menschen entscheiden. Die Regeln gelten für neue
Paare und beim Prüfen der Labels; abgenommen im Review von #454 am 29.10.2026.

1. **Wörtlich nehmen.** Quantoren und Häufigkeiten gelten so, wie sie dastehen, auch wenn
   sie im Alltag übertrieben gemeint sind. „Balkonsolar lohnt sich nie“ und „… lohnt sich
   selten“ widersprechen sich, weil „selten“ „manchmal“ einschließt. Das gilt auch für
   Wertungen: „Die Grünen wollen ständig alles verbieten“ ist stärker als „Die Grünen
   sind eine Verbotspartei“ und damit *verwandt* (VB03, C03), ebenso „Busse und Bahnen
   auf dem Land taugen nichts“ gegen „… ist zu schlecht“ (NV02). Sind beide Seiten
   gleich stark, ist es eine gleichwertige Umformung und *gleich* (C10: „funktionieren
   nur im Neubau“ / „im Altbau taugen sie nichts“, Regel 3).
2. **Skopus von „nicht“.** Entscheidend ist, was verneint wird, nicht wo das Wort steht.
   - Gleiche Bedeutung, andere Stellung: *gleich*. „Deutschland kann das Klima nicht alleine
     retten“ / „Deutschland kann nicht alleine das Klima retten“ (C02).
   - „nicht alle“ gegen „alle“: *widerspricht*. „Nicht alle Heizungen“ verneint „alle
     Heizungen“.
   - „nicht nur X“ gegen „nur X“: *widerspricht*. Gegen „X“ ohne „nur“: *verwandt*
     („Windräder töten nicht nur Vögel“ schließt „Windräder töten Vögel“ ein).
   - Doppelte Verneinung zählt als Bejahung: „bringt nicht nichts“ widerspricht „bringt
     nichts“; „ohne Kohlekraftwerke nicht sicher“ ist *gleich* „wir brauchen
     Kohlekraftwerke“.
3. **Quantoren.**
   - alle ↔ kein, nie ↔ immer, nie ↔ manchmal, kein ↔ manche: *widerspricht*.
   - alle ↔ manche, Aussage ohne Quantor ↔ „manche“, „alle“, „oft“, „teilweise“:
     *verwandt* (stärker oder schwächer, beides kann stimmen).
   - Gleichwertig umgeformt ist *gleich*: „immer unpünktlich“ = „nie pünktlich“.
4. **Fragen.** Eine Frage behauptet nichts. Frage gegen Behauptung ist *verwandt*, auch
   wenn nur das Satzzeichen anders ist (B09) und auch bei rhetorischen Fragen.
5. **Vergleiche und Rollen.** Die Umkehrung mit dem Gegenwort ist *gleich* („E-Autos sind
   schlechter als Verbrenner“ = „Verbrenner sind besser als E-Autos“). Vertauschte Rollen
   ohne Gegenwort widersprechen bei Vergleichen („Bahnfahren ist billiger als Fliegen“) und
   sind sonst *verwandt* („Deutschland schadet der EU“ gegen „Die EU schadet Deutschland“).
6. **Mehrfachthemen.** Eine Aussage mit zwei Behauptungen ist gegen eine ihrer Teile
   *verwandt*, nicht *gleich*: Die Antwort auf den Teil beantwortet nicht das Ganze.
7. **Tippfehler** ändern nichts: *gleich*. Wird daraus ein anderes Wort mit anderer
   Bedeutung (Wirtschaft / Landwirtschaft, D04), ist es kein Tippfehler.
8. **Zahlen** (Hintergrundinfos). Eine andere Zahl für dasselbe Jahr und denselben
   Gegenstand *widerspricht*. Dieselbe Zahl für ein anderes Jahr oder ein anderes Szenario
   (Tempo 130 statt 120) ist *verwandt*: Beides kann zugleich stimmen, auch wenn eins davon
   falsch ist. Eine angehängte Herkunft ändert nichts (*gleich*).
9. **Füllwörter** ohne Inhalt („doch eh“, „total“, „überhaupt“) ändern nichts: *gleich*.
   Quantoren und Wertungen („ständig alles“, „taugen nichts“) sind keine Füllwörter, sie
   zählen wörtlich nach Regel 1.
   Bei einer Konkretisierung zählt, ob dieselben Betroffenen gemeint sind. Benennt sie nur,
   was in der Debatte ohnehin gemeint ist, ist sie *gleich* (C08: „mir meine Heizung
   verbieten“ / „uns die Gasheizung wegnehmen“ meint beide Male die vorhandene Heizung
   der Sprechenden). Schränkt sie auf eine andere Gruppe ein, ist sie *verwandt* (HZ07:
   „neue Ölheizungen verbieten“ betrifft die vorhandene Heizung gerade nicht).
10. **Gegenteilige Haltungen** widersprechen sich, auch wenn beide Sätze streng logisch
    zugleich stimmen könnten: Wer dem einen zustimmt, lehnt in der Debatte das andere ab.
    „Windräder schützen Vögel“ / „Windräder töten Vögel“ (WI14) und „Ein Tempolimit
    schadet dem Klima“ / „Ein Tempolimit bringt nichts fürs Klima“ (TL12) sind
    *widerspricht*.

## Train/Test-Split

Der Split ist fest und hängt an der **Gruppe** eines Paares (`TEST_GRUPPEN` in
`aehnlichkeit_paare.py`), nicht am Zufall. Eine Gruppe ist ein Bestandstext mit seinen
Varianten; sie liegt ganz in einem Teil, damit kein Text in Train und Test zugleich
vorkommt (`test_kein_text_in_train_und_test`).

- **Train**: die 77 Paare vom 17.09.2026 (Gruppe `alt`, an ihnen sind die heutigen
  Schwellen gesetzt) und 22 Aussage- sowie 4 Hintergrundinfo-Gruppen. Zum Kalibrieren
  (τ/κ in #387) und später zum Feinjustieren.
- **Test**: 10 Aussage-Gruppen mit eigenen Bestandstexten (Wald, Nahverkehr,
  Deutschlandticket, Bio, Fliegen, Akku, Moor, Fernwärme, Wolf, Mülltrennung) und 2
  Hintergrundinfo-Gruppen (Stromausfall, Tempolimit). Nur zum Messen: Wer an ihnen Schwellen
  oder Modelle auswählt, hat keinen Test-Teil mehr.

Neue Paare kommen in eine bestehende Gruppe (ans Ende, die IDs werden durchgezählt) oder
in eine neue; eine neue Gruppe wird beim Anlegen einem Teil zugeordnet und wechselt nie.

Grenze des Splits: Train und Test teilen keinen Text, aber Themen und Vorlagen. Die
Varianten folgen in beiden Teilen denselben Mustern („Manche …“, „Ist … ?“, „Es stimmt
nicht, dass …“), und die Hintergrundinfo-Gruppe zum Tempolimit (Test) behandelt dasselbe
Thema wie ein Kommentar-Paar im Train-Teil. Ein Modell, das an Train justiert ist, kann
im Test daher besser aussehen als bei fremden Texten.

## Ergebnis mit multilingual-e5-base

Gemessen am 29.10.2026 mit `intfloat/multilingual-e5-base` und den Schwellen aus
`core/config.py`; die 77 alten Paare liefern dieselben Werte wie am 17.09.2026.
„als gleich entschieden“ zählt auch normalisiert gleiche Texte mit. Die Tabellen sind die
Ausgabe von `aehnlichkeit_messen.py` über `aehnlichkeit_gemessen.py`; ein Unit-Test
prüft, dass sie hier unverändert stehen (`test_messset_md_zeigt_die_gespeicherte_messung`).

- **Aussagen:** Die Schwelle 0,98 trennt *gleich* nicht von den anderen Labels. 31 von 151
  *widerspricht*-Paaren und 28 von 131 *verwandt*-Paaren lägen heute über ihr und würden
  still als dieselbe Aussage wiederverwendet (Verneinung, Gegenteil, vertauschte Rollen,
  „manche“, Fragen). Von 119 *gleich*-Paaren erreichen nur 45 die Schwelle, 50 gelten
  mit der Normalform als gleich. Über der Vorschlagsschwelle 0,885 liegen alle *gleich*-
  und *widerspricht*-Paare und 124 von 131 *verwandt*-Paaren.
- **Hintergrundinfos:** Alle 10 *widerspricht*-Paare (andere Zahl oder Verneinung im sonst
  gleichen Text) liegen über 0,975 und würden als Dublette angeboten, ebenso 3 von 9
  *verwandt*-Paaren; 4 von 14 *gleich*-Paaren (Umformulierungen) liegen darunter.
- Die Fehlentscheidungen stehen als `BEKANNTE_FEHLENTSCHEIDUNGEN` in
  `aehnlichkeit_messen.py`; ein Unit-Test hält die Liste deckungsgleich mit der Messung.
  Paare, deren Score weniger als 0,001 neben der Schwelle liegt (`KNAPP`), vergleicht der
  Regressionstest nicht: Ihre Entscheidung kann auf anderer Hardware kippen.
  Sie abzufangen ist Aufgabe der NLI-Stufe (#387); der Kosinus allein kann es nicht.

aussage (Score qq, Dublette ab 0.98):

| Label | Paare | train/test | Score min–max | als gleich entschieden | ≥ 0.98 | ≥ 0.885 |
|---|---|---|---|---|---|---|
| gleich | 119 | 89/30 | 0.887–1.000 | 50 | 45 | 119 |
| widerspricht | 151 | 104/47 | 0.906–0.996 | 31 | 31 | 151 |
| verwandt | 131 | 94/37 | 0.821–0.996 | 28 | 28 | 124 |
| fremd | 39 | 29/10 | 0.759–0.852 | 0 | 0 | 0 |

suche (Score qq, Dublette ab 0.98):

| Label | Paare | train/test | Score min–max | als gleich entschieden | ≥ 0.98 | ≥ 0.885 |
|---|---|---|---|---|---|---|
| gleich | 3 | 3/0 | 0.979–0.987 | 3 | 1 | 3 |
| verwandt | 3 | 3/0 | 0.888–0.935 | 0 | 0 | 3 |
| fremd | 1 | 1/0 | 0.746–0.746 | 0 | 0 | 0 |

kommentar (Score pp, Dublette ab 0.975):

| Label | Paare | train/test | Score min–max | als gleich entschieden | ≥ 0.975 | ≥ 0.885 |
|---|---|---|---|---|---|---|
| gleich | 10 | 10/0 | 0.955–1.000 | 7 | 6 | 10 |
| verwandt | 5 | 5/0 | 0.817–0.899 | 0 | 0 | 2 |
| fremd | 2 | 2/0 | 0.789–0.800 | 0 | 0 | 0 |

hintergrundinfo (Score pp, Dublette ab 0.975):

| Label | Paare | train/test | Score min–max | als gleich entschieden | ≥ 0.975 | ≥ 0.885 |
|---|---|---|---|---|---|---|
| gleich | 14 | 9/5 | 0.946–1.000 | 10 | 10 | 14 |
| widerspricht | 10 | 7/3 | 0.976–1.000 | 10 | 10 | 10 |
| verwandt | 9 | 6/3 | 0.827–0.999 | 3 | 3 | 6 |
| fremd | 6 | 4/2 | 0.772–0.843 | 0 | 0 | 0 |
