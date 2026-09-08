# ContentGrün — Rechtstexte: Lückenliste

Arbeitsdokument zur Überarbeitung von Impressum, Datenschutzerklärung und
Nutzungsbedingungen. Die Tabellen haben eine Eintrag-Spalte und sind zum Ausfüllen
gedacht — wer eine Angabe klärt, trägt sie hier ein.

**Dies ist keine Rechtsberatung.** Die Zuordnung Pflicht/optional ist eine
Arbeitsgrundlage, damit die offenen Punkte sichtbar sind; die fertigen Texte gehören
vor Veröffentlichung durch jemanden mit juristischer Qualifikation geprüft.

Stand der Analyse: 2026-08-19
Zeilenangaben beziehen sich auf den Stand vom 19.08.2026; die Neufassung in diesem
Branch weicht davon ab.
Geprüfte Dateien:
- `mvp/frontend/contentgruen-frontend/src/app/impressum/impressum.component.html` (14 Platzhalter)
- `mvp/frontend/contentgruen-frontend/src/app/datenschutz/datenschutz.component.html` (12 Platzhalter)
- (Kontext) `.../nutzungsbedingungen/nutzungsbedingungen.component.html` (1 Platzhalter)

Gesamt: 26 Platzhalter in den beiden Hauptdateien. **Stand 04.09.2026: keiner davon ist
mehr offen** — alle drei Texte sind ausformuliert, die Datenschutzerklärung zuletzt. Die
Tabellen bleiben stehen, weil in der Eintrag-Spalte steht, wie der jeweilige Punkt gelöst
wurde; sie sind jetzt Nachweis statt Arbeitsvorrat. Offen sind noch die Consent-Frage
(Abschnitt 5), die USt-IdNr. im Impressum (I11) und die Prüfliste am Ende.

Legende Pflicht-Spalte:
- PFLICHT = gesetzlich zwingend
- BEDINGT = nur zwingend, wenn der Sachverhalt zutrifft (z. B. Registereintrag vorhanden)
- OPTIONAL = kann ersatzlos gestrichen werden

---

## 1. IMPRESSUM — impressum.component.html

| # | Zeile | Platzhalter | Kontext / wofür | Pflicht? | Eintrag |
|---|-------|-------------|-----------------|----------|---------|
| I1 | 11 | `[Vollständiger Name/Organisation]` | „Anbieter" — Blockadresse | **PFLICHT** § 5 Abs. 1 Nr. 1 DDG | ✓ NETZBEGRÜNUNG — Verein für grüne Netzkultur e. V. (c/o Max Pfeuffer) |
| I2 | 12 | `[Straße und Hausnummer]` | „Anbieter" — ladungsfähige Anschrift | **PFLICHT** § 5 Abs. 1 Nr. 1 DDG | ✓ Heilig-Kreuz-Straße 16 |
| I3 | 13 | `[PLZ]` | „Anbieter" | **PFLICHT** § 5 Abs. 1 Nr. 1 DDG | ✓ 86609 |
| I4 | 13 | `[Ort]` | „Anbieter" | **PFLICHT** § 5 Abs. 1 Nr. 1 DDG | ✓ Donauwörth |
| I5 | 23 | `[Telefonnummer]` | „Kontakt: **Telefon:** …" | OPTIONAL* | ✓ +49 906 299940-0 |
| I6 | 24 | `[E-Mail-Adresse]` | „Kontakt: **E-Mail:** …" | **PFLICHT** § 5 Abs. 1 Nr. 2 DDG | ✓ backoffice@netzbegruenung.de |
| I7 | 34 | `[Name der vertretungsberechtigten Person(en)]` | „Vertreten durch" | **BEDINGT** § 5 Abs. 1 Nr. 1 DDG (bei jur. Person zwingend) | ✓ Jennifer Herbert, Korbinian Gall |
| I8 | 35 | `[Position/Funktion]` | „Vertreten durch" — Zeile unter dem Namen | OPTIONAL | ✓ Vertretungsberechtigter Vorstand nach § 26 BGB |
| I9 | 44 | `[Amtsgericht Ort]` | „Register…: **Registergericht:**" | **BEDINGT** § 5 Abs. 1 Nr. 4 DDG (nur bei Registereintrag) | ✓ Amtsgericht Augsburg |
| I10 | 45 | `[HRB/VR Nummer]` | „**Registernummer:**" | **BEDINGT** § 5 Abs. 1 Nr. 4 DDG | ✓ VR 201634 |
| I11 | — | — (Abschnitt mit der Neufassung entfallen) | USt-IdNr. gemäß § 27a UStG | **BEDINGT** § 5 Abs. 1 Nr. 6 DDG (nur wenn vorhanden) | **offen** — Rückfrage an Vorstand: hat der Verein eine USt-IdNr.? Falls ja, ist sie nach § 5 Abs. 1 Nr. 6 DDG aufzunehmen |
| I12 | 64 | `[Name der verantwortlichen Person]` | „Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV" | **BEDINGT** § 18 Abs. 2 MStV (bei journalistisch-redaktionellen Angeboten) | ✓ Sebastian Banach |
| I13 | 65 | `[Anschrift wie oben]` | Anschrift der inhaltlich verantwortlichen Person | **BEDINGT** § 18 Abs. 2 MStV | ✓ Anschrift wie oben (Vereinsanschrift) |
| I14 | 136 | `[Datum der letzten Aktualisierung]` | „**Stand:**" im Update-Hinweis | OPTIONAL | ✓ September 2026 |

