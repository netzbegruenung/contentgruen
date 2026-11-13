# Verzeichnis der Verarbeitungstätigkeiten (Art. 30 DSGVO)

> **Entwurf, nicht juristisch geprüft, nicht beschlossen.** Keine Rechtsberatung. Führen muss das
> Verzeichnis der Verantwortliche (Art. 30 Abs. 1); dieser Entwurf leitet es aus Code und Doku
> ab, damit der Vorstand es übernehmen kann. Aussagen ohne Beleg im Repo stehen als **offen** da.

Stand 12.11.2026, Code `main` @ `c4a95e9c` (letzter Tag `v0.8.3`). Grundlage sind die
Datenschutz-Folgenabschätzung ([`docs/DSFA.md`](./DSFA.md), Verarbeitungen V1 bis V22 in
Abschnitt 8.2), das Löschkonzept ([`docs/LOESCHKONZEPT.md`](./LOESCHKONZEPT.md), `LK`), die
Art.-9-Einwilligung ([`docs/ART9_EINWILLIGUNG.md`](./ART9_EINWILLIGUNG.md)) und die
Datenschutzerklärung
(`mvp/frontend/gutgesagt-frontend/src/app/datenschutz/datenschutz.component.html`, `DSE`).
Die Datenschutzerklärung zitieren wir mit dem Titel ihres Abschnitts, das Löschkonzept ebenso.
Begriffe wie in [`GLOSSARY.md`](../GLOSSARY.md).

**Warum ein Verzeichnis:** Die Ausnahme für Stellen unter 250 Beschäftigten (Art. 30 Abs. 5)
greift nicht: Gut gesagt verarbeitet Daten nach Art. 9 Abs. 1 (politische Meinung) und das nicht
nur gelegentlich.

**Pflege:** Wer eine Verarbeitung neu baut oder ändert, zieht im selben PR die DSFA (Abschnitt
8.2) und dieses Verzeichnis mit; Fristen stehen nur im Löschkonzept, hier steht der Verweis.

## Allgemeine Angaben (Art. 30 Abs. 1 lit. a, d, e, g)

- **Verantwortlicher:** NETZBEGRÜNUNG — Verein für grüne Netzkultur e. V., vertreten durch den
  Vorstand nach § 26 BGB. Anschrift, Registereintrag und Kontakt wie im Impressum und in der
  Datenschutzerklärung, Abschnitt „Verantwortlicher“ (Angaben aus
  `mvp/frontend/gutgesagt-frontend/src/app/shared/legal-entity.ts`).
  **Bewusste Lücke:** Dieses Verzeichnis liegt in einem öffentlichen Repository und nennt deshalb
  weder Namen noch Kontaktdaten. In der Fassung, die der Verein führt und der Aufsicht auf
  Anfrage vorlegt (Art. 30 Abs. 4), trägt er Name und Kontakt des Verantwortlichen und des
  Datenschutzbeauftragten selbst ein.
- **Gemeinsam Verantwortliche, Vertreter (Art. 27):** keine.
- **Datenschutzbeauftragter:** benannt; Kontakt wie in der Datenschutzerklärung, Abschnitt
  „Datenschutzbeauftragter“ (Angabe `DSB_KONTAKT` in
  `mvp/frontend/gutgesagt-frontend/src/app/datenschutz/datenschutz.component.ts`).
