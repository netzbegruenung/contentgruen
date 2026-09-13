# UI-Nachlese mobil, Paket 1

Branch `fix/ui-nachlese-paket1` von `origin/main` (`76055b4`). Grundlage ist die Analyse
„UI-Nachlese mobil – Analyse gegen origin/main“. Ein Commit je Block A bis H.

Nicht in diesem PR: Statistik-Kacheln (Zahlen und Berechnung), Startseiten-Umbau, Kartenhöhen,
Karussell, Erstnutzer-Satz, Footer-Version, Plattform-Mapping (Threads/X/Bluesky), Zähler offene
Einwürfe, Avatar.

## A. Rechtstexte mobil

- `app.component.css`: Die Media-Query, die `app-footer` unter 960 px ausblendete, ist entfernt.
  Der Footer steht auf allen Breiten.
- `footer.component.css`/`.html`: `white-space: nowrap` ist weg. Unter 600 px stehen die Angaben
  untereinander, die Trennstriche (`.trenner`, `aria-hidden`) sind dort ausgeblendet.
- `mobile-menu`: Impressum, Datenschutz und Nutzungsbedingungen sind `RouterLink`s, die danach
  `close()` aufrufen – gleiche Optik wie „Hilfe“ (`mat-button`, `mobile-menu-item`). Der Link
  „Sebastian Banach“ zeigt auf `/about` ohne `target="_blank"`.
- Geprüft, nicht geändert: `/impressum`, `/datenschutz` und `/nutzungsbedingungen` haben den
  `PublicGuard` (`app.routes.ts:92-106`), der immer `true` liefert (`auth/public.guard.ts:20-38`).
  Sie sind also ohne Login erreichbar.

Selbstentscheidungen:
- Die Grenze für die gestapelte Footer-Darstellung ist 599 px, passend zur `isMobile`-Grenze der
  App-Shell.
- Icons im Menü: `info` (Impressum, wie bisher), `privacy_tip`, `gavel`.
- Die Rechtstexte stehen im Menü auch ohne Anmeldung.

## B. Umschreibungen und Tippfehler

- Einwurf-Formular: später, Einwürfe, für, nächsten, können. Beitragen-Seite: später (zweimal).
- An den berührten Stellen ersetzt der Gedankenstrich „–“ den Bindestrich im Fließtext.
- „Hintergundinfo“ → „Hintergrundinfo“ (Tooltip der Hintergrundinfo-Karte).
- Backend `api/v1/raw_input.py`: „Dafür musst du angemeldet sein.“ und „Der Status konnte nicht
  geändert werden.“
- `share-target-debug` ist nicht angefasst.

Hinweis: Die beiden Beschreibungstexte auf der Beitragen-Seite ersetzt Block F danach ohnehin
durch die gemeinsame Konstante.

## C. Typnamen aus der Registry

- `shared/content-type-registry.ts`: Das `label`-Feld ist die einzige Quelle. commentary →
  Kommentar, generic_text → Hintergrundinfo, image → Bild, post → Post, dazu neu statement →
  Aussage und reference → Herkunft (nur Label, ohne Karte). `typLabel(type)` ist exportiert,
  versteht beide Schreibweisen (`generic_text`/`generictext`) und gibt einen unbekannten Typ
  unverändert zurück.
- Umgestellt auf `typLabel`: `app.constants.ts` (PAGE_TITLES.COMMENTARY/GENERIC_TEXT),
  `destillieren.component.ts` (Typwahl), `contribute-view.component.html` (mobile Kartentitel),
  Karten-Tooltips aller vier `*-result-item.html`, `content-moderation.component.ts`,
  `search-view.component.html`, `contributions-view.component.html` (Typspalte).
- Für `resolveResultComponent` sind Aussage und Herkunft registrierte Typen ohne Karte. Sie
  fallen still auf die Kommentarkarte zurück; die Warnung bleibt für unbekannte Formen.
- Sichtbare Texte „Quelle“/„Quellen“ heißen jetzt Herkunft: Kommentar- und
  Hintergrundinfo-Karte („Keine Herkunft hinterlegt“, „Herkunft 1“), die beiden
  Beitragsformulare („+ Herkunft“, „Herkunft (optional)“, Tooltip, Platzhalter) und
  `reference-input.component.html`.

**Abweichung vom Auftrag – Registry in zwei Dateien.** Mit den Karten-Komponenten in der Registry
zieht der Import von `typLabel` in `app.constants.ts` (über `RouteConfigService` in der App-Shell)
alle vier Karten ins initiale Bundle: gemessen 956,60 kB → 1,13 MB, über der 1-MB-Warngrenze aus
`angular.json`. Deshalb:
- `content-type-registry.ts` führt key, icon, label, resultField und importiert keine Komponenten.
- `content-type-components.ts` (neu) enthält `RESULT_COMPONENTS` und `resolveResultComponent`.
  `recent-content` und `result-view` lesen von dort.
- Ergebnis: initiales Bundle 958,04 kB. Nebenbei entfällt ein Importzyklus: Karten → Registry →
  Karten.
