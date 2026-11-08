# Gut gesagt Scripts Guide

All scripts are located in the `mvp/scripts/` directory and organized by category.

## Quick Reference

| Task | Windows | Unix/Linux/Mac |
|------|---------|----------------|
| **Start local development** | `scripts\dev\run-local.bat` | `scripts/dev/run-local.sh` |
| **Start Docker environment** | `scripts\dev\run-docker.bat` | `scripts/dev/run-docker.sh` |
| **Run all tests** | `scripts\test\run-all-tests.bat` | `scripts/test/run-all-tests.sh` |
| **Check environment** | `scripts\setup\check-environment.bat` | `scripts/setup/check-environment.sh` |
| **Install dependencies** | `scripts\setup\install-dependencies.bat` | `scripts/setup/install-dependencies.sh` |
| **Clean everything** | `scripts\utils\clean-all.bat` | `scripts/utils/clean-all.sh` |
| **Create backup** | N/A (Linux/Unix only) | `scripts/backup/backup.sh` |
| **Restore backup** | N/A (Linux/Unix only) | `scripts/backup/restore.sh` |
| **Test backup/restore** | N/A (Linux/Unix only) | `scripts/backup/test-backup-restore.sh` |
| **Einwürfe aus einer Liste einwerfen** | `python scripts\manual\einwuerfe_importieren.py` | `scripts/manual/einwuerfe_importieren.py` |
| **Startbestand einspielen, Beiträge entfernen** | `python scripts\manual\beitraege_importieren.py` | `scripts/manual/beitraege_importieren.py` |

## Directory Structure

```
mvp/scripts/
├── dev/                    # Development environment launchers
│   ├── run-local.*        # Start all services locally
│   ├── run-docker.*       # Start all services in Docker
│   └── run-docker-postgres.*  # Start only PostgreSQL in Docker
├── test/                   # Test runners
│   ├── run-all-tests.*   # Run all tests (backend, frontend, BFF)
│   ├── run-backend-tests.*   # Run Python backend tests only
│   ├── run-frontend-tests.*  # Run Angular frontend tests only
│   └── run-bff-tests.*   # Run .NET BFF tests only
├── setup/                  # Setup and installation
│   ├── check-environment.*   # Verify development environment
│   └── install-dependencies.*  # Install all project dependencies
├── backup/                 # Backup and restore (Linux/Unix only)
│   ├── backup.sh          # Create backup of Qdrant + PostgreSQL
│   ├── restore.sh         # Restore from backup
│   ├── test-backup-restore.sh  # Test backup/restore workflow
│   └── README.md          # Detailed backup documentation
├── manual/                 # Handarbeit an einer laufenden Instanz (README.md)
│   ├── einwuerfe_importieren.py  # Einwürfe aus einer Liste in den Fangkorb
│   └── beitraege_importieren.py  # Startbestand einspielen, Beiträge entfernen
└── utils/                  # Utility scripts
    ├── clean-all.*        # Clean all build artifacts and dependencies
    ├── switch-to-docker.* # Configure for Docker mode
    └── switch-to-local.*  # Configure for local mode
```

## Development Scripts (`scripts/dev/`)

### run-local
Starts all services in local development mode:
- PostgreSQL in Docker container
- Python Semantic Search API (port 8000)
- .NET BFF (port 5054)
- Angular Frontend (port 4200)

**Features:**
- Automatic virtual environment setup
- Dependency installation
- Environment configuration
- Live reload for all services

### run-docker
Starts all services in Docker containers:
- Uses `docker-compose.dev.yml`
- Frontend accessible on port 80
- All services networked together

### run-docker-postgres
Starts only the databases (`docker-compose.local-dbs.yml`):
- Useful for local development where the app services run on the host
- Qdrant on port 6333, PostgreSQL on port 5433
- Persistent volumes for data

## Test Scripts (`scripts/test/`)

### run-all-tests
Orchestrates all test suites:
1. Python backend unit tests
2. Angular frontend tests (headless Chrome)
3. .NET BFF tests

Returns appropriate exit codes for CI/CD integration.

### run-backend-tests
Runs Python pytest suite:
- Unit tests only (excludes integration tests)
- Skips seeding implementation tests (requires special setup)
- Uses virtual environment

