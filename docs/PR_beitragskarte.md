# Beitragskarte: eine Karte mit Varianten

**Stand:** Abschlussbericht nach Commit 7, Branch `feat/beitragskarte` auf `origin/main` `7f8ff9d` (Paket 2). Nicht gepusht.

**Worum es geht:** Die vier Ergebniskarten (Kommentar, Hintergrundinfo, Bild, Post) sind jetzt eine Komponente `app-beitragskarte`. Sie hat drei Varianten:

- **voll:** Suche und Teaser
- **kompakt:** Meine Beiträge
- **rohling:** Fangkorb

Mobil (≤ 599 px) zeigen Startseite und Suche eine Liste statt des Karussells. Meine Beiträge zeigt Karten statt einer Tabelle. Der Fangkorb zeigt Stapel aus Einwurf- und Satz-Karten.

## Commits

| # | Commit | Inhalt | Frontend (`ng test`) | Initial-Bundle |
|---|---|---|---|---|
| 1 | `fdb1714` | Meine Beiträge: Titel, Bildadresse und Nutzung fürs Backend | 328 * | 958,29 kB * |
| 2 | `4d9ca33` | KartenDaten und drei Adapter | 345 * | 958,29 kB * |
| 3 | `574466c` | `app-beitragskarte` (voll) und `app-karten-aktionen` | 400 * | 958,39 kB * |
| 4 | `67926f4` | Einbindung: Liste mobil, Karussell ab 600 px, Formular-Vorschau | 435 | 973,04 kB |
| – | `81c4680` | Karte: Kartencharakter zurück (Nachbesserung auf Wunsch, eigener Commit) | 436 | 973,06 kB |
| 5 | `859c744` | Meine Beiträge: kompakte Karten statt Tabelle | 442 | 972,73 kB |
| 6 | `95a878f` | Fangkorb: Rohling-Stapel und Dreischritt als Stepper | 444 | 972,41 kB |
| 7 | letzter Commit | Alte Karten, `BaseResultItemComponent` und Mixins entfernt | 404 | 972,41 kB |

\* Diese Zahlen stammen aus dem Lauf vor dem Rebase auf Paket 2. Nach dem Rebase lief die Suite auf Commit 4 (435) und auf jedem folgenden Commit.

Die Commits 1–6 wurden zweimal ohne interaktives Rebase neu aufgesetzt:
- einmal für den Engagement-Fix in Commit 3
- einmal für den `usage_count`-Fix in Commit 1

Beide Male unterschied sich der Endstand nur um den Fix. Einzeln getestet habe ich danach nur den gepatchten Commit 3 (400 grün); die übrigen neu aufgesetzten Commits sind im Frontend unverändert.

**Backend:** Commit 1 bringt 670 Tests grün, davon 5 neu. Nach dem Fix kamen 2 weitere dazu; die volle Suite steht unten unter „Tests“.

**Warum 404 nach Commit 7:** Mit den alten Karten gingen deren 40 Specs. 38 davon sind in Commit 3 portiert. Die 2 Tests zu `toggleNewBadge` entfallen, weil kein Template die Methode nutzte.

## Bundle: die „+8,65 kB“ gibt es nicht

Nach dem Rebase hatte ich meinen Build (973,04 kB) mit der Zahl aus dem PR-Text von Paket 2 (964,39 kB) verglichen. Das waren zwei Messungen unter unterschiedlichen Bedingungen.

Deshalb habe ich `origin/main` im selben Umfeld und mit denselben Einstellungen gebaut:

| Build | Initial total | Module im Initial-Bundle |
|---|---|---|
| `origin/main` (`7f8ff9d`) | **976,04 kB** | 855,32 kB |
| Branch nach Commit 7 | **972,41 kB** | 852,40 kB |

**Methode:** Beide Builds mit `--stats-json`. Initial ist alles, was von `main-*.js` und `polyfills-*.js` über statische Importe erreichbar ist.