- `CLAUDE.md` (Schritt 5 „Adding a New Content Type“) und `docs/CONTENT_MODEL.md` sind an die
  zwei Dateien angepasst.

Selbstentscheidungen:
- Über die Stellen aus dem Bericht hinaus umgestellt, weil es dieselben Typnamen sind: die
  Desktop-Paneltitel der Beitragen-Seite (`h3`) und die Formularköpfe „Fertiger Kommentar“ /
  „Hintergrundinfo“ in `add-commentary` und `add-generictext`.
- Startseite: Umgestellt sind alle vier Kachel-Beschriftungen, nicht nur `:46` und `:67`.
  Sonst stünden Einzahl und Mehrzahl gemischt nebeneinander. Sichtbar werden sie zu „Aussage,
  Kommentar, Hintergrundinfo, Herkunft“ (vorher „Aussagen, Fertige Kommentare,
  Hintergrundinfos, Quellen“). An Zahlen und Berechnung ist nichts geändert.
- „Fertiger Kommentar“ heißt in Titeln und Tooltips jetzt „Kommentar“. Knopftexte wie „Fertigen
  Kommentar verfassen“, aria-Labels und Beschreibungen sind unverändert.
- Wo die Mehrzahl grammatisch nötig ist, steht „Herkunftsangaben“: „3 / 10 Herkunftsangaben
  hinzugefügt“, „Füge Herkunftsangaben hinzu …“, „Maximale Anzahl an Herkunftsangaben erreicht.“
- Unverändert, weil es nicht „Quelle“ heißt: „Referenz“ in `reference-input` (Tooltips
  „Neue/Wiederverwendete Referenz“, „Referenz entfernen“, Snackbar „Referenz wird
  hinzugefügt…“). Code-Kommentare mit „Quelle“ sind ebenfalls nicht angefasst.
- Moderation zeigt jetzt „Hintergrundinfo“ statt „Generic Text“ und „Aussage“ statt
  „Statement“.

**Fundstellen „Quelle“ in den Rechtstexten: keine.** Gesucht wurde in `impressum/`,
`datenschutz/` und `nutzungsbedingungen/` nach „quell“ ohne Rücksicht auf Groß- und
Kleinschreibung: 0 Treffer.

## D. Tracking-Parameter

- `shared/url-bereinigen.ts`: neue host-bezogene Regel. Auf `youtube.com`, allen Subdomains
  (`www.`, `m.` …) und `youtu.be` werden zusätzlich `si`, `is`, `feature` und `pp` entfernt.
  Die globale Liste ist unverändert.
- Tests: youtube.com (si, feature; `v` und `t` bleiben), Subdomains (pp auf www., is auf m.),
  youtu.be (si, kein Rest-`?`). Gegenbeispiele: dieselben Parameter auf `example.org` und auf
  `notyoutube.com` bleiben stehen.
- `reference-input.component.ts`: `addCustomReference` ruft vor der lokalen Dublettenprüfung und
  vor dem Speichern `trackingParameterEntfernen` auf. Freitext ohne Adresse bleibt unverändert.
  Neuer Spec-Test.

**Hinweis:** Die Prozent-Kodierung durch `URL.toString()` (`url-bereinigen.ts`) ist nicht
geändert. Sie greift jetzt auch bei Herkunftsangaben: Wird dort ein Tracking-Parameter entfernt,
steht die Adresse umkodiert gespeichert (z. B. `ä` → `%C3%A4`). Ohne entfernten Parameter bleibt
die Eingabe unverändert.

## E. Beta-Banner und Block „Weitere Funktionen“

- `<app-metrics>` ist von der Startseite entfernt. Die Komponente war nirgends sonst eingebunden
  und ist mit Template, Styles und Spec gelöscht; damit fällt auch der `getMetrics`-Aufruf aus
  `metrics.component.ts` weg.
- `MetricsService` bleibt: Die Startseite nutzt ihn für die Kacheln, das Admin-Dashboard für
  `mvp-dashboard`.
- `contribute-view.component.html`: Der Block „Weitere Funktionen in Entwicklung“ ist gelöscht,
  mit `.roadmap-section`, `.coming-soon-card` und `.feedback-link`.

Selbstentscheidungen:
- Auch die mobile Regel für `.coming-soon-card` in der 768-px-Media-Query ist entfernt, weil sie
  sonst tot wäre.
- `.coming-soon-message` lag außerhalb der genannten Zeilen und bleibt.
- Der localStorage-Schlüssel `gutgesagt-metrics-seen` wird nicht mehr geschrieben. Vorhandene
  Werte in Browsern schaden nicht.

## F. Fangkorb-Wording

- `shared/fangkorb-texte.ts`: `FANGKORB_BESCHREIBUNG` = „Ein Link, ein Hinweis oder beides –
  roh, ohne Ausarbeiten. Jemand macht später einen Beitrag daraus.“
- Aus der Konstante gespeist: Beitragen-Seite Desktop und mobil, Einwurf-Formular, erster
  Schritt der Fangkorb-Liste. Die aria-Labels bleiben.

