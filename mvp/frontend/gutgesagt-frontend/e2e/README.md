# E2E-Tests (Playwright)

Prüfen die wichtigsten Szenarien am Handy gegen den laufenden Dev-Stack: Verfassen eines Kommentars und
einer Hintergrundinfo, „Antwort auf“ mit neuer Aussage, aus der Suche ergänzen, die Kette im
Fangkorb (Einwerfen, Destillieren, Ausformulieren, Nächster Einwurf), Speichern ohne Netz
sowie die Suche als Besucher (mit Umleitung zur Anmeldung auf geschützten Seiten und ohne
Umleitung bei einem 401 der Suche). Nicht in CI: Die Tests brauchen den vollen Stack.

## Starten

```bash
mvp/run-local.sh up          # Dev-Stack, Frontend auf http://127.0.0.1:8080
mvp/run-local.sh seed        # nur bei leerer content_collection (Suche braucht Daten)

cd mvp/frontend/gutgesagt-frontend/e2e
npm ci
npx playwright install chromium   # einmalig; entfällt, wenn der Browser schon im Cache liegt
npx playwright test
npx playwright show-report        # HTML-Report mit Screenshots und Traces der Fehlschläge
```

Einzelne Specs: `npx playwright test tests/04-fangkorb.spec.ts`, ein Projekt:
`--project=besucher`. Typprüfung: `../node_modules/.bin/tsc --noEmit -p .`
(nutzt das TypeScript des Frontends).

| Variable | Standard | Zweck |
|---|---|---|
| `E2E_BASE_URL` | `http://127.0.0.1:8080` | Gegen einen anderen Stand, z. B. `ng serve` mit Proxy |
| `E2E_EMAIL`, `E2E_PASSWORT` | Testkonto aus `mvp/config/managed-users.example.json` (`tests/konto.ts`) | Anmeldung über `/api/auth/login/managed` |
| `E2E_SCREENSHOTS` | `e2e/screenshots/` | Ablage der benannten Screenshots |

## Was man wissen muss

- **Daten:** Die Tests legen echte Einwürfe, Aussagen und Beiträge an, alle mit dem Präfix
  `[e2e-test]`. Sie bleiben im Dev-Stack liegen; `mvp/run-local.sh wipe` räumt auf.
- **Reihenfolge:** Ein Worker, nacheinander. Jede Spec legt ihre Daten selbst an, die
  Anmeldung (`anmelden.setup.ts`) läuft vorher einmal. Nacheinander, weil alle Specs mit
  demselben Testkonto am Rate-Limit hängen und `04-fangkorb` andere offene Einwürfe
  zurückstellt, auch solche, die eine parallele Spec gerade anlegt.
- **Rate-Limit:** Der Suchdienst erlaubt 10 Anlege-Anfragen pro Minute und 100 pro Stunde je
  Person; ein voller Lauf braucht 20 bis 30. Scheitert Speichern oder Einwerfen mit 429,
  warten die Helfer in `tests/fixtures.ts` eine Minute und versuchen es erneut (im Report als
  „Rate-Limit“ vermerkt). Nach drei, vier Läufen in einer Stunde hilft das nicht mehr;
  `mvp/run-local.sh reset` setzt den Zähler zurück (er liegt nur im Speicher).
- **Dubletten:** Ab dem zweiten Lauf gleicht ein neuer Kommentar dem aus dem Vorlauf. Die
  Specs wählen dann „Trotzdem speichern“ (`aufErgebnisWarten`) und vermerken das im Report.
- **Nächster Einwurf:** Die Reihenfolge kommt vom Server (eigene zuerst, dann die neuesten).
  Liegen im Fangkorb andere offene Einwürfe, stellt `04-fangkorb` sie mit „Später“ (ohne Satz,
  also ohne sie zu ändern) für die Runde zurück, bis die Runde im Fangkorb endet.
- **Bekannter Fehler:** `09-fangkorb-tabs` bei 320 px ist mit `test.fail` markiert (Tab-Namen
  gekürzt). Wird er behoben, meldet Playwright den Test als unerwartet bestanden.
- **Browser:** Playwright sucht Chromium unter `~/.cache/ms-playwright`; die Version in
  `package.json` muss zum installierten Browser passen.
