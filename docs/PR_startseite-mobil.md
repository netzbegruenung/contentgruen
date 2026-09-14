# PR: Startseite und Einstieg mobil (UI-Nachlese Paket 2)

**Branch:** `feat/startseite-mobil` (von `origin/main` @ f765136)
**Compare:** https://github.com/netzbegruenung/contentgruen/compare/main...feat/startseite-mobil?expand=1
**Vorgeschlagener Titel:** Startseite und Einstieg mobil: Suche im Hero, zwei Kacheln, kompakte Formulare, Version im Footer

Grundlage: Bericht „UI-Nachlese mobil – Analyse gegen origin/main“, Punkte 13–15. Erster Wurf ohne
Pixel-Feinschliff; nachgeschliffen wird am Handy mit `ng serve`. Mobil-Grenze für alles Neue: 599 px.

Nicht in diesem PR: Kartenhöhen, Karussell, Suchergebnisse, Meine Beiträge, Fangkorb-Karten,
Zähler offener Einwürfe, Avatar, Anzeigenamen. `result-view`, `recent-content`, `contributions-view`
und der Kartenteil von `raw-input-list` sind unberührt.

## Prüfstand

- `ng test`: nach jedem Block grün, zuletzt **354 SUCCESS** (11 skipped).
- `ng build` (production): Initial total **964,39 kB** (Warngrenze 1 MB). Die Style-Budget-Warnungen
  gab es schon vorher; `contribute-view.component.css` ist dabei von 4,96 auf 4,82 kB geschrumpft.
- Gemessen im Headless-Chrome bei **360×740**, mobil, angemeldet als `testuser`. Angegeben ist die
  Unterkante des Elements in px, der Bildschirm endet bei 740:

  | Route | Ziel | Unterkante |
  |---|---|---|
  | `/search` | Suchen-Knopf / zweite Kachel | 333 / 566 |
  | `/einwerfen` | Einwerfen-Knopf | 567 |
  | `/contribute` | vierte Typ-Zeile | 504 |
  | `/fangkorb`, erstes Öffnen | Filterleiste (Langfassung offen) | 645 |
  | `/fangkorb`, zweites Öffnen | Filterleiste | 418 |

- E end-to-end: Frontend-Image mit `--build-arg GIT_SHA=<40 Zeichen>` gebaut und `replace-env.sh`
  laufen lassen. Der SHA steht danach im Bundle, kein `${GIT_SHA}` bleibt übrig.

## A. Startseite (`search-view`, `about-teaser`, `_hero-styles`)

**Geändert**
- Titel, Untertitel, Suchfeld mit Suchen-Knopf und eine kleine Zeile „Beispiel probieren“ bilden
  einen Block. Der Drei-Schritte-Satz mit Emojis, der gelbe Block „Suchen“ und sein Erklärtext sind weg.
- Die Statistik-Kacheln sind samt `getGenericTextCount`, `contentCount$`, `contentStats$` und dem
  `MetricsService`-Aufruf entfernt.
- Statt der Beitragen-Spalte gibt es zwei gleich große Kacheln, mobil untereinander:
  „Einwerfen“ → `/einwerfen` und „Beitrag verfassen“ → `/contribute`. Beide ohne Zähler.
- About-Teaser: ein Absatz, parteineutral („Menschen, die politische Debatten besser führen
  wollen“), Porträt 48 px neben Name und Rolle, Knopf bleibt. Zitat und „Kontakt aufnehmen“ sind raus.

**Selbstentscheidungen**
- Als Untertitel bleibt „Gemeinsam stark: Bewährte Argumente aus der Community.“
- Die Kacheln sind schlichte `routerLink`s, auch für Nicht-Angemeldete. Der `AuthGuard` leitet dann
  zum Login mit `returnUrl` und danach zurück. Das ersetzt den eigenen Knopf „Anmelden zum Beitragen“.
  Dadurch sind `AuthService`, `userInfo`, `login()`, `loginToContribute()` und
  `navigateToContribute*()` in der Komponente unbenutzt und gelöscht.
