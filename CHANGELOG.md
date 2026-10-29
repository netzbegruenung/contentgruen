# Änderungen

Eine Änderungsliste je Release, die neueste oben. Der Abschnitt eines Release ist zugleich
der Text des Forgejo-Release zu seinem Tag. Wie er entsteht: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md),
„Releases“.

## v0.9.0 (noch nicht getaggt)

Erstes Release nach dem Abräumen der alten Tags `v1.0.0` bis `v1.1.0` (#295). Die Liste
beginnt beim Commit von `v1.1.0` (`fae44b4b`, laut Release-Lauf auf dem GitHub-Spiegel) und
reicht bis zum Tag; nur die Release-Vorbereitung selbst fehlt darin.

### Betriebsschritte (Umzug von Produktion)

Von Hand ergänzt, das Skript kennt sie nicht. Reihenfolge von oben nach unten.

1. **Backup ziehen**, bevor die neue Version startet (`mvp/scripts/backup/backup.sh`).
2. **Umbenennung (#204, #207):** Images, Container, Datenbank und Pfade heißen jetzt
   `gutgesagt-*`, `gutgesagt_app` und `/opt/gutgesagt*`. Produktion pinnt `:latest` der
   neuen Image-Namen; die Digests der alten `contentgruen-*`-Images bewegen sich nicht mehr.
   Die Übernahme der Daten und der Umzug laufen nach #206.
3. **Migrationen** laufen beim ersten Start des Suchdienstes von selbst. Beim ersten Start
   mit diesem Mechanismus (#331) erkennt er die drei nicht wiederholbaren, früher von Hand
   eingespielten Migrationen an ihrer Wirkung (`erkannt`); Stand danach mit
   `SELECT name, status FROM migrationsprotokoll ORDER BY name;` prüfen.
4. **Zustände umstellen (#214, einmalig):** nach dem Ausrollen `zustaende_umstellen.py`
   erst ohne, dann mit `--ausfuehren` (`mvp/scripts/manual/README.md`, „Zustaende umstellen“).
5. **`text_normalisiert` nachtragen (#301):** nach dem Ausrollen
   `text_normalisiert_nachtragen.py --ausfuehren` (`mvp/scripts/manual/README.md`, „Bestand in Qdrant“).
6. **Alten Platzhalter umstellen (#236, einmalig):** `beitraege_anonymisieren.py geloeschter-nutzer`
   wie in `docs/LOESCHKONZEPT.md` beschrieben, falls es Beiträge mit dem alten Platzhalter gibt.
7. **Arbeitsspeicher:** Der Suchdienst braucht seit #452 etwa 0,5 GB mehr
   (docs/DEPLOYMENT.md, „Operation“); ein Speicherlimit des Containers entsprechend anheben.
8. **Neue optionale Einstellung:** `SEMANTIC_SEARCH_SEARCH_EVENT_RETENTION_DAYS` (Default 90).

Stand: 51a78985 (2026-10-29), seit fae44b4b (2026-08-31)

### Breaking Changes

- refactor!: ContentGrün im Code in Gut gesagt umbenennen (Teil 1) ([#204](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/204))
- feat!: rename runtime names to gutgesagt (Teil 2, App) ([#207](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/207))

### Neu

- feat(fangkorb): Admins dürfen fremde Einwürfe verwerfen ([#230](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/230))
- feat(loeschung): Sätze an fremden Einwürfen bei Kontolöschung anonymisieren ([#232](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/232))
- feat(metrics): Kennzahl „Suchen ohne Treffer“ für Admins ([#235](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/235))
- feat(moderation): Admins sperren gemeldete Beiträge statt sie zu löschen ([#237](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/237))
- feat(loeschung): Beiträge gelöschter Personen als „ehemalige Person“ zeigen ([#247](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/247))
- feat: Markierung „Grün-Intern“ entfernen ([#266](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/266))
- feat(metrics): Mindestanzahl bei „Suchen ohne Treffer“ zählt Personen ([#259](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/259))
- feat(einwurf): Tab „Meine Einwürfe“ in „Meine Beiträge“ ([#306](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/306))
- feat(fangkorb): Anzeige beim Einwerfen, wenn ein gleicher Link schon im Fangkorb liegt ([#307](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/307))
- feat(hintergrundinfo): Dublettenprüfung wie beim Kommentar ([#310](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/310))
- feat(suche): Suchereignisse nach 90 Tagen zu Tageszählern verdichten ([#314](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/314))
- feat(beitrag): Autor löscht eigenen Beitrag (Zustand gelöscht) ([#319](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/319))
- feat(fangkorb): nur die Arbeitslisten Destillieren und Ausformulieren ([#320](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/320))
- feat(image): eigene Antworten ohne interne Felder fuer die lesenden Bild-Routen ([#328](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/328))
- feat(db): Migrationen beim Start des Semantic-Service einspielen ([#331](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/331))
- feat(post): Formular für Posts, Kachel, Typwahl beim Ausformulieren ([#338](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/338))
- feat(frontend): Kopieren als Text oder Text + Herkunft ([#366](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/366))
- feat: Suche und lesende Beitragsrouten ohne Kennung anderer Personen ([#382](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/382))
- feat(frontend): Ergebnisseite erklärt Kommentar, Hintergrundinfo und Post ([#367](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/367))
- feat(frontend): Schreibregeln und Schreibhilfen in der Formularhilfe ([#369](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/369))
- feat(startseite): Bereich "Diese Woche oft genutzt" ([#371](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/371))
- feat(search): Suchereignisse abgeschlossener Tage gemischt neu schreiben ([#381](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/381))
- feat: Feedback-Knopf, ein Anmelden-Weg am Desktop, Avatar ohne Würfeln ([#384](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/384))
- feat(scripts): Einwürfe aus einer Liste in den Fangkorb importieren ([#372](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/372))
- feat: Seite "Hier fehlt eine Antwort" für Mitwirkende ([#370](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/370))
- feat(usage): Rückmeldung zur Nutzung in Meine Beiträge und beim Anmelden ([#377](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/377))
- feat: Aussagen, Herkunft, Einwürfe und Meine Beiträge ohne Kennung anderer Personen ([#418](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/418))
- feat(frontend): Logo mit Daumen, Siegel-Komponente, Stimm-Knöpfe als Umriss-Hand ([#433](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/433))
- feat: CC0-Hinweis bei Satz und Aussage, Kennung des Wortlauts an Beitrag, Satz und Einwurf ([#439](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/439))
- feat(monitoring): Betriebskennzahlen unter /metrics, am BFF gesperrt (#420, A5) ([#453](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/453))
- feat(meldung): Meldegrund „Erfunden oder sachlich falsch“ ([#442](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/442))
- feat: Fassungen am Kommentar – Kurz, Mittel, Lang, Nutzung je Fassung ([#443](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/443))
- feat(frontend): Über-Seite neu ausrichten ([#441](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/441))
- feat: Themen aus fester Liste, Filter auf Ergebnisseite und „Hier fehlt eine Antwort“ ([#445](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/445))
- feat(datenschutz): Löschfristen für Meldungen, Einwürfe und gelöschte Beiträge ([#449](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/449))
- feat: Zweck und Stil am Kommentar ([#456](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/456))
- feat: Themen der neuen Aussage in den Beitragsformularen ([#462](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/462))
- feat(profilbild): Profilbild selbst wählen (Fluent Emoji), ohne Wahl nichts im Browser ([#458](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/458))

### Behoben

- fix(kommentar): eigene Dublette erst nach der Entscheidung verknüpfen ([#254](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/254))
- fix(search): Suchereignisse ohne Uhrzeit, Aussagen aus Suchen nicht mehr verknüpfbar ([#256](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/256))
- fix(bff): Beta-Zugänge mit reservierter Kennung ablehnen ([#270](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/270))
- fix(vision): Bildbeschreibung hebt eine Sperre nicht mehr auf ([#279](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/279))
- fix(logs): Kennungen in BFF und Suchdienst nur als Pseudonym ([#282](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/282))
- fix(cache): Änderungen leeren den GET-Cache, Fangkorb nie im Cache ([#308](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/308))
- fix(nutzung): Nutzungsstatistik ohne Kennung im Pfad ([#313](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/313))
- fix(db): Init-Skript und Modell der Nutzungstabellen angleichen ([#317](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/317))
- fix(bild): KI-Unterschrift nur als Vorschlag, den die Person übernimmt ([#316](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/316))
- fix(suche): Reihenfolge der Suchen eines Tages nicht mehr verknüpfbar ([#330](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/330))
- fix(suche): Suchtext ohne Ersetzen von Apostroph und Semikolon einbetten ([#335](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/335))
- fix(bff): Sitzung nach Kontolöschung beim nächsten Request beenden ([#332](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/332))
- fix(seed): Seed v1.0 bereinigt und als Testdaten für die Entwicklung gekennzeichnet ([#368](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/368))
- fix(moderation): Verweise an Aussagen für alle Beitragstypen entfernen und Fehler melden ([#378](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/378))
- fix(seed): Altdaten mit echten Namen aus Fixtures und Messdaten entfernen ([#426](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/426))
- fix(check): einzelne Frontend-Specs, sichtbares Rot ([#435](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/435))
- fix(aussagen): getAll und searchStatements für Nicht-Admins nur kuratierte Aussagen ([#450](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/450))

### Sonstiges

- Impressum und Nutzungsbedingungen neu fassen ([GitHub #31](https://github.com/netzbegruenung/contentgruen/pull/31))
- BFF: Adminrechte auch über eine konfigurierte Kennungsliste ([GitHub #33](https://github.com/netzbegruenung/contentgruen/pull/33))
- Datenschutzerklaerung ausformulieren ([GitHub #34](https://github.com/netzbegruenung/contentgruen/pull/34))
- Datenschutz: Angaben zu Dritten, Sitzungskennung und Logs nachziehen ([GitHub #35](https://github.com/netzbegruenung/contentgruen/pull/35))
- PWA-Share-Target: Instagram-Links direkt in den Fangkorb ([GitHub #36](https://github.com/netzbegruenung/contentgruen/pull/36))
- Beitragsformulare: Hinweis auf CC0 und Nutzungsbedingungen vor dem Ab… ([GitHub #37](https://github.com/netzbegruenung/contentgruen/pull/37))
- dev compose: bind published ports to 127.0.0.1 ([GitHub #38](https://github.com/netzbegruenung/contentgruen/pull/38))
- Destillier-Ablauf v1: Titel als Behauptung, Entwurf/Status im Backend,   Destillier-Ansicht ([GitHub #39](https://github.com/netzbegruenung/contentgruen/pull/39))
- Nachlese: Suchkarten, Formulare, Seed, toter Code ([GitHub #40](https://github.com/netzbegruenung/contentgruen/pull/40))
- Fangkorb v2: Destillieren als eigene Stufe, Kartenansicht, Einwurf mit Hinweis ([GitHub #41](https://github.com/netzbegruenung/contentgruen/pull/41))
- UI-Nachlese mobil, Paket 1 ([GitHub #42](https://github.com/netzbegruenung/contentgruen/pull/42))
- Mobiler Einstieg: Startseite, Beitragen-Kette, Fangkorb-Kopf, Version im Footer, Dev-Proxy ([GitHub #43](https://github.com/netzbegruenung/contentgruen/pull/43))
- Suche: usage_count auch für Bild und Post, sonst 500 bei jedem Bild i… ([GitHub #44](https://github.com/netzbegruenung/contentgruen/pull/44))
- Feat/beitragskarte ([GitHub #45](https://github.com/netzbegruenung/contentgruen/pull/45))
- Fangkorb als Arbeitsvorrat: Tabs, Rohling-Karte, Ansehen-Sheet ([GitHub #46](https://github.com/netzbegruenung/contentgruen/pull/46))
- Nachlese zum Review von #46. Ein Commit, sieben Punkte. ([GitHub #48](https://github.com/netzbegruenung/contentgruen/pull/48))
- Zurück-Navigation: festes Ziel je Route statt History ([GitHub #47](https://github.com/netzbegruenung/contentgruen/pull/47))
- Login: Keycloak-Cookie persistent (14 Tage gleitend), returnUrl bleibt erhalten, keine Tokens im Cookie ([GitHub #49](https://github.com/netzbegruenung/contentgruen/pull/49))
- Beitragen: /workflow/add-* einziger Formularcontainer, /contribute nur Übersicht, Aussage per ID aus der Suche ([GitHub #50](https://github.com/netzbegruenung/contentgruen/pull/50))
- Fix-Paket A: anonyme Suche, Stimmen, Erneut versuchen, Später-Schleife, Rawinput-Status, mobile Kopfzeile ([GitHub #51](https://github.com/netzbegruenung/contentgruen/pull/51))
- Beitragsformulare Kommentar und Hintergrundinfo: Antwort auf, feste Leiste, Ergebnisseite ([GitHub #52](https://github.com/netzbegruenung/contentgruen/pull/52))
- Ähnlichkeit kalibrieren: stille Wiederverwendung nur bei derselben Aussage, Kommentar-Dubletten passage/passage ([GitHub #53](https://github.com/netzbegruenung/contentgruen/pull/53))
- Handy-Nachlese: Icons, Zurück-Wege, Destillier-Schritt, eigener Beitrag ([GitHub #54](https://github.com/netzbegruenung/contentgruen/pull/54))
- Haertung Oktober: Backup-Kette, Cleanup-Settings, CLAUDE.md gegen den CodeFix/haertung oktober ([GitHub #55](https://github.com/netzbegruenung/contentgruen/pull/55))
- Anzeigenamen statt Kennung an Beiträgen und Einwürfen ([GitHub #56](https://github.com/netzbegruenung/contentgruen/pull/56))
- ci: push images only from main ([GitHub #58](https://github.com/netzbegruenung/contentgruen/pull/58))
- docs: CLAUDE.md auf Forgejo als führendes Repo umstellen ([#205](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/205))
- docs: Glossar, ADRs und Agent-Skills-Setup ([#208](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/208))
- docs(migrations): Kopfbefehle mit neuen Container- und Datenbanknamen ([#228](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/228))
- docs: historische Dokumente nach docs/archiv ([#229](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/229))
- Dubletten zeigen: zustimmen oder trotzdem speichern ([#234](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/234))
- docs(migrations): Anleitung zum Anwenden zentral in README ([#245](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/245))
- docs: Registrierungs-Analyse und Datenschutz-Bestandsaufnahme ins Archiv ([#244](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/244))
- refactor(fangkorb): Fangkorb-Wörter an das Glossar angleichen ([#248](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/248))
- docs: remove internal infrastructure details from public documentation ([#246](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/246))
- docs(loeschkonzept): Log-Aussagen am aktuellen Code belegen ([#269](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/269))
- docs(glossar): Ausformulierer über Verknüpfen statt Speichern ([#249](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/249))
- docs(architecture): Test-Anmeldung per E-Mail statt Benutzername ([#267](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/267))
- test(migrations): Migrationskonvention per Unit-Test prüfen ([#268](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/268))
- chore: gemeinsamer Prüfbefehl, Check gegen ausgemusterte Namen, Coding Standards ([#274](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/274))
- refactor(moderation): Suchindex über Repository, keine Admin-Kennung im Log ([#271](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/271))
- refactor(fangkorb): Einwurf-Modell im Frontend nach dem Glossar benennen ([#273](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/273))
- refactor(kommentar): Antwortfeld heißt dublette, verknuepft nur bei Verknüpfung ([#280](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/280))
- test(postgres): Integrationstests gegen echtes PostgreSQL im Wegwerf-Container ([#283](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/283))
- refactor(content): Zustände eines Beitrags auf sichtbar, gesperrt, gelöscht reduzieren ([#286](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/286))
- refactor(suchdienst): ungenutzte Router, konstante Kennzahlen, Bild-Antworten ([#309](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/309))
- test(e2e): Playwright-Specs vom Branch chore/e2e-playwright auf main übernehmen ([#312](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/312))
- perf(suche): Suchanfrage nur einmal einbetten, Direktsuche als eine Abfrage ([#318](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/318))
- docs(standards): Verhaltensänderung außerhalb des Tickets als Fachfrage ([#324](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/324))
- test(integration): Suite reparieren, check.sh --integration als Tor ([#325](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/325))
- refactor(frontend): Adressparameter für Einwürfe heißt einwurf ([#329](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/329))
- docs: Vision aus dem Konzeptarchiv, Glossar und ADR 0004 ([#339](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/339))
- docs(vision): langfristige Vision, Geld-Grundsatz und Ranglisten mit Zustimmung ([#373](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/373))
- docs(adr): spezialisierte NLP-Werkzeuge zuerst, generisch nur über Grünerator auf eigener Hardware ([#388](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/388))
- docs: Doku an Entscheidungen vom 28.10.2026 und Glossar angleichen ([#414](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/414))
- test(nginx): Webserver-Protokoll-Test bei belegtem Port neu starten ([#386](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/386))
- docs: Modell-Dienst statt Grünerator, KI-Texte nur für die Suche ([#428](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/428))
- ci: Woodpecker-CI für jeden PR mit CI-Bericht ([#334](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/334))
- test(integration): Wegwerf-Container samt anonymem Volume entfernen ([#434](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/434))
- docs(vision): Mobilisierungsplattform, keine Lernplattform ([#424](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/424))
- docs: alte Container- und DB-Namen aus der Doku entfernen (#206) ([#440](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/440))
- docs(deployment): Release-Anleitung und scripts/changelog.sh ([#451](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/451))
- Gegenlesen ohne KI beim Schreiben, mit Siegel unter der Vorschau ([#452](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/452))
- docs: Rechtstexte an Glossar und Funktionsumfang angleichen ([#444](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/444))
- test(messset): Paar-Labels, 503 Paare, fester Train/Test-Split ([#454](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/454))
- Sperren mit Sperrgrund, Sperrnachricht und Widerspruch ([#457](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/457))
- test: CI ohne versteckte Abhaengigkeit vom Dev-Stack (#460) ([#461](https://git.verdigado.com/Netzbegruenung/gutgesagt/pulls/461))

### Migrationen und Betriebsschritte

- Datenbank-Migrationen laufen beim Start des Suchdienstes von selbst (docs/DEPLOYMENT.md, „Database migrations“). Neue Migrationen:
  - `mvp/backend/postgres-app/migrations/2026-09-13-destillier-entwuerfe.sql`
  - `mvp/backend/postgres-app/migrations/2026-09-13-fangkorb-v2.sql`
  - `mvp/backend/postgres-app/migrations/2026-10-11-anzeigenamen.sql`
  - `mvp/backend/postgres-app/migrations/2026-10-26-init-angleichen.sql`
  - `mvp/backend/postgres-app/migrations/2026-10-26-search-events-nur-tag.sql`
  - `mvp/backend/postgres-app/migrations/2026-10-26-suchen-ohne-treffer-personen.sql`
  - `mvp/backend/postgres-app/migrations/2026-10-26-suchen-ohne-treffer.sql`
  - `mvp/backend/postgres-app/migrations/2026-10-26-suchereignisse-tageszaehler.sql`
  - `mvp/backend/postgres-app/migrations/2026-10-27-feedback.sql`
  - `mvp/backend/postgres-app/migrations/2026-10-27-gesehene-nutzung.sql`
  - `mvp/backend/postgres-app/migrations/2026-10-27-suchereignisse-reihenfolge.sql`
  - `mvp/backend/postgres-app/migrations/2026-10-29-355-nutzung-je-fassung.sql`
  - `mvp/backend/postgres-app/migrations/2026-10-29-431-cc0-fassung.sql`
  - `mvp/backend/postgres-app/migrations/2026-10-29-448-sperren.sql`
  - `mvp/backend/postgres-app/migrations/2026-10-29-aussage-themen.sql`
- Neue Skripte in `mvp/scripts/manual/` (Reihenfolge je README-Abschnitt):
  - `mvp/scripts/manual/beitraege_anonymisieren.py`
  - `mvp/scripts/manual/bestand_pruefen.py`
  - `mvp/scripts/manual/einwuerfe_importieren.py`
  - `mvp/scripts/manual/person_loeschen.sql`
  - `mvp/scripts/manual/text_normalisiert_nachtragen.py`
  - `mvp/scripts/manual/zustaende_umstellen.py`
