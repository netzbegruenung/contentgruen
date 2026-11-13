import { defineConfig, devices } from '@playwright/test';
import { SITZUNG } from './tests/konto';

/**
 * End-to-End-Checks der Kernszenarien gegen den laufenden Dev-Stack (mvp/run-local.sh up).
 *
 * Nicht in CI: Die Tests brauchen den vollen Stack. Start siehe README.md in diesem Verzeichnis.
 * Testdaten beginnen mit TESTDATEN_PRAEFIX (tests/fixtures.ts).
 */
const BASE_URL = process.env['E2E_BASE_URL'] ?? 'http://127.0.0.1:8080';

export default defineConfig({
  testDir: './tests',
  // Nacheinander: Alle Specs teilen sich das Rate-Limit des Testkontos und den Fangkorb
  // (04 stellt andere offene Einwuerfe zurueck, auch solche, die eine parallele Spec anlegt).
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'setup', testMatch: /anmelden\.setup\.ts/ },
    {
      // Besucher: ohne Sitzung, ohne Abhaengigkeit vom Anmelden.
      name: 'besucher',
      testMatch: /besucher\.spec\.ts/,
      use: { ...devices['Pixel 5'], viewport: { width: 360, height: 740 } },
    },
    {
      // Ergebnisseite mit gemockter Suche (route.fulfill): ohne Sitzung, je 390 und 1280 px im Spec.
      name: 'ergebnisseite',
      testMatch: /12-ergebnisseite\.spec\.ts/,
    },
    {
      // Teilen (B7) mit gemocktem /api (route.fulfill): ohne Sitzung, je 390 und 1280 px im Spec.
      name: 'teilen',
      testMatch: /13-teilen\.spec\.ts/,
    },
    {
      name: 'mobil-360',
      testIgnore: /(stichproben|besucher|fangkorb-desktop|12-ergebnisseite|13-teilen)\.spec\.ts/,
      dependencies: ['setup'],
      use: {
        ...devices['Pixel 5'],
        viewport: { width: 360, height: 740 },
        deviceScaleFactor: 3,
        storageState: SITZUNG,
      },
    },
    {
      name: 'tablet-600',
      testMatch: /stichproben\.spec\.ts/,
      dependencies: ['setup'],
      use: { viewport: { width: 600, height: 900 }, deviceScaleFactor: 2, storageState: SITZUNG },
    },
    {
      name: 'desktop-960',
      testMatch: /stichproben\.spec\.ts/,
      dependencies: ['setup'],
      use: { viewport: { width: 960, height: 900 }, storageState: SITZUNG },
    },
    {
      // Fangkorb mit Seitenleiste (ab 1024 px), Beispieldaten im Browser: liest nur.
      name: 'desktop-1280',
      testMatch: /fangkorb-desktop\.spec\.ts/,
      dependencies: ['setup'],
      use: { viewport: { width: 1280, height: 900 }, storageState: SITZUNG },
    },
  ],
});