- Neue Konstante `FANGKORB_KURZ` („Ein Link, ein Hinweis oder beides – roh, ohne Ausarbeiten.“).
  `FANGKORB_BESCHREIBUNG` wird daraus zusammengesetzt, damit die beiden nicht auseinanderlaufen.
- Satz der Verfassen-Kachel: „Ausgearbeitet und direkt verwendbar: Kommentar, Hintergrundinfo oder
  Bild.“ Die Typnamen kommen aus `typLabel()`.
- `MetricsService` bleibt bestehen, weil das Admin-Dashboard ihn nutzt.
- Hero-Abstände: `gap 30` und `margin-top 32` standen in `search-view.component.scss`. Die Datei ist
  neu geschrieben, mobil gelten jetzt 12/16 px. In `_hero-styles.scss` ist `.hero-value-proposal`
  mobil von 20 auf 12 und `.compact-intro` von 15 auf 12 gesetzt, die Grenze von 600 auf 599. Beide
  Klassen nutzt die Startseite nicht mehr; sie bleiben für andere Seiten in der geteilten Datei.
- Der Teaser-Knopf behält seinen Text „Mehr über Gut gesagt erfahren“.

## B. Einwurf-Infokarte (`add-raw-input`)

**Geändert**
- Kopf: padding 16, Icon 28 px, Beschreibung 14 px. Die Beschreibung braucht bei 360 px drei Zeilen.
- Hinweisfeld: `cdkTextareaAutosize`, `cdkAutosizeMinRows=2`, `cdkAutosizeMaxRows=8`.
- Consent-Text: eine globale Klasse `.submit-hint` in `styles.css` mit `font-size: 0.85em`, gleicher
  Zeilenhöhe und Farbe. Einwurf, Kommentar, Hintergrundinfo und Bild nutzen sie.

**Selbstentscheidungen**
- `.submit-hint` gab es schon, aber nur komponentenlokal: im Mixin `_contribution-form.scss` und als
  Kopie in `add-image`. Die Schrift ist jetzt global. Abstände und Trennlinie bleiben lokal, weil sie
  sich je Formular unterscheiden. Das Einwurf-Formular hieß vorher `.einwurf-hinweis` (14 px).
- Zusätzlich zur Vorgabe: Titel der Infokarte 20 → 18 px (mobil 16), Formular-Abstand mobil 12.

## C. Beitragen-Typkarten (`contribute-view`)

**Geändert**
- Mobil eine kompakte Zeile je Typ: Emoji links, Titel und ein Satz, Pfeil rechts. Unter 600 px gelten
  padding 12/16, Abstand 12, Emoji 28 px. Alle vier passen auf einen Bildschirm. Desktop ist unverändert.
- Einleitung: „Wähle, was du beitragen willst:“, auf Desktop und mobil gleich.
- Fangkorb: Der Desktop-Knopf heißt „Einwerfen“ und führt wie die mobile Zeile zu `/einwerfen`.
- `rgb(230, 240, 210)` in `.commentary-color` und als Startwert des Kommentar-Verlaufs ersetzt durch
  `var(--commentary-bg)`. Der Wert ist identisch.

**Selbstentscheidungen**
- Die mobile Ansicht hängt weiter an `BreakpointService.isMobile$`, also bis 768 px, weil der
  Formularwechsel daran gebunden ist. Die Zeilen erscheinen deshalb bis 768 px. Die Maße aus der Vorgabe
  gelten unter 600 px; zwischen 600 und 768 sind die Zeilen etwas größer (padding 16/20, Emoji 32) und
  höchstens 600 px breit.
- Die mobile Fangkorb-Zeile heißt „Einwerfen“ (vorher „Schnell einwerfen“), wie die Startseiten-Kachel.
  Eine eigene CTA-Beschriftung gibt es in der Zeile nicht; die ganze Zeile ist der Knopf.
- `mat-card` ist mobil durch native `<button>`s ersetzt (Tastatur und Fokus ohne eigene Handler),
  `MatCardModule` ist entfernt.
- Die Fangkorb-Farben (`rgb(245, 238, 215)` …) haben keine Theme-Variable und bleiben literal.