**I1–I10, I12 und I13 sind erledigt (03.09.2026).** Die Angaben sind vom Vorstand
bestätigt (Quelle: Korbinian Gall, 03.09.2026) und in `impressum.component.html`
sowie `impressum.component.ts` eingetragen. Damit ist auch die Grundsatzfrage aus
„Reihenfolge zum Ausfüllen" Nr. 1 entschieden: Anbieter ist der Verein, nicht
Sebastian Banach als Privatperson. Er ist ausschließlich nach § 18 Abs. 2 MStV
inhaltlich verantwortlich (I12/I13), unter der Vereinsanschrift.
I14 ist mit „September 2026" ebenfalls erledigt. Offen bleibt allein I11: Der
Abschnitt zur USt-IdNr. ist mit der Neufassung entfallen — zu klären ist per
Rückfrage an den Vorstand, ob der Verein eine USt-IdNr. hat; falls ja, ist sie
nach § 5 Abs. 1 Nr. 6 DDG wieder aufzunehmen.

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
| D1 | — | `[Name/Organisation]` | „Verantwortlicher" | **PFLICHT** Art. 13 Abs. 1 lit. a DSGVO | ✓ NETZBEGRÜNUNG — Verein für grüne Netzkultur e. V. |
| D2 | — | `[Straße und Hausnummer]` | Anschrift Verantwortlicher | **PFLICHT** Art. 13 Abs. 1 lit. a DSGVO | ✓ c/o Max Pfeuffer, Heilig-Kreuz-Straße 16 |
| D3 | — | `[PLZ]` | Anschrift Verantwortlicher | **PFLICHT** Art. 13 Abs. 1 lit. a DSGVO | ✓ 86609 |
| D4 | — | `[Ort]` | Anschrift Verantwortlicher | **PFLICHT** Art. 13 Abs. 1 lit. a DSGVO | ✓ Donauwörth |
| D5 | — | `[Telefonnummer]` | „Telefon:" Verantwortlicher | OPTIONAL | ✓ +49 906 299940-0 |
| D6 | — | `[E-Mail-Adresse]` | „E-Mail:" Verantwortlicher | **PFLICHT** (praktisch: Kontaktweg für Betroffenenrechte) | ✓ backoffice@netzbegruenung.de (Feld `KONTAKT_MAIL`) |
| D7 | — | `[Name der Landesbehörde]` | „zuständige Aufsichtsbehörde ist:" | OPTIONAL** | ✓ Bayerisches Landesamt für Datenschutzaufsicht (BayLDA) (Feld `BEHOERDE_NAME`) |
| D8 | — | `[Anschrift]` | Anschrift Aufsichtsbehörde | OPTIONAL** | ✓ Promenade 18 (Feld `BEHOERDE_ANSCHRIFT`) |
| D9 | — | `[PLZ]` | Aufsichtsbehörde | OPTIONAL** | ✓ 91522 |
| D10 | — | `[Ort]` | Aufsichtsbehörde | OPTIONAL** | ✓ Ansbach |
| D11 | — | `[URL der Behörde]` | „Webseite:" Aufsichtsbehörde | OPTIONAL** | ✓ https://www.lda.bayern.de (Feld `BEHOERDE_URL`), plus Telefon und Hinweis auf das Online-Formular |
| D12 | — | `[Datum der letzten Aktualisierung]` | „**Stand:**" | OPTIONAL | ✓ September 2026 |

\*\* D7–D11: Art. 13 Abs. 2 lit. d DSGVO verlangt nur den **Hinweis auf das Beschwerderecht**, nicht die
Nennung einer konkreten Behörde. Entschieden wurde, sie trotzdem zu nennen — das ist
nutzerfreundlicher, und der Sitz des Vereins ändert sich selten.

**D1–D12 sind erledigt (04.09.2026).** Die Zeilenangaben der Spalte „Zeile" beziehen sich auf
den alten Platzhaltertext und sind gegenstandslos: `datenschutz.component.html` ist
vollständig neu geschrieben. Adressen und Behörde stehen als Felder in
`datenschutz.component.ts`, alles Übrige literal im Template — dasselbe Muster wie im
Impressum. Der für Besucher sichtbare Platzhalter-Hinweis ist entfernt.

**Zur Zuständigkeit (D7):** Der Verein sitzt in Donauwörth, das Vereinsregister liegt beim
Amtsgericht Augsburg — beides Bayern; für nichtöffentliche Stellen ist dort das BayLDA
zuständig. Die Anschrift ist die vom Vorstand gelieferte (04.09.2026); wir haben sie nicht
gegen das Behördenverzeichnis gegengeprüft.

