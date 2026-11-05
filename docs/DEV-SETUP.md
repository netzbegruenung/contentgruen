# Dev-Setup: `ng serve` gegen den Dev-Stack

1. Einmalig `cp mvp/config/managed-users.example.json mvp/config/managed-users.json` (gitignoriert; ohne Datei ist die Direktanmeldung aus).
2. Backend aus `mvp/` starten – Compose-Datei `docker-compose.dev.yml`, nur diese Container:
   `docker compose -f docker-compose.dev.yml up -d qdrant postgres-app gutgesagt-semantic-search gutgesagt-bff`
   Ports: BFF 5054, Semantic Search 8000, PostgreSQL 5433, Qdrant 6333.
   Der Frontend-Container (8080) wird dafür nicht gebraucht; `mvp/run-local.sh up` startet ihn trotzdem mit.
3. Frontend: `cd mvp/frontend/gutgesagt-frontend && npm ci && npx ng serve`
   Fehlt `src/environments/environment.ts`, vorher `environment.local.ts` dorthin kopieren.
4. http://localhost:4200 → Anmelden → Direktanmeldung: `test.user@example.com` / `Liebe>Hass!`.

Die App ruft das BFF relativ auf (`baseUrl: ''`). `ng serve` leitet `/api`, `/content`, `/recent`, `/getMetrics`,
`/report` und `/reports` per `proxy.conf.json` an http://localhost:5054 weiter – kein CORS, Cookies same-origin.
Ein älteres lokales `environment.ts` mit `baseUrl: 'http://localhost:5054'` auf `''` umstellen.

## Dev-VM (Agenten-Sandbox): `mvp/run-local.sh`

Auf der Linux-Dev-VM läuft der ganze Stack in Docker Compose (`mvp/docker-compose.dev.yml`, Projekt
`gutgesagt-dev`) und wird über `mvp/run-local.sh` gesteuert: aus jedem Verzeichnis aufrufbar, nichts
im Vordergrund, Exit != 0 bei Fehler. Unterbefehle und Exit-Codes stehen im Kopf von
`mvp/scripts/dev/run-local.sh`.

- `reset` (etwa 30 s, Volumes bleiben) ist der Standard nach Code-Änderungen; `wipe` (etwa 2 min,
  `down -v`, Neubau und Seeding) nur bei Schema- oder Seed-Problemen.

- Ports: Frontend 8080, BFF 5054, Semantic Search 8000, Qdrant 6333/6334, PostgreSQL 5433.
  Rootless Docker kann keine Ports < 1024 binden, daher 8080 statt 80.
- VM-Voraussetzung (nicht im Repo): `docker buildx` >= 0.17 in `~/.docker/cli-plugins/`; das
  Debian-Paket 0.13 ist zu alt für Compose 2.40 und lässt jeden Build scheitern.
