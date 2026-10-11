import { expect, test as setup } from '@playwright/test';

setup('anmelden', async ({ page }) => {
  await page.goto('/search');
  const antwort = await page.request.post('/api/auth/login/managed', {
    data: { email: 'test.user@example.com', password: 'Liebe>Hass!' },
  });
  expect(antwort.status()).toBe(200);
  await page.context().storageState({ path: '.auth/nachlese.json' });
});