**Ergebnis:**
- Kein Modul ist nur im Branch initial.
- Die Differenzen liegen nur in `@angular/common`, `@angular/material`, `@angular/core` und `@angular/animations`, und dort ist der Branch kleiner.
- Die Startseite wird weiter lazy geladen (`app.routes.ts:10`).
- Das Budget in `angular.json` musste ich nicht anheben. Es ist unverändert.
- Das Style-Budget von `beitragskarte.component.scss` liegt bei 7,81 kB. Das ist über der Warngrenze von 4 kB, aber unter der Fehlergrenze von 15 kB. Zum Vergleich: die alten Karten-Styles lagen bei 12–14 kB je Karte.

## Was sich je Commit geändert hat

### 1 · Contributions-Backend
- **`ContributionEntry(ContentDbEntry)`:** hat `title`, `image_url` und `usage_count`.
  - `get_by_author` liest über ein optionales `eintrag_modell`.
  - Die Nutzung kommt über `enrich_content_with_usage` hinzu.
- **Den Typfilter** hatte Paket 1 schon eingebaut. Er ist unverändert.
- **Nachbesserung:** Ältere Qdrant-Payloads enthalten `usage_count: null`. `ContributionEntry` scheiterte daran schon beim Lesen, die ganze Liste lieferte 500.
  - Gefunden habe ich das beim Screenshot-Test von Meine Beiträge.
  - Ein Validator macht jetzt aus `None` den Wert 0. Dazu kommen zwei Tests.

### 2 · KartenDaten und Adapter
- **Datei:** `beitragskarte/karten-daten.ts`
  - `ausSuchergebnis`: Suche, `/recent`, Formular-Vorschau
  - `ausBeitrag`: Meine Beiträge
  - `ausEinwurf`: Fangkorb, liefert 1 + n Karten
- **`autorName`** ist vorgesehen und bleibt `null`.
- **Zustand je Satz:** kommt aus `links[].draft_id`, nicht aus dem Einwurf-Status.
- **Links ohne passenden Satz** überspringt der Adapter (deine Entscheidung, umgesetzt in Commit 6).

### 3 · Komponente
- **`app-beitragskarte` (voll):** Aufbau der Karte
  - Kopf als Grid aus Symbol, Titel und Badges
  - Statement als Aufklapper im Fluss
  - Kurz/Mittel/Lang-Umschalter
  - Text gekürzt mit „mehr“, keine feste Höhe
  - Blöcke für Herkunft, Post und Bild
- **`app-karten-aktionen`:** Abstimmen, Kopieren und Melden, übernommen aus `BaseResultItemComponent`.
  - Mit `vorschau` bleibt die Leiste sichtbar, reagiert aber nicht: `pointer-events: none`, `aria-disabled` und `tabIndex -1` laufen über die MatButton-Inputs.
- **Selbst entschieden:**
  - Das Typsymbol steht als `emoji` in der Registry.
  - Die Zeile „Von: …“ steht immer da, als gekürzte Kennung.
  - Die Karte ist ein `article` statt `mat-card`.
  - Der Tooltip zur Antwortqualität ist typneutral formuliert.

### 4 · Einbindung
- **Mobil (≤ 599 px):** Startseite und Suche zeigen `app-kartenliste`.
  - Der mobile Karussell-Zweig ist entfernt, samt Swipe-Direktive, Punkten, Zähler und mobilen Pfeilen.
- **Desktop-Karussell:**
  - Karten kommen per Input, nicht mehr über das `RESULT`-Token.
  - Keine Mindesthöhe mehr, die Reihe gleicht sich per `align-items: stretch` an.
  - Pfeile auf halber Höhe, deutsch beschriftet.
  - Die Scroll-Listener werden beim Zerstören der Komponente jetzt wirklich entfernt.
- **Teaser:** 5 Beiträge.
- **Formular-Vorschau:** zeigt die Karte mit `vorschau`, gecacht über einen Getter.
- **`content-type-components.ts` ist entfallen.**

