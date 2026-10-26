> **Historisch:** Dieses Dokument ist ein Beleg früherer Planung und teils vom Code überholt; maßgeblich sind [GLOSSARY.md](../../GLOSSARY.md) und [docs/adr/](../adr/).

# SPEC Fangkorb v2

*Stand 13.09.2026, aus Entscheidungsbaum. Baut auf `SPEC_Destillier-Ablauf_v1.md` auf. Bei Widerspruch gilt diese Datei.*

## Ziel

Der Fangkorb wird von einer Rohliste zur Arbeitsfläche für drei getrennte Schritte, die verschiedene Leute machen können: **Einwerfen → Destillieren (Satz) → Ausformulieren (Beitrag).**

## Entscheidungen (13.09.)

| # | Frage | Entscheidung |
|---|---|---|
| 1 | Personen-Felder | Zwei Felder auf `raw_inputs`: `destilled_by`, `processed_by` |
| 2 | Gruppierung der Liste | Nein. Ein Strom: eigene zuerst, dann neueste. Zustand nur über Kartenoptik |
| 3 | Negativbeispiele | In der Warteschlange, keine Unterscheidung. Verwerfen ist der Ausweg |
| 4 | Filter | Plattform + „nur offene“ + „nur meine“ |
| 5 | Seitentitel aus dem Share | Als Vorschlag ins Hinweis-Feld, sichtbar als Vorbelegung markiert, löschbar |
| 6 | Rechtstext | Je ein Satz in Datenschutzerklärung und Nutzungsbedingungen, im selben PR |

## A. Modell: drei Stufen

Status-Enum bleibt `open / in_progress / processed / discarded`. `in_progress` heißt im UI **„Destilliert“** und wird jetzt geschrieben.

**Regeln**
- Sobald irgendjemand einen Satz gespeichert hat (`raw_input_drafts`-Zeile mit nicht-leerem Text), ist der Einwurf `in_progress`. Setzt `destilled_by` = dieser Nutzer, falls noch leer.
- `destilled_by` = wer als **Erster** einen Satz gespeichert hat. Weitere Sätze anderer Nutzer bleiben an ihrer Draft-Zeile sichtbar, ändern das Feld nicht.
- `processed_by` = wer den Beitrag gespeichert hat (setzt `processed`).
- Kein Lock. Mehrere Sätze pro Einwurf sind erlaubt und alle sichtbar.
- Leerer Satz (Nutzer löscht seinen Text wieder) setzt den Status **nicht** zurück, solange ein anderer Satz existiert. Existiert kein Satz mehr: zurück auf `open`, `destilled_by` leeren.
- Verwerfen wie v1: nur eigene Einträge, bleibt grau sichtbar, andere dürfen trotzdem destillieren.

**Datenmodell**
- `raw_inputs`: `destilled_by` (nullable, Keycloak-UUID) neu; `processed_by` existiert.
- `raw_input_content_links`: Spalte `draft_id` (nullable, FK `raw_input_drafts`) ergänzen, damit die Karte weiß, welcher Satz ausformuliert wurde. Tabelle wird damit erstmals wirklich benutzt.
- Migration nach bestehendem Muster (`2026-09-XX-fangkorb-v2.sql`).

**Endpunkte**
- `PUT /rawinput/{id}/draft` setzt beim ersten nicht-leeren Speichern Status + `destilled_by` (Transaktion, `FOR UPDATE` wie in v1).
- `GET /getRawInputs` liefert je Einwurf: Status, `destilled_by`, `processed_by`, alle Drafts (Text, Nutzer, Zeitpunkt), verknüpfte Beiträge (Typ, ID, `draft_id`).
- Beitrag speichern aus dem Destillier-Ablauf schreibt `raw_input_content_links` inkl. `draft_id` und setzt `processed` + `processed_by`.

## B. Liste als Kartenansicht, mobil zuerst

Ersetzt die mat-table (= gestrichenes Paket 4 aus v1).

**Vier Zustände**
| Zustand | Optik | Inhalt |
|---|---|---|
| offen | blanko | Link, Plattform-Chip, Hinweis (grau), Einwerfer |
| destilliert | blanko | wie offen + alle Sätze (je mit Nutzer) |
| ausformuliert | Farbe des Content-Typs (`--commentary-bg` / `--generictext-bg`) | Satz(e), Link zum Beitrag, Destillierer, Ausformulierer |
| verworfen | abgedimmt | wie offen + Hinweis „verworfen“ |

- Sortierung: eigene zuerst, dann neueste. Keine Gruppierung, keine Abschnitte.
- Tippen auf offene/destillierte Karte öffnet `/destillieren/:id`. Tippen auf ausformulierte Karte öffnet den Beitrag.
- Personen bleiben UUIDs (Anzeigenamen = eigene Spec).

## C. Plattform-Chip und Filter