Selbstentscheidungen:
- Der Dateiname ist `fangkorb-texte.ts`, neben `plattform.ts`.
- Auf dem Desktop bleibt die Überschrift „Keine Zeit zum Ausarbeiten?“; nur der Absatz darunter
  kommt aus der Konstante.
- In der Fangkorb-Liste steht jetzt „Einwerfen – Ein Link, ein Hinweis oder beides – roh, …“.
  Der Satz ist länger als die beiden anderen Schritte und enthält zwei Gedankenstriche. So
  übernommen, wie entschieden.

## G. Meine Beiträge

- `contributions-view.component.html`: `hh:mm` → `HH:mm` in beiden Datumsspalten.
- `shared/paginator-intl-de.ts` (neu): deutsche `MatPaginatorIntl` ohne `LOCALE_ID`.
  Beschriftung: „Einträge pro Seite:“, „Nächste/Vorherige/Erste/Letzte Seite“, Bereich „1 – 20
  von 57“.
- Die Typspalte liest seit Block C `typLabel`.
- Backend `api/v1/contribution.py`: `AUSFORMULIERTE_TYPEN` = commentary, generic_text, image,
  post. Liste **und** Gesamtzahl sind eingegrenzt, sodass der Paginator zur Liste passt.

**Abweichung vom Auftrag – Provider an der Komponente statt in `app.config.ts`.** Im ersten Stand
stand der Provider in `app.config.ts`. Dieser Import zog den Paginator samt Material-Abhängigkeiten
ins initiale Bundle: 958,04 kB → 1,01 MB, wieder über der 1-MB-Warngrenze. Die Klasse hängt jetzt
in `ContributionsViewComponent.providers`, der einzigen Stelle mit `mat-paginator`.
`app.config.ts` ist damit unverändert gegenüber `origin/main`. Die Nachbesserung ist in den G-Commit
eingearbeitet (amend, noch nicht gepusht).

Umsetzung und Selbstentscheidungen:
- Die Eingrenzung sitzt im Repository als optionales `content_types` (Qdrant `MatchAny`) an
  `get_by_author`/`get_count_by_author` (Interface, Qdrant-Basis, aggregiertes Repository). Beide
  Methoden teilen sich jetzt `_autoren_filter`.
- Ohne Angabe ist der Filter unverändert. Die Nutzungsstatistik
  (`usage_tracking_repository.py:148`) ruft ohne Eingrenzung auf und zählt weiter alle Typen.
- Aussagen und Herkunftsangaben bleiben im Index; sie erscheinen nur nicht mehr in „Meine
  Beiträge“.
- Abweichung vom Auftrag: Bestehende Tests mussten nicht angepasst werden – sie rufen ohne
  `content_types` auf und das Verhalten ist dort gleich.
- Neue Tests:
  - zwei Repository-Tests (`test_base_repository.py`: Eingrenzung von Liste und Zählung, keine
    Eingrenzung ohne Angabe)
  - zwei API-Tests (`tests/unit/api/test_contributions_of_user.py`)
  - Spec für die Paginator-Klasse
  - neue `contributions-view.component.spec.ts`: gerenderter Paginator auf Deutsch, Typname,
    24-Stunden-Zeit

## H. Menü-Fußtext

- `mobile-menu.html`: „Ein Projekt von Netzbegrünung e.V., entwickelt von Sebastian Banach“. Der
  Anbieter steht zuerst, wie im Impressum. Netzbegrünung verlinkt extern, Sebastian Banach auf
  `/about` (seit Block A).
- Neuer Spec-Test für Text und Reihenfolge.

## Tests

| Stand | Frontend (`ng test`, ChromeHeadless) | Backend (`pytest` aus `app/`) |
|---|---|---|
| vorher (`origin/main`) | 305 von 316 grün, 11 übersprungen | 661 bestanden, 11 übersprungen |
| nach A | 310 von 321 | – |
| nach B | 310 von 321 | 661 |
| nach C | 318 von 329 | – |
| nach D | 323 von 334 | – |
| nach E | 322 von 333 (Metrics-Spec gelöscht) | – |
| nach F | 322 von 333 | – |
| nach G (erster Stand) | 326 von 337 | 665 bestanden, 11 übersprungen |
| nach H, inkl. G-Nachbesserung | 328 von 339 | 665 bestanden, 11 übersprungen |

- Die Frontend-Zahlen zählen ausgeführte von gesamt, jeweils ohne Fehlschlag; die 11
  übersprungenen gab es schon vorher.
- Der G-Stand nach der Provider-Nachbesserung ist nicht einzeln gelaufen, sondern zusammen mit
  den H-Änderungen (letzte Zeile).
- `dotnet test` ist nicht gelaufen: Das BFF ist nicht berührt (`git diff origin/main --
  mvp/backend/BFF` ist leer).
- Produktions-Build (`ng build`): initiales Bundle vorher 956,60 kB, nachher 958,29 kB, ohne
  Budget-Warnung für das Bundle. Die bestehenden Budget-Warnungen für Komponenten-Styles sind
  unverändert.
- Nicht gemacht: kein manueller Test im Browser oder auf dem Gerät (360 px, Android-PWA). Footer,
  Menü und Paginator sind nur über Specs und Build geprüft.
