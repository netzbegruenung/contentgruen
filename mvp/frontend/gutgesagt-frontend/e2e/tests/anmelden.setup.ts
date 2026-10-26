import { expect, test as setup } from '@playwright/test';

/**
 * Einmal anmelden (Direktanmeldung, docs/DEV-SETUP.md) und die Sitzung fuer alle
 * Tests speichern. Ueber den Ursprung der App (nginx bzw. ng-serve-Proxy leitet /api weiter),
 * damit das Sitzungs-Cookie dort gilt.
 */
setup('anmelden', async ({ page }) => {
  await page.goto('/search');
  const antwort = await page.request.post('/api/auth/login/managed', {
    data: {
      email: process.env.E2E_EMAIL ?? 'test.user@example.com',
      password: process.env.E2E_PASSWORT ?? 'Liebe>Hass!',
    },
  });
  expect(antwort.status()).toBe(200);
  expect((await page.request.get('/api/check-session')).status()).toBe(200);
  await page.context().storageState({ path: '.auth/sitzung.json' });
});