- Chip aus dem Hostnamen, rein Frontend: `instagram.com` → Instagram, `youtube.com`/`youtu.be` → YouTube, `tiktok.com` → TikTok, sonst Web. Ohne Link: kein Chip.
- Filterleiste oben, Chips mit Umschalt-Zustand:
  - Plattform (Mehrfachauswahl, Standard alle). Zweck: Leute ohne Instagram-Account blenden Instagram aus.
  - **„nur offene“** = `open` **und** `in_progress` (destilliert, aber nicht ausformuliert ist noch Arbeit).
  - **„nur meine“** = `submitted_by` = ich.
- Filterzustand hält innerhalb der Sitzung (sessionStorage), nicht darüber hinaus.

## D. Einwurf-Formular: zwei Felder

- **Link** (Pflicht, wenn kein Hinweis; `url`, bereinigt wie heute über `url-bereinigen.ts`). Share-Pfad füllt es, Handeingabe trägt es ein.
- **Hinweis für andere** (optional, `content`, max 5000). Label genau so. Keine Kategorien, keine Labels, keine Schalter.
- Seitentitel aus dem Share (nur Browser liefern ihn, Instagram nicht) landet als **Vorschlag** im Hinweis-Feld, sichtbar als Vorbelegung markiert (z. B. Präfix „Seitentitel: “ oder abgesetzter Stil) und mit einem Griff löschbar. Er wird beim Speichern nur übernommen, wenn der Nutzer ihn stehen lässt.
- Hinweis auf der Karte in grau.
- Consent-Zeile bleibt wie in v1.

## E. Destillier-Ansicht, Nachbesserungen

- Typwahl sauber gestylt (Erläuterungszeilen kommen schon im Fix-PR `fix/destillier-nachlese-v1`).
- Beim Öffnen eines Einwurfs mit Status `in_progress`: vorhandene Sätze **anderer** Nutzer oberhalb des eigenen Satz-Felds anzeigen (Text + Nutzer), nicht editierbar.
- Eigener Satz-Entwurf verhält sich wie v1 (Autosave, keepalive).

## F. Text und Einstieg

- Dreiklang oben kommt im Fix-PR; v2 nur Feinschliff.
- **Nicht v2:** Fangkorb von der Startseite erreichbar, Startseiten-Konzept.

## G. Rechtstext (im selben PR)

- Datenschutzerklärung: ein Satz beim Fangkorb, dass Einwürfe (Link, Hinweis, Kennung des Einwerfers, Sätze und Kennung der Destillierer) für alle angemeldeten Nutzer sichtbar sind.
- Nutzungsbedingungen: ein Satz, dass Einwürfe und Hinweise für alle angemeldeten Nutzer sichtbar sind und keine personenbezogenen Daten Dritter enthalten dürfen (deckt zugleich die Backlog-Lücke „Fangkorb nirgends erwähnt“).
- Keine neuen Löschfristen zusagen (`raw_inputs` werden nie gelöscht, siehe Audit).

## Nicht in v2

Anzeigenamen statt UUIDs · Punkte, Scoreboard, jede Belohnungsmechanik · Bilder im Share-Pfad · Rocket.Chat-Kanal · Kategorien/Labels für Einwürfe · Lock/Zuweisung · Verwerfen fremder Einträge.

## Beobachtungspunkte nach den ersten Nutzern (nicht bauen)

- Fremde Negativbeispiele kann nur der Einwerfer verwerfen. Stört das, kommt „Verwerfen für alle“ oder ein Notiz-Zustand.
- Vermischt der Seitentitel-Vorschlag die Hinweise so, dass die Beobachtung „was schreiben Leute rein“ nichts taugt, Vorschlag wieder raus.
- Was Leute ins Hinweis-Feld schreiben, entscheidet, ob es je Kategorien gibt.

## Reihenfolge und Abhängigkeiten

1. Fix-PR `fix/destillier-nachlese-v1` mergen.
2. Polish-PR `chore/nachlese-polish` mergen (fasst `.image-card`, Farben, `isMobile` an, die v2 auch braucht; sonst Konflikte). Voraussetzung laut eigener Regel: die zehn Einträge sind destilliert.
3. Erst dann v2-Branch von `main`.

**Aufwandsrahmen:** Backend (Migration, zwei Felder, Draft-Trigger, Link-Tabelle, Response-Erweiterung) ca. 2–3 h, Kartenansicht + Filter ca. 3–4 h, Formular + Destillier-Ansicht ca. 1,5 h, Rechtstext 0,5 h. Zusammen zwei bis drei Sessions. Ein PR mit getrennten Commits wie bei v1.

## Auftrag an den Agenten (Phase 1)

Read-only. Prüfen und melden:
1. Ist `raw_input_content_links` irgendwo beschrieben oder befüllt? Spaltenstand.
2. Wie ist `processed_by` heute gesetzt (welcher Pfad)? Wird `in_progress` wirklich nirgends geschrieben?
3. Liefert `getRawInputs` heute schon Drafts? In welcher Form?
4. Wo steht der Fangkorb in Datenschutzerklärung und Nutzungsbedingungen (Zeilen)?
5. Konfliktflächen mit `chore/nachlese-polish` (Dateiliste).
6. Aufwandsschätzung pro Block, dann **STOPP**.