### run-frontend-tests
Runs Angular tests:
- Uses `npm run test:ci` (headless, no-watch mode)
- ChromeHeadless browser
- Suitable for CI/CD

### run-bff-tests
Runs .NET tests:
- Uses `dotnet test`
- Includes all BFF unit and integration tests

## Setup Scripts (`scripts/setup/`)

### check-environment
Comprehensive environment verification:
- Checks for required tools (Docker, .NET, Node.js, Python)
- Verifies Docker is running
- Checks for port conflicts
- Cross-platform compatible

### install-dependencies
Installs all project dependencies:
1. Python: Creates venv, installs from requirements.txt
2. .NET: Runs `dotnet restore`
3. Node.js: Runs `npm install`

Run this after cloning the repository or after running `clean-all`.

## Backup Scripts (`scripts/backup/`) - Linux/Unix Only

### backup
Creates a complete backup of Qdrant and PostgreSQL:
- Qdrant vector database (content + embeddings)
- PostgreSQL metadata (usage tracking)
- Backup metadata with checksums
- Stored in `/opt/gutgesagt-backups/daily/backup_YYYYMMDD_HHMMSS/`
- On Sundays, additionally copied to `/opt/gutgesagt-backups/weekly/`
- Creates the backup directories on first run
- Automatic rotation keeps the last 7 daily and 4 weekly backups
  (`KEEP_DAILY` / `KEEP_WEEKLY` at the top of the script)

**Usage:**
```bash
scripts/backup/backup.sh
```

### restore
Restores data from a backup:
- Prompts for confirmation (destructive operation)
- Stops application container
- Restores Qdrant snapshot
- Restores PostgreSQL database
- Restarts application container
- Verifies restoration

**Usage:**
```bash
# Paths are resolved relative to /opt/gutgesagt-backups/
scripts/backup/restore.sh daily/latest                    # Restore latest daily backup
scripts/backup/restore.sh weekly/latest                   # Restore latest weekly backup
scripts/backup/restore.sh daily/backup_20250916_103000    # Restore a specific backup
```

### test-backup-restore
End-to-end test of backup/restore functionality:
- Counts current data state
- Creates backup
- Adds test marker to Qdrant
- Restores from backup
- Verifies data integrity
- Checks API health

**Usage:**
```bash
scripts/backup/test-backup-restore.sh
```

**Note:** Backup scripts are Linux/Unix only and require:
- Docker running with Gut gesagt containers
- `/opt/gutgesagt-backups/` directory (created by setup script)
- GNU coreutils (stat, md5sum, readlink)

See `scripts/backup/README.md` for detailed documentation.

## Einwürfe importieren (`scripts/manual/einwuerfe_importieren.py`)

