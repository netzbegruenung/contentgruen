> **Historisch:** Dieses Dokument ist ein Beleg früherer Planung und teils vom Code überholt; maßgeblich sind [GLOSSARY.md](../../GLOSSARY.md) und [docs/adr/](../adr/).

# Spezifikation: Destillier-Ablauf v1 (Fangkorb → Beitrag)

Stand: 13.09.2026, Ergebnis einer strukturierten Befragung. Entscheidungen sind markiert als **[E]** (vom Product Owner entschieden) oder **[A]** (Annahme, in Phase 1 bestätigen). Zeitbox für die Umsetzung: ein Nachmittag. Wenn das nicht reicht, wird v1 verkleinert, nicht verlängert.

## Ziel

Aus der rohen Fangkorb-Liste eine Warteschlange machen, die man leert. Der Nutzer wird pro Eintrag gezwungen, das Argument in einem Satz zu formulieren, bevor das Beitragsformular aufgeht. Wer das nicht kann, verwirft. Nach dem Speichern öffnet sich sofort der nächste offene Eintrag.

## Nicht-Ziele v1

- Keine Fortschrittsbalken, Punkte, Animationen
- Keine KI-Unterstützung im Ablauf
- Keine Queue-Zuweisung, keine Sperren
- Keine Bilder aus dem Share-Pfad (existieren dort noch nicht)
- Kein neues Statement-Modell, keine Änderung an der Suche

## Entscheidungen

| # | Frage | Entscheidung |
|---|---|---|
| 1 | Primäres Gerät | **[E]** Handy, Ablauf muss unterbrechbar sein |
| 2 | Warteschlange | **[E]** Alle Einträge aller Nutzer sichtbar; Verwerfen nur für eigene |
| 3 | Gleichzeitiges Destillieren | **[E]** Kein Lock, Duplikate erlaubt |
| 4 | Vorstufe | **[E]** Erst Satz-Feld, dann Typwahl, dann Formular |
| 5 | Satz-Limit | **[A]** Hart, 200 Zeichen, „Weiter" gesperrt darüber (Frage wurde abgebrochen; Begründung: Copy-Paste-Falle mit Original-Captions physisch verhindern) |
| 6 | Verbleib des Satzes | **[E]** Satz = Kartentitel des Beitrags (bestehendes Feld) |
| 7 | Verworfener Eintrag | **[E]** Bleibt für alle sichtbar, grau, andere dürfen ihn trotzdem destillieren |
| 8 | Nach dem Speichern | **[E]** Nächster offener Eintrag öffnet sich direkt |
| 9 | Reihenfolge | **[E]** Eigene Einträge zuerst, dann nach Neuheit |
| 10 | Statement-Verknüpfung | **[E]** Im Formular optional wie bisher, kein eigener Schritt |
| 11 | Fertige Fangkorb-Karte | **[E]** Nimmt die Farbe des entstandenen Content-Typs an (Farben sind in der App Typ-Farben, keine Status-Farben); zeigt Satz, Link zum Beitrag, wer destilliert hat. Offene Karten bleiben blanko/ungefärbt. Verworfen: blanko, abgedimmt, Hinweis „Verworfen von …". Entwurf: blanko mit Satz. Fehlende `.image-color` dabei anlegen |
| 12 | „Später" | **[A]** Eintrag bleibt `open`, Satz bleibt als Entwurf gespeichert und auf der Karte sichtbar |
| 13 | Leere Warteschlange | **[A]** Kurzer Hinweis „Alles destilliert", Link zurück zum Fangkorb |

## Ablauf (Nutzersicht)

1. Fangkorb-Liste, sortiert nach #9. Karten: offen (blanko), Entwurf vorhanden (blanko mit Satz), verworfen (blanko, abgedimmt), fertig (Farbe des Content-Typs, siehe #11).
2. Tap auf offenen oder verworfenen Eintrag → Destillier-Ansicht (`/destillieren/:id`, **[A]** Routenname):
   - Link (öffnet neuen Tab), ggf. Notiz und Titel aus dem Einwurf
   - Ein Textfeld „Was ist der Punkt? Ein Satz." mit Zähler `n / 200`
   - Knöpfe: Weiter, Später, Verwerfen (Verwerfen nur bei eigenem Eintrag sichtbar)
