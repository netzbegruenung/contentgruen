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
`fremd`. Minimalpaare sind die Phänomene `verneinung`, `antonym` und `quantor`: Kandidat
und Bestand unterscheiden sich in einem Wort oder einer Wendung.

## Regeln für Grenzfälle

Modelle können diese Fälle nicht für Menschen entscheiden. Die Regeln gelten für neue
Paare und beim Prüfen der Labels; sie werden im Review abgenommen.

1. **Wörtlich nehmen.** Quantoren und Häufigkeiten gelten so, wie sie dastehen, auch wenn
   sie im Alltag übertrieben gemeint sind. „Balkonsolar lohnt sich nie“ und „… lohnt sich
   selten“ widersprechen sich, weil „selten“ „manchmal“ einschließt.
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
9. **Verstärker** ohne Inhalt („doch eh“, „total“, „überhaupt“) ändern nichts: *gleich*.
   Eine Konkretisierung, die den Kern lässt, ist *gleich* (C08 „Heizung“ / „Gasheizung“);
   ändert sie, wer oder was betroffen ist, ist sie *verwandt* („Ölheizungen verbieten“
   gegen „meine Heizung verbieten“).

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

## Ergebnis mit multilingual-e5-base

Gemessen am 29.10.2026 mit `intfloat/multilingual-e5-base` und den Schwellen aus
`core/config.py`; die 77 alten Paare liefern dieselben Werte wie am 17.09.2026.
„als gleich entschieden“ zählt auch normalisiert gleiche Texte mit. Neu erzeugen mit
`aehnlichkeit_messen.py`.

- **Aussagen:** Die Schwelle 0,98 trennt *gleich* nicht von den anderen Labels. 21 von 96
  *widerspricht*-Paaren und 28 von 127 *verwandt*-Paaren lägen heute über ihr und würden
  still als dieselbe Aussage wiederverwendet (Verneinung, Gegenteil, vertauschte Rollen,
  „manche“, Fragen). Von 116 *gleich*-Paaren erreichen nur 43 die Schwelle, 48 gelten
  mit der Normalform als gleich. Über der Vorschlagsschwelle 0,885 liegen alle *gleich*-
  und *widerspricht*-Paare und 120 von 127 *verwandt*-Paaren.
- **Hintergrundinfos:** Alle 10 *widerspricht*-Paare (andere Zahl oder Verneinung im sonst
  gleichen Text) liegen über 0,975 und würden als Dublette angeboten, ebenso 3 von 9
  *verwandt*-Paaren; 4 von 14 *gleich*-Paaren (Umformulierungen) liegen darunter.
- Die Fehlentscheidungen stehen als `BEKANNTE_FEHLENTSCHEIDUNGEN` im Regressionstest.
  Sie abzufangen ist Aufgabe der NLI-Stufe (#387); der Kosinus allein kann es nicht.

aussage (Score qq, Dublette ab 0.98):

| Label | Paare | train/test | Score min–max | als gleich entschieden | ≥ 0.98 | ≥ 0.885 |
|---|---|---|---|---|---|---|
| gleich | 116 | 88/28 | 0.887–1.000 | 48 | 43 | 116 |
| widerspricht | 96 | 66/30 | 0.906–0.996 | 21 | 21 | 96 |
| verwandt | 127 | 91/36 | 0.821–0.996 | 28 | 28 | 120 |
| fremd | 39 | 29/10 | 0.759–0.852 | 0 | 0 | 0 |

hintergrundinfo (Score pp, Dublette ab 0.975):

| Label | Paare | train/test | Score min–max | als gleich entschieden | ≥ 0.975 | ≥ 0.885 |
|---|---|---|---|---|---|---|
| gleich | 14 | 9/5 | 0.946–1.000 | 10 | 10 | 14 |
| widerspricht | 10 | 7/3 | 0.976–1.000 | 10 | 10 | 10 |
| verwandt | 9 | 6/3 | 0.827–0.999 | 3 | 3 | 6 |
| fremd | 6 | 4/2 | 0.772–0.843 | 0 | 0 | 0 |

kommentar (Score pp, Dublette ab 0.975):

| Label | Paare | train/test | Score min–max | als gleich entschieden | ≥ 0.975 | ≥ 0.885 |
|---|---|---|---|---|---|---|
| gleich | 10 | 10/0 | 0.955–1.000 | 7 | 6 | 10 |
| verwandt | 5 | 5/0 | 0.817–0.899 | 0 | 0 | 2 |
| fremd | 2 | 2/0 | 0.789–0.800 | 0 | 0 | 0 |

suche (Score qq, Dublette ab 0.98):

| Label | Paare | train/test | Score min–max | als gleich entschieden | ≥ 0.98 | ≥ 0.885 |
|---|---|---|---|---|---|---|
| gleich | 3 | 3/0 | 0.979–0.987 | 3 | 1 | 3 |
| verwandt | 3 | 3/0 | 0.888–0.935 | 0 | 0 | 3 |
| fremd | 1 | 1/0 | 0.746–0.746 | 0 | 0 | 0 |
