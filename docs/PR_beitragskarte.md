# Beitragskarte: eine Karte mit Varianten

**Branch:** `feat/beitragskarte`, Basis `main` `7f8ff9d`.

Die vier Ergebniskarten (Kommentar, Hintergrundinfo, Bild, Post) sind jetzt eine Komponente `app-beitragskarte` mit drei Varianten:

- **voll:** Suche, Teaser auf der Startseite, Formular-Vorschau und das Bottom Sheet in Meine Beiträge
- **kompakt:** Meine Beiträge als Album
- **rohling:** Fangkorb

Mobil (≤ 599 px) zeigen Startseite und Suche eine Liste statt des Karussells. Meine Beiträge ist ein Album aus hochkanten Karten. Der Fangkorb zeigt Stapel aus Einwurf- und Satz-Karten.

## Commits

| Commit | Inhalt |
|---|---|
| `fdb1714` | Meine Beiträge: Titel, Bildadresse und Nutzung im Backend |
| `4d9ca33` | `KartenDaten` und drei Adapter |
| `574466c` | `app-beitragskarte` (voll) und `app-karten-aktionen` |
| `67926f4` | Einbindung: Liste mobil, Karussell ab 600 px, Formular-Vorschau |
| `81c4680` | Kartencharakter: Innenabstände, Titelgröße, Radius, Schatten |
| `859c744` | Meine Beiträge: kompakte Karten statt Tabelle |
| `95a878f` | Fangkorb: Rohling-Stapel und Dreischritt als Stepper |
| `0cec24c` | Alte Karten, `BaseResultItemComponent` und Mixins entfernt |
| `7c58deb` | Meine Beiträge als Album, Sortierung neueste zuerst |
| letzter Commit | Nach Review: Bottom Sheet statt Suche, Paginator-Status, robuste Autor-Sortierung, Doku-Verweise |

## Die Karte

- **Kopf:** Grid aus Typ-Symbol (aus der Registry), Titel und Badges. Titel 19 px fett, höchstens 3 Zeilen, Bilder 4.
- **Inhalt:** Statement als Aufklapper im Fluss, Kurz/Mittel/Lang am Desktop, Text gekürzt mit „mehr“, Blöcke für Herkunft, Post und Bild. Keine feste Höhe.
- **Fuß:** `app-karten-aktionen` (Abstimmen, Kopieren, Melden) und „Von: …“ mit gekürzter Kennung. In der Formular-Vorschau ist die Leiste sichtbar, reagiert aber nicht.
- **Nutzungs-Badge:** schreibt „3×“ auf allen Karten.
- **Typnamen** kommen aus der Registry (`typLabel`), die Ketten-Symbole aus `KETTEN_ICONS`.

## Meine Beiträge als Album

- **Raster:** 2 Spalten, 3 ab 600 px, 4 ab 960 px, 12 px Lücke, direkt auf dem Seitengrund.
- **Statistik:** eine Textzeile über dem Raster, „30 Beiträge · 171× genutzt“. Hinweisbox und Kacheln entfallen.
- **Karte (kompakt):** mindestens 150 px hoch, Schatten und Radius wie die übrigen Karten.
  - Kopfband mit Typ-Symbol. Hat der Beitrag ein Bild, füllt es das Band (`object-fit: cover`, lazy, `alt` aus dem Titel), das Symbol liegt klein unten links darauf. Die Bandhöhe bleibt gleich.
  - Titel 15 px fett und Anriss 13 px, je höchstens 2 Zeilen mit Auslassung.
  - Fuß: Datum links, Nutzung rechts, bei 0 dezent.
  - Keine Aktionsleiste. Die ganze Karte ist antippbar.
- **Tippen:** öffnet den Beitrag als volle Karte in einem Bottom Sheet, mit Aktionsleiste und Herkunft. Schließen per Wisch nach unten, Klick außerhalb oder Escape. Es wird keine Suche mehr gestartet und damit keine Suchaussage angelegt.
- **Paginator:** 24 pro Seite, erst ab 25 Beiträgen sichtbar, mobil ohne Seitengröße. Er liegt außerhalb des Ladezweigs und hat `pageIndex` und `pageSize` gebunden, damit der Seitenstand über das Nachladen erhalten bleibt.

## Backend

- **`ContributionEntry`** trägt `title`, `image_url`, `usage_count` und `references`. `usage_count: null` und Herkunft als JSON-Text aus älteren Payloads werden beim Lesen umgewandelt.
- **`getContributionsOfUser`**
  - löst die Herkunft auf (Adresse und Beschreibung), wie `/content/recent`
  - trägt die Nutzung aus PostgreSQL nach; ist die Datenbank nicht erreichbar, kommt die Liste trotzdem, mit `usage_count` 0 und einer Warnung im Log
