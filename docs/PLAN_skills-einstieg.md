# Plan: Einstieg in die Matt-Pocock-Skills für Gut gesagt

> Stand 2026-10-25, Branch `sb/skills-onboarding` auf Basis von `sb/rename-runtime`
> (enthält die Umbenennungen aus #204 und #207). Vorbereitung für die
> `grill-with-docs`-Session. Nichts hier ist abgestimmt; alles ist Vorschlag.
>
> Mitgeliefert auf diesem Branch:
> - `GLOSSARY.md`: Glossar-Entwurf im Format von `domain-modeling/GLOSSARY-FORMAT.md`
> - `docs/adr/0001` bis `0003`: drei ADR-Entwürfe (`status: proposed`)
> - dieser Plan
>
> Zeilenangaben beziehen sich auf den Stand dieses Branches (`114e214`).

## 0. Kurzfassung

- Das Projekt hat eine starke, aber **verstreute Fachsprache**: Die Kette
  Einwerfen → Destillieren → Ausformulieren ist im Code (Kommentare, Enums, UI-Texte)
  sauberer beschrieben als in der Doku. Für dieselben vier Stufen eines Einwurfs gibt es
  **drei Namenssätze** (Abschnitt 3.2). Ein Glossar fehlt, ADRs fehlen.
- Die Übersichtsdokumente (`STATUS.md`, `README.md`, `ARCHITECTURE.md`, `ROADMAP.md`)
  erwähnen den Fangkorb, das Hauptthema der letzten zwei Monate, kaum oder gar nicht. Die
  Spezifikationen `SPEC_*` sind vom Code überholt, ohne dass das irgendwo steht.
- **Issue-Tracker ist die erste harte Entscheidung**: Die Skills brauchen einen Tracker.
  Forgejo ist führend, aber dort gibt es praktisch keine Issues (5 insgesamt), es ist für
  Externe nicht erreichbar, und die Doku verweist auf GitHub-Nummern. `setup-matt-pocock-skills`
  kennt Forgejo nicht und braucht eine eigene Tracker-Beschreibung (Abschnitt 4.2).
- Vorschlag für morgen: **erst setup-Entscheidungen (30 min), dann grill-with-docs über
  die Domäne in sechs Blöcken** (Abschnitt 6). Danach `to-spec` erst, wenn ein konkretes
  Vorhaben ansteht; `improve-codebase-architecture` als zweite Session.

---

## 1. Was die Skills voraussetzen und erzeugen

Gelesen unter `~/.claude/skills/` (Dateien, nicht ausgeführt).

### 1.1 `grill-with-docs`

`grill-with-docs/SKILL.md:7` macht nichts anderes, als zwei Skills zu laden: `grilling` und
`domain-modeling`. Er ist nur vom Menschen aufrufbar (`disable-model-invocation: true`).

- **Voraussetzung:** ein Arbeitsverzeichnis mit Repo (sonst `grill-me`,
  `ask-matt/SKILL.md:626`). Ein vorher gelaufenes `setup-matt-pocock-skills` ist **nicht**
  Pflicht: `domain-modeling` legt `GLOSSARY.md` und `docs/adr/` selbst an
  (`domain-modeling/SKILL.md:40`). `setup` liefert nur die Lese-Regeln für die anderen Skills.
- **Ablauf (`grilling/SKILL.md`):** Die Entscheidungen werden als **Entscheidungsbaum**
  geführt. Pro Runde fragt der Agent die ganze **Frontier** (alle Fragen, deren
  Voraussetzungen geklärt sind), nummeriert, je mit empfohlener Antwort, so formuliert, dass
  „ja“ die Empfehlung annimmt (`grilling/SKILL.md:8-24`). Fakten sucht der Agent selbst
  (Subagent), Entscheidungen trifft der Mensch (`:28`). Fertig ist die Session, wenn die
  Frontier leer ist und der Mensch das gemeinsame Verständnis bestätigt (`:30`).
- **Erzeugt (`domain-modeling/SKILL.md`):**
  - `GLOSSARY.md` im Repo-Root, **sofort** fortgeschrieben, sobald ein Begriff geklärt ist
    (`:60-62`), ohne Implementierungsdetails (`:64`). Format: Kontextname, ein bis zwei
    Sätze Beschreibung, `## Language`, je Begriff fett, Definition in ein bis zwei Sätzen,
    `_Avoid_:` mit Synonymen (`GLOSSARY-FORMAT.md:5-30`).
  - `docs/adr/NNNN-slug.md`, nur wenn alle drei Kriterien gelten: schwer umkehrbar,
    ohne Kontext überraschend, Ergebnis einer echten Abwägung (`ADR-FORMAT.md:29-37`).
    Ein ADR kann ein Absatz sein.
  - **Keine** CONTEXT-Dateien. Bei mehreren Kontexten gäbe es `GLOSSARY-MAP.md` plus ein
    `GLOSSARY.md` je Kontext (`GLOSSARY-FORMAT.md:32-60`); das ist hier nicht nötig
    (Abschnitt 4.1).
- **Verhalten während der Session:** Begriffe gegen das Glossar prüfen, unscharfe Wörter
  schärfen, Grenzfälle mit konkreten Szenarien testen, Aussagen gegen den Code prüfen
  (`domain-modeling/SKILL.md:44-58`).

### 1.2 `setup-matt-pocock-skills`

Nur vom Menschen aufrufbar, einmal pro Repo. Ablauf: erkunden, Befund zeigen, drei
Abschnitte nacheinander abfragen, Entwurf zeigen, dann schreiben (`SKILL.md:17-118`).

| Abschnitt | Frage | Ergebnisdatei |
|---|---|---|
| A Issue-Tracker | GitHub, GitLab, lokale Markdown-Dateien oder „Other“ | `docs/agents/issue-tracker.md` |
| B Triage-Labels | Default-Labels übernehmen? (nur wenn `triage` installiert ist; hier ja) | `docs/agents/triage-labels.md` |
| C Domain-Doku | single-context oder multi-context | `docs/agents/domain.md` |

Dazu ein Block `## Agent skills` in `CLAUDE.md` (weil `CLAUDE.md` existiert, nie zusätzlich
`AGENTS.md`, `SKILL.md:74-80`). Bei GitHub/GitLab legt der Skill fehlende Labels im Tracker an
(`:104`). Die Vorlagen kennen GitHub (`gh`), GitLab (`glab`) und `.scratch/` lokal.

### 1.3 Die übrigen Skills, kurz

| Skill | Rolle | Liest | Schreibt |
|---|---|---|---|
| `grilling`, `grill-me` | Interview-Primitive; `grill-me` ohne Spuren | – | – |
| `domain-modeling` | Glossar und ADRs aktiv pflegen | `GLOSSARY.md`, `docs/adr/` | dieselben |
| `codebase-design` | Vokabular: Modul, Interface, Tiefe, Naht (seam), Adapter, Hebel, Lokalität | – | – |
| `improve-codebase-architecture` | Hotspots aus `git log`, HTML-Bericht nach `/tmp`, dann Grilling über einen Kandidaten | Glossar, ADRs | Glossar, ADRs |
| `to-spec` | Gespräch → Spec, ohne Interview; veröffentlicht im Tracker mit `ready-for-agent` | Tracker-Config | Tracker |
| `to-tickets` | Spec → vertikale Tracer-Bullet-Tickets mit Blockier-Kanten | Tracker-Config | Tracker |
| `implement` | ein Ticket bauen, `tdd` an vereinbarten Nähten, danach `code-review`, Commit | Ticket | Code |
| `implement-spec` | ganze Spec über Subagenten in Worktrees auf einem Integrationsbranch | Spec, Tickets | Code, PR |
| `tdd` | Rot→Grün, nur an vorher bestätigten Nähten | Glossar | Tests |
| `triage` | Eingehende Issues durch fünf Zustände, Agent-Briefs, `.out-of-scope/` | Tracker, Labels | Tracker, `.out-of-scope/` |
| `wayfinder` | sehr große, neblige Vorhaben als Karte aus Entscheidungs-Tickets | Tracker-Config | Tracker |
| `writing-for-agents` | Regeln für CLAUDE.md und Skills | – | – |
| `ask-matt` | Router: welcher Skill wann | – | – |

### 1.4 Reihenfolge laut den Skills

`ask-matt/SKILL.md:622-704`:

1. **Voraussetzung:** `setup-matt-pocock-skills` (`:704`).
2. **Hauptstrecke:** `grill-with-docs` → (bei Bedarf `prototype`) → bei Mehr-Session-Vorhaben
   `to-spec` → `to-tickets` → `implement` je Ticket (mit `/clear` dazwischen) oder
   `implement-spec` → `code-review` → `pr` → `retro` (`:626-641`).
3. **Kontext:** Schritte 1 bis `to-tickets` in **einem** Kontextfenster halten (`:645`).
4. **Auffahrten:** `triage` für fremde Issues, `diagnosing-bugs` für harte Fehler,
   `wayfinder` für Vorhaben größer als eine Session (`:651-661`).
5. **Pflege:** `improve-codebase-architecture` (`:667`).

---

## 2. Ist-Analyse

### 2.1 Repo und Prozess

- Monorepo, vier Dienste: Angular-Frontend, .NET-BFF (YARP, Auth), Python/FastAPI
  „Semantic Search“ (Qdrant + PostgreSQL), Postgres-Image. Root-`package.json` hat keine
  `workspaces`, kein `pnpm-workspace.yaml`: für den Setup-Skill ist das **single-context**
  (`setup-matt-pocock-skills/SKILL.md:30`).
- Hotspot seit August 2026 ist eindeutig das **Frontend** (rund 1150 Dateiänderungen unter
  `src/app`, alter und neuer Pfad zusammen), danach Backend-Tests, `api/`, `services/`.
  291 Commits seit 2026-08-01.
- Arbeitsweise bisher: Product Owner entscheidet in strukturierten Befragungen, Ergebnis
  landet als `docs/SPEC_*.md` mit Entscheidungstabellen (`SPEC_Destillier-Ablauf_v1.md:3`,
  `SPEC_Fangkorb_v2.md:3`). Danach Phase 1 „read-only prüfen, melden, STOPP“
  (`SPEC_Fangkorb_v2.md:110-118`), dann Umsetzung als ein PR mit Commit je Block. Die PR-Texte
  wurden als `docs/PR_*.md` ins Repo gelegt, Nachlesen als `docs/ISSUE_*.md`. Das ist
  `grill-with-docs` + `to-spec` + `to-tickets` von Hand, nur ohne Glossar und ohne Tracker.

### 2.2 Tracker

| Ort | Befund |
|---|---|
| Forgejo (führend) | 5 Issues insgesamt, davon 3 offen (#206 Umbenennung Teil 2, #194 und #37 Renovate). 201 PRs. Keine Repo-Labels. Vier alte Meilensteine (v0.1 bis v1.0). |
| GitHub (Spiegel, öffentlich) | Issues #22 (offen), #23, #25, #26 (geschlossen). #25 und #26 sind Sammel-Issues, die laut Text „in Einzel-Issues und Meilensteine überführt oder außerhalb dieses Repos weitergeführt“ wurden. Meilensteine „Erste Nutzer“, „Prod v1.2“, „Launch“, „Nach Launch“ melden zusammen 27 offene Issues, die Issue-API liefert aber nur eines. Labels: `bug`, `enhancement`, `wontfix`, `backend`, `frontend`, `bff`, `ci`, `documentation`, `schuld` u. a. |
| Repo | `docs/ISSUE_*.md`, `docs/PR_*.md` als Ersatz-Tracker. |

**Konsequenz:** Wo der Backlog heute liegt, ist aus Repo und APIs nicht zu klären
(Abschnitt 9). Issue-Nummern in der Doku zeigen auf GitHub, nicht auf Forgejo: `CLAUDE.md:378`
und `docs/ARCHITECTURE.md:313` meinen mit „#22“ das GitHub-Issue zu Watchtower, auf Forgejo
ist #22 ein Renovate-PR; `docs/ARCHITECTURE.md:285-286` meint mit „#26“ eine Härtung, auf
GitHub ist #26 ein geschlossenes Sammel-Issue. Zwei Nummernräume, kein Präfix.

### 2.3 Doku-Bestand

32 Markdown-Dateien. Einordnung:

| Gruppe | Dateien | Zustand |
|---|---|---|
| Einstieg | `README.md`, `CONTRIBUTING.md`, `STATUS.md`, `CLAUDE.md` | teils veraltet, siehe 2.4 |
| Architektur | `docs/ARCHITECTURE.md`, `docs/CONTENT_MODEL.md` | `CONTENT_MODEL` gut und aktuell; `ARCHITECTURE` lückenhaft und mit Infrastruktur-Details |
| Richtung | `docs/ROADMAP.md` | Leiter (Rungs) bis Juli, danach nur „Roadmap-Features“ |
| Analyse/Entwurf | `docs/ROHINPUT.md`, `docs/AUTH_REGISTRIERUNG_OPTIONEN.md` | gute Entscheidungsgrundlagen, Status-Zeilen veraltet |
| Spezifikation | `docs/SPEC_Destillier-Ablauf_v1.md`, `docs/SPEC_Fangkorb_v2.md` | vom Code überholt |
| Historisch | `docs/PR_*.md` (3), `docs/ISSUE_destillier-nachlese.md` | belegen feste Commits; laut #204 bewusst unverändert |
| Recht/Datenschutz | `docs/DATENSCHUTZ_BESTANDSAUFNAHME.md`, `docs/LOESCHKONZEPT.md`, `docs/RECHTSTEXTE_LUECKEN.md` | gründlich, mit Belegen; Fangkorb-Nachträge offen |
| Betrieb/Dev | `docs/DEPLOYMENT.md`, `docs/DEV_GUIDE.md`, `docs/DEV-SETUP.md`, `mvp/*.md`, Service-READMEs | teils Windows-lastig, teils doppelt |

### 2.4 Widersprüche und veraltete Stellen (Doku untereinander und gegen Code)

| # | Befund | Belege |
|---|---|---|
| D1 | **Fangkorb fehlt in den Übersichten.** `STATUS.md` („Last updated 2026-07-25“) nennt Fangkorb, Einwurf und Destillieren nicht; README, ARCHITECTURE und CONTRIBUTING ebenso nicht. Nur `CONTENT_MODEL.md` und der Anhang von `ROADMAP.md` erwähnen ihn. | `STATUS.md:3`, `STATUS.md:15-30`; `docs/ROADMAP.md:130-143`; grep über README/ARCHITECTURE/CONTRIBUTING ohne Treffer |
| D2 | **Roadmap-Position veraltet.** „Next: dogfood rungs 1–2, then decide rung 3“ (Stand Juli). Der Fangkorb ist in der Leiter nicht verortet. | `docs/ROADMAP.md:73`, `:119-128` |
| D3 | **Zielgruppe widersprüchlich.** STATUS: aktive Mitglieder der Netzbegrünung, 10–50 Nutzer. AUTH-Analyse: Zielgruppe nicht mehr auf Mitglieder begrenzt, breiteres Publikum. | `STATUS.md:9`; `docs/AUTH_REGISTRIERUNG_OPTIONEN.md:4-6` |
| D4 | **Satz-Limit.** Spec v1: hart 200 Zeichen. Code: 120, „dasselbe Limit wie der Titel“. CLAUDE.md: Titel 3–120. | `docs/SPEC_Destillier-Ablauf_v1.md:25`; `mvp/frontend/gutgesagt-frontend/src/app/services/raw-input.service.ts:14-16`; `CLAUDE.md:443-444` |
| D5 | **Fangkorb-Liste: Spec v2 gegen Code.** Spec: keine Gruppierung, ein Strom, eigene zuerst, Filter „nur offene“. Code: drei Tabs nach Arbeitsstufe, neueste zuerst „nicht eigene zuerst“, Verworfenes hinter einem Chip unter „Erledigt“. | `docs/SPEC_Fangkorb_v2.md:14`, `:54`, `:63`; `mvp/frontend/gutgesagt-frontend/src/app/raw-input-list/raw-input-list.component.ts:48-56`; `.../raw-input-list/fangkorb-filter.ts:18-25` |
| D6 | **Anzeigenamen gelten als offen, sind aber gebaut.** Spec v2 „Personen bleiben UUIDs“, Nachlese „Anzeigenamen statt Keycloak-Kennungen“, ROHINPUT „Es gibt keine Nutzertabelle“. Code: Tabelle `users`, `AnzeigenameService`, Migration vom 2026-10-11. | `docs/SPEC_Fangkorb_v2.md:56`; `docs/ISSUE_destillier-nachlese.md:51-54`; `docs/ROHINPUT.md:341-344`; `mvp/backend/semantic-search-service/app/infrastructure/database/models.py:329-344`; `.../app/services/anzeigename_service.py:1-11`; `mvp/backend/postgres-app/migrations/2026-10-11-anzeigenamen.sql` |
| D7 | **ROHINPUT „nichts implementiert“.** Der Status-Kopf ist veraltet; die Datei ist inzwischen die Begründung für ein gebautes Design. | `docs/ROHINPUT.md:3-4`; selbst festgestellt in `docs/ISSUE_destillier-nachlese.md:120` |
| D8 | **`in_progress` wechselt die Bedeutung.** Spec v1: wird nicht verwendet. Spec v2 und Code: heißt „Destilliert“ und wird gesetzt. ROHINPUT schlug `offen → in_arbeit → verarbeitet | verworfen` vor. | `docs/SPEC_Destillier-Ablauf_v1.md:54`; `docs/SPEC_Fangkorb_v2.md:22`; `docs/ROHINPUT.md:163`; `mvp/backend/semantic-search-service/app/domain/models/raw_input.py:18-45` |
| D9 | **Schema-Quelle.** ARCHITECTURE: Schema „once, in `init.sql`“. Datenschutz-Bestandsaufnahme: vier Mechanismen, `init.sql` deckt 2 von 7 Tabellen. Seitdem kamen `raw_input_drafts` und `users` dazu. | `docs/ARCHITECTURE.md:119-121`; `docs/DATENSCHUTZ_BESTANDSAUFNAHME.md:72-88`; `mvp/backend/postgres-app/migrations/` |
| D10 | **Test-Login.** README und ARCHITECTURE: `testuser`. CLAUDE.md und DEV-SETUP: `test.user@example.com`, `testuser` gilt nur für den alten Endpunkt ohne Formular. | `README.md:10`; `docs/ARCHITECTURE.md:13`, `:19`, `:25`, `:152`; `mvp/README_DEV_SETUP.md:113`; `CLAUDE.md:105`; `docs/DEV-SETUP.md:10-11` |
| D11 | **Frontend-Port.** README, CONTRIBUTING, ARCHITECTURE: `http://localhost`. Compose bindet 8080. | `README.md:35`; `CONTRIBUTING.md:26`; `docs/ARCHITECTURE.md:17`; `mvp/docker-compose.dev.yml:181-183` |
| D12 | **Repo-Ort.** CLAUDE.md, README, CONTRIBUTING: GitHub ist `origin`, Issues und PRs dort. PR #205 (offen) stellt CLAUDE.md auf Forgejo um und nennt README/CONTRIBUTING selbst als offen. | `CLAUDE.md:9-25`; `README.md:52`; `CONTRIBUTING.md:13-15`, `:88`, `:97` |
| D13 | **Commit-Trailer.** CLAUDE.md verbietet `Co-Authored-By: Claude`; PR #205 erlaubt ihn ausdrücklich. Die Commits auf diesem Branch tragen den Trailer (Auftrag), widersprechen also dem Stand von `CLAUDE.md` auf diesem Branch. | `CLAUDE.md:7`; PR #205 |
| D14 | **Datenschutzerklärung nennt Screenshots.** „ein Link, ein Screenshot, ein Satz“, obwohl es keinen Datei-Upload gibt und Bilder im Share-Pfad ausdrücklich nicht in v2 sind. Außerdem „verarbeitende Person“ statt Ausformulierer. | `mvp/frontend/gutgesagt-frontend/src/app/datenschutz/datenschutz.component.html:379-383`; `docs/ROHINPUT.md:75-79`; `docs/SPEC_Fangkorb_v2.md:94` |
| D15 | **Rename-Reste in Doku.** `contentgruen-frontend` als Pfad, „ContentGrün“ als Titel. Laut #204 bewusst, weil historisch; für ein Glossar trotzdem eine Quelle alter Namen. | `docs/ISSUE_destillier-nachlese.md:6`; `docs/RECHTSTEXTE_LUECKEN.md:1` |
| D16 | **Infrastruktur-Details im öffentlichen Repo.** ARCHITECTURE und CLAUDE.md nennen interne Hostnamen, Host-Ports, Registry und Salt-Abläufe. Nicht Teil dieses Plans, aber vor einem Umbau von CLAUDE.md zu entscheiden. | `docs/ARCHITECTURE.md:28-34`, `:138-145`, `:170-172`; `CLAUDE.md:276-281`, `:371-383` |

---

## 3. Domäne und Fachsprache

### 3.1 Wo die Sprache heute definiert ist

- **Im Code, nicht in der Doku.** Die besten Definitionen stehen in deutschen Docstrings
  und Konstanten: `RawInputStatus` und `RawInputSource`
  (`mvp/backend/semantic-search-service/app/domain/models/raw_input.py:1-70`),
  `FANGKORB_KURZ`, `EINWERFEN_TITEL`, `KETTEN_ICONS`
  (`mvp/frontend/gutgesagt-frontend/src/app/shared/fangkorb-texte.ts:1-33`), die
  Typ-Registry mit deutschen Labels und Beschreibungen
  (`.../src/app/shared/content-type-registry.ts:40-85`).
- **In Entscheidungsdokumenten**, als Begründung: `docs/ROHINPUT.md`
  („Rohinput ist kein halbfertiger Beitrag, sondern ein Arbeitsauftrag mit Anhang“, `:16-18`).
- **Eine einzige Sprachregel in CLAUDE.md**: Titel als Behauptung (`CLAUDE.md:442-455`).
- **In den Seed-Daten**: Aussage = „Typischer Angriff/Vorwurf gegen Grüne“
  (`mvp/data/seed/v1.0/prompt_generate_seedcontent.md:11`).

### 3.2 Begriffskonflikte

| # | Konzept | Namen im Umlauf | Belege |
|---|---|---|---|
| B1 | das roh abgelegte Fundstück | Einwurf (UI, Datenschutz), Rohinput (Doku-Titel), raw input / `raw_inputs` (Code), Rohling (Karten-Variante), Eintrag (Spec v1) | `docs/ROHINPUT.md:1`; `docs/CONTENT_MODEL.md:197`; `docs/SPEC_Destillier-Ablauf_v1.md:7`; `fangkorb-texte.ts:19` |
| B2 | vier Stufen eines Einwurfs | Code: `open / in_progress / processed / discarded`; Spec v2: offen / destilliert / ausformuliert / verworfen; Fangkorb-Tabs: Destillieren / Ausformulieren / Erledigt (+ Verworfen); Karten-Band: „Zu destillieren“ / „Auszuformulieren“ / „Erledigt“ / „Verworfen“; ROHINPUT: offen / in_arbeit / verarbeitet / verworfen | `raw_input.py:18-45`; `SPEC_Fangkorb_v2.md:46-52`; `fangkorb-filter.ts:18-25`; `beitragskarte.component.ts:53-58`; `ROHINPUT.md:163` |
| B3 | wer aus einem Einwurf einen Beitrag macht | Ausformulierer (UI), `processed_by` (Code), verarbeitende Person (Datenschutz), Bearbeiter (ROHINPUT) | `SPEC_Fangkorb_v2.md:27`; `datenschutz.component.html:383`; `ROHINPUT.md:211` |
| B4 | dritter Kettenschritt | Ausformulieren, Verfassen („`verfassen` steht auch für Ausformulieren“), Verarbeiten | `fangkorb-texte.ts:23-32`; `ROHINPUT.md:316` |
| B5 | Freitext am Einwurf | Hinweis (für andere) (Spec v2, UI), Notiz (Spec v1, ROHINPUT), `content` (Code) | `SPEC_Fangkorb_v2.md:70`; `SPEC_Destillier-Ablauf_v1.md:39` |
| B6 | Quellenangabe | Herkunft (UI seit Paket 1), Quelle (älter), Referenz (noch in `reference-input`), `reference` (Code) | `docs/PR_ui-nachlese-paket1.md:44-45`, `:55-58`, `:79-81` |
| B7 | Angriff, auf den geantwortet wird | Aussage (UI), Statement (Code und CLAUDE.md-Fließtext), „statement with a list of reply suggestions“ (Docstring) | `content-type-registry.ts:76`; `CLAUDE.md:444`; `.../app/domain/models/statement.py:64-72` |
| B8 | Hintergrundinfo | UI: „Fakten und Zahlen, die eine Antwort stützen“; Backend: Sammelbecken für alles ohne eigenen Typ (Reden, Gedichte, Programmauszüge); Enum: „generic text that does not yet have a specific content type“; zwei Schlüssel `generic_text` / `generictext` | `content-type-registry.ts:51-54`; `.../app/domain/models/generic_text.py:52-58`; `.../app/domain/models/content_type.py:16-17`; `docs/PR_ui-nachlese-paket1.md:46-47` |
| B9 | Lebenszyklus eines Beitrags | `ContentStatus` mit 12 Zuständen eines generischen CMS (draft, approved, released_internal, published_external …); STATUS führt „Content status feature“ als nicht begonnen | `.../app/domain/models/content_status.py:4-60`; `STATUS.md:41` |
| B10 | Suchanfrage | wird als Inhalt mit Herkunft `search_query` in Qdrant abgelegt und überall ausgefiltert | `.../app/domain/models/content_origin.py:17-26`; `docs/ROHINPUT.md:53-58`; `docs/DATENSCHUTZ_BESTANDSAUFNAHME.md:537` |
| B11 | Mitwirkende | Nutzer, Nutzende, User, Mitglieder; Rollen Finder/Bearbeiter (ROHINPUT) vs. Einwerfer/Destillierer/Ausformulierer (Spec v2) | `ROHINPUT.md:170`, `:335`; `SPEC_Fangkorb_v2.md:13`, `:25-27` |
| B12 | Schreibweise im Code | `destilled_by` (weder Deutsch noch Englisch) | `SPEC_Fangkorb_v2.md:13`; `raw_input.py` |

### 3.3 Glossar-Entwurf

`GLOSSARY.md` im Repo-Root. Entscheidungen, die der Entwurf vorwegnimmt (alle in der
Session zu bestätigen):

- **Sprache:** Glossar auf Deutsch, weil Domäne, UI, Spezifikationen und Product Owner
  Deutsch sprechen. Englische Code-Namen stehen unter `_Avoid_`.
- **Kontextname:** „Gut gesagt“, ein Kontext.
- **Kanonische Wahl je Konflikt:** Einwurf (B1), offen/destilliert/ausformuliert/verworfen
  (B2, wie Spec v2), Ausformulierer (B3), Ausformulieren (B4), Hinweis (B5), Herkunft (B6),
  Aussage (B7), Hintergrundinfo im Sinn der UI (B8), Mitwirkende (B11).
- **Weggelassen**, weil Technik und nicht Domäne: Embedding, Registry, Seam, Qdrant,
  Kennung/`X-User`, Rate-Limit, `ContentStatus` (B9 ist eine Frage, kein Begriff).
- `_Offene Frage_`-Zeilen sind ein Zusatz zum Format, nur für die Session. Sie werden dort
  beantwortet und gelöscht.

### 3.4 Belege zum Glossar-Entwurf

| Begriff | Belege |
|---|---|
| Kette | `fangkorb-texte.ts:21-33`; `raw-input-list.component.html:25-26`; `SPEC_Fangkorb_v2.md:7` |
| Einwurf, Einwerfen | `fangkorb-texte.ts:1-19`; `ROHINPUT.md:12-18`; `raw_input.py:1-13`; `datenschutz.component.html:377-383` |
| Fangkorb | `SPEC_Destillier-Ablauf_v1.md:22`; `raw-input-list.component.ts:48-60` („der Vorrat ist gemeinsam“) |
| Einwerfer | `SPEC_Fangkorb_v2.md:30`, `:49`; `karten-daten.ts:85` |
| Hinweis | `SPEC_Fangkorb_v2.md:70-72`; `fangkorb-texte.ts:5` |
| Plattform | `SPEC_Fangkorb_v2.md:58-62`; `docs/PR_startseite-mobil.md:152` (`shared/plattform.ts`) |
| Eingangskanal | `raw_input.py:47-68` (`web`, `share`) |
| Destillieren, Satz | `SPEC_Destillier-Ablauf_v1.md:7`, `:40`; `destillieren.component.html:49`; `raw-input.service.ts:14-16`; `CLAUDE.md:445-446` |
| Destillierer | `SPEC_Fangkorb_v2.md:25-26` |
| Ausformulieren, Ausformulierer | `raw-input-list.component.html:26`; `SPEC_Fangkorb_v2.md:7`, `:27` |
| Verwerfen | `SPEC_Destillier-Ablauf_v1.md:22`, `:27`; `SPEC_Fangkorb_v2.md:30`; `raw_input.py:43-44` |
| Stufen | `raw_input.py:18-45`; `SPEC_Fangkorb_v2.md:22`, `:46-52` |
| Beitrag, Beitragstyp | `docs/CONTENT_MODEL.md:24-47`; `content-type-registry.ts:40-85`; `docs/PR_beitragskarte.md:5` |
| Aussage | `mvp/data/seed/v1.0/prompt_generate_seedcontent.md:11`; `content-type-registry.ts:76`; `CLAUDE.md:444` |
| Kommentar | `content-type-registry.ts:42-45`; `.../app/domain/models/commentary.py:55-63`; Seed-Prompt `:13-17` |
| Hintergrundinfo | `content-type-registry.ts:51-54`; `generic_text.py:52-58` |
| Bild | `content-type-registry.ts:67-70` |
| Post | `.../app/domain/models/post.py:12-18`; `STATUS.md:23` |
| Titel | `CLAUDE.md:442-455`; Seed-Prompt `:14` |
| Herkunft | `docs/PR_ui-nachlese-paket1.md:44-58`; `.../app/domain/models/reference.py:10-14` |
| Stil | Seed-Prompt `:17` |
| Nutzung | `docs/ROHINPUT.md:64-65` („zählt Kopiervorgänge“); `docs/PR_beitragskarte.md:91` |
| Stimme | `docs/ROADMAP.md:93-95`; `docs/DATENSCHUTZ_BESTANDSAUFNAHME.md:449` |
| Meldung | `STATUS.md:25`; `docs/DATENSCHUTZ_BESTANDSAUFNAHME.md:297` |
| Suchanfrage | `content_origin.py:17-26`; `docs/ROHINPUT.md:53-58` |
| Mitwirkende, Besucher | `STATUS.md:18`; `docs/AUTH_REGISTRIERUNG_OPTIONEN.md:4-6` |
| Autor | `docs/ROHINPUT.md:335-337`; `docs/PR_beitragskarte.md:53-58` |
| Anzeigename | `anzeigename_service.py:1-11`; `datenschutz.component.html:386-391` |
| Admin | `docs/ARCHITECTURE.md:199-206`; `STATUS.md:26` |

Dateipfade ohne Präfix liegen unter `mvp/frontend/gutgesagt-frontend/src/app/` (`.ts`,
`.html`) bzw. `mvp/backend/semantic-search-service/app/domain/models/` (`.py`).

### 3.5 ADR-Entwürfe

Nur Entscheidungen, die schon gefallen und belegt sind und alle drei Kriterien erfüllen
(`domain-modeling/ADR-FORMAT.md:29-37`):

| ADR | Entscheidung | Quelle |
|---|---|---|
| `0001-einwuerfe-in-postgresql.md` | Einwürfe in PostgreSQL statt als Beitragstyp in Qdrant | `docs/ROHINPUT.md:83-153`; `raw_input.py:1-13` |
| `0002-beitragstyp-als-registry-eintrag.md` | Neuer Typ = Registry-Eintrag + Modell + Karten-Fragment | `docs/CONTENT_MODEL.md:13-47`, `:246-277` |
| `0003-keine-generierten-antworten.md` | Keine KI-generierten Antworten; KI nur beim Erfassen | `STATUS.md:61`; `docs/CONTENT_MODEL.md:66-67`; `docs/ROADMAP.md:36-38`, `:87-91` |

Weitere Kandidaten, bewusst **nicht** vorgeschrieben, weil die Abwägung in der Session
bestätigt werden sollte: „Kein Lock beim Destillieren, Duplikate erlaubt“
(`SPEC_Destillier-Ablauf_v1.md:23`), „Einwürfe werden nie gelöscht“
(`docs/DATENSCHUTZ_BESTANDSAUFNAHME.md:420-423`), „snake_case auf dem Draht“
(`docs/CONTENT_MODEL.md:281-286`, leicht umkehrbar, daher eher kein ADR), „Identität ist die
Kennung aus dem BFF, keine eigene Registrierung“ (hängt an Block 6 unten).

---

## 4. Was `setup-matt-pocock-skills` hier einrichten würde

Nicht ausgeführt. So würde der Lauf aussehen, mit den nötigen Anpassungen.

### 4.1 Erkundung (Schritt 1)

| Prüfpunkt | Befund |
|---|---|
| `git remote -v` | `origin` = Forgejo, `github` = Spiegel. Weder GitHub- noch GitLab-Vorlage passt. |
| `CLAUDE.md` / `AGENTS.md` | `CLAUDE.md` vorhanden, kein `## Agent skills`-Block; kein `AGENTS.md` |
| `GLOSSARY.md`, `GLOSSARY-MAP.md` | fehlen (Entwurf liegt jetzt auf diesem Branch) |
| `docs/adr/` | fehlt (Entwürfe auf diesem Branch) |
| `docs/agents/` | fehlt |
| `.scratch/` | fehlt |
| `triage` installiert | ja |
| Monorepo-Signale | keine (`package.json` ohne `workspaces`) → single-context |

### 4.2 Abschnitt A: Issue-Tracker

Der Skill schlägt bei einem GitHub-Remote GitHub vor. Hier liegt `origin` auf Forgejo, also
fällt er auf die Auswahl zurück. **Empfehlung: „Other“ mit einer eigenen
`docs/agents/issue-tracker.md` für Forgejo.** Gründe:

- Forgejo ist führend; GitHub ist Spiegel, dort keine Issues und PRs (Regel aus #205).
- `tea` funktioniert mit repo-beschränkten Tokens nicht; `gh` ist nicht angemeldet. Es
  bleibt die REST-API per `curl`.
- Lokale `.scratch/`-Dateien wären möglich, verlieren aber die Sichtbarkeit für Mitwirkende
  und bringen Arbeitsstände ins öffentlich gespiegelte Repo.

Offene Punkte, die in der Datei geregelt werden müssen:

1. **Freigabe-Pflicht:** Kommentare und Reviews nur nach Freigabe (Regel des Maintainers),
   die Skills (`triage`, `to-spec`, `to-tickets`, `wayfinder`) schreiben dagegen direkt.
   Vorschlag: Skills erstellen **Issues** direkt (wie PRs), Kommentare an fremden Issues nur
   nach Freigabe.
2. **Kennzeichnungszeile** (`*Beauftragt von … · Modell: …*`) als erste Zeile jedes
   Issue-Texts und Kommentars; `triage` verlangt zusätzlich seinen eigenen Disclaimer
   (`triage/SKILL.md:15-19`). Beide untereinander.
3. **Sub-Issues und Abhängigkeiten:** Forgejo kennt Abhängigkeiten zwischen Issues
   (in der UI „Blockiert durch“). Ob die API das mit dem Bot-Token erlaubt, ist ungeprüft
   (Abschnitt 9). Fallback wie in den Vorlagen: `Blocked by: #n` am Kopf, `Part of #n`.
4. **Nummernraum:** Forgejo zählt Issues und PRs gemeinsam (wie GitHub). Verweise auf alte
   GitHub-Issues mit Präfix schreiben (`GitHub #22`).
5. **Externe:** Forgejo ist für Externe nicht erreichbar (#205, „Offen“). Ob GitHub-Issues
   als Eingang für `triage` dienen, ist eine Produktentscheidung (Block 0 unten).

Entwurf (würde nach `docs/agents/issue-tracker.md` gehen, hier nur als Text):

```markdown
# Issue tracker: Forgejo

Issues, specs and tickets live as Forgejo issues in the primary repository (`origin`).
GitHub is a read-only push mirror: never create issues, PRs or comments there.

## Conventions

- Use the REST API with curl; `tea` and `gh` do not work here. Base: `<origin>/api/v1/repos/<owner>/<repo>`,
  header `Authorization: token <repo-scoped token>`. Never print the token; on errors print only the HTTP status.
- **List issues**: `GET /issues?type=issues&state=open` (without `type=issues` the list includes PRs).
- **Read an issue**: `GET /issues/{n}` and `GET /issues/{n}/comments`.
- **Create an issue**: `POST /issues` with `title`, `body`, `labels` (label ids).
- **Comment**: `POST /issues/{n}/comments`. Only after the maintainer approved the draft.
- **Labels**: `POST /issues/{n}/labels` / `DELETE /issues/{n}/labels/{id}`.
- **Close**: `PATCH /issues/{n}` with `state: closed`.
- Every issue body and comment starts with the attribution line required by the maintainer.
- Refer to old GitHub issues as `GitHub #n`; a bare `#n` means Forgejo.

## Pull requests as a triage surface

**PRs as a request surface: no.**

## When a skill says "publish to the issue tracker"

Create a Forgejo issue.

## When a skill says "fetch the relevant ticket"

Read the issue and its comments as above.

## Wayfinding operations

- **Map**: one issue labelled `wayfinder:map`.
- **Child ticket**: `Part of #<map>` as first body line; labels `wayfinder:<type>`.
- **Blocking**: Forgejo issue dependencies if the API allows them for the bot, otherwise a
  `Blocked by: #n, #n` line at the top of the body.
- **Claim**: assign the issue to the driving dev.
```

### 4.3 Abschnitt B: Triage-Labels

Forgejo hat keine Repo-Labels. Der Skill würde die fünf Default-Labels anlegen
(`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`); `triage`
braucht zusätzlich die Kategorien `bug` und `enhancement`, `wayfinder` die Labels
`wayfinder:map|research|prototype|grilling|task`. **Empfehlung:** Defaults übernehmen, aber
Labels **nicht** automatisch anlegen lassen (ein Schreibzugriff auf Forgejo-Einstellungen,
den der Bot-Token vielleicht nicht darf), sondern die Liste dem Maintainer geben. Auf GitHub
gibt es `bug`, `enhancement`, `wontfix` schon; wird GitHub Eingang für Externe, müssen beide
Seiten dieselben Namen haben.

### 4.4 Abschnitt C: Domain-Doku

Single-context: `GLOSSARY.md` im Root, `docs/adr/`. Begründung: ein Produkt, eine Sprache;
BFF und Suche haben keine eigene Fachsprache, sondern sind Technik. Ein zweiter Kontext wäre
höchstens „Recht und Datenschutz“, der aber keine eigenen Begriffe für dieselben Dinge hat.
`docs/agents/domain.md` würde aus der Vorlage
(`setup-matt-pocock-skills/domain.md`) unverändert übernommen.

### 4.5 Block in `CLAUDE.md`

```markdown
## Agent skills

### Issue tracker

Issues live on Forgejo (primary repo), accessed via the REST API; GitHub is a mirror. See `docs/agents/issue-tracker.md`.

### Triage labels

Default triage vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` at the root, decisions in `docs/adr/`. See `docs/agents/domain.md`.
```

### 4.6 Nötige Anpassungen an diesem Repo vor oder mit dem Setup

1. **#205 zuerst mergen.** Sonst verbietet `CLAUDE.md:7` den Co-Author-Trailer und
   `CLAUDE.md:9-25` schickt Agenten nach GitHub. Der Skill-Block gehört auf den Stand nach #205.
2. **`CLAUDE.md` entschlacken** (`writing-for-agents`): 467 Zeilen, davon viel Cache dessen,
   was in Skripten steht (Quick Commands, Backup-Befehle, Ports), plus Infrastruktur-Details
   (D16). Vorschlag: eigener PR nach der Session, nicht im Setup-PR.
3. **`docs/SPEC_*`, `docs/PR_*`, `docs/ISSUE_*` einordnen.** Die Skills legen Specs im Tracker
   ab, nicht in `docs/`. Vorschlag: bestehende Dateien nach `docs/archiv/` mit einem Satz
   „historisch, Stand X, vom Code überholt“, neue Specs nur noch als Forgejo-Issue.
4. **Kein `.claude/` und keine Hooks im Repo** im ersten Schritt; `git-guardrails-claude-code`
   und `setup-pre-commit` passen nicht (es gibt schon pre-commit mit Ruff/Black/Tests).

---

## 5. Reihenfolge der Skills für Gut gesagt

| Schritt | Skill | Wann | Ergebnis |
|---|---|---|---|
| 0 | (Vorarbeit) | erledigt | dieser Plan, Glossar- und ADR-Entwürfe |
| 1 | Setup-Entscheidungen | morgen, Block 0 | Antworten zu A/B/C; Ausführung danach |
| 2 | `grill-with-docs` | morgen, Blöcke 1–6 | abgestimmtes `GLOSSARY.md`, ADRs bestätigt oder verworfen |
| 3 | `setup-matt-pocock-skills` | direkt nach der Session, gleicher Branch oder eigener | `docs/agents/*.md`, `## Agent skills` in `CLAUDE.md` |
| 4 | Doku-Aufräumen | eigener PR | STATUS/README/ARCHITECTURE an Glossar und Code angleichen, Specs archivieren |
| 5 | `improve-codebase-architecture` | eigene Session | HTML-Bericht; Hotspot Frontend (Fangkorb, Beitragskarte), Legacy-Typen außerhalb der Registry |
| 6 | `triage` | sobald Issues auf Forgejo liegen | Altlasten aus GitHub-Meilensteinen und `docs/ISSUE_*` sichten |
| 7 | `to-spec` → `to-tickets` → `implement` | beim nächsten Vorhaben | erstes Vorhaben komplett über den Tracker |
| 8 | `retro` | nach dem ersten Vorhaben | Anpassungen an CLAUDE.md, Standards |

`wayfinder` erst, wenn ein Vorhaben ansteht, das größer ist als eine Session, etwa Rung 3
(Analyse-Schicht mit Eval-Set) oder die offene Registrierung.

---

## 6. Agenda für die `grill-with-docs`-Session

Rahmen: rund drei Stunden, ein Kontextfenster. Grilling-Format: je Runde die ganze Frontier,
nummeriert, mit Empfehlung. Das Glossar wird **während** der Session geändert, nicht danach.
Reihenfolge so gewählt, dass frühe Antworten spätere Fragen schließen.

### Block 0 – Setup-Rahmen (15–30 min, ohne Glossar)

Fragen:
1. Tracker = Forgejo via API („Other“)? Empfehlung: ja (4.2).
2. Dürfen Skills Issues ohne Freigabe anlegen, Kommentare nur mit? Empfehlung: ja.
3. Sind GitHub-Issues ein Eingang für Externe, den `triage` liest? Empfehlung: nein, bis
   #205 „Offen“ entschieden ist; dann gegebenenfalls Flag nachziehen.
4. Default-Triage-Labels, vom Maintainer angelegt statt vom Skill? Empfehlung: ja.
5. Single-context? Empfehlung: ja.
6. Glossar auf Deutsch, ADRs auf Deutsch, `docs/agents/*` auf Englisch (Agentenanweisungen)?
   Empfehlung: ja.
7. Wo liegt der Backlog aus den GitHub-Meilensteinen heute? (Faktenfrage an den Maintainer,
   nicht aus dem Repo klärbar.)

### Block 1 – Produktkern: Was ist Gut gesagt, für wen?

Fragen:
1. Ein-Satz-Beschreibung des Kontexts: Ist Gut gesagt ein Vorrat an Antworten auf Angriffe
   (Seed-Prompt, Kommentar-Beschreibung) oder eine allgemeine „semantic content platform“
   (README, STATUS)? Empfehlung: Ersteres, siehe Glossar-Kopf.
2. Wer sind Mitwirkende: Mitglieder der Netzbegrünung oder ein breiteres Publikum (D3)?
3. Was dürfen Besucher ohne Anmeldung (Suche ja, Fangkorb nein, `STATUS.md:18`)? Bleibt das?
4. Gilt ADR 0003 (keine generierten Antworten)? Empfehlung: annehmen.

Widersprüche: D1, D2, D3.

### Block 2 – Die Kette: Einwurf, Destillieren, Ausformulieren

Fragen:
1. Kanonischer Name für das Fundstück: Einwurf (Empfehlung), Rohinput oder Rohling (B1)?
2. Kanonische Namen der vier Stufen (B2). Empfehlung: offen, destilliert, ausformuliert,
   verworfen als Zustände; die Tabs heißen nach der **nächsten Arbeit** und sind kein
   Zustandsname. Dazu Szenario: Ein verworfener Einwurf wird von jemand anderem destilliert
   und ausformuliert. Welche Stufe hat er?
3. Ausformulieren und Verfassen: ein Begriff oder zwei (B4)? Szenario: Jemand schreibt einen
   Kommentar ohne Einwurf.
4. Wer ist Autor eines Beitrags aus dem Fangkorb: Ausformulierer allein, oder auch Einwerfer
   und Destillierer (Glossar „Autor“)? Folgen für „Meine Beiträge“ und spätere Punkte.
5. Ist der Satz immer der Titel (`CLAUDE.md:445-446`)? Gilt dann das Titel-Limit (D4)?
6. Wer darf verwerfen, und ist „verworfen“ endgültig (`raw_input.py:28` erlaubt
   verworfen → ausformuliert)?
7. Soll ADR 0001 (Einwürfe in PostgreSQL, nie löschen) so stehen?
8. „Kein Lock, Duplikate erlaubt“ als ADR?
9. Eingangskanal: Domänenbegriff oder Technik?

10. Wer bestimmt die Stufe eines Einwurfs: der gespeicherte Status oder die Ableitung aus
    Sätzen und Verknüpfungen (8.1, `FE/beitragskarte/karten-daten.ts:250-274`)? Fachlich
    gefragt: Ist ein Einwurf ausformuliert, sobald ein Beitrag verknüpft ist, auch wenn er
    verworfen war?
11. „Später“ oder „Überspringen“ (C5)?

Widersprüche: D4, D5, D6, D7, D8, D14, B1–B5, B11, B12, C4, C5.

### Block 3 – Beiträge und Beitragstypen

Fragen:
1. Welche Typen sind Beiträge: Kommentar, Hintergrundinfo, Bild, Post. Sind Aussage und
   Herkunft Beiträge oder etwas anderes (Glossar „Beitrag“)?
2. Hintergrundinfo: „Fakten zu einer Antwort“ oder „Sammelbecken“ (B8)? Folgt daraus ein
   neuer Typ für das Sammelbecken?
3. Aussage: nur Angriffe von außen? Wer legt Aussagen an, wenn nicht die Seed-Daten (B7)?
   Und sind gespeicherte Suchanfragen Aussagen im Entstehen (B10)?
4. Post gegen Einwurf mit Link: Wann ist ein Social-Media-Post ein Beitrag, wann ein Einwurf?
5. Herkunft statt Quelle und Referenz, auch im Code-Vokabular künftiger Tickets (B6)?
6. Gilt ADR 0002 (Registry), und bleiben Aussage und Herkunft dauerhaft außerhalb
   (`docs/CONTENT_MODEL.md:292-296`)?

7. „Destillat“ (Nutzungsbedingungen: das Argument in eigenen Worten, im Gegensatz zur
   Herkunft) als Begriff übernehmen oder aus dem Rechtstext entfernen (C6)?
8. „Herkunft“ auch für „woher kam das Formular“ (Fangkorb, Suche, frei)? Empfehlung: nein,
   dafür ein anderes Wort (C3).

Widersprüche: B6, B7, B8, B10, C3, C6, C7.

### Block 4 – Lebenszyklus, Qualität, Moderation

Fragen:
1. Welche Zustände hat ein Beitrag fachlich? `ContentStatus` kennt zwölf, die Doku
   „Content status feature: not started“ (B9). Empfehlung: Glossar nennt nur, was es gibt;
   der Rest geht als Frage an `improve-codebase-architecture`.
2. Meldung, Moderation, Admin: eine Rolle oder zwei?
3. Nutzung = Kopiervorgang: Ist das die Erfolgsmetrik? Zählt eine Stimme mit?
4. Dubletten: Kommentar-Dedup meldet Erfolg und liefert einen fremden Kommentar
   (`docs/ISSUE_destillier-nachlese.md:106-108`). Gewollt?

### Block 5 – Personen, Identität, Sichtbarkeit

Fragen:
1. Anzeigename, Kennung, Klarname: was sehen andere (D6, C2, `datenschutz.component.html:386-391`)?
2. Was passiert mit Sätzen an fremden Einwürfen bei Kontolöschung
   (`docs/LOESCHKONZEPT.md:87-92`, `docs/ROADMAP.md:138-140`)?
3. Hängt Registrierung (AUTH-Analyse) an Block 1, Frage 2? Dann als `wayfinder`-Kandidat
   vormerken, nicht heute entscheiden.

### Block 6 – Doku-Ordnung (20 min)

Fragen:
1. `STATUS.md` und `ROADMAP.md`: zusammenlegen oder STATUS als kurze Lageseite neu?
2. `docs/SPEC_*`, `PR_*`, `ISSUE_*` archivieren (4.6, Punkt 3)?
3. Infrastruktur-Details aus öffentlicher Doku entfernen (D16)?
4. Wer pflegt das Glossar (nur Agent in Sessions, oder auch von Hand)?

### Abschluss

- Glossar durchgehen, alle `_Offene Frage_`-Zeilen weg.
- ADRs: `status: accepted` oder löschen.
- Phase-Grenze nach `ask-matt/PHASE-BOUNDARIES.md`: Setup direkt im selben Kontext
  ausführen (Continue), Doku-Aufräumen als Subagent.

---

## 7. Nach der Session

1. `setup-matt-pocock-skills` mit den Antworten aus Block 0 ausführen; Ergebnis plus
   bestätigtes Glossar und ADRs als ein PR („docs: Glossar, ADRs und Skill-Setup“).
2. Doku-PR: D1, D2, D9–D11, D14 beheben; Specs archivieren; STATUS neu.
3. Labels auf Forgejo anlegen (Maintainer).
4. `improve-codebase-architecture` mit Richtung „Fangkorb und Beitragskarte“ sowie
   „Legacy-Typen außerhalb der Registry“.
5. Erstes echtes Vorhaben über `to-spec` → `to-tickets` → `implement`, um den Tracker-Weg
   zu erproben. Kandidaten aus dem Bestand: Post-Formular (`STATUS.md:37`), Detailansicht
   Beitrag (`docs/ROADMAP.md:134-137`), Löschlogik für Sätze (`docs/ROADMAP.md:138-140`).
6. `retro` nach dem ersten Vorhaben.

---

## 8. Architektur und Tests (Kurzbefund für spätere Skills)

Für `improve-codebase-architecture`, `tdd` und `to-spec` (Nähte, Testflächen). Kurzform:
`PY` = `mvp/backend/semantic-search-service/app`, `FE` = `mvp/frontend/gutgesagt-frontend/src/app`,
`BFF` = `mvp/backend/BFF`, `PG` = `mvp/backend/postgres-app`.

### 8.1 Module und Nähte

- **Aufrufkette:** Browser → nginx im Frontend-Container → BFF (Cookie-Auth, YARP-Catch-all,
  `BFF/Program.cs:219-233`) → Python. Das BFF hat keine Datenbank (`BFF/BFF.csproj:10-16`).
- **Identität ist eine Naht aus Headern.** Das BFF entfernt Client-Header und setzt `X-User`,
  `X-Is-Admin`, `X-User-Display-Name` (`BFF/Proxy/IdentityHeaderTransform.cs:21-31`, `:47-55`).
  Python prüft nichts selbst und vertraut diesen Headern (`PY/dependencies.py:217-262`). Wer
  Port 8000 erreicht, ist beliebiger Nutzer (`docs/ARCHITECTURE.md:281-286`).
- **Admin zweimal:** `require_admin` liest `X-Is-Admin` (`PY/dependencies.py:249-262`), die
  Usage-Endpunkte prüfen eine eigene Liste (`PY/core/config.py:142-156`, `PY/api/v1/usage.py:260`).
- **Datenhoheit:** Python besitzt Qdrant (alle Beitragstypen in einer Collection) und
  PostgreSQL (acht Tabellen, `PY/infrastructure/database/models.py:30-348`, plus `votes` per
  Laufzeit-DDL). Kein Migrationswerkzeug: `create_all` plus sechs handangewendete SQL-Dateien;
  `create_all` ergänzt keine Spalten (`PG/migrations/2026-09-13-fangkorb-v2.sql:17-21`).
- **Beitragstypen:** Registry-Weg für Post und Bild, handgeschriebene Klassen für die vier
  älteren Typen (`docs/CONTENT_MODEL.md:8-11`). Zwei Wege für dasselbe Konzept.
- **Fangkorb im Frontend leitet den Zustand selbst ab**, aus Sätzen und Verknüpfungen statt aus
  `status` (`FE/beitragskarte/karten-daten.ts:250-274`). Zwei Wahrheiten für die Stufe eines
  Einwurfs: Backend-Status und Frontend-Ableitung.
- **Frontend-Typen hinken nach:** `ContentType` ohne `post`/`image`
  (`FE/services/dtos/statementDtos.ts:5`), `ContentStatus` ohne die beiden Bild-Zustände
  (`FE/services/dtos/content-status-enum.ts`), `ContentOrigin` ohne `search_query`.
- **Ungenutzte Endpunkte:** Themen und Kategorien von Aussagen (`PY/api/v1/statement.py:223-284`)
  ruft das Frontend nicht auf. Kein Domänenbegriff „Thema“ oder „Tag“ im Datenmodell.
- **KI zur Laufzeit:** nur lokale E5-Einbettungen und, abgeschaltet ohne Schlüssel, die
  Bildbeschreibung (`PY/core/config.py:20`, `:139`). Destillieren ist rein menschlich.

### 8.2 Tests

| Dienst | Umfang | Werkzeug | CI |
|---|---|---|---|
| Python | 68 Testdateien, rund 870 Tests (unit, integration, regression) | pytest | unit + integration mit Qdrant-Container; `integration/api` und `regression` ausgenommen |
| BFF | 9 Testklassen, 95 Facts/Theories | xUnit, Moq, Mvc.Testing | `dotnet test GutGesagt.sln` |
| Frontend | 60 Specs, rund 645 `it` | Karma + Jasmine | `ng test --browsers=ChromeHeadless` |

- Kein End-to-End-Test (kein Playwright/Cypress im Branch; ein Branch `chore/e2e-playwright`
  existiert auf dem Remote).
- Lücken: Moderation und Admin auf allen Ebenen, `content_report_repository.py`,
  `metrics_service.py`, mehrere Frontend-Services und Guards, SQL-Migrationen.
- `PY/pytest.ini:2-4` sagt „nur Unit-Tests in CI“, die CI fährt auch Integrationstests.
- Pre-commit prüft nur Python (Ruff, Black, Unit-Tests), nichts für Frontend und .NET.
- Bestehende **Nähte für `tdd`**: Python-Router über FastAPI-Testclient, Repositories gegen
  echtes Qdrant in `tests/integration/`, Frontend-Komponenten mit Headless-Chrome, BFF-Pipeline
  mit `AuthGatePipelineTests`.

### 8.3 Hotspots seit Juli 2026

Fangkorb → Destillieren → Beitragsformular (`add-commentary`, `add-generictext`,
`destillieren`, `raw-input-list`), die Beitragskarte und die geteilte Frontend-Schicht;
dahinter Python-API und -Tests zu Kommentar, Hintergrundinfo und Einwurf; dann Datenschutz
und das Auth-Gate im BFF. Größte Dateien: `PY/repositories/implementations/qdrant/base_repository.py`
(791 Zeilen), `PY/services/orchestration/content_orchestrator.py` (752), `BFF/Program.cs` (665),
`FE/beitragskarte/beitragskarte.component.scss` (805). Kandidaten für
`improve-codebase-architecture`: Legacy-Typen auf die Registry, ein Ort für die Stufe eines
Einwurfs, `Program.cs` aufteilen, Identitäts-Naht zwischen BFF und Python.

### 8.4 Weitere Funde aus dem Code

| # | Befund | Beleg |
|---|---|---|
| C1 | Alle sechs Migrationen nennen im Kopf noch Container `contentgruen-app-postgres` und DB `contentgruen_app`; der Befehl funktioniert so nicht mehr. | `PG/migrations/2026-08-19-rohinput-fangkorb.sql:17-19`; `mvp/docker-compose.dev.yml:58` |
| C2 | Anzeigename unter fünf Namen: `anzeigename`, `DisplayName`, `X-User-Display-Name`, `autor_name`, `submitted_by_name`/`user_name`. | `PG/migrations/2026-10-11-anzeigenamen.sql:23-27`; `BFF/Models/ManagedUser.cs:14`; `PY/dtos/search.py:48`; `FE/services/raw-input.service.ts:47`, `:71` |
| C3 | „Herkunft“ ist doppelt belegt: Label für `reference` und Typ `Herkunft = 'fangkorb' | 'suche' | 'frei'` (woher ein Formular kam). | `FE/shared/content-type-registry.ts:83`; `FE/beitragsformular/beitrag-gespeichert/gespeichert-adresse.ts:18` |
| C4 | „web“ ist zugleich Eingangskanal und Plattform. | `PY/domain/models/raw_input.py:57`; `FE/shared/plattform.ts:8` |
| C5 | Knopf „Überspringen“ ruft `spaeter()` (Spec v1: „Später“), „Ausformulieren“ ruft `weiter()`. | `FE/destillieren/destillieren.component.html:59-63` |
| C6 | „Destillat“ steht nur in den Nutzungsbedingungen, nirgends im Code oder in der Doku. | `FE/nutzungsbedingungen/nutzungsbedingungen.component.html:43`, `:48`, `:57`, `:73` |
| C7 | Sichtbarkeit `internal` heißt im UI „Grün-Intern“ und ist Default jedes Beitrags. | `FE/services/dtos/content-visibility-display.ts:13`; `PY/domain/models/base_content.py:101` |

---

## 9. Nicht geklärt

- Wo der Backlog liegt: GitHub-Meilensteine zeigen 27 offene Issues, die API nur eines;
  Forgejo hat keine. Vermutlich übertragen, gelöscht oder in einem anderen System.
- Ob der Bot-Token auf Forgejo Labels anlegen und Issue-Abhängigkeiten setzen darf.
- Ob Forgejo-Issue-Abhängigkeiten über die API auslesbar sind (für `wayfinder`/`to-tickets`).
- Welche `ContentStatus`-Werte in Produktion tatsächlich vorkommen.
- Ob #204/#207 vor der Session gemergt sind; die Zeilenangaben beziehen sich auf den
  Branch-Stand.
