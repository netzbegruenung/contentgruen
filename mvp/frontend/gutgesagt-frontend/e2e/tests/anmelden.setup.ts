import { expect, test as setup } from '@playwright/test';
import { KONTO, SITZUNG } from './konto';

/**
 * Einmal anmelden (Direktanmeldung, docs/DEV-SETUP.md) und die Sitzung fuer alle
 * Tests speichern. Ueber den Ursprung der App (nginx bzw. ng-serve-Proxy leitet /api weiter),
 * damit das Sitzungs-Cookie dort gilt.
 */
setup('anmelden', async ({ page }) => {
  await page.goto('/search');
  const antwort = await page.request.post('/api/auth/login/managed', {
    data: { email: KONTO.email, password: KONTO.passwort },
  });
  expect(antwort.status()).toBe(200);
  expect((await page.request.get('/api/check-session')).status()).toBe(200);
  // Ohne Art.-9-Einwilligung fuehrt die App auf /einwilligung und sperrt Beitragen und
  // Bewerten (#489). Das Testkonto willigt einmal in den aktuellen Wortlaut ein.
  const stand = await page.request.get('/api/v1/art9-einwilligung');
  expect(stand.status()).toBe(200);
  const { aktueller_wortlaut } = await stand.json();
  expect(
    (await page.request.post('/api/v1/art9-einwilligung', { data: { wortlaut: aktueller_wortlaut.kennung } })).status(),
  ).toBe(204);
  await page.context().storageState({ path: SITZUNG });
});