- **Empfänger, für alle Tätigkeiten gleich:**
  - verdigado eG als Auftragsverarbeiterin für Server, Anmeldedienst und Mailversand des
    Anmeldedienstes; laut Datenschutzerklärung mit der Hetzner Online GmbH als
    Unterauftragsverarbeiterin, Rechenzentrum in Deutschland (DSE „Wo deine Daten liegen“).
    **Offen:** ob ein AV-Vertrag nach Art. 28 Abs. 3 Gut gesagt mit Zweck, Datenarten (auch
    Art. 9) und Betroffenen erfasst, und welche Rolle Hetzner hat (DSFA 8.6, F1; #506).
  - SMTP-Server für Mails zu Meldungen und Entscheidungen, aus der Konfiguration
    (`smtp_host` in `mvp/backend/semantic-search-service/app/core/config.py`). **Offen:** welcher Server in Produktion, wer ihn
    betreibt (DSFA 8.6, F2).
  - Intern: Admins der Plattform (Rolle aus dem Anmeldedienst oder der Liste `admin_users`,
    `docs/ARCHITECTURE.md`). **Offen:** wer Admin ist und wer Zugang zu Host, Datenbank und
    Konfiguration hat (DSFA 8.6, F4).
  - Keine Weitergabe an Dritte, keine Analysedienste, kein KI-Anbieter (DSE „Wo deine Daten
    liegen“, `CLAUDE.md` „Datenschutz — keine KI-Anbieter“).
- **Übermittlung in Drittländer (lit. e):** keine (DSE „Keine Übermittlung außerhalb der EU“).
  Bilder von fremden Servern lädt der Browser der Person erst nach Klick (DSE „Bilder von fremden
  Servern“, T11).
- **Technische und organisatorische Maßnahmen (lit. g, Art. 32 Abs. 1):** je Tätigkeit unter
  „TOM“ mit Verweis auf die Maßnahmen der DSFA. Für alle gelten:
  - Pseudonymisierung: In der Datenbank steht die Kennung des Kontos, kein Name und keine
    E-Mail-Adresse; Prüfwerte und Tagespseudonyme als HMAC, die Schlüssel der Prüfwerte und der
    Besucher nur im Arbeitsspeicher (DSFA V7, V9, V11).
  - Datenminimierung: Zähler statt Einzelzeilen, wo möglich (DSFA 8.5).
  - Automatische Löschung nach Fristen durch einen täglichen Task (LK „Fristen“), Löschen einer
    Person von Hand nach dem Löschkonzept (LK „Ablauf“).
  - Zugriffsschutz: Kennungen, Meldungen und Muster-Hinweise nur für Admins; Mitwirkung nur mit
    Art.-9-Einwilligung, durch einen Test abgesichert (`docs/ART9_EINWILLIGUNG.md` „Sperren“).
  - Protokolle der Anwendung ohne Suchtexte und mit gekürzter Kennung (LK „Was nicht gelöscht
    wird“).
  - Sicherungen täglich, 7 Tages- und 4 Wochenstände (`mvp/scripts/backup/backup.sh`).
  - **Offen:** Verschlüsselung der Sicherungen (das Skript verschlüsselt nicht; DSFA 8.6, F3),
    Rollen- und Zugriffskonzept (F4), Frist der Protokolle am Host (F6).

## Verarbeitungstätigkeiten (Art. 30 Abs. 1 lit. b, c, d, f)

Rechtsgrundlagen wie in der Datenschutzerklärung; juristisch geprüft hat sie niemand (#296).
„Art.-9-Einwilligung“ heißt Art. 9 Abs. 2 lit. a DSGVO, eingeholt nach dem ersten Anmelden
(`docs/ART9_EINWILLIGUNG.md`).

### T1 Konten, Anmeldung und Anzeigename

- **Zweck:** Anmelden, Mitwirkung einem Konto zuordnen, Anzeigename an Beiträgen; Konten auf
  Einladung einrichten; Bedienung im Browser.
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. b (Konto, Einladung, Beta-Zugang), lit. f
  (Anzeigename, Missbrauchsabwehr bei Einladungen); § 25 Abs. 2 TDDDG für Einträge im Browser.
- **Betroffene:** Mitglieder der Netzbegrünung mit Netzbegrünung-Login, Personen mit Konto aus
  einer Einladung, Personen mit Beta-Zugang.
- **Daten:** Kennung, Anzeigename (Vorname und Initial); Kennung, E-Mail-Adresse und Name im
  verschlüsselten Anmelde-Cookie; bei Konten aus Einladungen im Anmeldedienst E-Mail-Adresse und
  Passwort-Hash (DSE „Konto aus einer Einladung“); beim Beta-Zugang E-Mail-Adresse, Anzeigename und Prüfsumme des
  Passworts in einer Konfigurationsdatei; Anmelde-Cookie; an Einladungen nur Zähler und Notiz.
  Schon das Konto kann eine politische Nähe erkennen lassen (Art. 9).
- **Empfänger:** wie oben; der Anzeigename ist für andere Angemeldete sichtbar, nicht für
  Besucher.
- **Fristen:** LK „Fristen“ (nie benutzte Konten aus Einladungen) und „Ablauf“
  (Kontolöschung); LK „Fristen außerhalb des täglichen Tasks“: Anmelde-Cookie 14 Tage nach
  letzter Nutzung, Beta-Zugänge bis von Hand entfernt.
- **TOM:** DSFA V1, V15, V19, V21. **Offen:** Anzeigename entsteht vor der
  Art.-9-Einwilligung (DSFA V1, Abschnitt 4).

### T2 Einwilligungen

- **Zweck:** Rechtsgrundlage der Mitwirkung einholen und nachweisen; gesonderte Zustimmung zur
  Sichtbarkeit der Meilenstein-Abzeichen.
- **Rechtsgrundlage:** Art. 9 Abs. 2 lit. a, Nachweis nach Art. 7 Abs. 1; für die
  Abzeichen Art. 6 Abs. 1 lit. a und Art. 9 Abs. 2 lit. a.
- **Betroffene:** angemeldete Personen.
- **Daten:** Kennung, Zeitpunkt, Kennung des Wortlauts, Zeitpunkt des Widerrufs; je Antwort zur
  Sichtbarkeit Kennung, Ja/Nein, Wortlaut, Zeitpunkt; je Widerruf ein Löschauftrag mit Kennung,
  Zeitpunkt, Frist und Zeitpunkt der Ausführung.
- **Empfänger:** wie oben, nur Admins in der Datenbank.
- **Fristen:** solange das Konto besteht, auch widerrufene (LK „Ablauf“, Schritt 2; für die
  Abzeichen auch LK „Fristen“); Löschaufträge offen bis zur Ausführung, erledigte nach LK
  „Fristen“, alle mit dem Konto.
- **TOM:** DSFA V2, V22. Mit #658 löscht ein Widerruf die Stimmen der Person (T4). Für Beiträge,
  Einwürfe und Sätze legt er einen Löschauftrag an, den ein Admin binnen sieben Tagen ausführt
  (DSFA V2, R9, Maßnahme R9b); bis dahin behalten sie ihren Personenbezug.

### T3 Beiträge, Einwürfe und Gegenlesen

- **Zweck:** durchsuchbarer Bestand an Argumenten, Rohmaterial im Fangkorb, Herkunft und
  Änderungsverlauf nachvollziehen; beim Schreiben Anmerkungen, Sprachhinweis und
  Kürzungsvorschlag zeigen.
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. b, lit. f für Herkunft und Änderungsverlauf;
  zusätzlich Art.-9-Einwilligung. Gegenlesen: lit. b, ohne Speicherung.
- **Betroffene:** Mitwirkende; Dritte, die in Beiträgen, Links oder „Gepostet von“ genannt
  sind.
- **Daten:** Text, Kennung von Autor und letzter Änderung, Zeitpunkte, Änderungsverlauf ohne
  alten Wortlaut, Kennung des CC0-Hinweises; Einwürfe mit Hinweis, Link, Weg und Kennungen der
  einwerfenden Person und der Personen mit Sätzen; Kontoname des ursprünglichen Posters. Daten
  Dritter, auch deren politische Zuordnung.
- **Empfänger:** Beiträge für alle, auch Besucher; der Anzeigename daran nur für Angemeldete;
  Einwürfe nur für Angemeldete; wegen CC0 darf jede Person Beiträge weiterverwenden.
- **Fristen:** LK „Fristen“ (gelöschte Beiträge, Einwürfe) und LK „Zwei Wege, einen Beitrag zu
  löschen“; Beiträge ohne Frist. Bei Kontolöschung werden Beiträge anonymisiert (LK „Ablauf“,
  Schritt 3), Sätze an fremden Einwürfen bekommen einen Platzhalter, eigene Einwürfe werden
  gelöscht (Schritt 2); dasselbe mit dem Löschauftrag nach einem Widerruf der Art.-9-Einwilligung
  (T2), dann bleibt das Konto.
- **TOM:** DSFA V3, V4, V20. **Offen:** Information der Dritten nach Art. 14 (DSFA V3, R3).

### T4 Bewertungen und Güte

- **Zweck:** Beiträge nach Brauchbarkeit sortieren, Güte im Siegel zeigen.
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. b, zusätzlich Art.-9-Einwilligung.
- **Betroffene:** angemeldete Personen, die bewerten.
- **Daten:** Kennung, Beitrag, Richtung, Zeitpunkt; Güte und Summen nicht gespeichert.
- **Empfänger:** Summen und Güte für alle ab drei Stimmenden; Einzelstimmen nur Admins in der
  Datenbank.
- **Fristen:** LK „Fristen“ (Stimmen); mit #658 zusätzlich sofort beim Widerruf der
  Art.-9-Einwilligung.
- **TOM:** DSFA V5 (M5), R8.

### T5 Suche und Messung der Suche

- **Zweck:** Bestand aufbauen aus dem, was gesucht wird; Personen pro Tag zählen, die suchen;
  erkennen, wo Antworten fehlen.
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f. Für das Tagespseudonym der Besucher **offen**
  mit § 25 TDDDG (DSFA V7, Abschnitt 6, Frage 3).
- **Betroffene:** alle, die suchen, angemeldet oder nicht; Dritte, die in Suchtexten genannt
  sind.
- **Daten:** Suchtext als Aussage ohne Autor; Suchereignisse mit Tag, Trefferzahl und
  Tagespseudonym (Besucher: aus Anschluss und Tag, ohne User-Agent; Angemeldete: aus Kennung und
  Tag); je Aussage und Woche Zahl der Suchen und Personen ohne Treffer.
- **Empfänger:** offene Aussagen aus Suchen für alle, sobald jemand antwortet oder zwei Personen
  ohne Treffer danach suchten; Zähler für Angemeldete und Admins.
- **Fristen:** LK „Fristen“ (Suchereignisse bis zum Ende ihres Tages, dann zu Tageszählern
  verdichtet) und „Was nicht gelöscht wird“ (Suchanfragen als Aussage, Suchen ohne Treffer).
- **TOM:** DSFA V6, V7, V8. **Offen:** Schlüssel des Pseudonyms der Angemeldeten in Produktion
  gesetzt (DSFA 8.6, F5).

### T6 Messung der Nutzung und Rückmeldungen

- **Zweck:** erkennen, welche Beiträge gebraucht werden; Mitwirkenden zeigen, dass ihre Beiträge
  helfen; Zahl der Menschen je Woche, die nach dem Kopieren „Ja, gepostet“ melden.
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f; für „Ja, gepostet“ zusätzlich
  Art.-9-Einwilligung.
- **Betroffene:** alle, die kopieren oder teilen; Mitwirkende, deren Beiträge genutzt werden.
- **Daten:** Nutzungsereignisse ohne Kennung (Beitrag, Art, Zeitpunkt, Geräteklasse, Fassung);
  Prüfwert der entdoppelten Nutzung; je Kennung eine Zahl für die Rückmeldung; je Person und
  Woche ein Prüfwert „Ja, gepostet“, danach nur die Zahl der Woche.
- **Empfänger:** Zähler an der Karte für alle; die Rückmeldung nur für die Person; Zahlen je
  Woche für Admins.
- **Fristen:** LK „Fristen“ (Prüfwerte, „Ja, gepostet“); Nutzungsereignisse 90 Tage als
  Einzelzeilen, danach nur Zähler je Beitrag (LK „Fristen außerhalb des täglichen Tasks“;
  `usage_retention_days` in `mvp/backend/semantic-search-service/app/core/config.py`, wirkt
  über den abschaltbaren Bereinigungsjob, Standard an; DSE „Verwendung von Beiträgen“); Zahl
  für die Rückmeldung bis zur Kontolöschung (LK „Ablauf“, Schritt 2).
- **TOM:** DSFA V9, V9a, V10. „Ja, gepostet“ hinter dem Schalter `gepostet_aktiv`.

### T7 Punkte, Meilensteine, Abzeichen und Muster-Hinweise (gebaut, ausgeschaltet)

- **Zweck:** Wirkung der Mitwirkung zeigen, Anerkennung sichtbar machen, Punkte gegen Absprachen
  schützen.
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. a und Art. 9 Abs. 2 lit. a über die eigene, freiwillige
  Einwilligung „Punkte und Meilensteine“ (`punkte_einwilligung`, #351), getrennt von der
  Art.-9-Einwilligung zur Mitwirkung (Kopplungsverbot, Art. 7 Abs. 4); Sichtbarkeit der
  Abzeichen mit gesonderter Zustimmung (T2).
- **Betroffene:** angemeldete Personen mit Einwilligung „Punkte und Meilensteine“, ohne
  Startkonten; Muster-Hinweise nur, wenn beide Konten eingewilligt haben.
- **Daten:** Punkte und Meilensteine nicht gespeichert, bei jedem Abruf berechnet;
  Paar-Prüfwerte; Muster-Hinweise mit zwei Kennungen; je Antwort auf die Einwilligung eine
  Zeile mit Kennung, ja/nein, Wortlaut und Zeitpunkt.
- **Empfänger:** Punkte nur für die Person; Abzeichen für andere Angemeldete mit Zustimmung;
  Muster-Hinweise nur für Admins.
- **Fristen:** LK „Fristen“ (Paar-Prüfwerte, Muster-Hinweise, Abzeichen).
- **TOM:** DSFA Abschnitt 3, V11, V22. Schalter `punkte_aktiv` und `abzeichen_sichtbar_aktiv`,
  Standard aus; einschalten erst nach Übernahme der DSFA (DSFA Abschnitt 7).

### T8 Meldungen, Sperren und Widerspruch

- **Zweck:** gemeldete Inhalte prüfen, Entscheidungen mitteilen, Widerspruch prüfen (DSA).
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. c mit Art. 16, 17 und 20 DSA; lit. f für
  Rate-Limit und Tagespseudonym.
- **Betroffene:** meldende Personen, angemeldet oder nicht; Autorinnen und Autoren gemeldeter
  oder gesperrter Beiträge; Admins.
- **Daten:** Beitrag, Grund, Freitext, Erklärung guten Glaubens, freiwillig Name und
  E-Mail-Adresse, Kennung oder Tagespseudonym, Bearbeitungsvermerk; Sperrgrund, Begründung,
  Kennungen, Widerspruch, Prüfergebnis.
- **Empfänger:** Admins; Mails an die meldende Person über den SMTP-Server (siehe oben); die
  Entscheidung an die betroffene Person.
- **Fristen:** LK „Fristen“ (Meldungen, Sperren, Tagespseudonym an Meldungen).
- **TOM:** DSFA V12, V13; Auskunft und Löschung für Personen ohne Konto über „Nach Person“
  (LK „Fristen“, Meldungen).

### T9 Feedback

- **Zweck:** Plattform verbessern, auf Feedback antworten.
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f.
- **Betroffene:** Personen, die Feedback geben.
- **Daten:** Text, freiwillige Kontaktangabe, Tag; keine Kennung.
- **Empfänger:** Admins.
- **Fristen:** LK „Feedback“.
- **TOM:** DSFA V14.

### T10 Betrieb: Protokolle, Sicherungen, Schutz vor Missbrauch

- **Zweck:** Betrieb, Fehlersuche, Abwehr von Angriffen und Überlastung, Wiederherstellung.
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f (DSE „Protokolldateien“); Sicherungen teilen die
  Rechtsgrundlage der gesicherten Daten und dienen Art. 32 Abs. 1 lit. c.
- **Betroffene:** alle, die die Plattform aufrufen.
- **Daten:** im vorgelagerten Webserver volle IP-Adresse, Zeitpunkt, aufgerufene Adresse,
  verweisende Seite, Angaben zu Browser und Betriebssystem (User-Agent); im Webserver der
  Anwendung Zeitpunkt, aufgerufene Seite ohne Suchtext, Ergebnis und User-Agent, ohne die
  IP-Adresse der Person und ohne verweisende Seite, für Suchen keine Zeile (DSE „Zugriffe
  innerhalb der Anwendung“); in den Protokollen der Anwendung gekürzte Kennung ohne Suchtext; für Rate-Limits gekürzte Adresse oder Kennung nur im
  Arbeitsspeicher; in Sicherungen alle Datenbanken.
- **Empfänger:** wie oben (Betrieb bei der Auftragsverarbeiterin).
- **Fristen:** LK „Fristen außerhalb des täglichen Tasks“: vorgelagerter Webserver 14 Tage,
  Rate-Limits höchstens etwa 16 Minuten, Sicherungen bis zu 28 Tage. **Offen:** Protokolle der Anwendung und des Frontend-nginx haben in Produktion keine
  Frist (DSFA V16, 8.6, F6; #485, #336).
- **TOM:** DSFA V16, V17, V18. **Offen:** Verschlüsselung der Sicherungen (DSFA 8.6, F3).

### T11 Bilder von fremden Servern

- **Zweck:** ein Bild zeigen, das in einem Beitrag über eine Adresse eingebunden ist.
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f (DSE „Bilder von fremden Servern“).
- **Betroffene:** alle, die ein solches Bild laden, angemeldet oder nicht.
- **Daten:** IP-Adresse und Angaben zum Browser, die der Browser beim Laden an den fremden
  Server schickt; bei Gut gesagt wird der Klick nicht gespeichert.
- **Empfänger:** der Betreiber des fremden Servers, den die einstellende Person eingetragen hat;
  welcher, steht vorher nicht fest. Der Browser der Person spricht ihn direkt an; dass er außerhalb
  der EU sitzt, ist nicht ausgeschlossen (lit. e oben).
- **Fristen:** bei Gut gesagt keine Speicherung; beim fremden Server unbekannt.
- **TOM:** Platzhalter „Bild laden“, das Bild lädt erst nach Klick und nur für dieses eine Bild;
  der Klick wird nicht gemerkt (DSE „Bilder von fremden Servern“).

## Offen

Gesammelt in DSFA 8.6: AV-Vertrag (F1), SMTP-Server (F2), Verschlüsselung der Sicherungen (F3),
Rollen und Zugriff (F4), Schlüssel des Tagespseudonyms (F5), Frist der Protokolle (F6). Dazu
die Lücken aus DSFA 8.5: Anzeigename vor der Einwilligung (T1), Widerruf ohne volle Folgen (T2, nach #658 nur Stimmen gelöscht).