### FEHLENDE Pflichtangaben nach Art. 13 DSGVO (keine Platzhalter — die Abschnitte fehlen komplett)

| # | Fehlt | Rechtsgrundlage | Eintrag / Entscheidung |
|---|-------|-----------------|------------------------|
| D-M1 | **Speicherdauer / Löschfristen** je Verarbeitung | Art. 13 Abs. 2 lit. a DSGVO — **PFLICHT** | ✓ je Vorgang benannt. Belegte Fristen: Zugriffslogs des Webservers **14 Tage** (logrotate auf dem Prod-Host, geprüft 04.09.2026), Nutzungsereignisse **90 Tage** (fest im Code), Anmelde-Cookie **8 h gleitend**, Sitzungskennung im Browser **30 Tage**, Sicherungskopien **bis 4 Wochen**. **Ohne Frist und im Text auch so benannt:** Suchprotokoll, Meldungen, Bewertungen, Fangkorb, Beiträge, Zugänge, Anwendungslogs |
| D-M2 | **Datenschutzbeauftragter** | Art. 13 Abs. 1 lit. b DSGVO — BEDINGT | ✓ Sven Seeberg, erreichbar über backoffice@netzbegruenung.de (Feld `DSB_KONTAKT`). Weil er benannt **ist**, ist die Angabe Pflicht; ob die Benennung selbst nach § 38 BDSG erforderlich war, ist für den Text ohne Belang |
| D-M3 | **Empfänger / Auftragsverarbeiter** — Hoster, IdP, Dritte | Art. 13 Abs. 1 lit. e DSGVO — **PFLICHT** | ✓ verdigado eG als Auftragsverarbeiterin (Art. 28 DSGVO), Hetzner Online GmbH als Unterauftragsverarbeiterin, Rechenzentrum in Deutschland. AV-Verträge liegen vor (verdigado, 04.09.2026). Der Identitätsdienst ist derselbe Verein und damit kein Empfänger. Weitere Empfänger gibt es nicht |
| D-M4 | **Drittlandtransfer** + Garantien | Art. 13 Abs. 1 lit. f DSGVO — BEDINGT | ✓ **trifft nicht zu.** Als Negativaussage aufgenommen: Beiträge, Suchanfragen und verlinkte Bilder werden nicht zur Verarbeitung an Dienste außerhalb der EU übermittelt. Davon abgegrenzt der Abruf eingebundener Bilder, den der Browser der Besuchenden selbst auslöst — der kann außerhalb der EU landen (D-N13b). **Gilt nur, solange kein OpenAI-Key gesetzt ist**, siehe D-N9 |
| D-M5 | **Widerspruchsrecht Art. 21 DSGVO** | Art. 13 Abs. 2 lit. b / Art. 21 Abs. 4 DSGVO — **PFLICHT**, hervorgehoben darzustellen | ✓ eigener abgesetzter Kasten (`warning-box`) am Ende der Betroffenenrechte, mit Nennung der konkret betroffenen Verarbeitungen: Nutzungsmessung, Protokolldateien, Herkunftsangabe an Beiträgen und Einwürfen |
| D-M6 | **Rechtsgrundlage** je Verarbeitung | Art. 13 Abs. 1 lit. c DSGVO — **PFLICHT** | ✓ je Vorgang genannt: lit. b für Anmeldung, Beiträge, Bewertungen und Fangkorb-Funktion; lit. f für Nutzungsmessung, Protokolle, Herkunftsangabe, Bild-Einbindung und Missbrauchsabwehr; lit. c i. V. m. Art. 16 DSA für Meldungen. **Die Zuordnung ist eine juristische Wertung und steht in der Prüfliste unten** |
| D-M7 | **Erforderlichkeit der Bereitstellung** | Art. 13 Abs. 2 lit. e DSGVO — **PFLICHT** | ✓ eigener Abschnitt „Was Sie angeben müssen und was freiwillig ist": Suchen und Lesen ohne Angaben; für ein Konto Kennung und ggf. E-Mail; alles Weitere freiwillig, ohne Nachteile |
| D-M8 | **Automatisierte Entscheidungsfindung / Profiling** | Art. 13 Abs. 2 lit. f DSGVO — PFLICHT (auch als Negativaussage üblich) | ✓ als Negativaussage aufgenommen, mit Verweis auf Art. 4 Nr. 4 DSGVO. Im Code wurde kein solcher Pfad gefunden |

---

## 3. Beschriebene Vorgänge, die es in ContentGrün NICHT gibt

**X1–X5 sind mit der Neufassung vom 04.09.2026 erledigt.** Der Platzhaltertext ist
vollständig ersetzt; keiner der hier beschriebenen Vorgänge steht noch darin. Die Zeilen
bleiben als Begründung stehen, warum der jeweilige Abschnitt nicht einfach übernommen
wurde. Die Spalte „Zeile" bezieht sich auf den alten Text.

