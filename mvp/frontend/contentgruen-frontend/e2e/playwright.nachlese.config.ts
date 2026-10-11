import { defineConfig, devices } from '@playwright/test';

/**
 * Nur fuer den Live-Check von PR A (feat/handy-nachlese) gegen den Dev-Server
 * aus dem Worktree cg-nachlese2 (Port 4210). Eigene Datei, damit die Wege in
 * ./tests davon unberuehrt bleiben.
 */
const BASE_URL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:4210';

export default defineConfig({
  testDir: './nachlese',
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  use: { baseURL: BASE_URL, screenshot: 'only-on-failure' },
  projects: [
    { name: 'setup', testMatch: /anmelden\.setup\.ts/ },
    {
      name: 'mobil-360',
      testIgnore: /anmelden\.setup\.ts/,
      dependencies: ['setup'],
      use: {
        ...devices['Pixel 5'],
        viewport: { width: 360, height: 740 },
        deviceScaleFactor: 3,
        storageState: '.auth/nachlese.json',
      },
    },
  ],
});
