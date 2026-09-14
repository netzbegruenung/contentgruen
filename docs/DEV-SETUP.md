# Dev-Setup: `ng serve` gegen den Dev-Stack

1. Einmalig `cp mvp/config/managed-users.example.json mvp/config/managed-users.json` (gitignoriert; ohne Datei ist die Direktanmeldung aus).
2. Backend aus `mvp/` starten – Compose-Datei `docker-compose.dev.yml`, nur diese Container:
   `docker compose -f docker-compose.dev.yml up -d qdrant postgres-app contentgruen-semantic-search contentgruen-bff`
   Ports: BFF 5054, Semantic Search 8000, PostgreSQL 5433, Qdrant 6333.
   Der Frontend-Container (8080) wird dafür nicht gebraucht; `mvp/run-local.sh up` startet ihn trotzdem mit.
3. Frontend: `cd mvp/frontend/contentgruen-frontend && npm ci && npx ng serve`
   Fehlt `src/environments/environment.ts`, vorher `environment.local.ts` dorthin kopieren.
4. http://localhost:4200 → Anmelden → Direktanmeldung: `test.user@example.com` / `Liebe>Hass!`.
   `testuser` gilt nur für den alten Dummy-Endpunkt `POST /login`; ein Formular dafür hat die App nicht mehr.

Die App ruft das BFF relativ auf (`baseUrl: ''`). `ng serve` leitet `/api`, `/content`, `/recent`, `/getMetrics`,
`/report` und `/reports` per `proxy.conf.json` an http://localhost:5054 weiter – kein CORS, Cookies same-origin.
Ein älteres lokales `environment.ts` mit `baseUrl: 'http://localhost:5054'` auf `''` umstellen.