| # | Zeile | Abschnitt | Befund | Empfehlung |
|---|-------|-----------|--------|------------|
| X1 | 126–140 | **„Registrierung auf dieser Website"** | Es gibt **keine Selbstregistrierung**. `app.routes.ts` hat keine Register-Route; `login-selector.component.html:9` sagt wörtlich „Aktuell ist keine Selbstregistrierung möglich". Zugang läuft über Netzbegrünung-Keycloak-SSO oder manuell angelegte Beta-Accounts (Mail an accounts@contentgruen.de). Die Liste „Benutzername / E-Mail / Passwort / Zeitpunkt der Registrierung" beschreibt eine Erhebung, die so nicht existiert | **Ersetzen** durch „Anmeldung und Nutzerkonto" (s. D-N1) |
| X2 | 26–27 | „…Daten, die Sie in ein **Kontaktformular** eingeben" | Es gibt kein Kontaktformular im Frontend (grep: kein Treffer außerhalb dieses Textes). Kontakt läuft per `mailto:` | Formulierung ersetzen: Anmeldedaten, Beitragsinhalte, Meldungen |
| X3 | 152–159 | **„4. Analyse-Tools und Werbung"** | Zwei Aussagen: „keine Analyse-Tools von Drittanbietern" ✓ zutreffend und übernommen. „**Wir erheben lediglich anonymisierte Nutzungsstatistiken**" trifft nicht zu. **Begründung neu gefasst (04.09.2026):** Die ursprüngliche Begründung — `user_id`, `ip_hash` und `user_agent` stünden im Klartext in `usage_events` — trägt nicht mehr, denn diese drei Spalten sind mit PR #27 entfallen. Die **Schlussfolgerung bleibt trotzdem richtig**, jetzt getragen von der `session_id` allein: eine bis zu 30 Tage stabile Gerätekennung, verknüpft mit Beitrag und Zeitstempel — und `content_reports` führt genau diese Kennung neben einer Nutzerkennung. Das ist pseudonym, nicht anonym | **Erledigt.** Der neue Text sagt ausdrücklich „nicht anonym, sondern pseudonym" und erklärt den Unterschied in einem Halbsatz |
| X4 | 164–177 | **„5. Plugins und Tools / Einbindung von Diensten Dritter"** | Abstrakt und ohne Ross und Reiter. **Korrigiert (04.09.2026):** Der früher hier genannte Fall Google Fonts ist erledigt (D-N10), und auch die Avatare kommen seit dem Wegfall von DiceBear lokal aus `public/avatars/`. Es bleibt aber **ein** realer Fall, entgegen der früheren Einschätzung, der Abschnitt könne ersatzlos entfallen: die von Beitragenden eingetragenen **Bild-Adressen**. Der Browser jedes Betrachters lädt sie direkt vom fremden Server, der dabei IP und User-Agent erfährt — und weil die Suche öffentlich ist, trifft das auch Menschen ohne Konto. Welcher Host das ist, lässt sich vorher nicht benennen | **Erledigt durch Konkretisieren, nicht durch Streichen.** Eigener Abschnitt „Bilder von fremden Servern" mit dem Zusatz, dass dies der einzige Fall ist |
| X5 | 93–106 | „Cookies" | Beschreibt „Sitzungscookies" und „Authentifizierungscookies". Auth-Cookie existiert (.NET-Cookie-Auth im BFF) ✓. Nicht erwähnt: die App nutzt **localStorage**, nicht nur Cookies — Session-ID (`services/session.service.ts:40`), Suche (`services/search.service.ts:29–37`), `contentgruen-metrics-seen` (`metrics/metrics.component.ts:35`), plus sessionStorage für Profilbild/Return-URL | **Ergänzen** um localStorage/sessionStorage (§ 25 TDDDG gilt für jede Endgerätespeicherung, nicht nur Cookies) |
| X6 | — | Newsletter | Kommt im Text nicht vor und existiert nicht — ✓ keine Aktion |
| X7 | — | Social Plugins | Kommen im Text nicht vor und existieren nicht — ✓ keine Aktion |

---

## 4. Reale Vorgänge, die im Text FEHLEN

**Stand 04.09.2026: D-N1 bis D-N10, D-N12 und die neuen D-N13/D-N13b sind im Text
abgedeckt.** Offen bleibt allein **D-N11** (geplante KI-Analyse von Beitragstexten) — die
Verarbeitung existiert nicht, also ist nichts zu beschreiben; die Frage, ob sie später eine
Einwilligung braucht, ist beim Bau zu entscheiden. Die Spalte Eintrag/Entscheidung hält je
Zeile fest, wie der Vorgang im Text gelandet ist.