- **`get_by_author`**
  - holt alle Punkte der Person, validiert jeden einzeln und überspringt ungültige mit einer Warnung, statt die ganze Liste mit 500 scheitern zu lassen
  - sortiert danach nach `created`, neueste zuerst, und schneidet erst dann die Seite. Ist `created` null oder kein Text, sortiert der Punkt ans Ende.
  - Qdrant scrollt ohne `order_by` in ID-Reihenfolge, und `order_by` bräuchte einen Payload-Index auf `created`. Die Sortierung im Speicher lädt pro Anfrage alle Beiträge der Person; bei der heutigen Menge unkritisch.
  - `get_count_by_author` zählt übersprungene Punkte weiter mit. Die Gesamtzahl kann also um die Zahl kaputter Punkte höher sein als die Liste.
- **Deploy:** Wirksam erst mit neu gebautem Semantic-Image. Die Suche braucht außerdem #44 (`usage_count` für Bild und Post), sonst antwortet `searchByText` mit 500, sobald ein Bild im Index liegt.

## Fangkorb

- **Stapel je Einwurf:** Einwurf-Karte oben (gestrichelt, Plattform-Chip, Link, Hinweis), Satz-Karten eingerückt darunter (destilliert grau, ausformuliert in Typfarbe mit „In der Suche anzeigen“).
- **Tippen** öffnet `/destillieren/:id`. Verworfene Einwürfe sind abgedimmt und nicht antippbar.
- **Kopf:** Dreischritt als Stepper, Hilfe-Icon, FAB und eine Chip-Zeile aus `main`.

## Aufgeräumt

- Die vier alten Kartenordner mit Specs, `BaseResultItemComponent`, `_result-item-base.scss`, die Swipe-Direktive und `content-type-components.ts`.
- Tote Selektoren auf `app-*-result-item` in `add-commentary.component.css` und `add-generictext.component.css`, die ungenutzte `listAnimation`.
- **Doku:**
  - `DATENSCHUTZ_BESTANDSAUFNAHME.md` und `RECHTSTEXTE_LUECKEN.md` zeigen auf die aktuellen Zeilen in `beitragskarte.component.html` und vermerken die zwei `<img [src]>`-Stellen (volle Karte und Album-Kopf).
  - `ISSUE_destillier-nachlese.md` verweist nicht mehr auf gelöschte Dateien.
  - `CONTENT_MODEL.md` beschreibt die eine Karte mit Varianten.

## Tests und Bundle

- **Frontend (`ng test`):** 416 grün
- **Backend (`pytest` aus `app/`):** 678 grün, 11 übersprungen
- **Initial-Bundle:** 972,43 kB, Budget in `angular.json` unverändert. `beitragskarte.component.scss` liegt mit 8,68 kB über der Warngrenze (4 kB), unter der Fehlergrenze (15 kB). Der Chunk von Meine Beiträge ist mit Bottom Sheet 26,8 kB groß.

## Bitte prüfen

Direktanmeldung mit einem Testkonto, dann:

1. **`/search`:** Karten in einer Liste (mobil) bzw. im Karussell (ab 600 px), Titel fett, „mehr“ bei langem Text, am Desktop Kurz/Mittel/Lang.
2. **`/result?searchQuery=Klimaschutz`:** Aussage aufklappen, Daumen, Kopieren (die Nutzung zählt hoch), Menü.
3. **`/contributions`**
   - 2/3/4 Spalten bei 360/600/960 px, Statistikzeile, Bild im Kopfband
   - Karte antippen: Bottom Sheet mit voller Karte und Herkunft; Wisch nach unten und Klick daneben schließen es
   - bei mehr als 24 Beiträgen zweimal „Weiter“: Seite 3, mobil ohne Seitengröße
4. **`/fangkorb`:** Stepper in einer Reihe bei 360 px, Tippen auf einen Satz öffnet das Destillieren, Links in Karten öffnen nur den Link.
5. **`/workflow/add-commentary`, `/workflow/add-image`:** Vorschau wie in der Suche, Knöpfe reagieren nicht.

## Nicht in diesem Paket

- Detailansicht `/beitrag/:id`
- Anzeigenamen (nur das Feld `autorName`)
- Karten für Aussage und Herkunft, Post-Formular
- Bearbeiten und Löschen aus Meine Beiträge