3. Satz wird beim Verlassen des Felds (blur) und bei jedem Knopf serverseitig gespeichert (#1: Android räumt die PWA beim Wechsel zum Reel weg). Entwurf gehört zu (Eintrag, Nutzer), nicht zum Eintrag allein (#3).
4. Weiter → Typwahl: Kommentar / Hintergrundinfo / Bild. **[A]** Standard vorausgewählt: Kommentar.
5. Formular öffnet vorbefüllt: Herkunft = URL (bereinigt, wie im Share-Pfad), Titel = Satz (#6). Alles im Formular änderbar. Bestehende Consent-Zeile bleibt.
6. Speichern → Eintrag `processed`, Link-Tabelle geschrieben, Zurücksprung in die Destillier-Ansicht des nächsten offenen Eintrags (#8). Kein Eintrag mehr → #13.
7. Verwerfen → `discarded`, Karte abgedimmt, nächster Eintrag öffnet sich.

## Datenmodell und Backend

Vorhanden (laut Audit 08.09.): `raw_inputs` mit Statusfeld `open/in_progress/processed/discarded` (nur `open` wird je geschrieben), Tabelle `raw_input_content_links` (angelegt, unbeschrieben), Endpunkte `addRawInput`, `getRawInputs`.

Neu:

- Status-Endpunkt: `PATCH /api/v1/rawinput/{id}/status` mit `discarded` (nur Einwerfer) und `processed` (jeder angemeldete Nutzer, nur zusammen mit `content_id`). `in_progress` wird **nicht** verwendet (kein Lock, #3).
- Entwurf-Endpunkt: `PUT /api/v1/rawinput/{id}/draft` mit `sentence` (≤200), gespeichert je (raw_input_id, user_id). **[A]** Eigene kleine Tabelle `raw_input_drafts`, nicht am Eintrag.
- Link schreiben: beim Speichern eines Beitrags aus dem Ablauf `raw_input_content_links(raw_input_id, content_id, processed_by, processed_at)`. **[A]** Der Beitrags-Endpunkt bekommt ein optionales Feld `raw_input_id`; alternativ ein separater Aufruf nach dem Speichern, wenn das den Endpunkt zu sehr aufbläht. Agent entscheidet in Phase 1.
- `getRawInputs` liefert zusätzlich: Status, eigener Entwurfssatz, bei `processed` den ersten verknüpften `content_id` und `processed_by`.
- Rate-Limits der bestehenden Endpunkte übernehmen.

## Abhängigkeiten und Risiken

- **Anzeigenamen:** „wer destilliert hat" (#11) und die „Von"-Spalte brauchen Anzeigenamen statt Keycloak-UUIDs. Bekannter offener Bug (11.08.). Wenn bis v1 nicht gelöst: UUID gekürzt anzeigen, nicht blockieren.
- **Datenschutz:** `processed_by` ist ein neues personenbezogenes Feld, sichtbar für alle angemeldeten Nutzer, analog zu `submitted_by`. Datenschutzerklärung erwähnt Fangkorb-Verarbeitung bisher nicht. Nachtrag als Docs-Follow-up, kein Blocker vor dem „drei Leuten zeigen".
- **Titelfeld (#6):** Titel ist ein bestehendes Feld, kein Schemarisiko.
- **Schwelle Duplikat-Guard 0.9:** Zwei Nutzer, die denselben Link destillieren (#3), können in den stillen Dedup laufen. Für v1 hinnehmen, Verhalten beobachten.

## Coding-Pakete (Vorschlag für den Agenten, Phase 1 = read-only-Analyse, dann Freigabe)

1. **Backend Status + Entwurf** — Tabelle `raw_input_drafts`, zwei Endpunkte, Tests. Unabhängig vom Frontend testbar.
2. **Backend Link beim Speichern** — `raw_input_id` am Beitrags-Endpunkt oder Folgeaufruf; `raw_input_content_links` befüllen; `getRawInputs` erweitern.
3. **Frontend Destillier-Ansicht** — Route, Satz-Feld mit Autosave, drei Knöpfe, Typwahl, Übergabe ans Formular (Vorbefüllung per Query-Params oder Service-State, **[A]** Query-Params wegen Unterbrechbarkeit).
4. **Frontend Fangkorb-Karten** — Sortierung, vier Zustände, Fertig-Karte mit Satz/Link/Name, Weiterspringen nach Speichern.
5. **Follow-ups, nicht v1** — Datenschutz-Nachtrag, Anzeigenamen, Icons.

Reihenfolge 1 → 3 → 2 → 4: Nach Paket 3 kann bereits von Hand destilliert werden, auch wenn Karten und Links noch fehlen.

## Erfolgskriterium

Die zehn aktuell offenen Einträge sind bis Mittwochabend am Handy destilliert oder verworfen, mit diesem Ablauf. Wenn der Ablauf bis dahin nicht auf Test ist, werden die zehn von Hand gemacht und die Beobachtungen in diese Datei geschrieben.
