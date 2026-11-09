# Messset Ähnlichkeit

Das Messset ist die Grundlage für die Schwellen der Dublettenprüfung, für die NLI-Stufe
(#387) und für jeden Modellwechsel (ADR 0005). Es besteht aus Textpaaren, die ein Mensch
entschieden hat: Ist der Kandidat dieselbe Behauptung wie der Bestandstext?

| Datei | Inhalt |
|---|---|
| `aehnlichkeit_paare.py` | die Paare mit Paar-Label, Kategorie, Phänomen und Gruppe (von Hand) |
| `aehnlichkeit_gemessen.py` | Scores und Entscheidung je Paar (erzeugt, nicht von Hand ändern) |
| `aehnlichkeit_messen.py` | misst und gibt die Auswertung je Paar-Label aus |
| `test_aehnlichkeit_messset.py` | Regressionstest mit Modell (langsam, nicht in der PR-CI, jede Nacht in `.woodpecker/nacht.yaml`) |
| `nli_messen.py`, `nli_gemessen.py`, `nli_bestaetiger_gemessen.py` | NLI-Stufe (#387): Urteile je Aussagepaar (erstes Modell und Bestätiger), Auswertung, Antwortzeit |
| `test_nli_messset.py`, `../unit/test_nli_messset.py` | NLI-Stufe mit Modell (langsam) bzw. über die gespeicherten Urteile (in CI) |
| `../unit/test_aehnlichkeit_messset_aufbau.py` | Aufbau, Umfang und Split ohne Modell (in CI) |

```bash
cd mvp/backend/semantic-search-service/app
../venv/bin/python -m tests.regression.aehnlichkeit_messen              # nur Auswertung
../venv/bin/python -m tests.regression.aehnlichkeit_messen --schreiben  # gemessen.py neu
../venv/bin/python -m pytest tests/regression -m langsam -q
```

Jede Nacht läuft der Regressionstest in `.woodpecker/nacht.yaml`; wann ein PR den Lauf
anstoßen muss, steht in `docs/CI.md`, „Nightly run“.

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

## NLI-Stufe (#387)

Die zweite Stufe der Prüfung auf dieselbe Aussage (`services/dieselbe_behauptung`): Die
Einbettung liefert Kandidaten, ein NLI-Modell urteilt je Paar in beide Richtungen.
Gemessen am 06.11.2026 mit `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`
(MIT, fp32) an den Aussage- und Suchpaaren; Kommentare und Hintergrundinfos prüft die
Stufe nicht.

```bash
../venv/bin/python -m tests.regression.nli_messen               # nur Auswertung
../venv/bin/python -m tests.regression.nli_messen --schreiben   # nli_gemessen.py neu
../venv/bin/python -m tests.regression.nli_messen --zeit        # Antwortzeit, Speicher
```

**Regel** (`regel.entscheiden`): Normalisiert gleich zählt immer. Sonst muss der Kandidat
eine query/query-Ähnlichkeit ab `nli_kandidaten_ab` haben, zwei Vorprüfungen bestehen
und das Modell muss in beiden Richtungen mit mindestens τ = `nli_folgerung_ab` folgern,
ohne dass eine Richtung mit κ = `nli_widerspruch_unter` oder mehr widerspricht.

- **Vorprüfung Frage:** Frage gegen Behauptung wird nie geprüft (Regel 4, B09). Frage
  heißt: Fragezeichen am Ende oder ein finites Verb an erster Stelle (`regel.FRAGEVERBEN`,
  für Suchanfragen ohne Fragezeichen); am Messset ändert das nichts.
- **Vorprüfung Quantoren:** Unterscheiden sich die Quantoren (`regel.QUANTOREN`: alle,
  manche, nie, immer, nur …), wird nicht geprüft. Ohne sie folgert das Modell „Manche
  Windräder töten Vögel“ und „Windräder töten Vögel“ in beide Richtungen mit über 0,95
  (WI07, RW06, WA06, BI06), nach Regel 1 und 3 sind sie *verwandt*. Der Preis: Gleichwertige
  Umformungen mit anderem Quantor („immer unpünktlich“ / „nie pünktlich“, DB02) bleiben
  getrennt.
- **Untergrenze 0,85:** Das niedrigste *gleich*-Paar der Aussagen liegt bei 0,887, alle
  *fremd*-Paare darunter (höchstens 0,852). **Höchstens 5 Kandidaten** (10 Modellaufrufe
  in einem Stapel): Im Messset hat jede Aussage einen Bestandstext; mehr Kandidaten
  kosten Antwortzeit (unten), ohne dass das Messset einen Fall dafür hat.
- **τ und κ am Train-Teil:** Gitter τ 0,30–0,98, κ 0,01–0,5; gewählt ist das τ mit den
  meisten erkannten *gleich*-Paaren ohne eine falsche Zusammenführung im Train-Teil.
  τ = 0,95 erkennt 58 von 92 (Aussage und Suche), schon 0,94 führte TL12 und IN05
  zusammen. κ ändert bei τ = 0,95 nichts, 0,05 schließt nur klare Widersprüche aus.
- **Vorschläge im Feld „Antwort auf“:** nicht vorgeschlagen, wenn eine Richtung mit
  mindestens `aussage_vorschlag_widerspruch_ab` = 0,5 widerspricht. Am Train-Teil
  fallen damit 101 von 104 *widerspricht*-Paaren weg und 2 von 89 *gleich*-Paaren.

Ergebnis (Ausgabe von `nli_messen.py`; ein Unit-Test prüft, dass sie hier unverändert
steht):

```text
aussage (NLI ab Score 0.85, tau 0.95, kappa 0.05):

| Label | Paare (train/test) | dieselbe heute | dieselbe mit NLI train | dieselbe mit NLI test | nicht vorgeschlagen (Widerspruch) |
|---|---|---|---|---|---|
| gleich | 119 (89/30) | 50 | 55/89 | 20/30 | 4/119 |
| widerspricht | 151 (104/47) | 31 | 0/104 | 0/47 | 148/151 |
| verwandt | 131 (94/37) | 28 | 0/94 | 0/37 | 15/124 |
| fremd | 39 (29/10) | 0 | 0/29 | 0/10 | 0/0 |

suche (NLI ab Score 0.85, tau 0.95, kappa 0.05):

| Label | Paare (train/test) | dieselbe heute | dieselbe mit NLI train | dieselbe mit NLI test | nicht vorgeschlagen (Widerspruch) |
|---|---|---|---|---|---|
| gleich | 3 (3/0) | 3 | 3/3 | 0/0 | 0/3 |
| verwandt | 3 (3/0) | 0 | 0/3 | 0/0 | 0/3 |
| fremd | 1 (1/0) | 0 | 0/1 | 0/0 | 0/0 |

Andere Behauptung als dieselbe: keine
gleich, nur mit der Schwelle erkannt (7): HZ02, CO01, RW01, WA03, NV12, AK01, FW01
gleich, aber nicht erkannt (44): C01, C04, C05, C08, C09, C10, C11, C12, C13, WI02, WI03, BS03, EA03, FL01, FL03, EE02, EE13, HZ01, HZ02, HZ03, AT02, DB01, DB02, KW02, KW13, SP03, LR01, LR03, CO01, RW01, RW03, GN02, WS02, IN01, WA02, WA03, NV01, NV12, FB01, AK01, AK02, MO02, FW01, WO02
```

- **Test-Teil:** 20 von 30 *gleich*-Paaren werden dieselbe Aussage (mit der Schwelle 0,98
  heute 14), keins der 84 *widerspricht*- und *verwandt*-Paare (heute 23). D11, B09 und
  D15 bleiben getrennt.
- **Nicht erkannt** werden vor allem Umformulierungen mit anderen Wörtern („Windkraft im
  Wald macht die Natur kaputt“, WA02), andere Wortstellung mit Objekt vorn (SP03, RW03,
  WA03) und Tippfehler, deren Folgerung knapp unter τ liegt (0,92–0,95: FB01, AK01, FW01).
  Hier bleibt es bei einer Aussage zu viel, nie bei einer falschen Zusammenführung.
- **Nur mit der Schwelle erkannt** werden 7 *gleich*-Paare (oben), vier davon Tippfehler
  über 0,98 („teuerer“ / „teurer“, FW01). Die 14 von heute sind also keine Teilmenge der
  20. Die Schwelle zusätzlich gelten zu lassen, wenn das Modell keinen Widerspruch sieht,
  führte TL13, HZ09, SP07, IN05 und WA10 falsch zusammen; deshalb entscheidet im Modus
  `an` nur die NLI-Stufe.
- **Antwortzeit und Speicher** (`--zeit`, 2 Threads, AMD EPYC 9684X, geteilter Host unter
  Last, Median aus 5 Läufen): 1 Kandidat 176 ms, 5 Kandidaten 507 ms, 10 Kandidaten
  1241 ms; Laden 2,5 s, Speicher bis zu rund 2 GB zusätzlich (höchster Stand beim Laden,
  ohne torch). Auf der Ziel-VM neu messen.

### Bestätiger (zweites NLI-Modell)

Schalter `nli_bestaetiger` (`SEMANTIC_SEARCH_NLI_BESTAETIGER`, Standard aus). Gemessen am
09.11.2026 mit `joeddav/xlm-roberta-large-xnli` (MIT laut Model Card, fp32; Tokenizer aus
`FacebookAI/xlm-roberta-large`). Selbst identische Texte folgert das erste Modell nur mit
0,84–0,92 (A01, A02, A04), der Bestätiger mit über 0,99; allein führt er aber
„Es stimmt nicht, dass …“ und ähnliche Paare zusammen (AK06). Deshalb hat das erste Modell
ein Veto.

**Regel** (`regel.bestaetigt`, zusätzlich zu `regel.entscheiden`): Der Kandidat liegt über
der Untergrenze, das erste Modell widerspricht in keiner Richtung (κ) und folgert in beiden
mindestens `nli_bestaetiger_veto_ab` = 0,1, und der Bestätiger sieht mit τ und κ dieselbe
Behauptung. Nur in diesem Band rechnet der Bestätiger; landet schon ein Kandidat nach der
Regel oben, rechnet er nicht. Auf diesem Weg zählt „kein“ nicht als Quantor
(`regel.KEIN_WOERTER`), die anderen Quantoren und Fragen trennen weiter.

Ergebnis (zweite Ausgabe von `nli_messen.py`, ein Unit-Test prüft sie hier):

```text

aussage (NLI ab Score 0.85, tau 0.95, kappa 0.05, mit Bestaetiger (Veto ab 0.1)):

| Label | Paare (train/test) | dieselbe heute | dieselbe mit NLI train | dieselbe mit NLI test | nicht vorgeschlagen (Widerspruch) |
|---|---|---|---|---|---|
| gleich | 119 (89/30) | 50 | 69/89 | 26/30 | 4/119 |
| widerspricht | 151 (104/47) | 31 | 1/104 | 0/47 | 148/151 |
| verwandt | 131 (94/37) | 28 | 1/94 | 0/37 | 15/124 |
| fremd | 39 (29/10) | 0 | 0/29 | 0/10 | 0/0 |

suche (NLI ab Score 0.85, tau 0.95, kappa 0.05, mit Bestaetiger (Veto ab 0.1)):

| Label | Paare (train/test) | dieselbe heute | dieselbe mit NLI train | dieselbe mit NLI test | nicht vorgeschlagen (Widerspruch) |
|---|---|---|---|---|---|
| gleich | 3 (3/0) | 3 | 3/3 | 0/0 | 0/3 |
| verwandt | 3 (3/0) | 0 | 0/3 | 0/0 | 0/3 |
| fremd | 1 (1/0) | 0 | 0/1 | 0/0 | 0/0 |

Andere Behauptung als dieselbe: TL13, IN05
gleich, nur mit der Schwelle erkannt (2): WA03, NV12
gleich, aber nicht erkannt (24): C01, C05, C08, C09, C10, C11, C12, C13, WI02, WI03, EA03, EE02, AT02, DB01, DB02, SP03, RW03, GN02, WS02, IN01, WA02, WA03, NV12, WO02
```

- **Erkannt:** 98 statt 78 von 122 *gleich*-Paaren, im Test-Teil 26 statt 20 von 30; neu
  vor allem Tippfehler knapp unter τ (FB01, AK01, FW01) und Umformulierungen (HZ01–HZ03,
  LR01, LR03). Im Test-Teil keine falsche Zusammenführung.
- **Preis:** zwei falsche Zusammenführungen von 325 *widerspricht*-, *verwandt*- und
  *fremd*-Paaren, beide im Train-Teil (`BEKANNT_FALSCH_MIT_BESTAETIGER`): TL13 „Nicht nichts
  bringt ein Tempolimit fürs Klima“ (doppelte Verneinung, *widerspricht*) und IN05
  „Pestizide sind mitschuld“ / „… schuld“ (*verwandt*). D11, B09 und D15 bleiben getrennt.
- **Gewählt** am Messset und am Suchtestset zusammen (Analyse vom 09.11.2026): Die Wirkung
  ist eher zu optimistisch. τ 0,90 ohne zweites Modell erkannte weniger und führte TL12
  („Tempolimit schadet dem Klima“ / „bringt nichts“) zusammen.
- **Antwortzeit und Speicher** (`--zeit`, 2 Threads, gleicher Host wie oben): 1 Kandidat
  351 ms, 5 Kandidaten 1147 ms, 10 Kandidaten 2083 ms; Laden 2,4 s, Speicher in einem
  eigenen Prozess bis zu rund 1,6 GB zusätzlich (Modelldatei 2,2 GB). Weil er nur im
  unsicheren Band rechnet, urteilt er im Suchtestset bei 12 von 99 Suchen über je einen
  Kandidaten (`SUCHTESTSET.md`, Zerfaserung). Auf der Ziel-VM neu messen.
