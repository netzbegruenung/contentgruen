# ContentGrün — Rechtstexte: Lückenliste

Arbeitsdokument zur Überarbeitung von Impressum, Datenschutzerklärung und
Nutzungsbedingungen. Die Tabellen haben eine Eintrag-Spalte und sind zum Ausfüllen
gedacht — wer eine Angabe klärt, trägt sie hier ein.

**Dies ist keine Rechtsberatung.** Die Zuordnung Pflicht/optional ist eine
Arbeitsgrundlage, damit die offenen Punkte sichtbar sind; die fertigen Texte gehören
vor Veröffentlichung durch jemanden mit juristischer Qualifikation geprüft.

Stand der Analyse: 2026-08-19
Geprüfte Dateien:
- `mvp/frontend/contentgruen-frontend/src/app/impressum/impressum.component.html` (14 Platzhalter)
- `mvp/frontend/contentgruen-frontend/src/app/datenschutz/datenschutz.component.html` (12 Platzhalter)
- (Kontext) `.../nutzungsbedingungen/nutzungsbedingungen.component.html` (1 Platzhalter)

Gesamt: 26 Platzhalter in den beiden Hauptdateien.

Legende Pflicht-Spalte:
- PFLICHT = gesetzlich zwingend
- BEDINGT = nur zwingend, wenn der Sachverhalt zutrifft (z. B. Registereintrag vorhanden)
- OPTIONAL = kann ersatzlos gestrichen werden

---

## 1. IMPRESSUM — impressum.component.html

| # | Zeile | Platzhalter | Kontext / wofür | Pflicht? | Eintrag |
|---|-------|-------------|-----------------|----------|---------|
| I1 | 11 | `[Vollständiger Name/Organisation]` | „Anbieter" — Blockadresse | **PFLICHT** § 5 Abs. 1 Nr. 1 DDG | ______________ |
| I2 | 12 | `[Straße und Hausnummer]` | „Anbieter" — ladungsfähige Anschrift | **PFLICHT** § 5 Abs. 1 Nr. 1 DDG | ______________ |
| I3 | 13 | `[PLZ]` | „Anbieter" | **PFLICHT** § 5 Abs. 1 Nr. 1 DDG | ______________ |
| I4 | 13 | `[Ort]` | „Anbieter" | **PFLICHT** § 5 Abs. 1 Nr. 1 DDG | ______________ |
| I5 | 23 | `[Telefonnummer]` | „Kontakt: **Telefon:** …" | OPTIONAL* | ______________ |
| I6 | 24 | `[E-Mail-Adresse]` | „Kontakt: **E-Mail:** …" | **PFLICHT** § 5 Abs. 1 Nr. 2 DDG | ______________ |
| I7 | 34 | `[Name der vertretungsberechtigten Person(en)]` | „Vertreten durch" | **BEDINGT** § 5 Abs. 1 Nr. 1 DDG (bei jur. Person zwingend) | ______________ |
| I8 | 35 | `[Position/Funktion]` | „Vertreten durch" — Zeile unter dem Namen | OPTIONAL | ______________ |
| I9 | 44 | `[Amtsgericht Ort]` | „Register…: **Registergericht:**" | **BEDINGT** § 5 Abs. 1 Nr. 4 DDG (nur bei Registereintrag) | ______________ |
| I10 | 45 | `[HRB/VR Nummer]` | „**Registernummer:**" | **BEDINGT** § 5 Abs. 1 Nr. 4 DDG | ______________ |
| I11 | 55 | `[DE-Nummer]` | „USt-IdNr. gemäß § 27a UStG" | **BEDINGT** § 5 Abs. 1 Nr. 6 DDG (nur wenn vorhanden) | ______________ |
| I12 | 64 | `[Name der verantwortlichen Person]` | „Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV" | **BEDINGT** § 18 Abs. 2 MStV (bei journalistisch-redaktionellen Angeboten) | ______________ |
| I13 | 65 | `[Anschrift wie oben]` | Anschrift der inhaltlich verantwortlichen Person | **BEDINGT** § 18 Abs. 2 MStV | ______________ |
| I14 | 136 | `[Datum der letzten Aktualisierung]` | „**Stand:**" im Update-Hinweis | OPTIONAL | ______________ |

