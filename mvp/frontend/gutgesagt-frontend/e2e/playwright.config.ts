import { defineConfig, devices } from '@playwright/test';

/**
 * End-to-End-Checks der Kernszenarien gegen den laufenden Dev-Stack (mvp/run-local.sh up).
 *
 * Nicht in CI: Die Tests brauchen den vollen Stack. Start siehe README.md in diesem Verzeichnis.
 * Testdaten beginnen mit TESTDATEN_PRAEFIX (tests/fixtures.ts).
 */
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:8080';
const SITZUNG = '.auth/sitzung.json';

export default defineConfig({
  testDir: './tests',
  // Die Szenarien legen Daten an und bauen aufeinander auf (Fangkorb): nacheinander.
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
      name: 'mobil-360',
      testIgnore: /(stichproben|besucher)\.spec\.ts/,
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
  ],
});