### Nachbesserung · Kartencharakter
Auf deine Vorgabe, danach amendet:
- **Kopf:** 16 px Innenabstand, Titel 19 px fett, höchstens 3 Zeilen (Bilder 4), Mindesthöhe 2 Zeilen, im Karussell 3; Emoji 28 px.
- **Körper:** 16 px Innenabstand, Text 15 px.
- **Karte:** Radius 12 px, weicher Schatten.
- **Liste:** auf `--kartenliste-bg` (#f4f4f2).
- **Umschalter:** mobil ausgeblendet, am Desktop „Kurz / Mittel / Lang“.

### 5 · kompakt
- **Aussehen:** gleiche Optik wie voll, nur kleiner.
  - Kopf mit Typfarbe, Titel 16 px auf 2 Zeilen
  - nur der Nutzungs-Badge, darunter das Datum
  - keine Autorzeile, keine Aktionen
- **Tippen:** Die ganze Karte ist antippbar und öffnet `/result?searchQuery=<Titel>`, ohne Titel mit dem Text.
- **Meine Beiträge:**
  - Liste mobil, Raster ab 600 px, das Layout macht CSS
  - Server-Paginator bleibt
  - `isMobile` und die 768-px-Grenze sind raus
- **Spec:** mit 6 Tests. Der Paginator-Test von Paket 1 bleibt, die Tabellen-Tests sind ersetzt.

### 6 · rohling und Fangkorb-Kopf
- **Stapel je Einwurf:**
  - **Einwurf-Karte oben:** gestrichelte Kante, grauer Kopf, Plattform-Chip, Link, Hinweis in der globalen `.hinweis-box` (3 Zeilen), „eingeworfen von“
  - **Satz-Karten eingerückt darunter:**
    - destilliert: durchgezogene Kante, grau, Satz im Titelfeld, „destilliert von“
    - ausformuliert: Typfarbe, „destilliert von · ausformuliert von“, Knopf „In der Suche anzeigen“
  - **Tippen:** Beide Kartenarten öffnen `/destillieren/:id`.
  - **Verworfen:** Deckkraft 0,55, nicht antippbar, auch die Sätze darunter nicht.
  - **Links und Knöpfe** in Karten laufen weiter über `stopPropagation`.
- **Kopf:**
  - Dreischritt als Stepper: drei gleich breite Spalten, Emoji 24 px über dem Wort in 12 px, dazwischen `chevron_right` 16 px grau
  - `help_outline` 20 px, ohne Knopfrahmen und Schatten, klappt die Langfassung auf
  - Chip-Zeile und FAB unverändert
- **Herkunftsmarker `INGESTED`:** ⚙️ statt 📥.
- **Specs:** Der Fangkorb-Spec hatte nach Paket 2 30 Tests, nicht 22 wie im Phase-1-Bericht. Jetzt sind es 32: Stepper-Spalten und Tippen auf die Satz-Karte sind dazugekommen.
- **Selbst entschieden:** Die Fangkorb-Liste liegt wie die anderen Listen auf `--kartenliste-bg`.

### 7 · Aufräumen
- **Gelöscht:** die vier Kartenordner mit ihren Specs, `BaseResultItemComponent`, `_result-item-base.scss` und die toten Vorschau-Regeln in den Formular-SCSS.
- **`CONTENT_MODEL.md`:** §2 beschreibt jetzt die eine Karte mit Varianten, dazu Vertragstabelle und „Adding a new type“. Der historische Schritt 3 hat einen Hinweis bekommen.
- **Doc-Verweise umgestellt:** `DATENSCHUTZ_BESTANDSAUFNAHME.md` und `RECHTSTEXTE_LUECKEN.md` zeigen auf `beitragskarte.component.html` (Bild `:121`, „Von:“ `:174`).
  - Neu vermerkt ist dort: Die Karte kürzt die Kennung auf 8 Zeichen, über die API geht weiter die volle.
- **Nicht angefasst:**
  - `add-commentary.component.css` und `add-generictext.component.css` hängen an keiner Komponente, die Formulare binden die `.scss` ein. Sie enthalten noch Regeln für die alten Karten. Die Dateien stammen nicht aus diesem Paket.
  - `listAnimation` in `shared/animations.ts` ist ohne Nutzer.

## Tests

- **Frontend:** 404 grün, 11 übersprungen. Dazu wie oben: Commit 4 lief auch mit 390 px Fensterbreite grün.
- **Backend (`pytest` aus `app/`):** 672 grün, 11 übersprungen (670 aus Commit 1 plus 2 Tests zum `usage_count`-Fix).
- **Headless-Chrome gegen den Dev-Stack** (Branch-Build statisch ausgeliefert, `/api` ans BFF):

| Seite | 360 px | 1280 px |
|---|---|---|
| `/search` | Liste mit 5 Karten, 328 px breit, 293–434 px hoch, kein Überlauf | Karussell, gleiche Höhe pro Reihe |
| `/result?searchQuery=…` | 10 Karten | 2 Karussells mit je 10 Karten |
| `/workflow/add-generictext` | – | Vorschau-Karte 450 px breit |
| `/fangkorb` | Stepper: Spalten je 83 px, „Ausformulieren“ 79 px, Kopf 46 px hoch, also eine Reihe. 12 Stapel, 10 Satz-Karten | – |
| `/contributions` | im Dev-Stack 500 (siehe unten) | im Dev-Stack 500 |

## Bitte prüfen

**Voraussetzung für Meine Beiträge:**
- Das Backend im Dev-Stack stammt aus dem Reset vom 14.09., vor dem `usage_count`-Fix.
- `/contributions` liefert dort 500, bis das Backend neu gebaut ist (`../cg-beitragskarte/mvp/run-local.sh reset`, behält die Volumes).
- Das habe ich nicht ausgeführt.

Das Frontend kommt über `ng serve` auf `127.0.0.1:4201`. Direktanmeldung: `test.user@example.com`.

1. **`/search`, „Frisch aus der Community“**
   - Karten auf grauem Grund, 16 px Rand
   - Titel fett, höchstens 3 Zeilen
   - kein Kurz/Mittel/Lang mobil, „mehr“ bei langem Text
2. **`/result?searchQuery=Klimaschutz`**
   - Liste unter den Tabs
   - Aussage aufklappen schiebt den Inhalt nach unten
   - Daumen, Kopieren (die Nutzung zählt hoch), Menü
3. **Gerät drehen oder über 600 px:** Das Karussell erscheint, die Pfeile sitzen auf halber Höhe, am Desktop gibt es Kurz/Mittel/Lang.
4. **`/contributions`** (nach dem Backend-Reset)
   - kompakte Karten mit Typfarbe, Titel auf 2 Zeilen, Nutzung, Datum
   - Tippen öffnet die Suche
   - Raster ab 600 px, deutscher Paginator
5. **`/fangkorb`**
   - Stepper in einer Reihe bei 360 px, Hilfe-Icon ohne Rahmen klappt die Erklärung auf
   - Einwurf gestrichelt, Sätze eingerückt
   - Tippen auf einen Satz öffnet das Destillieren
   - Link in der Karte öffnet nur den Link
   - „In der Suche anzeigen“ öffnet nur die Suche
   - verworfen abgedimmt und nicht antippbar
6. **`/workflow/add-commentary`, `/workflow/add-image`:** Die Vorschau sieht aus wie in der Suche, die Knöpfe reagieren nicht.
7. **Emojis** im Kartenkopf und Stepper erscheinen als Symbol. Headless-Chrome zeigt dort Kästchen, das ist kein Fehler der App.

## Nicht in diesem Paket

- Detailansicht `/beitrag/:id`: Die Übergänge über die Suche bleiben.
- Anzeigenamen: nur das Feld `autorName`.
- Post-Add-Form, Karten für Aussage und Herkunft.
- BreakpointService, Kacheln der Beitragen-Seite.
- Bearbeiten und Löschen aus kompakt.
- Außerdem gesehen, nicht angefasst:
  - Anonyme Suche leitet auf `/login` um, weil das Anlegen der Suchaussage 401 liefert.
  - Im Dev-Schema fehlt die Spalte `search_events.actor_hash`.