## D. Fangkorb-Kopf (`raw-input-list`, nur oberhalb der Karten)

**Geändert**
- Eine Zeile „Einwerfen → Destillieren → Ausformulieren“, darunter „Jeder Schritt kann von jemand
  anderem kommen.“ Die Langfassung (die drei Schritte mit Erklärung) klappt über „So funktioniert es“
  auf und zu.
- Plattform-Chips: ungewählt in der Default-Optik, gewählt gefüllt. Sind alle Plattformen aktiv, gibt
  es keinen Filter und kein Chip ist gefüllt – wie „nur offene“ im Ruhezustand.
- „Etwas einwerfen“ unter 600 px in voller Breite.
- `ERSTNUTZER_SATZ` in `fangkorb-texte.ts`: Er steht unter dem Kopf, nur für Angemeldete, und auf der
  Beitragen-Seite über „Wähle, was du beitragen willst:“.

**Selbstentscheidungen**
- „Nach dem ersten Aufklappen eingeklappt“ habe ich so gelesen: Beim ersten Öffnen des Fangkorbs in
  der Sitzung ist die Langfassung offen, bei jedem weiteren zu (sessionStorage
  `contentgruen.fangkorb.erklaerung-gesehen`). Ist kein Storage verfügbar, bleibt sie zu, sonst stünde
  sie jedes Mal offen.
- Chip-Verhalten: Weil „alle aktiv“ jetzt ungefüllt aussieht, hieße ein Tipp als Abwählen, dass die
  anderen Chips gefüllt aufleuchten. Deshalb ist es eine Auswahl: Ohne Filter wählt ein Tipp genau diese
  Plattform. Mit Filter nimmt ein Tipp eine Plattform dazu oder weg. Wird die letzte abgewählt, gilt
  wieder kein Filter. `aria-pressed` folgt der Füllung. Die Tests dazu sind angepasst.
- „Angemeldet“ heißt hier: Die eigene Kennung ist bekannt, also die Quelle, die auch „nur meine“ nutzt.
  Auf `/contribute` gibt es keine eigene Prüfung, weil die Route ohnehin den `AuthGuard` hat.
- Der Satz steht unter dem Knopf „Etwas einwerfen“. Der Schlusssatz der Langfassung ist gekürzt auf
  „Alle sehen alles. Tippe auf eine Karte, um weiterzumachen.“, weil der erste Teil jetzt in der Kurzzeile steht.

## E. Version im Footer

**Geändert**
- `package.json` (und `package-lock.json` per `npm version`) auf **1.1.0**.
- Footer: eigene Zeile unter den Links, rechtsbündig, 11 px, grau: `v1.1.0 · <sha7>`.
- `Dockerfile`: `ARG GIT_SHA=dev` und `ENV GIT_SHA` in der nginx-Stage. `replace-env.sh` ersetzt
  `${GIT_SHA}`. `build.yml` und `release.yml` übergeben `build-args: GIT_SHA=${{ github.sha }}`.
- `environment.prod.ts`: `gitSha: '${GIT_SHA}'`. Die Dateien docker, local und template: `gitSha: 'dev'`.

**Mechanik: `replace-env.sh` statt Ersetzung beim Build – Begründung**
- Keine neue Datei und kein neuer Pfad. Es ist derselbe Platzhalter-Mechanismus, den `API_BASE_URL`
  und `USE_KEYCLOAK` schon nutzen, mit einer zusätzlichen `sed`-Zeile.
- Eine Ersetzung beim Build hätte mehr Neues gebraucht: entweder `define` in `angular.json` plus eine
  globale Deklaration plus einen Fallback für Karma, wo `define` nicht greift, oder einen `sed`-Schritt
  in der Build-Stage mit eigener Platzhalter-Konvention.
- Das `ARG` steht spät in der nginx-Stage. Ein neuer SHA baut deshalb nur die letzten Layer neu, nicht
  `npm install` und `ng build`.
