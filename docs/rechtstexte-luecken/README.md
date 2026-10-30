# Gut gesagt — Rechtstexte: Lückenliste

Arbeitsdokument zur Überarbeitung von Impressum, Datenschutzerklärung und
Nutzungsbedingungen. Die Einträge haben ein Eintrag-Feld und sind zum Ausfüllen
gedacht — wer eine Angabe klärt, trägt sie in der Datei des Eintrags ein.

**Ablage (#500):** Jeder nummerierte Eintrag ist eine eigene Datei im Ordner seines
Abschnitts, benannt nach seiner Nummer (`4-fehlende-vorgaenge/D-N5.md`); die Felder der Datei
sind die Spalten der früheren Tabelle. Text und Überschrift eines Abschnitts stehen in
seiner `README.md`. Ein neuer Eintrag ist eine neue Datei mit derselben Felderfolge wie die
anderen im Ordner, nichts sonst; so kollidieren zwei PRs mit je einem neuen Eintrag nicht.
Bis #500 stand alles in einer Datei, `docs/RECHTSTEXTE_LUECKEN.md`; Verweise in `docs/archiv/`
nennen noch diesen Namen.
Die Tabellen als Übersicht: `python3 scripts/rechtstexte_uebersicht.py luecken`.
`scripts/tests/test_rechtstexte_uebersicht.py` prüft die Ablage.

**Dies ist keine Rechtsberatung.** Die Zuordnung Pflicht/optional ist eine
Arbeitsgrundlage, damit die offenen Punkte sichtbar sind; die fertigen Texte gehören
vor Veröffentlichung durch jemanden mit juristischer Qualifikation geprüft.

Stand der Analyse: 2026-08-19, nachgeführt mit #222 am 2026-10-29
Zeilenangaben beziehen sich auf den Stand vom 19.08.2026; die Neufassung in diesem
Branch weicht davon ab.
Geprüfte Dateien:
- `mvp/frontend/gutgesagt-frontend/src/app/impressum/impressum.component.html` (14 Platzhalter)
- `mvp/frontend/gutgesagt-frontend/src/app/datenschutz/datenschutz.component.html` (12 Platzhalter)
- (Kontext) `.../nutzungsbedingungen/nutzungsbedingungen.component.html` (1 Platzhalter)

Gesamt: 26 Platzhalter in den beiden Hauptdateien. **Stand 04.09.2026: keiner davon ist
mehr offen** — alle drei Texte sind ausformuliert, die Datenschutzerklärung zuletzt. Die
Einträge bleiben stehen, weil in ihrem Eintrag-Feld steht, wie der jeweilige Punkt gelöst
wurde; sie sind jetzt Nachweis statt Arbeitsvorrat. Offen sind noch die Zustimmung beim
Anmelden (Abschnitt 5, #429), die USt-IdNr. im Impressum (I11) und die Prüfliste am Ende.

Legende Pflicht-Spalte:
- PFLICHT = gesetzlich zwingend
- BEDINGT = nur zwingend, wenn der Sachverhalt zutrifft (z. B. Registereintrag vorhanden)
- OPTIONAL = kann ersatzlos gestrichen werden

---

## 1. IMPRESSUM — impressum.component.html

Einträge und Text des Abschnitts: [`1-impressum/`](1-impressum/)

### Weitere Befunde im Impressum (keine Platzhalter, aber zu korrigieren)

Einträge und Text des Abschnitts: [`1-impressum-befunde/`](1-impressum-befunde/)

---

## 2. DATENSCHUTZERKLÄRUNG — datenschutz.component.html

Einträge und Text des Abschnitts: [`2-datenschutz/`](2-datenschutz/)

### FEHLENDE Pflichtangaben nach Art. 13 DSGVO (keine Platzhalter — die Abschnitte fehlen komplett)

Einträge und Text des Abschnitts: [`2-pflichtangaben-art-13/`](2-pflichtangaben-art-13/)

---

## 3. Beschriebene Vorgänge, die es in Gut gesagt NICHT gibt

Einträge und Text des Abschnitts: [`3-nicht-vorhandene-vorgaenge/`](3-nicht-vorhandene-vorgaenge/)

---

## 4. Reale Vorgänge, die im Text FEHLEN

Einträge und Text des Abschnitts: [`4-fehlende-vorgaenge/`](4-fehlende-vorgaenge/)

---

## 5. Consent-Checkbox / Verweis auf Nutzungsbedingungen

**Entschieden (#415, 28.10.2026): beides.** Ein CC0-Hinweis über dem Absende-Knopf in jedem Formular
(#431) und die Zustimmung zu den Nutzungsbedingungen beim ersten Anmelden (#429).

**CC0-Hinweis im Formular: umgesetzt.** Der Wortlaut steht in `shared/consent-hinweis.ts` und verlinkt
die Nutzungsbedingungen (neuer Tab): „Mit dem Absenden stellst du deine eigene Formulierung
unter CC0 und bestätigst die Nutzungsbedingungen – keine personenbezogenen Daten Dritter.“ Keine
Checkbox; die bewusste Handlung ist das Absenden. Beim Satz, der beim Tippen gespeichert wird,
ist die eigene Fassung so gewollt (Entscheidung 29.10.2026 in #439). Dass die Freigabe nicht
zurückgenommen werden kann, steht in den Nutzungsbedingungen, nicht im Hinweis (ebenfalls
29.10.2026); seit #222 auch dort ohne das Wort „unwiderruflich“.

| Ort | Formular | Seit |
|-----|----------|------|
| `add-raw-input/` | Einwurf | 55bb5cb8 |
| `add-commentary/`, `add-generictext/`, `add-image/` | Kommentar, Hintergrundinfo, Bild (auch im Ablauf Ausformulieren) | 55bb5cb8 |
| `add-post/` | Post (auch im Ablauf Ausformulieren) | cc52f2e1 |
| `hier-fehlt-eine-antwort/` | Aussage vorab anlegen („Aussage anlegen“) | #431 |
| `destillieren/` | Satz. Ohne Absende-Knopf, weil er beim Tippen gespeichert wird: eigener Wortlaut `CONSENT_HINWEIS_SATZ` („Dein Satz wird beim Tippen gespeichert. Damit stellst du …“) über den Knöpfen | #431 |

Jedes dieser Formulare prüft den vollen Wortlaut samt Link im eigenen Komponententest (seit #431
auch Kommentar, Hintergrundinfo, Bild und Post; vorher nur den Link).

**Nutzungsbedingungen:** Die Behauptung, mit der Nutzung erkläre man sich einverstanden, ist
seit der Neufassung (20c1b06b) nicht mehr im Text. Unsere Einschätzung, nicht geprüft: Die
Einbeziehung soll der CC0-Hinweis im Formular tragen (§ 305 Abs. 2 BGB: ausdrücklicher Hinweis bei
Vertragsschluss), die Rechteeinräumung unter CC0 das Absenden als bewusste Handlung. Ob das trägt,
klärt #296; wer nie etwas absendet, sieht den Hinweis nicht, dafür ist #429 da.

**Nachweis:** Jeder Wortlaut hat eine Kennung; sie wird mit jedem neuen Beitrag (Qdrant-Payload),
Satz und Einwurf (PostgreSQL, `cc0_wortlaut`) gespeichert (Entscheidung 29.10.2026 in #439).
Wortlaute und Kennungen: `docs/CC0_HINWEIS_WORTLAUTE.md`. Bestand von davor hat keine Kennung.
Eine vorab angelegte Aussage trägt keine, weil sie kein Beitrag ist.
Datenschutzerklärung und Nutzungsbedingungen beschreiben das seit #222 (Kennung unter „Beiträge,
die du einstellst“, Freigabe beim Absenden und beim Satz beim Tippen in Abschnitt 4).

**Änderungen und Ersatzlizenz (#466):** Seit dem Stand vom 30. Oktober 2026 gelten geänderte
Nutzungsbedingungen erst nach ausdrücklicher Zustimmung beim Anmelden (§10, statt der früheren
Zustimmung durch Schweigen und Weiternutzen; BGH XI ZR 26/20). Dafür wird die Pflichtaktion aus
#429 je wesentlich geändertem Stand für alle Konten erneut ausgelöst, und alle werden abgemeldet;
reine Korrekturen gelten ohne erneute Zustimmung (Entscheidung Maintainer, 30.10.2026).
§4 räumt ein Nutzungsrecht ein, wo der CC0-Verzicht nach deutschem Recht nicht wirkt (Ersatzlizenz nach Abschnitt 3 der CC0-Erklärung).
Stände und Ablauf: `docs/nutzungsbedingungen-staende/`. Die Juristin prüft beide Stellen und die
Ausnahme für Korrekturen mit (#296); live erst danach.

**Offen:**
- Juristische Prüfung beider Wortlaute und der geänderten §4/§10: #296.
- Zustimmung beim ersten Anmelden mit persistentem Feld pro Person: #429.
- Herkunft: Im Kommentar- und Hintergrundinfo-Formular wird eine neue Herkunft schon beim
  Hinzufügen gespeichert (`reference-input.component.ts`, `POST /api/v1/references/add`), also vor
  dem Absenden, auf das sich der CC0-Hinweis bezieht. Nicht entschieden.

Der frühere Zusatzbefund (Platzhalter-Hinweis, `[Datum]`, Verweis auf „Community-Richtlinien“)
ist mit der Neufassung erledigt; seit #466 trägt die Stand-Zeile ein Tagesdatum (`docs/nutzungsbedingungen-staende/`).

---

## Bereits umgesetzt (PR #14)

Zwei Befunde sind erledigt, bevor die Texte geschrieben werden. Beide Vorgänge
existieren nicht mehr und müssen deshalb auch nicht beschrieben werden — die
Datenschutzerklärung wird dadurch kürzer, nicht länger.

| Befund | Was geändert wurde | Folge für den Text |
|--------|--------------------|--------------------|
| D-N10 Google Fonts | Roboto und Material Icons kommen aus `public/fonts/` statt von `fonts.googleapis.com` | Kein Drittlandtransfer beim Seitenaufruf mehr. Nichts zu ergänzen. Überholt, siehe X4: Bild-Adressen bleiben ein realer Fall, der Abschnitt ist konkretisiert statt gestrichen |
| D-N4 Suchprotokollierung | `query_text` und `ip_hash` ersatzlos entfernt (wurden geschrieben, nie gelesen). `user_id` und `session_id` ersetzt durch `actor_hash` = HMAC-SHA256 über Kennung + UTC-Datum | Der Volltext der Suchanfragen wird nicht mehr gespeichert, die IP nicht mehr verarbeitet |
| Zugriffsprotokolle (#275) | Der Webserver der Anwendung schreibt keinen Adresszusatz und keinen Referrer mehr (beide trugen den Suchtext aus `/result?searchQuery=…`), für die Suche selbst und für Aufrufe der Ergebnisseite keine Zeile und für fehlende Dateien keine Fehlerzeile. Browser schicken als Referrer nur noch den Ursprung (`src/index.html`) | **Seit #222 im Text:** „Zugriffe innerhalb der Anwendung“ nennt den Pfad ohne Suchtext, keine verweisende Seite und keine Zeile für Suche und Ergebnisseite; „Protokolle der Anwendung“ nimmt ältere Zeilen aus demselben Sammelstrom ausdrücklich aus (entfällt mit #315). Ältere Zeilen (vor #275) im selben Sammelstrom tragen Suchtexte, bis der Strom am Host rotiert oder geleert wird; „Protokolle der Anwendung … nicht, wonach jemand gesucht hat“ gilt für sie nicht (siehe `docs/LOESCHKONZEPT.md`, Frontend-nginx, Altbestand). „Zugriffe auf den vorgelagerten Webserver“ bleibt zutreffend (dessen Format steht nicht im Repo; offen, siehe `docs/LOESCHKONZEPT.md`, Logs) |

### Was zu `search_events` trotzdem noch in den Text muss

Die Verarbeitung ist kleiner geworden, aber nicht verschwunden. Zu beschreiben bleibt:

- **Dass** Suchvorgänge protokolliert werden — Trefferzahl, Zeitstempel, Pseudonym.
- **Wozu** — Reichweiten- und Nutzungsmessung für die Weiterentwicklung.
- **Dass das Pseudonym täglich wechselt** und Suchverhalten deshalb nicht über
  Tagesgrenzen hinweg zusammengeführt werden kann. Das ist die eigentliche Zusage
  an die Nutzenden und gehört ausdrücklich hinein, nicht nur implizit.
- **Rechtsgrundlage und Löschfrist** — Rechtsgrundlage offen (D-M6). Löschfrist seit
  #289: 90 Tage als Einzelzeilen, danach nur Tageszähler; im Text seit #222.

Ob die Angabe damit unter Art. 13 DSGVO überhaupt noch pflichtig ist, hängt daran,
ob man das Tagespseudonym als personenbezogen einstuft. Die ehrlichere Variante ist,
den Vorgang zu beschreiben, statt sich auf die Einstufung als anonym zu verlassen.

### Was sich dadurch **nicht** erledigt hat — überholt (04.09.2026)

Hier stand, `usage_events` sei unverändert und führe `user_id`, `ip_hash` und
`user_agent` weiter im Klartext. **Das trifft seit PR #27 nicht mehr zu**, siehe D-N4.

Die Schlussfolgerung für den Text bleibt trotzdem: „lediglich anonymisierte
Nutzungsstatistiken" wäre auch heute unzutreffend — nur trägt sie jetzt die
Sitzungskennung allein (X3). Der neue Text sagt deshalb „pseudonym", nicht „anonym".

---

## Offene Punkte, die den Text beeinflussen, aber noch in Arbeit sind

Einträge und Text des Abschnitts: [`offene-punkte/`](offene-punkte/)

---

## Reihenfolge zum Ausfüllen

1. ~~**Zuerst D1–D4 / I1–I4 klären**: Wer ist Anbieter und Verantwortlicher — Netzbegrünung e. V. oder
   der Maintainer als Privatperson?~~ **Entschieden 03.09.2026: Anbieter und Verantwortlicher
   ist NETZBEGRÜNUNG — Verein für grüne Netzkultur e. V.** Damit sind I1–I10 und I12/I13
   erledigt; D7–D11 und die AVV-Frage (D-N7) bleiben offen, weil die Datenschutzerklärung
   noch nicht überarbeitet ist.
2. ~~Danach die Kontaktdaten (I5–I6, D5–D6).~~ I5–I6 erledigt (03.09.2026), D5–D6 offen.
3. ~~Dann die Entscheidungen zu Streichen/Ersetzen (X1–X5, I-E).~~ Erledigt (04.09.2026).
4. ~~Zuletzt die neuen Abschnitte D-N1 bis D-N12 und die Fristen (D-M1).~~ Erledigt
   (04.09.2026), bis auf D-N11 (existiert noch nicht).

**Damit ist die Liste für Impressum, Nutzungsbedingungen und Datenschutzerklärung
abgearbeitet.** Was bleibt, sind die Punkte der Prüfliste unten, die Produkt- und
Codetickets aus dem Datenschutz-PR und die Zustimmung beim Anmelden aus Abschnitt 5 (#429).

---

## Offene Launch-Blocker (Stand 04.09.2026)

**Alle drei Rechtstexte sind ausformuliert.** Der Platzhaltertext der
Datenschutzerklärung ist ersetzt, der für Besucher sichtbare Platzhalter-Hinweis
entfernt. Die beiden früher hier geführten inhaltlichen Blocker sind aufgelöst:

- **D-N4** — erledigt und **am Code nachgeprüft** (04.09.2026, siehe
  `docs/archiv/DATENSCHUTZ_BESTANDSAUFNAHME.md`, Abschnitt 1.2): PR #27 hat die drei
  personenbeziehbaren Spalten entfernt. Die Textaussage ist neu formuliert und
  spricht jetzt von pseudonymer, nicht anonymer Messung.
- **D-N9** — erledigt: Der OpenAI-Pfad ist mit #393 aus dem Code entfernt, in
  Produktion war er nie aktiv. Erklärung und Nutzungsbedingungen erwähnen ihn nicht mehr.

**Was vor dem Launch bleibt:**

1. **Juristische Prüfung** der Datenschutzerklärung — die Punkte stehen unten in der
   Prüfliste. Diese Liste ist keine Rechtsberatung und ersetzt sie nicht.
2. **Die Consent-Frage aus Abschnitt 5** ist entschieden; der Hinweis in den Formularen
   steht (#431), die Zustimmung beim Anmelden fehlt noch (#429). Sie berührt den
   Datenschutz an einer Stelle mit: § 25 TDDDG (Prüfliste, Punkt 3).
3. **Eine USt-IdNr.-Rückfrage** im Impressum (I11).

Die Code- und Produkttickets, die sich aus dem Schreiben der Erklärung ergeben haben —
fehlende Löschfristen, der Retention-Bug, die Sichtbarkeit im Fangkorb, der
KI-Vorschlagsbutton ohne Key (mit #393 entfernt) — sind **keine** Launch-Blocker: die Erklärung beschreibt
den Ist-Zustand zutreffend. Sie stehen im Beschreibungstext des Datenschutz-PR.

---

## Prüfliste für die juristische Durchsicht der Datenschutzerklärung

Einträge und Text des Abschnitts: [`pruefliste/`](pruefliste/)
