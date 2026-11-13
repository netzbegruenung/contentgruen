# Art.-9-Einwilligung

Mitwirkung bei Gut gesagt kann auf eine politische Meinung schließen lassen (Art. 9 DSGVO,
Lückenliste D-N15). Rechtsgrundlage ist eine ausdrückliche Einwilligung (Art. 9 Abs. 2 lit. a),
die die App selbst einholt, nicht Keycloak (Entscheidung Maintainer, 05.11.2026,
#489). Begriff: `GLOSSARY.md`, „Art.-9-Einwilligung“.

## Ablauf

- **Fragen:** Nach dem Anmelden fragt die App einmal je Person und App-Start nach dem Stand
  (`GET /api/v1/art9-einwilligung`) und führt auf `/einwilligung`, solange sich die Person
  noch nicht entschieden hat (`zurEinwilligungUmleiten` in `art9-einwilligung.service.ts`).
  Das gilt für jede Kontoart (Netzbegrünung-Login, Konto aus einer Einladung, Beta-Zugang).
  Dort steht der Wortlaut an einem eigenen Häkchen, getrennt von den Nutzungsbedingungen und
  nicht angehakt: als Label der erste Satz, der ganze Wortlaut aufklappbar darunter (#620).
  Fragt die App so (mit Rückweg in der Adresse), heißt die Seite im Kopf „Einwilligung“, aus
  dem Profilmenü „Datenschutz-Einstellungen“.
  „Ohne Einwilligung weiter“ führt zurück; die Person kann suchen und lesen.
- **Nicht drängen (UX-Review B2):** Wer „Ohne Einwilligung weiter“ gewählt oder widerrufen
  hat, wird nicht bei jedem App-Start wieder auf `/einwilligung` geführt. Den Widerruf kennt
  das Backend (`widerrufen_am`), das „ohne“ steht am Konto: Tabelle `art9_ohne_einwilligung`,
  je Kennung höchstens eine Zeile mit dem Wortlaut, der da galt, und dem Zeitpunkt
  (`POST /api/v1/art9-einwilligung/ohne`, im Stand als `ohne_wortlaut`). Im Browser liegt
  dafür nichts (Entscheidung Maintainer, 13.11.2026, bis § 25 TDDDG geprüft ist); einen
  älteren Eintrag `gutgesagt-art9-ohne` im localStorage räumt die App einmal weg. Eine
  Einwilligung löscht die Zeile, ein Widerruf lässt sie stehen (dann gilt ohnehin
  „widerrufen“); sie geht mit dem Konto (`person_loeschen.sql`), mit dem Löschablauf eines
  Löschauftrags und zieht beim Umstellen der Kennungen mit. Ausnahme: Wer einem früheren
  Wortlaut zugestimmt hat, der nicht mehr zählt, wird zum neuen einmal gefragt.
  Erst beim Beitragen zeigen die Formulare (Einwerfen, Satz beim Destillieren, Kommentar,
  Hintergrundinfo, Bild, Post, auch beim Ausformulieren) über dem Formular einen Hinweis mit
  „Einwilligen“ (`EinwilligungHinweisComponent`). Eine schon begonnene Eingabe hält die App
  nur im Arbeitsspeicher (`entwurf-vor-einwilligung.ts`, mit Zeitpunkt und einem Prüfwert
  des Kontos statt der Kennung): Sie übersteht den Weg über `/einwilligung` und zurück, nicht
  aber ein Neuladen; nach einer Stunde wird sie nicht mehr verwendet, beim Abmelden und
  Kontowechsel ist sie weg. Pfeil und Haus in Destillieren warten ohne Einwilligung nicht auf
  ein 403, sondern legen den Satz dorthin. Wer trotzdem absendet, bekommt den Kasten in den
  Blick geholt; den Fokus nimmt er nur, wenn er nicht in einem Eingabefeld steht, und
  Speichern im Hintergrund holt ihn nie (Destillieren speichert ohne Einwilligung im
  Hintergrund gar nicht). Auf `/einwilligung` selbst zeigt ein später 403 keine Snackbar.
  Wird der Tab wieder sichtbar, holt die App den Stand neu, damit eine Einwilligung aus
  einem anderen Tab ankommt.
- **Widerruf mit Rückfrage (UX-Review B3):** „Einwilligung widerrufen“ und „Frühere
  Einwilligung widerrufen“ fragen erst nach und nennen die Folgen (Bewertungen gelöscht,
  Löschauftrag binnen sieben Tagen); widerrufen wird nur mit „Widerrufen“.
- **Speichern:** Tabelle `art9_einwilligungen`, je Einwilligung eine Zeile mit Kennung der
  Person, Zeitpunkt und Kennung des gezeigten Wortlauts. Es gilt die jüngste Zeile.
- **Sperren:** Ohne geltende Einwilligung antworten die Endpunkte, die mit Personenbezug etwas
  speichern, aus dem sich auf die politische Meinung schließen lässt, mit 403
  (`art9_einwilligung_fehlt`); die App zeigt dann einen Hinweis mit Knopf, der auf
  `/einwilligung` und danach zurück führt, und bleibt sonst auf der Seite, damit kein Text im
  Formular verloren geht. Auf einer Seite mit Hinweiskasten ist das der Kasten, ohne
  „Bitte versuche es erneut“; anderswo (etwa bei den Stimm-Knöpfen) eine Snackbar.
  Gesperrt: Beiträge anlegen und ändern, Herkunft anlegen, Einwurf und Satz, einen Einwurf
  ausformulieren, Stimmen abgeben, „Ja, gepostet“ nach dem Kopieren melden und erfragen, ob es
  angeboten wird (#643). Offen bleiben Lesen, Suchen, Löschen, einen Einwurf
  verwerfen, Melden, Feedback, Gegenlesen, Sprachhinweis, Kürzungsvorschlag und Widerspruch
  gegen eine Sperre. Die Liste prüft `tests/unit/api/test_art9_einwilligung_api.py`
  (`GESPERRT`, `OFFEN`): Ein neuer schreibender Endpunkt fällt dort auf, bis er in einer der
  beiden steht; gesperrte tragen `require_art9_einwilligung` (`dependencies.py`).
- **Kopieren:** bleibt offen und zählt am Zähler der Karte (Kopieren ist Lesen). Ohne geltende
  Einwilligung entsteht dabei aber kein Prüfwert und kein Paar-Prüfwert: keine entdoppelte
  Nutzung, also keine Wirkung-Punkte für die Autorin und kein Eintrag in „Diese Woche oft
  genutzt“, und keine Muster-Hinweise. Einen Paar-Prüfwert gibt es auch nicht, wenn die
  Autorin des Beitrags nicht eingewilligt hat (#559, `track_content_usage` in
  `api/v1/usage.py`, Tests `TestArt9Einwilligung` in
  `tests/unit/api/test_usage_eigene_kopie.py`). Gefragt wird je Kopie; ist die Einwilligung
  nicht lesbar, gilt sie als nicht erteilt und die Kopie zählt trotzdem. Paar-Prüfwerte und
  Hinweise von vor einem Widerruf gehen mit ihren Fristen (`docs/LOESCHKONZEPT.md`).
- **Punkte und Meilensteine:** gehören seit dem Wortlaut `2026-11-13` nicht mehr zu dieser
  Einwilligung, sondern hängen an der eigenen, freiwilligen Einwilligung „Punkte und
  Meilensteine“ (#668, Entscheidung Maintainer 13.11.2026); ohne sie kann die Person genauso
  beitragen und bewerten. Bis #668 gemergt ist, prüft der Code dafür noch diese Einwilligung
  (`PunkteService.punkte`, #559, F559-1: ohne sie 0 in jeder Stufe, gefragt je Abruf); das ist
  folgenlos, solange der Schalter `punkte_aktiv` aus ist.
- **Abzeichen (#351):** Ohne geltende Einwilligung kein Abzeichen am Anzeigenamen. Ein Widerruf nimmt das Abzeichen sofort weg und hält ein
  früheres Ja zur Sichtbarkeit als Nein fest, damit es nach einer neuen Einwilligung nicht
  ohne neue Frage wieder erscheint (`AbzeichenService.zuruecknehmen`). Die Antwort zur
  Sichtbarkeit (`PUT /api/v1/usage/users/me/abzeichen-sichtbarkeit`) geht auch ohne
  Einwilligung, weil ein Nein ein Zurücknehmen ist (`OFFEN` in
  `tests/unit/api/test_art9_einwilligung_api.py`). Die Zustimmung zur Sichtbarkeit hat
  eigene Wortlaute mit Kennung (`domain/abzeichen_sichtbarkeit.py`, aktuell `2026-11-09-b`:
  kurze Frage, Hinweise unter „Mehr dazu“); wie hier bleibt jede frühere Kennung bekannt.
- **Widerrufen:** jederzeit unter `/einwilligung` (Profilmenü „Datenschutz-Einstellungen“, bis #644 „Einwilligung“; Seitentitel ebenso). Die Zeile bekommt
  den Zeitpunkt des Widerrufs und bleibt stehen, als Nachweis, dass die Verarbeitung bis dahin
  auf der Einwilligung beruhte (Art. 7 Abs. 1); danach ist wieder gesperrt. In derselben
  Transaktion löscht der Widerruf alle Stimmen der Person (`Art9EinwilligungService.widerrufen`,
  Art. 17 Abs. 1 lit. b DSGVO, juristische Vorprüfung vom 12.11.2026); scheitert das, gilt auch
  der Widerruf nicht, die Antwort ist 500, und die Person kann über die Seite erneut widerrufen.
  Das Abzeichen nimmt der Endpunkt vorher und unabhängig davon zurück. In derselben Transaktion
  legt der Widerruf auch einen **Löschauftrag** an, wenn er eine geltende Einwilligung trifft
  (Frist sieben Tage, je Person höchstens ein offener): Ein Admin führt unter „Moderation“, „Löschaufträge“ den Löschablauf aus, danach
  zeigen ihre Beiträge „ehemalige Person“, ihre Einwürfe sind gelöscht und ihre Sätze an fremden
  Einwürfen tragen einen Platzhalter; Konto, Anzeigename und diese Zeile bleiben
  (`docs/LOESCHKONZEPT.md`, „Löschauftrag nach dem Widerruf“, DSFA R9b). Bis dahin bleiben
  Beiträge, Einwürfe und Sätze an der Person. Willigt die Person vor der Ausführung neu ein,
  bleibt der Auftrag offen, erfasst beim Ausführen aber nur, was vor der neuen Einwilligung
  gespeichert wurde, gleich zu welchem Wortlaut sie war; was sie danach beiträgt, bleibt an ihr
  (Entscheidung Maintainer, 13.11.2026). Ohne neue Einwilligung erfasst er alles. Die Liste der Admins zeigt dann „Neu eingewilligt am …“. Eine neue
  Einwilligung ist eine neue Zeile; die früheren bleiben. Jede Prüfung fragt die Datenbank,
  damit ein Widerruf und das Löschkommando sofort wirken.
- **Startkonten und Import:** Auch ein Startkonto willigt einmal in der App ein, bevor es
  schreibt oder `mvp/scripts/manual/einwuerfe_importieren.py` bzw. `beitraege_importieren.py`
  unter ihm läuft (`mvp/SCRIPTS.md`).
  Verwerfen eines Einwurfs bleibt ohne Einwilligung offen, wie Löschen.
- **Löschen und Umstellen:** Die Zeile (und die in `art9_ohne_einwilligung`) geht mit dem Konto (`docs/LOESCHKONZEPT.md`, Schritt 2)
  und zieht beim Umstellen der Kennungen mit (`services/wartung/kennungen_umstellen.py`).

## Wortlaut ändern

Der Wortlaut steht an einer Stelle: `WORTLAUTE` in
`mvp/backend/semantic-search-service/app/domain/art9_einwilligung.py`. Das Frontend zeigt,
was das Backend liefert, und hat keinen eigenen Text. Die Kennung eines Wortlauts ist sein
Stand-Datum; ein zweiter Wortlaut vom selben Tag bekommt ein Suffix (`-b`, `-c` …).

1. Neuen Eintrag in `WORTLAUTE` mit dem Tagesdatum als Kennung anlegen; den alten stehen lassen,
   sonst ist eine gespeicherte Kennung keinem Text mehr zuzuordnen. Ein Datum nie für einen
   anderen Text wiederverwenden; gibt es das Tagesdatum schon, mit Suffix (`2026-11-05-b`).
2. `AKTUELLER_WORTLAUT` auf die neue Kennung setzen.
3. Unten in der Tabelle eine Zeile ergänzen, beim vorigen Wortlaut das „bis“-Datum nach dem
   Produktiv-Deploy.

Ob ein geänderter Wortlaut eine neue Einwilligung verlangt, ist beim Ändern zu entscheiden; das
regelt `GELTENDE_WORTLAUTE` in derselben Datei. Nur eine nicht widerrufene Einwilligung zu einer
dieser Kennungen zählt (`Art9Einwilligung.zaehlt`): Dann meldet das Backend `eingewilligt`, und
`Art9EinwilligungService.eingewilligt` gibt frei. Eine Einwilligung zu einer anderen Kennung
bleibt als Nachweis stehen und kann widerrufen werden (der Widerruf legt dann auch den
Löschauftrag an), zählt aber nicht, und neu einwilligen lässt sich nur zu einer geltenden
Kennung (sonst 400): Das Backend meldet `eingewilligt: false`, das Frontend führt
beim nächsten Besuch auf `/einwilligung`, und dort steht ein Hinweis auf den früheren Wortlaut
mit dem Knopf „Frühere Einwilligung widerrufen“. Bis dahin ist gesperrt wie ohne Einwilligung.
Tests: `test_einwilligung_zu_frueherem_wortlaut_fragt_neu`, `test_frueherer_wortlaut_gesperrt`,
`test_nur_der_aktuelle_wortlaut_zaehlt` und die Spec „fragt neu, wer einem frueheren Wortlaut
zugestimmt hat …“.

- **Ohne neue Frage** (neue Kennung zu `GELTENDE_WORTLAUTE` hinzufügen): wenn die Änderung
  redaktionell ist oder nur zugunsten der Person wirkt: gleiche Zwecke, gleiche Datenarten, keine
  weiter gehenden Folgen des Widerrufs, etwa ein neuer Name des Menüpunkts (`2026-11-10`, #644)
  oder das Löschen der Bewertungen (`2026-11-12`). Bis `2026-11-12` zählte jede Kennung.
- **Mit neuer Frage** (`GELTENDE_WORTLAUTE` nur mit der neuen Kennung): neue Zwecke, neue
  Datenarten oder weiter gehende Folgen des Widerrufs. So bei `2026-11-13` (Löschauftrag,
  Entscheidung Maintainer, 13.11.2026).
- **Überschrieben `2026-11-13`:** Die erste Fassung vom 13.11.2026 nannte noch Punktestand,
  Level, Quests, Freischaltungen und den Muster-Hinweis. Nach juristischer Prüfung hat der
  Maintainer entschieden (13.11.2026), den Text unter derselben Kennung zu ersetzen, statt eine
  neue zu vergeben: Er war in keinem Release. Restrisiko: `2026-11-13` stand seit dem Merge von
  #661 in gebauten `:main`-Images; wurde die erste Fassung irgendwo gezeigt, steht dieselbe
  Kennung für zwei Texte. Sonst gilt: eine Kennung nie für einen anderen Text.

## Wortlaut ändern: diese Stellen mitziehen

Diese Stellen geben den Wortlaut wieder oder setzen ihn voraus (ermittelt per `git grep` nach
der Kennung, „Art.-9-Einwilligung“, „Einwilligung“ und den Zwecken des Wortlauts). Wer den
Wortlaut ändert, prüft jede und zieht sie im selben PR mit; Rechtstexte nur über ein eigenes
Ticket (`CODING_STANDARDS.md`, „Legal texts change through their own ticket“).

- **Quelle:** `WORTLAUTE` und `AKTUELLER_WORTLAUT` in
  `mvp/backend/semantic-search-service/app/domain/art9_einwilligung.py`; Kennung höchstens
  `WORTLAUT_KENNUNG_MAX` Zeichen (Spalte `art9_einwilligungen.wortlaut`).
- **Diese Datei:** Tabelle „Wortlaute“ unten, Abschnitt „Wortlaut ändern“ (Prüfung nach Kennung).
- **Prüfung der Einwilligung:** `Art9EinwilligungService.eingewilligt` in
  `mvp/backend/semantic-search-service/app/services/art9_einwilligung_service.py` zählt nur
  Einwilligungen zu `GELTENDE_WORTLAUTE` (`Art9Einwilligung.zaehlt`); ihre Aufrufer setzen
  voraus, dass diese Wortlaute ihren Zweck nennen: `punkte_service.py` (Punkte),
  `muster_hinweise_service.py` (Muster-Hinweise) und `api/v1/usage.py` (`_eingewilligt`).
- **Backend-Tests:** `TestWortlaute` in
  `mvp/backend/semantic-search-service/app/tests/unit/api/test_art9_einwilligung_api.py`
  (aktuelle Kennung, geltende Kennungen, zitierte Zwecke, Wortgleichheit mit dem Vorgänger,
  Kennungsformat, Spaltenlänge) und `TestStand` (neue Frage bei früherem Wortlaut).
- **Frontend:** `wortlautDatum` in
  `mvp/frontend/gutgesagt-frontend/src/app/services/art9-einwilligung.service.ts` liest das
  Stand-Datum aus der Kennung (nur das führende `JJJJ-MM-TT`, ein Suffix fällt weg); das
  Kennungsformat `JJJJ-MM-TT` mit optionalem `-x` sichert `TestWortlaute`; Specs
  `mvp/frontend/gutgesagt-frontend/src/app/einwilligung/einwilligung.component.spec.ts`
  (Wortlaut mit Suffix, Auszug aus dem Text) und
  `mvp/frontend/gutgesagt-frontend/src/app/services/art9-einwilligung.service.spec.ts`.
- **DSFA:** `docs/DSFA.md`, Abschnitt 3 Risiko 1 (Opt-in für die Sichtbarkeit),
  Abschnitt 4 (Zwecke, die der Wortlaut nennen muss, Kennung), Abschnitt 5 (Folgen des
  Widerrufs), Abschnitt 7 (Stand mit Kennung).
- **Glossar:** `GLOSSARY.md`, „Art.-9-Einwilligung“ (Zwecke, Kennungsformat), „Level“
  (bisher nur im Wortlaut genannt) und „Meilenstein“ (Abzeichen nur mit Zustimmung).
- **Vision:** `docs/VISION.md`, Abschnitt mit „Meilensteine“ (Abzeichen nur mit Opt-in) und
  „Ranglisten“ (Zustimmung, Art. 9).
- **Datenschutzerklärung:** `mvp/frontend/gutgesagt-frontend/src/app/datenschutz/datenschutz.component.html`,
  „Rückschlüsse auf deine politische Haltung“ → „Deine Einwilligung“ (Kennungsformat, Folgen,
  Widerruf) und „Punkte“ (Rechtsgrundlage, ohne Einwilligung keine Punkte); Spec
  `mvp/frontend/gutgesagt-frontend/src/app/datenschutz/datenschutz.component.spec.ts`
  (`describe`-Blöcke „Rückschlüsse auf die politische Haltung“ und „Entdoppelte Nutzung, Punkte
  und Muster-Hinweise“).
- **Lückenliste:** `docs/rechtstexte-luecken/pruefliste/P11.md` (Wortlaut zur Prüfung mit
  #296) und `docs/rechtstexte-luecken/4-fehlende-vorgaenge/D-N15.md` (fasst „Deine
  Einwilligung“ samt Widerrufsfolgen zusammen).

- **Seite `/einwilligung`:** `mvp/frontend/gutgesagt-frontend/src/app/einwilligung/einwilligung.component.html`
  zeigt den Wortlaut vom Backend, wiederholt aber in eigenen Sätzen, was ohne Einwilligung
  geht und was der Widerruf bewirkt. Am Häkchen steht nur der erste Satz des Wortlauts,
  unverändert, der ganze Wortlaut aufklappbar direkt darunter (#620); den Satz schneidet
  `wortlautErsterSatz` in `art9-einwilligung.service.ts` ab. Ein neuer Wortlaut braucht
  deshalb einen ersten Satz, der für sich die Einwilligung ausdrückt.
- **Profilmenü:** Der Wortlaut nennt den Widerruf „im Profilmenü unter
  „Datenschutz-Einstellungen““ (bis #644 „Einwilligung“); der Name steht als
  `DATENSCHUTZ_EINSTELLUNGEN` in `mvp/frontend/gutgesagt-frontend/src/app/shared/fangkorb-texte.ts`
  (auch Seitentitel von `/einwilligung`; die Karte darauf heißt weiter „Einwilligung“, so
  finden auch Personen mit dem Wortlaut `2026-11-05-b` den Widerruf), der Eintrag in `mvp/frontend/gutgesagt-frontend/src/app/app.component.html` und
  `mvp/frontend/gutgesagt-frontend/src/app/shared/components/mobile-menu/mobile-menu.html`.

Ohne Änderung zieht die E2E-Anmeldung mit
(`mvp/frontend/gutgesagt-frontend/e2e/tests/anmelden.setup.ts`): Sie nimmt den aktuellen
Wortlaut vom Backend.

## Wortlaute

| Kennung | Stand | gültig |
|---------|-------|--------|
| `2026-11-05` | vorläufig, Prüfung mit #296 (Lückenliste P11) | nie produktiv: von `2026-11-05-b` abgelöst, bevor #489 in einem Release war |
| `2026-11-05-b` | vorläufig, Prüfung mit #296; nennt zusätzlich Punktestand, Level, Quests und Meilenstein-Abzeichen (nur für die Person, für andere Angemeldete nur mit gesonderter Zustimmung), Freischaltungen eines höheren Levels und die Muster-Hinweise (#559, Zwecke aus `docs/DSFA.md` Abschnitt 4); vor dem Merge noch zweimal geändert, Kennung beibehalten, weil nie auf `main` und in keinem Release | seit dem Produktiv-Deploy von #489 und #559 bis zum Produktiv-Deploy von #644 (Daten nach dem Ausrollen eintragen); wer zugestimmt hat, bleibt eingewilligt |
| `2026-11-10` | redaktionell (#644): wortgleich mit `2026-11-05-b` bis auf den Widerrufsweg „im Profilmenü unter „Datenschutz-Einstellungen““ statt „Einwilligung“, weil der Menüpunkt umbenannt ist; gleiche Zwecke, deshalb keine neue Frage | seit dem Produktiv-Deploy von #644 bis zum Produktiv-Deploy des Wortlauts `2026-11-12` (Daten nach dem Ausrollen eintragen) |
| `2026-11-12` | Folgen des Widerrufs nach der juristischen Vorprüfung vom 12.11.2026: Die Bewertungen werden gelöscht, das Übrige bleibt bis zur eigenen Löschung oder Kontolöschung; sonst wortgleich mit `2026-11-10` (ein Test sichert das). Keine neuen Zwecke, und die Änderung wirkt nur zugunsten der Person, deshalb keine neue Frage | seit dem Produktiv-Deploy (Datum nach dem Ausrollen eintragen) bis zum Produktiv-Deploy von `2026-11-13` |
| `2026-11-13` | Löschauftrag nach dem Widerruf (#661, Entscheidung Maintainer, 13.11.2026): Binnen sieben Tagen zeigen Beiträge „ehemalige Person“, Einwürfe werden gelöscht, Sätze an fremden Einwürfen bleiben ohne Namen; was nach einer neuen Einwilligung beigetragen wird, bleibt unberührt. Ohne Spielelemente: Punktestand, Level, Quests, Meilenstein-Abzeichen, Freischaltungen und der Muster-Hinweis fallen weg, die Mitte lautet „Gut gesagt nutzt meine Mitwirkung nur für den Betrieb der Plattform, wertet sie nicht nach politischer Haltung aus und gibt sie nicht an Dritte weiter.“ (ErwG 43 S. 2, Art. 7 Abs. 4 DSGVO; Punkte und Meilensteine bekommen eine eigene, freiwillige Einwilligung, #668). Am 13.11.2026 vor jedem Release überschrieben (Entscheidung Maintainer). Sonst wortgleich mit `2026-11-12` (ein Test sichert das). Neue Frage, weil die Folgen des Widerrufs weiter gehen: Nur dieser Wortlaut steht in `GELTENDE_WORTLAUTE`, wer einem früheren zugestimmt hat, wird beim nächsten Besuch neu gefragt | seit dem Produktiv-Deploy (Datum nach dem Ausrollen eintragen) |