\* I5 Telefon: § 5 Abs. 1 Nr. 2 DDG verlangt „Angaben, die eine schnelle elektronische Kontaktaufnahme
und unmittelbare Kommunikation ermöglichen". E-Mail allein genügt nach EuGH C-298/07, wenn ein
zweiter schneller Kanal (z. B. Rückrufformular) besteht. Telefonnummer ist der sichere Weg — wenn
keine da ist, Zeile streichen statt leer lassen.

### Weitere Befunde im Impressum (keine Platzhalter, aber zu korrigieren)

| # | Zeile | Befund |
|---|-------|--------|
| I-A | 4 | Untertitel „Angaben gemäß § 5 TMG" — **TMG ist seit 14.05.2024 aufgehoben**, korrekt: § 5 DDG |
| I-B | 78–79 | „§ 7 Abs. 1 TMG" / „§§ 8 bis 10 TMG" — jetzt §§ 7–10 DDG (inhaltsgleich, aber falsche Fundstelle) |
| I-C | 62 | „§ 55 Abs. 2 RStV" — RStV ist seit 07.11.2020 durch den MStV ersetzt, korrekt: § 18 Abs. 2 MStV |
| I-D | 25 | Verlinkt `contentgruen.de` — Produktivdomain ist laut `docs/ARCHITECTURE.md:32` `contentgruen.netzbegruenung.de`. Prüfen, welche Domain im Impressum stehen soll |
| I-E | 119–132 | „Streitschlichtung" verweist auf die **OS-Plattform der EU-Kommission — diese wurde zum 20.07.2025 eingestellt**. Der Link geht ins Leere. Für ein nicht-kommerzielles Angebot ohne Verbraucherverträge ist der ganze Abschnitt entbehrlich → **Kandidat zum Streichen** |
| I-F | 137–140 | Sichtbarer Platzhalter-Hinweis („Dies ist ein Platzhalter-Impressum…") ist im Produktivbetrieb **live sichtbar** — muss weg |

---

## 2. DATENSCHUTZERKLÄRUNG — datenschutz.component.html

| # | Zeile | Platzhalter | Kontext / wofür | Pflicht? | Eintrag |
|---|-------|-------------|-----------------|----------|---------|
| D1 | 54 | `[Name/Organisation]` | „verantwortliche Stelle für die Datenverarbeitung ist:" | **PFLICHT** Art. 13 Abs. 1 lit. a DSGVO | ______________ |
| D2 | 55 | `[Straße und Hausnummer]` | Anschrift Verantwortlicher | **PFLICHT** Art. 13 Abs. 1 lit. a DSGVO | ______________ |
| D3 | 56 | `[PLZ]` | Anschrift Verantwortlicher | **PFLICHT** Art. 13 Abs. 1 lit. a DSGVO | ______________ |
| D4 | 56 | `[Ort]` | Anschrift Verantwortlicher | **PFLICHT** Art. 13 Abs. 1 lit. a DSGVO | ______________ |
| D5 | 58 | `[Telefonnummer]` | „Telefon:" Verantwortlicher | OPTIONAL | ______________ |
| D6 | 59 | `[E-Mail-Adresse]` | „E-Mail:" Verantwortlicher | **PFLICHT** (praktisch: Kontaktweg für Betroffenenrechte) | ______________ |
| D7 | 80 | `[Name der Landesbehörde]` | „zuständige Aufsichtsbehörde ist:" | OPTIONAL** | ______________ |
| D8 | 81 | `[Anschrift]` | Anschrift Aufsichtsbehörde | OPTIONAL** | ______________ |
| D9 | 82 | `[PLZ]` | Aufsichtsbehörde | OPTIONAL** | ______________ |
| D10 | 82 | `[Ort]` | Aufsichtsbehörde | OPTIONAL** | ______________ |
| D11 | 84 | `[URL der Behörde]` | „Webseite:" Aufsichtsbehörde | OPTIONAL** | ______________ |
| D12 | 232 | `[Datum der letzten Aktualisierung]` | „**Stand:**" | OPTIONAL | ______________ |

\*\* D7–D11: Art. 13 Abs. 2 lit. d DSGVO verlangt nur den **Hinweis auf das Beschwerderecht**, nicht die
Nennung einer konkreten Behörde. Der Abschnitt kann also auch auf den reinen Rechtehinweis reduziert
werden. Falls ausgefüllt: zuständig ist die Aufsichtsbehörde am Sitz des Verantwortlichen (D1–D4) —
also erst D1 klären, dann D7.

### FEHLENDE Pflichtangaben nach Art. 13 DSGVO (keine Platzhalter — die Abschnitte fehlen komplett)

| # | Fehlt | Rechtsgrundlage | Eintrag / Entscheidung |
|---|-------|-----------------|------------------------|
| D-M1 | **Speicherdauer / Löschfristen** je Verarbeitung — kommt im gesamten Dokument nicht vor | Art. 13 Abs. 2 lit. a DSGVO — **PFLICHT** | Server-Logs: ___ Tage · Suchverlauf: ___ · Beiträge: ___ · Accounts: ___ |
| D-M2 | **Datenschutzbeauftragter** (Kontaktdaten oder Feststellung, dass keiner benannt ist) | Art. 13 Abs. 1 lit. b DSGVO — BEDINGT | ☐ keiner benannt ☐ Name/Kontakt: ______ |
| D-M3 | **Empfänger / Auftragsverarbeiter** — Hoster, IdP, Dritte | Art. 13 Abs. 1 lit. e DSGVO — **PFLICHT** | siehe Abschnitt 4 unten |
| D-M4 | **Drittlandtransfer** + Garantien | Art. 13 Abs. 1 lit. f DSGVO — BEDINGT (trifft zu, s. u.) | siehe D-N2, D-N6 |
| D-M5 | **Widerspruchsrecht Art. 21 DSGVO** — fehlt in Abschnitt 6, obwohl Verarbeitungen auf Art. 6 Abs. 1 lit. f gestützt werden (Z. 123, 169) | Art. 13 Abs. 2 lit. b / Art. 21 Abs. 4 DSGVO — **PFLICHT**, hervorgehoben darzustellen | — |
| D-M6 | **Rechtsgrundlage** für Account, Beiträge, Suche — nur die Server-Logs (Z. 123) und Dritt-Inhalte (Z. 169) nennen eine | Art. 13 Abs. 1 lit. c DSGVO — **PFLICHT** | Vertrag/Nutzungsverhältnis Art. 6 Abs. 1 lit. b? Berechtigtes Interesse lit. f? |
| D-M7 | **Erforderlichkeit der Bereitstellung** (freiwillig vs. Voraussetzung der Nutzung) | Art. 13 Abs. 2 lit. e DSGVO — **PFLICHT** | — |
| D-M8 | **Automatisierte Entscheidungsfindung / Profiling** — Feststellung, dass keine stattfindet | Art. 13 Abs. 2 lit. f DSGVO — PFLICHT (auch als Negativaussage üblich) | ☐ findet nicht statt |

---

## 3. Beschriebene Vorgänge, die es in ContentGrün NICHT gibt

| # | Zeile | Abschnitt | Befund | Empfehlung |
|---|-------|-----------|--------|------------|
| X1 | 126–140 | **„Registrierung auf dieser Website"** | Es gibt **keine Selbstregistrierung**. `app.routes.ts` hat keine Register-Route; `login-selector.component.html:9` sagt wörtlich „Aktuell ist keine Selbstregistrierung möglich". Zugang läuft über Netzbegrünung-Keycloak-SSO oder manuell angelegte Beta-Accounts (Mail an accounts@contentgruen.de). Die Liste „Benutzername / E-Mail / Passwort / Zeitpunkt der Registrierung" beschreibt eine Erhebung, die so nicht existiert | **Ersetzen** durch „Anmeldung und Nutzerkonto" (s. D-N1) |
| X2 | 26–27 | „…Daten, die Sie in ein **Kontaktformular** eingeben" | Es gibt kein Kontaktformular im Frontend (grep: kein Treffer außerhalb dieses Textes). Kontakt läuft per `mailto:` | Formulierung ersetzen: Anmeldedaten, Beitragsinhalte, Meldungen |
| X3 | 152–159 | **„4. Analyse-Tools und Werbung"** | Zwei Aussagen: „keine Analyse-Tools von Drittanbietern" ✓ zutreffend. „**Wir erheben lediglich anonymisierte Nutzungsstatistiken**" war für beide Ereignistabellen falsch. Für `search_events` stimmt die Aussage seit PR #14 weitgehend (nur noch Tagespseudonym + Trefferzahl). Für **`usage_events` gilt sie weiterhin nicht**: dort stehen `user_id`, `session_id`, `ip_hash` und `user_agent` unverändert im Klartext (`infrastructure/database/models.py:68–83`) | **Umschreiben**, nicht streichen — siehe D-N4 |
| X4 | 164–177 | **„5. Plugins und Tools / Einbindung von Diensten Dritter"** | Abstrakt und ohne Ross und Reiter. Der einzige reale Fall ist Google Fonts (`index.html:10–11`, zwei `fonts.googleapis.com`-Links) — den benennt der Text nicht | **Konkretisieren** (D-N7) oder Fonts lokal ausliefern und Abschnitt streichen |
| X5 | 93–106 | „Cookies" | Beschreibt „Sitzungscookies" und „Authentifizierungscookies". Auth-Cookie existiert (.NET-Cookie-Auth im BFF) ✓. Nicht erwähnt: die App nutzt **localStorage**, nicht nur Cookies — Session-ID (`services/session.service.ts:40`), Suche (`services/search.service.ts:29–37`), `contentgruen-metrics-seen` (`metrics/metrics.component.ts:35`), plus sessionStorage für Profilbild/Return-URL | **Ergänzen** um localStorage/sessionStorage (§ 25 TDDDG gilt für jede Endgerätespeicherung, nicht nur Cookies) |
| X6 | — | Newsletter | Kommt im Text nicht vor und existiert nicht — ✓ keine Aktion |
| X7 | — | Social Plugins | Kommen im Text nicht vor und existieren nicht — ✓ keine Aktion |

---

## 4. Reale Vorgänge, die im Text FEHLEN

| # | Vorgang | Fundstelle im Code | Was in den Text muss | Eintrag / Entscheidung |
|---|---------|--------------------|----------------------|------------------------|
| D-N1 | **Keycloak-SSO über Netzbegrünung** | `login-selector.component.html:26`, `BFF/Program.cs:73` (Scope `email`), `docs/AUTH_REGISTRIERUNG_OPTIONEN.md:665` | IdP benennen, übermittelte Claims (`sub`, `email`, Name), Verantwortlichkeitsabgrenzung bzw. AV-Vertrag mit Netzbegrünung/Verdigado | Betreiber-Realm ☐ eigener ☐ fremder · AVV vorhanden? ☐ |
| D-N2 | **Managed Login (ContentGrün-Account)** | `BFF/Controllers/AuthController.cs:45–98`, `BFF/Models/ManagedUser.cs` | E-Mail + Passwort-Hash, manuell durch Admins angelegt, keine Selbstregistrierung; Rate-Limiting bei Fehlversuchen (`ManagedUserService.cs:82–113`) | Speicherdauer nach Account-Ende: ___ |
| D-N3 | **Beitrags-, Bewertungs- und Bilddaten** | `domain/models/base_content.py:82–95` — `original_author`, `last_modified_by`, `authors[]`, `edit_history[]`, `created`, `last_modified` | Autorenname und **vollständige Bearbeitungshistorie** werden dauerhaft am Inhalt gespeichert und sind anderen Nutzenden sichtbar. Der jetzige Text (Z. 142–147) nennt nur „Kommentar + Zeitpunkt + Nutzername" — Edit-History fehlt | Sichtbarkeit: ☐ nur intern ☐ öffentlich |
| D-N4 | **Nutzungsprotokollierung** (`usage_events`) | `infrastructure/database/models.py:68–83`: content_id, user_id, session_id, ip_hash, user_agent; dazu `:33–42` (`usage_tracking`) | Bei jedem Kopieren/Verwenden eines Inhalts wird festgehalten, **wer welchen Beitrag wann genutzt hat**, inklusive User-Agent und IP-Hash. Steht bisher nirgends im Text. Von PR #14 **nicht** berührt — die Änderung betraf nur `search_events` | Zweck: ___ · Rechtsgrundlage: ___ · Löschfrist: ___ |
| D-N4b | **Suchprotokollierung** (`search_events`) | `infrastructure/database/models.py:96–118`, `services/search_tracking_service.py` | Seit PR #14 nur noch Trefferzahl, Zeitstempel und ein täglich rotierendes Pseudonym (HMAC-SHA256 über Nutzer-/Session-Kennung + UTC-Datum). Kein Suchtext, keine IP, keine Kennung mehr. Zu beschreiben bleibt: **dass** protokolliert wird, wozu (Reichweitenmessung), und dass das Pseudonym täglich wechselt | Zweck: ___ · Löschfrist: ___ |
| D-N5 | **Melde-/Moderationsfunktion** | `infrastructure/database/models.py:122–139` (`content_reports`), `shared/components/report-dialog/` | Freitext-Meldung + meldende Person + Moderationsentscheidung + Prüfer werden gespeichert | Löschfrist: ___ |
| D-N6 | **Speicherung in Qdrant + PostgreSQL** | `docs/ARCHITECTURE.md`, `mvp/docker-compose.prd.yml` | Konkrete Speicherorte benennen (Vektordatenbank Qdrant, PostgreSQL), beides selbst gehostet auf der Verdigado-/Hetzner-Infrastruktur | — |
| D-N7 | **Hosting** | `docs/DEPLOYMENT.md:65` (Hetzner VPS), `:113` + `docs/ARCHITECTURE.md:143` (`contentgruen.netzbegruenung.verdigado.net`, SaltStack durch Verdigado) | Hoster/Betreiber der Infrastruktur benennen, **AV-Vertrag nach Art. 28 DSGVO** (auch `docs/AUTH_REGISTRIERUNG_OPTIONEN.md:372` fordert das ausdrücklich) | AVV Verdigado ☐ · AVV Hetzner ☐ |
| D-N8 | **Embedding-Verarbeitung** | `services/embeddings/qdrant_embeddings_manager.py:102` — `SentenceTransformer("intfloat/multilingual-e5-base")` | **Entlastend**: läuft lokal im eigenen Container, keine Übermittlung an Dritte. Suchanfragen und Beitragstexte werden in Vektoren umgerechnet und in Qdrant gespeichert | — |
| D-N9 | **KI-Bildbeschreibung über OpenAI** ⚠️ | `services/vision/caption_suggestion_service.py:16` (`gpt-4o-mini`), `services/vision/image_description_worker.py`, `domain/content_registry.py:108–118`, `docs/ROADMAP.md:124` | **Hochgeladene Bilder werden an OpenAI (USA) übermittelt**, wenn `OPENAI_API_KEY` gesetzt ist. Das ist ein Drittlandtransfer und fehlt komplett. Hinweis: in `docker-compose.prd.yml`/`.tst.yml` ist derzeit **kein** `OPENAI`-Env gesetzt — also aktuell wohl inaktiv, aber der Code ist live | Aktiv in Prod? ☐ ja ☐ nein · Falls ja: AVV + Art. 46 DSGVO-Garantien nötig |
| D-N10 | ~~**Google Fonts vom CDN**~~ ✅ | vormals `src/index.html:10–11` | **Erledigt durch PR #14.** Roboto und Material Icons liegen in `public/fonts/`, die `@font-face`-Regeln in `src/styles/fonts.css`. Es geht keine IP mehr an Google. Im Text ist daher **nichts** zu ergänzen — der Vorgang existiert nicht mehr | — |
| D-N11 | **Geplante KI-Analyse von Beitragstexten** | `docs/ROADMAP.md:15, 104–107` | Erst dokumentieren, wenn implementiert — aber jetzt schon entscheiden, ob dafür eine Einwilligung eingeholt werden muss | ☐ später ☐ jetzt vorbereiten |
| D-N12 | **Nutzung ohne Anmeldung** | `app.routes.ts` — `PublicGuard` auf `/search`, `/result`, `/about` | Anonyme Nutzung ist möglich; auch dabei laufen `search_events` und `usage_events` mit Session-ID mit. Der Text unterscheidet nirgends zwischen angemeldeter und anonymer Nutzung | — |

---

## 5. Consent-Checkbox / Verweis auf Nutzungsbedingungen

**Ergebnis: existiert nicht.** Weder im Anmelde- noch in einem Beitragsformular.

| Ort | Befund |
|-----|--------|
| `login/login.component.html` | Reines Formular (E-Mail/Benutzername, Passwort, Button). Kein Checkbox-Element, kein Link auf Nutzungsbedingungen oder Datenschutz |
| `login/login-selector.component.html` | Zwei Login-Buttons + Info-Panel zur Zugangsbeschaffung. Kein Consent-Element |
| `contribute-view/`, `workflow/add-commentary`, `workflow/add-generictext`, `workflow/add-image` | Kein `mat-checkbox`, kein Hinweistext auf Nutzungsbedingungen (repo-weiter grep über `app/` nach `mat-checkbox|consent|einwillig|zustimm|akzeptier|nutzungsbedingung`: **kein einziger Treffer** außerhalb der Rechtstext-Seiten selbst) |
| `footer/footer.component.html:25–27` | **Einziger** Verweis auf die Nutzungsbedingungen im gesamten Frontend — als Footer-Link |

**Konflikt:** `nutzungsbedingungen.component.html:16` behauptet, mit der Nutzung erkläre man sich
„mit diesen Nutzungsbedingungen einverstanden". Ein reiner Footer-Link trägt diese Einbeziehung
nicht (§ 305 Abs. 2 BGB verlangt einen ausdrücklichen Hinweis bei Vertragsschluss). Für die
Beitragsfunktion kommt hinzu, dass dort eine **Rechteeinräumung** an den Betreiber erklärt werden
soll — die braucht eine bewusste Handlung.

**Zu entscheiden:**
- ☐ Checkbox beim ersten Login („Ich habe die Nutzungsbedingungen und die Datenschutzerklärung gelesen") — braucht persistentes Feld pro Nutzer, das es aktuell nicht gibt
- ☐ Hinweistext im Beitragsformular über dem Absende-Button (ohne Checkbox, „Mit dem Absenden akzeptierst du …")
- ☐ Beides
- ☐ Vorerst nichts

**Zusatzbefund:** Auch die Nutzungsbedingungen tragen einen sichtbaren Platzhalter-Hinweis
(`nutzungsbedingungen.component.html:264`) und einen offenen `[Datum]`-Platzhalter (Z. 1 Treffer) —
sowie in Z. 254 einen Verweis auf „Community-Richtlinien", die es als Seite nicht gibt.

---

## Bereits umgesetzt (PR #14)

Zwei Befunde sind erledigt, bevor die Texte geschrieben werden. Beide Vorgänge
existieren nicht mehr und müssen deshalb auch nicht beschrieben werden — die
Datenschutzerklärung wird dadurch kürzer, nicht länger.

| Befund | Was geändert wurde | Folge für den Text |
|--------|--------------------|--------------------|
| D-N10 Google Fonts | Roboto und Material Icons kommen aus `public/fonts/` statt von `fonts.googleapis.com` | Kein Drittlandtransfer beim Seitenaufruf mehr. Nichts zu ergänzen. Falls X4 („Einbindung von Diensten Dritter") ausformuliert werden sollte: es bleibt **kein** realer Anwendungsfall übrig, der Abschnitt kann ersatzlos gestrichen werden |
| D-N4 Suchprotokollierung | `query_text` und `ip_hash` ersatzlos entfernt (wurden geschrieben, nie gelesen). `user_id` und `session_id` ersetzt durch `actor_hash` = HMAC-SHA256 über Kennung + UTC-Datum | Der Volltext der Suchanfragen wird nicht mehr gespeichert, die IP nicht mehr verarbeitet |

### Was zu `search_events` trotzdem noch in den Text muss

Die Verarbeitung ist kleiner geworden, aber nicht verschwunden. Zu beschreiben bleibt:

- **Dass** Suchvorgänge protokolliert werden — Trefferzahl, Zeitstempel, Pseudonym.
- **Wozu** — Reichweiten- und Nutzungsmessung für die Weiterentwicklung.
- **Dass das Pseudonym täglich wechselt** und Suchverhalten deshalb nicht über
  Tagesgrenzen hinweg zusammengeführt werden kann. Das ist die eigentliche Zusage
  an die Nutzenden und gehört ausdrücklich hinein, nicht nur implizit.
- **Rechtsgrundlage und Löschfrist** — weiterhin offen, siehe D-M1 und D-M6.

Ob die Angabe damit unter Art. 13 DSGVO überhaupt noch pflichtig ist, hängt daran,
ob man das Tagespseudonym als personenbezogen einstuft. Die ehrlichere Variante ist,
den Vorgang zu beschreiben, statt sich auf die Einstufung als anonym zu verlassen.

### Was sich dadurch **nicht** erledigt hat

`usage_events` ist unverändert (siehe D-N4). Dort stehen `user_id`, `session_id`,
`ip_hash` und `user_agent` weiter im Klartext, verknüpft mit dem genutzten Beitrag.
Die Aussage in Abschnitt 4 der Datenschutzerklärung („lediglich anonymisierte
Nutzungsstatistiken") ist deswegen nach wie vor unzutreffend.

---

## Offene Punkte, die den Text beeinflussen, aber noch in Arbeit sind

Hier nur vermerkt, damit sie beim Schreiben nicht vergessen werden. **Noch nicht
ausformulieren** — der Stand ändert sich gerade.

| # | Punkt | Stand |
|---|-------|-------|
| O1 | **Suchanfragen werden als Statements gespeichert** — jede Suchanfrage landet zusätzlich als eigener Inhalt in Qdrant (`api/v1/search.py`) | Wird gerade geändert: der Autor entfällt, die Statements bekommen einen eigenen `origin`-Wert. Erst wenn das steht, lässt sich sagen, was die Datenschutzerklärung dazu sagen muss |

---

## Reihenfolge zum Ausfüllen

1. **Zuerst D1–D4 / I1–I4 klären**: Wer ist Anbieter und Verantwortlicher — Netzbegrünung e. V. oder
   Sebastian Banach als Privatperson? Davon hängen I7–I13, D7–D11 und die AVV-Frage (D-N7) ab.
2. Danach die Kontaktdaten (I5–I6, D5–D6).
3. Dann die Entscheidungen zu Streichen/Ersetzen (X1–X5, I-E).
4. Zuletzt die neuen Abschnitte D-N1 bis D-N12 und die Fristen (D-M1).

Blocker für einen echten Produktivbetrieb, unabhängig vom Ausfüllen:
**D-N4** (`usage_events` protokolliert personenbezogen und der Text behauptet das
Gegenteil) und **D-N9** (OpenAI-Bildbeschreibung, falls in Prod aktiviert).
D-N10 (Google Fonts) ist mit PR #14 erledigt, die Suchprotokollierung aus D-N4
weitgehend entschärft.