Legt Einwürfe aus einer CSV- oder Markdown-Liste in den Fangkorb, je Zeile einen,
über dieselbe API wie das Einwurf-Formular. Das Skript meldet sich am BFF unter dem
angegebenen Konto an (E-Mail und Passwort wie im Login-Formular, also nur mit einem
Beta-Zugang, nicht mit dem Netzbegrünung-Login); dieses Konto ist dann der Einwerfer.
Nach dem Umzug der Beta-Zugänge in den Realm (#488) gibt es die Direktanmeldung nur noch in
der Entwicklung; einen Import in Test oder Produktion also vorher laufen lassen
(`docs/KEYCLOAK_REALM.md`, „Beta-Zugänge umziehen“).
Für den Startbestand ist das ein Startkonto (`docs/VISION.md`). Als Weg trägt jeder
Einwurf „Import“ (`import`), nicht „Formular“.
Das Konto muss vorher einmal in der App in die Art.-9-Einwilligung eingewilligt haben
(`docs/ART9_EINWILLIGUNG.md`); sonst bricht das Skript beim ersten Einwurf mit diesem Hinweis ab.

- Liegt schon ein Einwurf mit gleichem Link im Fangkorb, egal in welcher Stufe, wird
  die Zeile übersprungen und mit dem vorhandenen Einwurf gemeldet. Was als gleicher
  Link gilt, entscheidet der Server (`GLOSSARY.md`).
- `--trockenlauf` zeigt nur, was eingeworfen würde. Angemeldet wird trotzdem, weil die
  Prüfung auf gleichen Link eine Anmeldung braucht. Doppelte Zeilen innerhalb der
  Liste erkennt der Trockenlauf nur bei wortgleichem Link; im echten Lauf findet sie
  der Server.
- Tracking-Parameter (`utm_…`, `fbclid` usw.) entfernt der Server beim Einwerfen,
  im Link und in Links im Hinweis, wie das Formular.
- Zeilen ohne http(s)-Link und vom Server abgelehnte Zeilen (etwa ein Hinweis über
  5000 Zeichen) werden gemeldet; der Rest läuft weiter.
- Exit-Code 0: alles eingeworfen oder übersprungen; 1: mindestens eine Zeile mit
  Fehler; 2: Liste unlesbar, `--adresse` unpassend, Anmeldung gescheitert, Server
  nicht erreichbar oder keine API-Antwort (`--adresse` zeigt nicht auf Gut gesagt).
- `--adresse` muss https sein; http nur für `localhost`, damit das Passwort nie
  unverschlüsselt übers Netz geht.
- Nur Python-Standardbibliothek, läuft also ohne venv und ohne Repo-Checkout.

**Dateiformat** (Beispiele: `scripts/manual/einwuerfe_beispiel.csv`,
`scripts/manual/einwuerfe_beispiel.md`):

- **CSV** mit Kopfzeile, Spalte `link` und optional `hinweis`; Trennzeichen Komma,
  Semikolon oder Tab; UTF-8.
- **Markdown** (Endung `.md`): Jeder Listenpunkt (`-`, `*`, `+`, `1.`) ist ein Einwurf.
  Der erste Link im Punkt ist der Link (nackt, `<…>` oder `[Text](…)`), der übrige Text
  der Hinweis. Satzzeichen direkt nach einem nackten Link gehören nicht zum Link.
  Überschriften und Fließtext werden ignoriert.

Echte Listen gehören nicht ins Repo, auch nicht als Testdaten.

**Usage:**
```bash
# Erst ansehen, dann einwerfen. Ohne GUTGESAGT_PASSWORT fragt das Skript nach dem Passwort.
python3 scripts/manual/einwuerfe_importieren.py liste.csv --email konto@example.org \
  --adresse https://gutgesagt-test.netzbegruenung.de --trockenlauf
python3 scripts/manual/einwuerfe_importieren.py liste.csv --email konto@example.org \
  --adresse https://gutgesagt-test.netzbegruenung.de
```

`--adresse` ist die Adresse des BFF (auf Test und Produktion leitet das Frontend `/api`
nicht weiter, im Dev-Stack schon); Standard ist das lokale BFF `http://localhost:5054`. Getestet in
`tests/unit/services/test_einwuerfe_importieren_skript.py` (Lesen, Import) und
`tests/integration/api/test_einwuerfe_importieren_bff.py` (gegen den Dev-Stack).

## Startbestand einspielen (`scripts/manual/beitraege_importieren.py`)

Legt Kommentare aus einer Markdown-Datei an, je Kommentar ein Aufruf derselben API wie im
Kommentar-Formular (`/api/v1/commentary/addCommentary`): mit Titel, Fassungen und Herkunft,
als Antwort auf seine Aussage. Die Aussage legt der Server an oder nimmt eine vorhandene,
sehr ähnliche; eine vorhandene Herkunft nimmt er wieder. Gedacht für den Startbestand
(`GLOSSARY.md`); Autor ist das angemeldete Konto, das vorher einmal in der App in die
Art.-9-Einwilligung eingewilligt haben muss. Als CC0-Kennung schickt das Skript die des Kommentar-Formulars
(`docs/CC0_HINWEIS_WORTLAUTE.md`): Wer mit `--ausfuehren` importiert, stellt die Texte unter
CC0 wie beim Absenden im Formular. Kennt der Dienst die Kennung noch nicht (ältere Version),
legt es ohne Kennung an und sagt das.

**Anmeldung.** Auf Test und Produktion meldet man sich nur über Keycloak im Browser an;
das Skript nimmt deshalb die Sitzung des Browsers:

1. In Gut gesagt mit dem Konto anmelden, das schreiben soll (beim Entfernen ein Admin).
2. Entwicklertools öffnen (F12), Reiter „Netzwerkanalyse“ (Firefox) bzw. „Netzwerk“ (Chrome),
   Seite neu laden, eine Anfrage an den BFF-Host wählen (Produktion
   `bff.gutgesagt.netzbegruenung.de`) und unter den Anfrage-Kopfzeilen die ganze Zeile
   `Cookie` kopieren. Das Cookie `GutGesagtAuthCookie` gehört zum BFF-Host: unter „Cookies“
   der Frontend-Adresse im Web-Speicher steht es nicht. Nur der Wert des Cookies geht auch.
3. Die Zeile in eine Datei schreiben, die nur man selbst lesen kann, und sie mit
   `--sitzung-datei <datei>` angeben (oder sie in `GUTGESAGT_SITZUNG` legen).

`--adresse` ist auf Test und Produktion die Adresse des BFF, nicht des Frontends. Das Frontend antwortet dort auf
`/api/...` mit seiner Seite (HTML, Status 200); dann bricht das Skript mit einem Hinweis auf
die BFF-Adresse ab, ohne die Antwort auszugeben.

Das Cookie ist HttpOnly und gilt 14 Tage nach der letzten Anfrage, gleitend
(`BFF/Program.cs`, `AddCookie`). Das BFF führt keine Sitzungen auf dem Server: Abmelden im
Browser macht den kopierten Wert nicht ungültig. Die Datei deshalb nach dem Lauf löschen.
Antiforgery-Token oder eine Origin-Prüfung gibt es im BFF nicht, das Cookie allein reicht.
Das Skript gibt das Cookie nirgends aus; es zeigt nur, als wer es angemeldet ist
(`/api/user-info`). Im lokalen Dev-Stack geht stattdessen `--email` mit Passwort
(Direktanmeldung, auf Test und Produktion aus).

- Weiterleitungen folgt das Skript nicht (sonst ginge das Cookie an die neue Adresse);
  antwortet `--adresse` mit einer Weiterleitung, bricht es mit deren Ziel ab.
- **Ohne `--ausfuehren` ein Trockenlauf:** prüft Pflichtfelder und Längen lokal (Titel
  3–120 Zeichen in einer Zeile, Mittel Pflicht mit 10–500 wie im Formular, Kurz bis 280, Lang
  bis 2000, Aussage 10–1000, Herkunft mit http(s)-Link) und zeigt je Kommentar, was angelegt
  würde: Titel, Aussage, gefundene Fassungen mit Länge, Zweck/Stil und jede Herkunft; ohne
  Server und Passwort. Als „Hinweis“ meldet er, was übergangen wurde und vielleicht dazugehört:
  `###`-Kommentare unter einer nummerierten `##`-Überschrift, die keine erkannte Aussage ist,
  und Textzeilen im Kommentar, die zu keinem Feld gehören (Vermerke ab `geprüft:`,
  `Hinweis …:` und Trennlinien `---` ausgenommen). Hinweise ändern den Exit-Code nicht.
- Ist schon ein sehr ähnlicher Kommentar da, legt der Server nichts an; das Skript meldet ihn
  als übersprungen und übergeht die Dublettenprüfung nicht. Ist der vorhandene vom selben
  Konto und hat denselben Titel (ein früherer Lauf dieser Datei), hängt das Skript ihn an die
  Aussage, wie „den eigenen nehmen“ im Formular. Ein zweiter Lauf mit derselben Datei legt also
  nichts doppelt an und holt fehlende Verknüpfungen nach. Einen nur ähnlichen eigenen
  Kommentar (anderer Titel, etwa zu einer anderen Aussage) hängt es nicht um, es meldet ihn.
- Je angelegtem Kommentar nennt die Ausgabe seine ID und die der Aussage; hängt er an einer
  schon vorhandenen Aussage mit anderem Wortlaut, steht deren Text dabei.
- Der Dienst nimmt höchstens 10 Kommentare je Minute und 100 je Stunde und Konto an; bei
  einer Ablehnung wartet das Skript eine Minute und versucht es bis zu dreimal. Bleibt es
  dabei (Stundenlimit), endet der Lauf, die übrigen stehen als „nicht versucht“ im Bericht:
  nach einer Stunde mit derselben Datei erneut laufen lassen.
- Exit-Code 0: alles angelegt oder übersprungen; 1: mindestens ein Kommentar mit Fehler (in
  der Datei, vom Server abgelehnt, oder angelegt, aber nicht mit der Aussage verknüpft);
  2: Datei unlesbar, `--adresse` unpassend, Anmeldung gescheitert (auch: Sitzung abgelaufen),
  ohne Einwilligung, ohne Admin beim Entfernen oder Server nicht erreichbar.

**Dateiformat** (Beispiel: `scripts/manual/beitraege_beispiel.md`), UTF-8:

- `## 1.1 „Aussage“` (nummeriert und in Anführungszeichen, die entfernt werden) oder
  `## Aussage: …` beginnt eine Aussage. Andere Überschriften (`## Stand`, `## 9. Hinweise`),
  Einleitung und Fließtext zählen nicht.
- Jede `###`-Überschrift darunter beginnt einen Kommentar; `### Kommentar: <Titel>` setzt
  zugleich den Titel.
- Felder je Zeile, fett (`**Kurz:**` oder `**Kurz**:`) oder als Listenpunkt, Groß- und
  Kleinschreibung egal: `Titel:`,
  `Kurz:`, `Mittel:`, `Lang:`, `Herkunft:` (mehrfach; auch `Zweite Herkunft (…):`),
  optional `Zweck:` (`kommentarspalte`, `eigene_leute`) und `Stil:` (`sachlich`,
  `humorvoll`, `persoenlich`, `brueckenbauend`, `bissig`). Kurz, Mittel und Lang gehen auf
  den Folgezeilen weiter bis zur nächsten Leerzeile; jede Zeile bleibt eine eigene Zeile im
  Text (Zeilenumbruch, wie im Formular), also nicht von Hand umbrechen. Die Karte zeigt die
  Umbrüche derzeit nicht, der kopierte Text behält sie. `####`-Überschriften im Kommentar zählen
  nicht.
- Herkunft: `URL – Beschreibung` oder `URL | Beschreibung` (Link auch als `<URL>` oder
  `[Text](URL)`); ein Vermerk ab `geprüft:` und Zeilen darunter, die kein Feld sind, werden
  nicht übernommen. Eine Herkunft ohne Link ist ein Fehler (etwa „[Quelle fehlt]“), außer sie
  beginnt mit „keine“ (bewusst keine Herkunft).

## Beiträge endgültig entfernen (`beitraege_importieren.py --entfernen`)

Entfernt Beiträge endgültig über die Admin-API
(`DELETE /api/v1/moderation/content/{typ}/{id}`), mit einem Admin-Konto. Im Frontend gibt es
dafür keinen Knopf, nur das Sperren. Die Aussagen, auf die ein Beitrag antwortete, bleiben;
ihnen fehlt danach nur diese Antwort (ohne andere Antwort sind sie wieder unbeantwortet).
Stimmen und Varianten-Verknüpfungen des Beitrags gehen mit.

- Datei: je Zeile `<typ> <id>`, Typ `commentary`, `generic_text`, `post` oder `image`;
  Leerzeilen und alles ab `#` zählen nicht.
- Angemeldet wie beim Import, mit einem Admin-Konto; ohne Admin bricht es vor dem ersten
  Beitrag ab.
- Ohne `--ausfuehren` zeigt es je Beitrag Typ, ID und Titel; mit `--ausfuehren` steht der
  Titel ebenso beim entfernten Beitrag. Gesperrte Beiträge zeigt die Ansicht nicht, ihren
  Titel holt das Skript aus der Admin-Liste der gesperrten (`/api/v1/moderation/gesperrt`)
  und markiert sie „(gesperrt)“.
- Passt der Typ in der Liste nicht zum Beitrag (der Server nimmt den Typ nur fürs Log), bleibt
  der Beitrag stehen und wird als Fehler gemeldet.
- Was weder sichtbar noch gesperrt ist (schon entfernt, gelöscht oder nie
  da), wird nie entfernt, nur als übersprungen gemeldet. Die Ansicht `/api/v1/content/beitrag`
  gibt es ab v0.8.1; auf einem älteren Stand findet das Skript nichts und entfernt nichts.

**Usage:**
```bash
# Erst prüfen (ohne Server), dann mit der Sitzung des schreibenden Kontos anlegen.
# --adresse: der BFF-Host (hier Produktion; auf Test der BFF-Host des Testsystems).
python3 scripts/manual/beitraege_importieren.py bestand.md
python3 scripts/manual/beitraege_importieren.py bestand.md --sitzung-datei ~/sitzung.txt \
  --adresse https://bff.gutgesagt.netzbegruenung.de --ausfuehren
# Entfernen mit der Sitzung eines Admins: erst Titel ansehen, dann entfernen.
python3 scripts/manual/beitraege_importieren.py entfernen.txt --entfernen \
  --sitzung-datei ~/sitzung-admin.txt --adresse https://bff.gutgesagt.netzbegruenung.de
python3 scripts/manual/beitraege_importieren.py entfernen.txt --entfernen \
  --sitzung-datei ~/sitzung-admin.txt --adresse https://bff.gutgesagt.netzbegruenung.de --ausfuehren
rm ~/sitzung.txt ~/sitzung-admin.txt
# Lokaler Dev-Stack: Direktanmeldung
python3 scripts/manual/beitraege_importieren.py bestand.md --email test.user@example.com --ausfuehren
```

Getestet in `tests/unit/services/test_beitraege_importieren_skript.py` (Lesen, Import,
Entfernen) und `tests/integration/api/test_beitraege_importieren_bff.py` (gegen den
Dev-Stack, auch mit Sitzungs-Cookie; das Entfernen als Admin dort direkt am Suchdienst mit
den Admin-Kopfzeilen des BFF; auf einem Dev-Stack vor v0.8.1 übersprungen).

## Utility Scripts (`scripts/utils/`)

### clean-all
Complete environment cleanup:
- Stops and removes all Docker containers and volumes
- Removes Python virtual environment and cache
- Removes .NET build artifacts
- Removes node_modules and Angular cache
- **WARNING:** Destructive operation, requires reinstallation

### switch-to-docker / switch-to-local
Environment configuration helpers:
- Updates `environment.ts` for the appropriate mode
- Docker mode: Empty baseUrl (uses nginx proxy)
- Local mode: baseUrl points to localhost:5054

## Platform Notes

### Windows
- All scripts have `.bat` versions
- Use backslashes in paths: `scripts\dev\run-local.bat`
- PowerShell wrapper available for run-local

### Unix/Linux/Mac
- All scripts have `.sh` versions
- Make scripts executable: `chmod +x scripts/**/*.sh`
- Use forward slashes: `scripts/dev/run-local.sh`

### Cross-Platform Features
- Consistent behavior across platforms
- Color-coded output on Unix systems
- Proper error handling and exit codes
- Environment detection for Python venv

## Common Workflows

### First-Time Setup
```bash
# 1. Check your environment
scripts/setup/check-environment.bat

# 2. Install all dependencies
scripts/setup/install-dependencies.bat

# 3. Start development
scripts/dev/run-local.bat
```

### Daily Development
```bash
# Start local environment
scripts/dev/run-local.bat

# Or start Docker environment
scripts/dev/run-docker.bat
```

### Before Committing
```bash
# Run all tests
scripts/test/run-all-tests.bat
```

### Clean Restart
```bash
# 1. Clean everything
scripts/utils/clean-all.bat

# 2. Reinstall dependencies
scripts/setup/install-dependencies.bat

# 3. Start fresh
scripts/dev/run-local.bat
```

### Switching Environments
```bash
# Switch from local to Docker
scripts/utils/switch-to-docker.bat
scripts/dev/run-docker.bat

# Switch from Docker to local
scripts/utils/switch-to-local.bat
scripts/dev/run-local.bat
```

## Troubleshooting

### Port Conflicts
Run `scripts/setup/check-environment.bat` to identify conflicting services.

### Missing Dependencies
Run `scripts/setup/install-dependencies.bat` to install all requirements.

### Tests Failing
- Check individual test scripts for specific service tests
- Ensure all dependencies are installed
- Verify services are not running (for unit tests)

### Clean Start
If experiencing issues, run `scripts/utils/clean-all.bat` followed by `scripts/setup/install-dependencies.bat`.

## Script Conventions

- **Naming**: Hyphen-separated lowercase (e.g., `run-local.bat`)
- **Exit Codes**: 0 for success, non-zero for failure
- **Output**: Colored on Unix, clear status messages
- **Error Handling**: All scripts check for errors and provide helpful messages
- **Cross-Platform**: Every `.bat` has a corresponding `.sh`
