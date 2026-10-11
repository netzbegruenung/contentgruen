import { defineConfig, devices } from '@playwright/test';

/**
 * End-to-End-Checks der Kernwege gegen den lokalen Dev-Stack.
 *
 * Nicht in CI: Die Tests brauchen den vollen Stack. Start siehe docs/DEV-SETUP.md.
 * Testdaten beginnen mit TESTDATEN_PRAEFIX (tests/fixtures.ts).
 */
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:4201';

export default defineConfig({
  testDir: './tests',
  // Die Wege legen Daten an und bauen aufeinander auf (Fangkorb): nacheinander.
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    screenshot: 'on',
    trace: 'on',
  },
  projects: [
    { name: 'setup', testMatch: /anmelden\.setup\.ts/ },
    {
      name: 'mobil-360',
      testIgnore: /stichproben\.spec\.ts/,
      dependencies: ['setup'],
      use: {
        ...devices['Pixel 5'],
        viewport: { width: 360, height: 740 },
        deviceScaleFactor: 3,
        storageState: '.auth/sitzung.json',
      },
    },
    {
      name: 'tablet-600',
      testMatch: /stichproben\.spec\.ts/,
      dependencies: ['setup'],
      use: { viewport: { width: 600, height: 900 }, deviceScaleFactor: 2, storageState: '.auth/sitzung.json' },
    },
    {
      name: 'desktop-960',
      testMatch: /stichproben\.spec\.ts/,
      dependencies: ['setup'],
      use: { viewport: { width: 960, height: 900 }, storageState: '.auth/sitzung.json' },
    },
  ],
});