- Grenzen: `GIT_SHA` ist eine `ENV` im Image und ließe sich beim Containerstart überschreiben; das halte
  ich für harmlos. Nur Docker-Images bekommen den SHA. `ng serve` und `ng build` ohne Container zeigen
  `dev`, ebenso ein unersetzter Platzhalter (`buildKennung()`).

**Selbstentscheidungen**
- Die Version wird per `import paket from '../../../package.json'` gelesen, dafür steht
  `resolveJsonModule` in `tsconfig.json`. Es ist ein **Default**-Import, weil der Karma-Builder (webpack)
  benannte JSON-Importe ablehnt. Folge: Das ganze `package.json` (~1 kB, mit Abhängigkeitsliste) liegt
  im Main-Bundle. Das Repo ist öffentlich, geheim ist daran nichts. Wer das nicht will, braucht eine
  generierte Versionsdatei – das wäre ein neuer Pfad.
- Lokale, nicht eingecheckte `environment.ts` ohne `gitSha` kompilieren weiter; der Footer liest das Feld optional.

## F. Plattform-Mapping (`shared/plattform.ts`, `fangkorb-filter.ts`)

**Geändert**
- `threads.net`/`threads.com` → Threads, `x.com`/`twitter.com` → X, `bsky.app` → Bluesky.
  Subdomains zählen mit (`mobile.twitter.com`). Mastodon bleibt Web.
- Modulkommentar: Zweck ist ein Herkunfts-Tag, nicht mehr „braucht ein Konto“.
- Gespeicherter Filter: `filterSpeichern` legt zusätzlich `bekannte` ab, also die Plattformen beim
  Speichern. `filterLaden` behandelt jede Plattform, die der gespeicherte Filter nicht kannte, als aktiv.

**Selbstentscheidungen**
- Filter der Vorversion haben kein `bekannte`. Für sie gelten Instagram, YouTube, TikTok und Web als
  bekannt, Threads, X und Bluesky werden also eingeblendet.
- Chip-Reihenfolge: Instagram, YouTube, TikTok, Threads, X, Bluesky, Web.
- Sieben Plattform-Chips plus zwei Filter ergeben bei 360 px drei Chip-Reihen (im Headless-Screenshot gesehen).
  Kandidat zum Nachschleifen.

## Am Handy mit `ng serve` anschauen

Hinweis zum Aufsetzen: CORS im Dev-Stack erlaubt nur den Frontend-Port 8080. Mit `ng serve` auf 4200
gegen das BFF auf 5054 scheitern die API-Aufrufe. Gemessen habe ich mit `baseUrl: ''` in der lokalen
`environment.ts` und einer Proxy-Konfiguration für `/api`, `/login`, `/content`, `/recent`,
`/getMetrics`, `/report` und `/reports` auf `http://localhost:5054`. Die Worktree-`environment.ts`
steht wieder auf dem Ausgangswert.

1. `/search` – abgemeldet und angemeldet: Suchfeld, Beispielzeile, beide Kacheln über dem Falz;
   Kachel antippen (abgemeldet → Login → zurück); weiter unten der About-Teaser.
2. `/einwerfen` – Infokarte in drei Zeilen, Hinweisfeld wächst beim Tippen bis acht Zeilen,
   Einwerfen-Knopf ohne Scrollen; auch über Teilen (`/teilen`) mit vorbelegtem Hinweis.
3. `/contribute` – Erstnutzer-Satz, Einleitung, vier Zeilen; jede antippen
   (Einwerfen → `/einwerfen`, die anderen öffnen das Formular).
4. `/contribute?form=commentary`, `…=generictext`, `…=image` – Consent-Text in 0.85em über der Knopfleiste.
5. `/fangkorb` – zweimal öffnen (erst Langfassung offen, dann zu), aufklappen/zuklappen, Chips
   durchtippen (eine wählen, zweite dazu, alle abwählen → ungefüllt), „Etwas einwerfen“ volle Breite.
6. Footer auf einer beliebigen Seite – `v1.1.0 · dev` rechts unten.
7. Desktop kurz gegenprüfen: `/search` (Kacheln nebeneinander) und `/contribute` (Fangkorb-Knopf „Einwerfen“).