| # | Vorgang | Fundstelle im Code | Was in den Text muss | Eintrag / Entscheidung |
|---|---------|--------------------|----------------------|------------------------|
| D-N1 | **Keycloak-SSO über Netzbegrünung** | `login-selector.component.html:26`, `BFF/Program.cs:73` (Scope `email`), `docs/AUTH_REGISTRIERUNG_OPTIONEN.md:665` | IdP benennen, übermittelte Claims (`sub`, `email`, Name), Verantwortlichkeitsabgrenzung bzw. AV-Vertrag mit Netzbegrünung/Verdigado | ✓ Abschnitt „Anmeldung über die Netzbegrünung": IdP benannt, übermittelte Angaben (Kennung, E-Mail, Name) benannt, und ausdrücklich, dass es **derselbe Verein und damit kein Dritter** ist — für diesen Weg braucht es deshalb keinen AV-Vertrag |
| D-N2 | **Managed Login (ContentGrün-Account)** | `BFF/Controllers/AuthController.cs:45–98`, `BFF/Models/ManagedUser.cs` | E-Mail + Passwort-Hash, manuell durch Admins angelegt, keine Selbstregistrierung; Rate-Limiting bei Fehlversuchen (`ManagedUserService.cs:82–113`) | ✓ Abschnitt „Zugang, den wir selbst anlegen": E-Mail, Anzeigename, interne Kennung, Passwort-Prüfsumme; keine Selbstregistrierung; Sperre nach Fehlversuchen (15 Minuten). **Speicherdauer nach Account-Ende: keine automatische Löschung**, im Text so benannt |
| D-N3 | **Beitrags-, Bewertungs- und Bilddaten** | `domain/models/base_content.py:82–95` — `original_author`, `last_modified_by`, `authors[]`, `edit_history[]`, `created`, `last_modified` | Autorenname und **vollständige Bearbeitungshistorie** werden dauerhaft am Inhalt gespeichert und sind anderen Nutzenden sichtbar. Der jetzige Text (Z. 142–147) nennt nur „Kommentar + Zeitpunkt + Nutzername" — Edit-History fehlt | ✓ **Sichtbarkeit: öffentlich** — der Code beantwortet die Frage: die Suche ist ein Public-Endpoint, die Antwort bettet den vollständigen Datensatz ein, und das Frontend rendert „Von: …". Im Text steht das ausdrücklich, samt Bearbeitungsgeschichte und dem Hinweis, dass dort die Kennung steht und nicht der Klarname |
| D-N4 | **Nutzungsprotokollierung** (`usage_events`) — ⚠️ **Beschreibung überholt** | `infrastructure/database/models.py:83–96` | **Die obige Beschreibung galt für den Stand vom 19.08.2026 und trifft nicht mehr zu.** PR #27 hat `user_id`, `ip_hash` und `user_agent` entfernt; an die Stelle des User-Agent tritt `device_category` mit vier möglichen Werten. Festgehalten wird jetzt: welcher Beitrag, welche Art Ereignis, wann, aus welcher Geräteklasse und unter welcher Sitzungskennung — also **welches Gerät, nicht welches Konto und nicht welche Adresse** | ✓ Zweck: erkennen, welche Beiträge gebraucht werden · Rechtsgrundlage: Art. 6 Abs. 1 lit. f · Löschfrist: **90 Tage**, danach bleibt nur ein Zähler je Beitrag |
| D-N4b | **Suchprotokollierung** (`search_events`) | `infrastructure/database/models.py:96–118`, `services/search_tracking_service.py` | Seit PR #14 nur noch Trefferzahl, Zeitstempel und ein täglich rotierendes Pseudonym (HMAC-SHA256 über Nutzer-/Session-Kennung + UTC-Datum). Kein Suchtext, keine IP, keine Kennung mehr. Zu beschreiben bleibt: **dass** protokolliert wird, wozu (Reichweitenmessung), und dass das Pseudonym täglich wechselt | ✓ Eigener Unterabschnitt „Suchvorgänge". Zweck: erkennen, wie viele Menschen die Suche an einem Tag nutzen · Rechtsgrundlage: Art. 6 Abs. 1 lit. f · **Löschfrist: keine**, im Text so benannt — es gibt zwar Löschcode, aber keinen Aufrufer. Die tägliche Rotation des Pseudonyms ist ausdrücklich als Zusage formuliert |
| D-N5 | **Melde-/Moderationsfunktion** | `infrastructure/database/models.py:122–139` (`content_reports`), `shared/components/report-dialog/` | Freitext-Meldung + meldende Person + Moderationsentscheidung + Prüfer werden gespeichert | ✓ Eigener Abschnitt. **Löschfrist: keine**, im Text so benannt, auch für abgeschlossene Bearbeitungen. Ergänzt um den anonymen Meldeweg (Art. 16 DSA) und die flüchtige IP-Verarbeitung für das Rate-Limit |
| D-N6 | **Speicherung in Qdrant + PostgreSQL** | `docs/ARCHITECTURE.md` | Konkrete Speicherorte benennen, beides selbst gehostet | ✓ Abschnitt „Wo Ihre Daten liegen". Bewusst **ohne** die Produktnamen der Datenbanken: sie sagen Nutzenden nichts, und interne Bezeichner gehören nicht in einen Nutzertext. Genannt ist, wer die Server betreibt und wo sie stehen |
| D-N7 | **Hosting** | `docs/DEPLOYMENT.md:65` (Hetzner VPS), `:113` + `docs/ARCHITECTURE.md:143` (`contentgruen.netzbegruenung.verdigado.net`, SaltStack durch Verdigado) | Hoster/Betreiber der Infrastruktur benennen, **AV-Vertrag nach Art. 28 DSGVO** (auch `docs/AUTH_REGISTRIERUNG_OPTIONEN.md:372` fordert das ausdrücklich) | ✓ **Beide AV-Verträge liegen vor** (bestätigt durch verdigado, 04.09.2026). Im Text: verdigado eG als Auftragsverarbeiterin nach Art. 28 DSGVO, Hetzner Online GmbH als Unterauftragsverarbeiterin, Rechenzentrum in Deutschland |
| D-N8 | **Embedding-Verarbeitung** | `services/embeddings/qdrant_embeddings_manager.py` — `SentenceTransformer` | **Entlastend**: läuft lokal im eigenen Container, keine Übermittlung an Dritte | ✓ Im Abschnitt „Ihre Suchanfragen" in einem Satz erklärt (rechnet die Eingabe in Zahlenfolgen um, die inhaltliche Ähnlichkeit abbilden) und in „Keine Übermittlung außerhalb der EU" als tragendes Argument aufgegriffen |
| D-N9 | **KI-Bildbeschreibung über OpenAI** — **inaktiv** | `services/vision/caption_suggestion_service.py`, `services/vision/image_description_worker.py`, `domain/content_registry.py:107–127`, Warnung in `core/config.py:104–113` | **Aktiv in Prod: nein** (bestätigt 04.09.2026). Der Key ist die einzige Weiche und wird **einmal beim Modulimport** ausgewertet; ohne ihn geht nichts an OpenAI, weder über `/suggestCaption` noch über den Hintergrund-Worker. Eine Präzisierung zur obigen Beschreibung: übermittelt würde **nicht das Bild, sondern seine URL** — OpenAI lädt das Bild dann selbst beim fremden Host nach. Am Drittlandtransfer ändert das nichts | ✓ Im Text als Negativaussage abgedeckt (D-M4). **Wird der Key je gesetzt, ist die Erklärung vorher um einen Abschnitt nach Art. 44 ff. DSGVO zu erweitern**; zusätzlich AV-Vertrag und Art.-46-Garantien. Die Warnung dazu steht in `core/config.py` und `CLAUDE.md` |
| D-N10 | ~~**Google Fonts vom CDN**~~ ✅ | vormals `src/index.html:10–11` | **Erledigt durch PR #14.** Roboto und Material Icons liegen in `public/fonts/`, die `@font-face`-Regeln in `src/styles/fonts.css`. Es geht keine IP mehr an Google. **Nachtrag 04.09.2026:** dasselbe gilt inzwischen für die Avatare, die früher von `api.dicebear.com` kamen und jetzt als 16 lokale SVG-Dateien in `public/avatars/` liegen. Ein Grep über `src/` und `public/` findet **keinen einzigen externen Host** | ✓ Als entlastende Aussage aufgenommen: Schriften, Symbole und Profilbilder liefern wir selbst aus |
| D-N11 | **Geplante KI-Analyse von Beitragstexten** | `docs/ROADMAP.md` | Erst dokumentieren, wenn implementiert | **Offen — der einzige offene D-N-Punkt.** Nichts zu beschreiben, solange die Verarbeitung nicht existiert. Die Einwilligungsfrage ist beim Bau zu klären, zusammen mit der Frage aus D-N9, ob dabei ein Anbieter außerhalb der EU beteiligt wäre |
| D-N12 | **Nutzung ohne Anmeldung** | `app.routes.ts` — `PublicGuard` auf `/search`, `/result`, `/about` und die Rechtstextseiten | Anonyme Nutzung ist möglich; auch dabei laufen Such- und Nutzungsmessung mit Sitzungskennung mit | ✓ Im Abschnitt „Was diese Erklärung abdeckt" benannt, und bei der Sitzungskennung ausdrücklich: sie wird auch gesetzt, wenn niemand angemeldet ist |
| D-N13 | **Fangkorb** (`raw_inputs`) — **fehlte in dieser Liste** | `infrastructure/database/models.py:170–213`, `api/v1/raw_input.py`, `fe/app/raw-input-list/` | Diese Liste datiert auf den 19.08.2026, der Fangkorb wurde am 22.08.2026 gemergt (PR #19) und war deshalb nie erfasst. Gespeichert werden Freitext (bis 5000 Zeichen), eine fremde URL, eine fremde Bild-URL und die Kennung der einwerfenden Person. Zwei Punkte, die niemand erwartet: die Kennung ist **für alle angemeldeten Nutzenden sichtbar**, als eigene Tabellenspalte — nicht nur für die Moderation; und Einwürfe enthalten typischerweise Angaben über **Dritte**, die von der Erhebung nichts wissen | ✓ Eigener Abschnitt. Zweck: Material sammeln · Rechtsgrundlage: Art. 6 Abs. 1 lit. b für die Funktion, lit. f für die Herkunftsangabe · **Löschfrist: keine**, im Text so benannt; bei Kontolöschung werden Einwürfe mitgelöscht. Die Sichtbarkeit ist beschrieben, nicht beschönigt — ihre Einschränkung ist eine Produktentscheidung und ein Folgeticket |
| D-N13b | **Bild-Adressen Dritter** | `fe/app/image-result-item/image-result-item.component.html:41`, `domain/models/image.py:37` | Der einzige Abruf, den der Browser der Nutzenden an einen fremden Server richtet — siehe X4 | ✓ Eigener Abschnitt „Bilder von fremden Servern" |

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

### Was sich dadurch **nicht** erledigt hat — überholt (04.09.2026)

Hier stand, `usage_events` sei unverändert und führe `user_id`, `ip_hash` und
`user_agent` weiter im Klartext. **Das trifft seit PR #27 nicht mehr zu**, siehe D-N4.

Die Schlussfolgerung für den Text bleibt trotzdem: „lediglich anonymisierte
Nutzungsstatistiken" wäre auch heute unzutreffend — nur trägt sie jetzt die
Sitzungskennung allein (X3). Der neue Text sagt deshalb „pseudonym", nicht „anonym".

---

## Offene Punkte, die den Text beeinflussen, aber noch in Arbeit sind

Hier nur vermerkt, damit sie beim Schreiben nicht vergessen werden. **Noch nicht
ausformulieren** — der Stand ändert sich gerade.

| # | Punkt | Stand |
|---|-------|-------|
| O1 | ~~**Suchanfragen werden als Statements gespeichert**~~ ✅ | **Erledigt und beschrieben (04.09.2026).** Die Änderung ist umgesetzt: als Autor steht ein fester Systemwert am Datensatz, die Herkunft ein eigener `origin`-Wert. Damit gilt: der **Suchtext** wird dauerhaft gespeichert und öffentlich auffindbar, die **suchende Person** ist am Datensatz nicht erkennbar. Der Text sagt beides — einschließlich der Warnung, nichts ins Suchfeld zu tippen, das nicht öffentlich werden soll |

---

## Reihenfolge zum Ausfüllen

1. ~~**Zuerst D1–D4 / I1–I4 klären**: Wer ist Anbieter und Verantwortlicher — Netzbegrünung e. V. oder
   Sebastian Banach als Privatperson?~~ **Entschieden 03.09.2026: Anbieter und Verantwortlicher
   ist NETZBEGRÜNUNG — Verein für grüne Netzkultur e. V.** Damit sind I1–I10 und I12/I13
   erledigt; D7–D11 und die AVV-Frage (D-N7) bleiben offen, weil die Datenschutzerklärung
   noch nicht überarbeitet ist.
2. ~~Danach die Kontaktdaten (I5–I6, D5–D6).~~ I5–I6 erledigt (03.09.2026), D5–D6 offen.
3. ~~Dann die Entscheidungen zu Streichen/Ersetzen (X1–X5, I-E).~~ Erledigt (04.09.2026).
4. ~~Zuletzt die neuen Abschnitte D-N1 bis D-N12 und die Fristen (D-M1).~~ Erledigt
   (04.09.2026), bis auf D-N11 (existiert noch nicht).

**Damit ist die Liste für Impressum, Nutzungsbedingungen und Datenschutzerklärung
abgearbeitet.** Was bleibt, sind die Punkte der Prüfliste unten, die Produkt- und
Codetickets aus dem Datenschutz-PR und die Consent-Frage aus Abschnitt 5.

---

## Offene Launch-Blocker (Stand 04.09.2026)

**Alle drei Rechtstexte sind ausformuliert.** Der Platzhaltertext der
Datenschutzerklärung ist ersetzt, der für Besucher sichtbare Platzhalter-Hinweis
entfernt. Die beiden früher hier geführten inhaltlichen Blocker sind aufgelöst:

- **D-N4** — erledigt und **am Code nachgeprüft** (04.09.2026, siehe
  `docs/DATENSCHUTZ_BESTANDSAUFNAHME.md`, Abschnitt 1.2): PR #27 hat die drei
  personenbeziehbaren Spalten entfernt. Die Textaussage ist neu formuliert und
  spricht jetzt von pseudonymer, nicht anonymer Messung.
- **D-N9** — geklärt: In Produktion ist kein OpenAI-Key gesetzt, das Feature ist
  inaktiv. Die Erklärung deckt das als Negativaussage ab. **Wird der Key je gesetzt,
  ist sie vorher zu erweitern** — die Warnung dazu steht in `core/config.py` und
  `CLAUDE.md`.

**Was vor dem Launch bleibt:**

1. **Juristische Prüfung** der Datenschutzerklärung — die Punkte stehen unten in der
   Prüfliste. Diese Liste ist keine Rechtsberatung und ersetzt sie nicht.
2. **Die Consent-Frage aus Abschnitt 5** ist unverändert offen. Sie berührt den
   Datenschutz an einer Stelle mit: § 25 TDDDG (Prüfliste, Punkt 3).
3. **Eine USt-IdNr.-Rückfrage** im Impressum (I11).

Die Code- und Produkttickets, die sich aus dem Schreiben der Erklärung ergeben haben —
fehlende Löschfristen, der Retention-Bug, die Sichtbarkeit im Fangkorb, der
KI-Vorschlagsbutton ohne Key — sind **keine** Launch-Blocker: die Erklärung beschreibt
den Ist-Zustand zutreffend. Sie stehen im Beschreibungstext des Datenschutz-PR.

---

## Prüfliste für die juristische Durchsicht der Datenschutzerklärung

**Dies ist keine Rechtsberatung.** Die Liste sammelt die Stellen, an denen wir eine
Wertung getroffen haben, die wir nicht belegen können — sortiert nach dem Gewicht, das
wir ihnen beimessen. Alles Übrige im Text ist am Code belegt.

| # | Stelle | Was zu prüfen ist |
|---|--------|-------------------|
| P1 | **Sitzungskennung und § 25 TDDDG** | Die Kennung wird auch **ohne Anmeldung** gesetzt und dient der Nutzungsmessung, nicht der Bereitstellung des ausdrücklich gewünschten Dienstes. Ob sie unter die Ausnahme des § 25 Abs. 2 Nr. 2 TDDDG fällt, haben wir **nicht** entschieden: Der Text beschreibt den Vorgang, stuft ihn aber nicht als technisch erforderlich ein. Ein Consent-Mechanismus existiert nicht (Abschnitt 5). **Braucht eine Antwort, bevor die Plattform öffentlich beworben wird.** Produktseitig damit verbunden: soll für nicht angemeldete Besucher überhaupt eine Kennung gesetzt werden? |
| P2 | **Rechtsgrundlagen je Vorgang (D-M6)** | Die Zuordnung lit. b / lit. f / lit. c ist unsere Einschätzung, nicht mehr. Besonders zu prüfen: die **öffentliche Herkunftsangabe an Beiträgen** (auf lit. f gestützt) und der **Fangkorb**, wo die Kennung für alle Angemeldeten sichtbar ist |
| P3 | **Löschung als Anonymisierung** | Beiträge werden bei Kontolöschung nicht gelöscht, sondern die Kennung durch einen Platzhalter ersetzt. Ob das Art. 17 DSGVO in dieser Konstellation genügt — CC0-Lizenz, Bestandscharakter, Verweise anderer Beiträge —, ist eine Wertung. Der Text beschreibt das Verfahren offen, einschließlich der Grenze, dass CC0-Freigaben nicht zurückgeholt werden können |
| P4 | **Verarbeitungen ohne Löschfrist** | Suchprotokoll, Meldungen, Bewertungen, Fangkorb und Beiträge haben keine automatische Löschfrist. Der Text benennt das ehrlich statt eine Frist zu behaupten. Zu prüfen ist, ob das gegenüber Art. 5 Abs. 1 lit. e DSGVO (Speicherbegrenzung) tragfähig ist oder ob Fristen einzuführen sind — Tickets sind angelegt |
| P5 | **Daten Dritter in Fangkorb und Beiträgen** | Einwürfe und Beiträge enthalten regelmäßig Angaben über Personen, die von der Erhebung nichts wissen — Handles von Fremdplattformen, Links auf fremde Profile, fremde Bilder. Der Text weist Einwerfende darauf hin, erfüllt aber **keine Informationspflichten nach Art. 14 DSGVO** gegenüber diesen Dritten. Ob und wie das zu lösen ist, ist offen |
| P6 | **Suchanfragen werden öffentlicher Bestand** | Der Suchtext wird dauerhaft gespeichert und auffindbar, ohne Bezug zur suchenden Person. Der Text warnt ausdrücklich davor, Personenbezogenes ins Suchfeld zu tippen. Zu prüfen: genügt die Warnung, oder braucht es eine technische Vorkehrung? |
| P7 | **Protokolldateien ohne feste Frist** | Für die Anwendungsprotokolle gibt es derzeit keine Frist; der Text sagt das und kündigt eine Volumenbegrenzung an. **Diese Stelle ist nach dem Salt-Deploy des `logging:`-Blocks anzupassen**, dann kann eine Zahl genannt werden |
| P8 | **Rechtsgrundlage der Bild-Einbindung** | Der Abruf fremder Bild-Hosts durch den Browser der Besuchenden ist auf lit. f gestützt. Ob das trägt oder ob es einen Zwischenschritt braucht (Proxy, Vorschaubild, Klick-zum-Laden), ist zu prüfen — ein Proxy wäre auch die technische Lösung |

**Sprachliche Anmerkung, keine Rechtsfrage:** Impressum und Datenschutzerklärung siezen,
die Nutzungsbedingungen duzen. Das war schon vor dieser Änderung so und ist beim
Durchsehen zu entscheiden, nicht nebenbei.
